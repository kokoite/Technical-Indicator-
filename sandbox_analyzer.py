import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from buy_sell_signal_analyzer import BuySellSignalAnalyzer

from stock_list_manager import stock_list_manager
from sandbox_extended_analyzer import ExtendedHistoryAnalyzer
from sandbox_database import sandbox_db
import time
import random
from typing import List, Dict, Optional, Any, Tuple

class SandboxAnalyzer:
    """
    Sandbox analyzer that creates a separate testing environment
    - Analyzes all NSE stocks using same technical indicators
    - Stores in separate sandbox database
    - Provides performance tracking like daily_monitor.py
    - Allows threshold testing without affecting main system
    """
    
    def __init__(self, use_extended_history: bool = False):
        """
        Initialize SandboxAnalyzer
        
        Args:
            use_extended_history: If True, uses ExtendedHistoryAnalyzer for more comprehensive analysis
        """
        self.sandbox_db = "sandbox_recommendations.db"
        self.analyzer = BuySellSignalAnalyzer()
        self.use_extended_history = use_extended_history
        self.extended_analyzer = ExtendedHistoryAnalyzer() if use_extended_history else None
        self.db = sandbox_db  # Use the singleton database manager
    

    
    def populate_friday_stocks_analysis(self, limit=None, force_refresh=False):
        """
        Populate the friday_stocks_analysis table with all stocks' Friday analysis
        This is done once and then queried by threshold
        """
        friday_date = self.get_last_friday_date()
        friday_date_str = friday_date.strftime('%Y-%m-%d')
        
        # Check if Friday analysis already exists
        if not force_refresh:
            existing_count = self.db.check_friday_analysis_exists(friday_date_str)
            if existing_count > 0:
                print(f"📋 Friday analysis already exists for {friday_date_str} ({existing_count} stocks)")
                return existing_count
        
        print(f"\n{'='*100}")
        print(f"📊 POPULATING FRIDAY STOCKS ANALYSIS TABLE")
        print(f"{'='*100}")
        print(f"📅 Friday Date: {friday_date_str}")
        print(f"🔄 Force Refresh: {force_refresh}")
        
        start_time = datetime.now()
        
        # Get stock list
        stock_symbols = self.get_nse_stock_list_from_api(limit)
        total_stocks = len(stock_symbols)
        
        print(f"📊 Analyzing {total_stocks} stocks for Friday analysis...")
        
        # Clear existing Friday data if force refresh
        if force_refresh:
            self.db.clear_friday_analysis_data(friday_date_str)
            print(f"🗑️  Cleared existing Friday data for {friday_date_str}")
        
        successful_analysis = 0
        processed = 0
        
        for symbol in stock_symbols:
            try:
                print(f"📊 {symbol:<12}", end=" ", flush=True)
                
                yahoo_symbol = f"{symbol}.NS"
                
                # Get proper Friday analysis using historical data clipping.
                friday_date_obj = datetime.combine(friday_date, datetime.min.time())
                analysis_results = self.analyze_stock_for_multiple_fridays(symbol, [friday_date_obj])
                
                if not analysis_results or friday_date_str not in analysis_results:
                    print("❌ Friday analysis failed")
                    continue
                
                friday_analysis = analysis_results[friday_date_str]
                friday_price = friday_analysis['price']
                
                # Get stock info for company details
                ticker = yf.Ticker(yahoo_symbol)
                info = ticker.info
                
                # Use the proper Friday analysis data
                record_data = {
                    'symbol': symbol,
                    'company_name': info.get('longName', symbol),
                    'friday_date': friday_date_str,
                    'friday_price': friday_price,
                    'total_score': friday_analysis['total_score'],
                    'recommendation': friday_analysis['recommendation'],
                    'risk_level': 'N/A',  # Not calculated in optimized method
                    'sector': info.get('sector', 'Unknown'),
                    'market_cap': info.get('marketCap', 0),
                    'trend_score': friday_analysis['scores']['trend'],
                    'momentum_score': friday_analysis['scores']['momentum'],
                    'rsi_score': friday_analysis['scores']['rsi'],
                    'volume_score': friday_analysis['scores']['volume'],
                    'price_action_score': friday_analysis['scores']['price'],
                    'ma_50': friday_analysis['indicators']['ma_50'],
                    'ma_200': friday_analysis['indicators']['ma_200'],
                    'rsi_value': friday_analysis['indicators']['rsi'],
                    'macd_value': friday_analysis['indicators']['macd'],
                    'macd_signal': friday_analysis['indicators']['macd_signal'],
                    'volume_ratio': friday_analysis['indicators']['volume_ratio'],
                    'price_change_1d': friday_analysis['indicators']['price_change_1d'],
                    'price_change_5d': friday_analysis['indicators']['price_change_5d'],
                    'trend_raw': friday_analysis['raw_scores']['trend'],
                    'momentum_raw': friday_analysis['raw_scores']['momentum'],
                    'rsi_raw': friday_analysis['raw_scores']['rsi'],
                    'volume_raw': friday_analysis['raw_scores']['volume'],
                    'price_raw': friday_analysis['raw_scores']['price']
                }
                
                # Insert into database using the database manager
                self.db.insert_friday_analysis_record(record_data)
                
                successful_analysis += 1
                print(f"✅ Score: {friday_analysis['total_score']:.1f} @ ₹{friday_price:.2f}")
                
                processed += 1
                if processed % 20 == 0:
                    progress = (processed / total_stocks) * 100
                    print(f"\n📊 Progress: {processed}/{total_stocks} ({progress:.1f}%) | Success: {successful_analysis}")
                
                # Optimized rate limiting (Yahoo Finance allows ~2000 requests/hour)
                time.sleep(random.uniform(0.02, 0.05))
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                continue
        
        duration_minutes = (datetime.now() - start_time).total_seconds() / 60
        
        print(f"\n✅ Friday analysis population completed!")
        print(f"📊 Successfully analyzed: {successful_analysis}/{total_stocks} stocks")
        print(f"⏰ Duration: {duration_minutes:.1f} minutes")
        print(f"💾 Data stored in friday_stocks_analysis table for {friday_date_str}")
    
    def analyze_stock_for_multiple_fridays(self, symbol, friday_dates):
        """
        Analyze a single stock for multiple Friday dates using historical data clipping.
        Uses the main BuySellSignalAnalyzer system for consistent scoring.
        Single API call approach: Fetch 2 years of data once, then analyze multiple Fridays.
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE')
            friday_dates: List of datetime objects representing Fridays to analyze
            
        Returns:
            dict: Analysis results for each Friday date, or empty dict if analysis fails
        """
        results = {}
        yahoo_symbol = f"{symbol}.NS"
        ticker = yf.Ticker(yahoo_symbol)
        
        try:
            # Get 2 years of historical data (single API call for all Friday analyses)
            full_data = ticker.history(period="2y")
            
            if full_data.empty:
                print(f"❌ No historical data for {symbol}")
                return {}
                
            for friday_date in sorted(friday_dates):
                try:
                    date_str = friday_date.strftime('%Y-%m-%d')
                    
                    # Filter data up to the Friday date (inclusive)
                    # Handle both datetime and date objects
                    if hasattr(friday_date, 'date'):
                        target_date = friday_date.date()
                    else:
                        target_date = friday_date
                    
                    historical_data = full_data[full_data.index.date <= target_date]
                    
                    if len(historical_data) < 200:  # Need at least 200 days for 200-DMA
                        print(f"⚠️  Insufficient data for {symbol} as of {date_str}")
                        continue
                        
                    # Use the new combined function that gives us both analysis and raw indicators
                    analysis_result = self.analyzer.calculate_overall_score_with_indicators(symbol, historical_data)
                    
                    if not analysis_result:
                        print(f"⚠️  Analysis failed for {symbol} as of {date_str}")
                        continue
                    
                    # Extract values from the combined result - no redundant calculations!
                    raw_indicators = analysis_result['raw_indicators']
                    friday_price = raw_indicators['friday_price']
                    ma_50 = raw_indicators['ma_50']
                    ma_200 = raw_indicators['ma_200']
                    rsi = raw_indicators['rsi']
                    macd_value = raw_indicators['macd']
                    macd_signal = raw_indicators['macd_signal']
                    volume_ratio = raw_indicators['volume_ratio']
                    price_change_1d = raw_indicators['price_change_1d']
                    price_change_5d = raw_indicators['price_change_5d']
                    
                    # Clean up recommendation text (remove emojis for database)
                    recommendation = analysis_result['recommendation'].replace('🟢 ', '').replace('🟡 ', '').replace('⚪ ', '').replace('🔴 ', '')
                    
                    # Store results using main system's analysis
                    results[date_str] = {
                        'symbol': symbol,
                        'date': date_str,
                        'price': friday_price,
                        'total_score': analysis_result['total_score'],
                        'recommendation': recommendation,
                        'risk_level': analysis_result['risk_level'],
                        'indicators': {
                            'ma_50': ma_50,
                            'ma_200': ma_200,
                            'rsi': rsi,
                            'macd': macd_value,
                            'macd_signal': macd_signal,
                            'volume_ratio': volume_ratio,
                            'price_change_1d': price_change_1d,
                            'price_change_5d': price_change_5d
                        },
                        'scores': {
                            'trend': analysis_result['breakdown']['trend']['weighted'],
                            'momentum': analysis_result['breakdown']['momentum']['weighted'],
                            'rsi': analysis_result['breakdown']['rsi']['weighted'],
                            'volume': analysis_result['breakdown']['volume']['weighted'],
                            'price': analysis_result['breakdown']['price']['weighted']
                        },
                        'raw_scores': {
                            'trend': analysis_result['breakdown']['trend']['raw'],
                            'momentum': analysis_result['breakdown']['momentum']['raw'],
                            'rsi': analysis_result['breakdown']['rsi']['raw'],
                            'volume': analysis_result['breakdown']['volume']['raw'],
                            'price': analysis_result['breakdown']['price']['raw']
                        }
                    }
                    
                except Exception as e:
                    print(f"⚠️ Error processing {symbol} for {date_str}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error fetching data for {symbol}: {str(e)}")
            
        return results

    def get_nse_stock_list_from_api(self, limit: Optional[int] = None, force_refresh: bool = False) -> List[str]:
        """
        Get list of NSE stocks using StockListManager and apply an optional limit.
        
        Args:
            limit: Optional number of stocks to return
            force_refresh: If True, forces refresh of stock list
            
        Returns:
            List of stock symbols
        """
        try:
            stocks = stock_list_manager.get_stock_list(force_refresh=force_refresh)
            if limit:
                return stocks[:limit]
            return stocks
        except Exception as e:
            print(f"❌ Error getting NSE stock list: {e}")
            return self._get_basic_stock_list()
            
    def _get_basic_stock_list(self):
        """Basic fallback stock list"""
        return ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK']
    
    def get_last_friday_date(self):
        """Get last Friday's date - works for any day of the week"""
        return self.get_nth_last_friday(1)
    
    def get_nth_last_friday(self, n=1):
        """
        Get the nth last Friday's date (1=last Friday, 2=2nd last Friday, etc.)
        Dynamic Friday selection for backtesting
        """
        from datetime import datetime, timedelta
        
        today = datetime.now()
        current_weekday = today.weekday()  # Monday=0, Tuesday=1, ..., Friday=4, Saturday=5, Sunday=6
        
        # Calculate days back to last Friday
        if current_weekday == 4:  # Today is Friday
            # If it's Friday but market hasn't closed yet, use last Friday
            if today.hour < 15:  # Market closes at 3:30 PM IST, so before 3 PM use last Friday
                days_back = 7
            else:
                days_back = 0  # Use today (current Friday)
        elif current_weekday < 4:  # Monday(0), Tuesday(1), Wednesday(2), Thursday(3)
            days_back = current_weekday + 3  # Mon=3, Tue=2, Wed=1, Thu=0 days back to last Friday
        else:  # Saturday(5), Sunday(6)
            days_back = current_weekday - 4  # Sat=1, Sun=2 days back to last Friday
        
        # Add additional weeks for nth last Friday
        days_back += (n - 1) * 7
        
        nth_last_friday = today - timedelta(days=days_back)
        return nth_last_friday.date()
    
    def get_friday_sequence(self, start_friday_n, periods=4):
        """
        Get a sequence of Friday dates for backtesting
        start_friday_n: which Friday to start from (1=last, 2=2nd last, etc.)
        periods: how many consecutive Fridays to include
        
        Returns list of (friday_date, period_name) tuples in chronological order (oldest first)
        """
        fridays = []
        
        # Generate Friday dates from oldest to newest
        for i in range(periods):
            # Calculate which Friday: if start_friday_n=4 and periods=4, we want 4th, 3rd, 2nd, 1st
            friday_n = start_friday_n - i
            friday_date = self.get_nth_last_friday(friday_n)
            
            if friday_n == 1:
                period_name = "Last Friday"
            elif friday_n == 2:
                period_name = "2nd Last Friday"
            elif friday_n == 3:
                period_name = "3rd Last Friday"
            elif friday_n == 4:
                period_name = "4th Last Friday"
            else:
                period_name = f"{friday_n}th Last Friday"
            
            fridays.append((friday_date, period_name))
        
        return fridays
    
    def analyze_stocks_as_of_friday(self, threshold=67, limit=None):
        """
        Step 1: Find stocks that were STRONG as of last Friday
        Uses friday_stocks_analysis table for efficiency
        """
        print(f"📅 STEP 1: Finding stocks that were STRONG as of last Friday")
        
        friday_date = self.get_last_friday_date()
        print(f"🗓️  Reference Date: {friday_date.strftime('%Y-%m-%d %A')}")
        
        # Check if Friday analysis table is populated
        friday_date_str = friday_date.strftime('%Y-%m-%d')
        existing_count = self.db.check_friday_analysis_exists(friday_date_str)
        
        if existing_count == 0:
            print(f"📊 Friday analysis table is empty. Populating it first...")
            self.populate_friday_stocks_analysis(limit=limit)
        else:
            print(f"📋 Using existing Friday analysis data ({existing_count} stocks)")
        
        # Get STRONG stocks from table
        friday_strong_stocks = self.get_friday_strong_stocks_from_table_by_date(friday_date_str, threshold, limit)
        
        if friday_strong_stocks:
            print(f"\n✅ Step 1 Complete: Found {len(friday_strong_stocks)} STRONG stocks as of Friday")
            
            # Show summary
            print(f"📊 Top 10 Friday STRONG stocks:")
            for i, stock in enumerate(friday_strong_stocks[:10], 1):
                print(f"   {i:2d}. {stock['symbol']:<12} Score: {stock['friday_score']:5.1f} Price: ₹{stock['friday_price']:7.2f} Sector: {stock['sector']}")
        else:
            print(f"\n❌ No STRONG stocks found with threshold {threshold}")
        
        return friday_strong_stocks
    
    def reanalyze_friday_picks_with_today_data(self, friday_strong_stocks):
        """
        Step 2: Re-analyze Friday's STRONG picks using today's data
        This shows how they're performing now
        """
        print(f"\n📅 STEP 2: Re-analyzing Friday's STRONG picks with today's data")
        print(f"🔄 Re-analyzing {len(friday_strong_stocks)} stocks...")
        
        today_analysis = []
        
        for stock_data in friday_strong_stocks:
            symbol = stock_data['symbol']
            try:
                print(f"🔍 {symbol:<12}", end=" ", flush=True)
                
                yahoo_symbol = f"{symbol}.NS"
                
                # Get current price and analysis
                ticker = yf.Ticker(yahoo_symbol)
                current_hist = ticker.history(period="1d")
                
                if current_hist.empty:
                    print("❌ No current data")
                    continue
                
                current_price = current_hist['Close'].iloc[-1]
                
                # Get today's technical analysis
                today_analysis_result = self.analyzer.calculate_overall_score_silent(yahoo_symbol)
                
                if today_analysis_result:
                    # Calculate performance since Friday
                    friday_price = stock_data['friday_price']
                    price_change_pct = ((current_price - friday_price) / friday_price * 100) if friday_price > 0 else 0
                    
                    # Determine current tier
                    today_score = today_analysis_result['total_score']
                    if today_score >= 67:
                        today_tier = 'STRONG'
                    elif today_score >= 50:
                        today_tier = 'WEAK'  
                    else:
                        today_tier = 'HOLD'
                    
                    combined_data = {
                        **stock_data,  # Friday data
                        'current_price': current_price,
                        'current_score': today_score,
                        'current_recommendation': today_analysis_result['recommendation'],
                        'current_tier': today_tier,
                        'current_analysis': today_analysis_result,
                        'price_change_pct': price_change_pct,
                        'price_change_amount': current_price - friday_price,
                        'score_change': today_score - stock_data['friday_score'],
                        'status_change': f"STRONG→{today_tier}" if today_tier != 'STRONG' else 'STRONG→STRONG'
                    }
                    
                    today_analysis.append(combined_data)
                    
                    # Status indicators
                    price_emoji = "📈" if price_change_pct > 0 else "📉" if price_change_pct < 0 else "➖"
                    tier_emoji = "🟢" if today_tier == 'STRONG' else "🟡" if today_tier == 'WEAK' else "⚪"
                    
                    print(f"✅ {today_score:.1f} {tier_emoji} {today_tier} | {price_emoji}{price_change_pct:+.2f}% (₹{friday_price:.2f}→₹{current_price:.2f})")
                else:
                    print("❌ Analysis failed")
                
                # Optimized rate limiting
                time.sleep(random.uniform(0.02, 0.05))
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                continue
        
        print(f"\n✅ Step 2 Complete: Re-analyzed {len(today_analysis)} stocks")
        return today_analysis
    
    def run_friday_to_today_analysis(self, threshold=67, limit=None):
        """
        Complete two-step process:
        1. Find Friday STRONG stocks
        2. Re-analyze them with today's data
        """
        print(f"\n{'='*100}")
        print(f"🎯 FRIDAY-TO-TODAY ANALYSIS SYSTEM")
        print(f"{'='*100}")
        print(f"📊 Threshold: {threshold} | Limit: {limit or 'All stocks'}")
        
        start_time = datetime.now()
        
        # Clear previous data
        self.clear_sandbox_data()
        
        # Step 1: Find Friday STRONG stocks
        friday_strong_stocks = self.analyze_stocks_as_of_friday(threshold, limit)
        
        if not friday_strong_stocks:
            print("❌ No STRONG stocks found as of Friday")
            return []
        
        # Step 2: Re-analyze with today's data
        final_analysis = self.reanalyze_friday_picks_with_today_data(friday_strong_stocks)
        
        if final_analysis:
            # Save to database
            self.save_friday_to_today_results(final_analysis, threshold, start_time)
            
            # Generate comprehensive report
            self.generate_friday_to_today_report(final_analysis, threshold, start_time)
        
        return final_analysis

    def get_last_friday_price(self, yahoo_symbol):
        """Get the closing price from last Friday"""
        try:
            from datetime import datetime, timedelta
            
            # Use the same logic as get_last_friday_date
            last_friday_date = self.get_last_friday_date()
            last_friday = datetime.combine(last_friday_date, datetime.min.time())
            
            # Get historical data from last Friday
            ticker = yf.Ticker(yahoo_symbol)
            # Get data for a week to ensure we catch the Friday
            hist = ticker.history(start=last_friday - timedelta(days=7), end=last_friday + timedelta(days=1))
            
            if not hist.empty:
                # Get the last available price (should be Friday or closest trading day)
                return hist['Close'].iloc[-1]
            else:
                return 0
                
        except Exception as e:
            print(f"⚠️ Error getting Friday price for {yahoo_symbol}: {str(e)}")
            return 0


    
    def analyze_specific_stocks(self, stock_list, threshold=67):
        """Analyze specific stocks only - for quick testing"""
        print(f"🔬 Analyzing {len(stock_list)} specific stocks with corrected Friday prices")
        
        results = []
        
        for symbol in stock_list:
            try:
                print(f"🔍 {symbol:<12}", end=" ", flush=True)
                
                # Analyze using the same technical indicators as main system
                yahoo_symbol = f"{symbol}.NS"
                analysis_result = self.analyzer.calculate_overall_score_silent(yahoo_symbol)
                
                if analysis_result:
                    # Get stock info
                    ticker = yf.Ticker(yahoo_symbol)
                    info = ticker.info
                    hist = ticker.history(period="1d")
                    
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        
                        # Get Friday price (last Friday's closing price)
                        friday_price = self.get_last_friday_price(yahoo_symbol)
                        if friday_price == 0:  # Fallback to current price if Friday price not available
                            friday_price = current_price
                        
                        # Create stock info
                        stock_info = {
                            'symbol': symbol,
                            'company_name': info.get('longName', symbol),
                            'current_price': current_price,
                            'friday_price': friday_price,
                            'market_cap': info.get('marketCap', 0),
                            'sector': info.get('sector', 'Unknown')
                        }
                        
                        # Classify by tier using threshold
                        score = analysis_result['total_score']
                        if score >= threshold:
                            tier = 'STRONG'
                        elif score >= 50:
                            tier = 'WEAK'
                        else:
                            tier = 'HOLD'
                        
                        # Add to results
                        analysis_result['symbol'] = symbol
                        analysis_result['stock_info'] = stock_info
                        analysis_result['recommendation_tier'] = tier
                        analysis_result['friday_price'] = friday_price  # Use actual Friday price
                        results.append(analysis_result)
                        
                        # Show price difference
                        price_change = ((current_price - friday_price) / friday_price * 100) if friday_price > 0 else 0
                        tier_emoji = "🟢" if tier == "STRONG" else "🟡" if tier == "WEAK" else "⚪"
                        print(f"✅ {score:5.1f} {tier_emoji} {tier} | Fri: ₹{friday_price:.2f} → Cur: ₹{current_price:.2f} ({price_change:+.2f}%)")
                    else:
                        print("❌ No price data")
                else:
                    print("❌ Analysis failed")
                    
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                continue
        
        return results

    def analyze_stocks_directly(self, threshold=67, limit=None):
        """
        Directly analyze stocks using technical indicators (bypassing broken database dependencies)
        This is the REAL solution - analyze stocks directly!
        """
        print(f"🔬 Analyzing stocks directly using technical indicators")
        
        # Get stock list from NSE API
        stock_symbols = self.get_nse_stock_list_from_api(limit)
        total_stocks = len(stock_symbols)
        
        print(f"📊 Analyzing {total_stocks} stocks with threshold {threshold}")
        
        results = []
        processed = 0
        
        for symbol in stock_symbols:
            try:
                print(f"🔍 {symbol:<12}", end=" ", flush=True)
                
                # Analyze using the same technical indicators as main system
                yahoo_symbol = f"{symbol}.NS"
                analysis_result = self.analyzer.calculate_overall_score_silent(yahoo_symbol)
                
                if analysis_result:
                    # Get stock info
                    ticker = yf.Ticker(yahoo_symbol)
                    info = ticker.info
                    hist = ticker.history(period="1d")
                    
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        
                        # Get Friday price (last Friday's closing price)
                        friday_price = self.get_last_friday_price(yahoo_symbol)
                        if friday_price == 0:  # Fallback to current price if Friday price not available
                            friday_price = current_price
                        
                        # Create stock info
                        stock_info = {
                            'symbol': symbol,
                            'company_name': info.get('longName', symbol),
                            'current_price': current_price,
                            'friday_price': friday_price,
                            'market_cap': info.get('marketCap', 0),
                            'sector': info.get('sector', 'Unknown')
                        }
                        
                        # Classify by tier using threshold
                        score = analysis_result['total_score']
                        if score >= threshold:
                            tier = 'STRONG'
                        elif score >= 50:
                            tier = 'WEAK'
                        else:
                            tier = 'HOLD'
                        
                        # Add to results
                        analysis_result['symbol'] = symbol
                        analysis_result['stock_info'] = stock_info
                        analysis_result['recommendation_tier'] = tier
                        analysis_result['friday_price'] = friday_price  # Use actual Friday price
                        results.append(analysis_result)
                        
                        tier_emoji = "🟢" if tier == "STRONG" else "🟡" if tier == "WEAK" else "⚪"
                        print(f"✅ {score:5.1f} {tier_emoji} {tier}")
                    else:
                        print("❌ No price data")
                else:
                    print("❌ Analysis failed")
                
                processed += 1
                
                # Progress update every 10 stocks
                if processed % 10 == 0:
                    progress = (processed / total_stocks) * 100
                    strong_count = len([r for r in results if r['recommendation_tier'] == 'STRONG'])
                    print(f"\n📊 Progress: {processed}/{total_stocks} ({progress:.1f}%) | STRONG: {strong_count}")
                
                # Optimized rate limiting
                time.sleep(random.uniform(0.02, 0.05))
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        
        print(f"\n✅ Analysis completed: {len(results)} stocks analyzed")
        return results
    

    
    def run_full_sandbox_analysis(self, threshold=67, limit=None, batch_size=20):
        """Run complete analysis using WeeklyAnalysisSystem (same as main system)"""
        print(f"\n{'='*100}")
        print(f"🧪 SANDBOX ANALYSIS SYSTEM")
        print(f"{'='*100}")
        print(f"🎯 Threshold: {threshold} | Database: {self.sandbox_db}")
        print(f"🔬 Using same WeeklyAnalysisSystem as main system")
        
        start_time = datetime.now()
        
        # Clear previous sandbox data for this threshold
        self.clear_sandbox_data()
        
        # Analyze stocks directly using technical indicators (REAL SOLUTION)
        print(f"📊 Analyzing stocks directly using same technical indicators...")
        all_results = self.analyze_stocks_directly(threshold, limit)
        
        if not all_results:
            print("❌ No results from analysis")
            return []
        
        # Save all results to sandbox database
        self.save_sandbox_results(all_results, threshold, start_time)
        
        # Generate summary report
        self.generate_sandbox_summary(all_results, threshold, start_time)
        
        return all_results
    
    def clear_sandbox_data(self):
        """Clear previous sandbox data"""
        self.db.clear_sandbox_data()
    
    def save_sandbox_results(self, results, threshold, start_time):
        """Save analysis results to sandbox database"""
        self.db.save_sandbox_results(results, threshold, start_time)
    
    def save_friday_to_today_results(self, results, threshold, start_time):
        """Save Friday-to-today analysis results to sandbox database"""
        self.db.save_friday_to_today_results(results, threshold, start_time)
    
    def generate_friday_to_today_report(self, results, threshold, start_time):
        """Generate comprehensive Friday-to-today analysis report"""
        duration_minutes = (datetime.now() - start_time).total_seconds() / 60
        friday_date = self.get_last_friday_date()
        
        print(f"\n{'='*100}")
        print(f"📊 FRIDAY-TO-TODAY ANALYSIS REPORT")
        print(f"{'='*100}")
        print(f"📅 Friday Reference: {friday_date.strftime('%Y-%m-%d %A')}")
        print(f"📅 Today's Analysis: {datetime.now().strftime('%Y-%m-%d %A')}")
        print(f"🎯 Threshold Used: {threshold}")
        print(f"⏰ Analysis Duration: {duration_minutes:.1f} minutes")
        print(f"📈 Total Stocks Analyzed: {len(results)}")
        
        # Performance Summary
        total_invested = sum(r['friday_price'] for r in results)
        total_current_value = sum(r['current_price'] for r in results)
        total_pnl = total_current_value - total_invested
        total_return_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        print(f"\n💰 PORTFOLIO PERFORMANCE (Friday STRONG picks):")
        print(f"{'='*60}")
        print(f"💵 Friday Investment:  ₹{total_invested:>12,.2f}")
        print(f"💰 Current Value:      ₹{total_current_value:>12,.2f}")
        
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        return_emoji = "🟢" if total_return_pct >= 0 else "🔴"
        
        print(f"{pnl_emoji} Total P&L:         ₹{total_pnl:>+12,.2f}")
        print(f"{return_emoji} Total Return:      {total_return_pct:>+11.2f}%")
        
        # Tier Transitions
        tier_transitions = {}
        for r in results:
            transition = r['status_change']
            tier_transitions[transition] = tier_transitions.get(transition, 0) + 1
        
        print(f"\n🔄 RECOMMENDATION TIER CHANGES:")
        print(f"{'='*50}")
        for transition, count in sorted(tier_transitions.items()):
            emoji = "🟢" if "STRONG→STRONG" in transition else "🟡" if "WEAK" in transition else "⚪"
            print(f"   {emoji} {transition:<15} {count:2d} stocks")
        
        # Top Performers
        sorted_by_performance = sorted(results, key=lambda x: x['price_change_pct'], reverse=True)
        
        print(f"\n🏆 TOP 10 PERFORMERS (Friday STRONG picks):")
        print(f"{'='*90}")
        print(f"{'Stock':<12} {'Fri Score':<9} {'Today Score':<11} {'Price Change':<12} {'Status':<15} {'Tier Change'}")
        print(f"{'-'*90}")
        
        for i, stock in enumerate(sorted_by_performance[:10], 1):
            price_emoji = "📈" if stock['price_change_pct'] > 0 else "📉" if stock['price_change_pct'] < 0 else "➖"
            tier_emoji = "🟢" if stock['current_tier'] == 'STRONG' else "🟡" if stock['current_tier'] == 'WEAK' else "⚪"
            
            print(f"{stock['symbol']:<12} "
                  f"{stock['friday_score']:<9.1f} "
                  f"{stock['current_score']:<11.1f} "
                  f"{price_emoji}{stock['price_change_pct']:>+8.2f}% "
                  f"{tier_emoji}{stock['current_tier']:<10} "
                  f"{stock['status_change']}")
        
        # Sector Analysis
        sector_performance = {}
        for stock in results:
            sector = stock['sector']
            if sector not in sector_performance:
                sector_performance[sector] = {'total_return': 0, 'count': 0, 'stocks': []}
            sector_performance[sector]['total_return'] += stock['price_change_pct']
            sector_performance[sector]['count'] += 1
            sector_performance[sector]['stocks'].append(stock['symbol'])
        
        print(f"\n🏭 SECTOR PERFORMANCE:")
        print(f"{'='*60}")
        for sector, data in sorted(sector_performance.items(), key=lambda x: x[1]['total_return']/x[1]['count'], reverse=True):
            avg_return = data['total_return'] / data['count']
            sector_emoji = "🟢" if avg_return > 0 else "🔴"
            print(f"{sector_emoji} {sector:<25} {avg_return:>+6.2f}% ({data['count']} stocks)")
        
        # Summary Statistics
        winners = [s for s in results if s['price_change_pct'] > 0]
        losers = [s for s in results if s['price_change_pct'] < 0]
        
        print(f"\n📊 SUMMARY STATISTICS:")
        print(f"{'='*40}")
        print(f"🟢 Winners:     {len(winners):2d} stocks ({len(winners)/len(results)*100:.1f}%)")
        print(f"🔴 Losers:      {len(losers):2d} stocks ({len(losers)/len(results)*100:.1f}%)")
        print(f"📊 Win Rate:    {len(winners)/len(results)*100:.1f}%")
        
        if winners:
            best = max(winners, key=lambda x: x['price_change_pct'])
            print(f"🏆 Best:        {best['symbol']} ({best['price_change_pct']:+.2f}%)")
        
        if losers:
            worst = min(losers, key=lambda x: x['price_change_pct'])
            print(f"⚠️  Worst:       {worst['symbol']} ({worst['price_change_pct']:+.2f}%)")
        
        print(f"\n✅ Friday-to-today analysis completed! Database: {self.sandbox_db}")
    
    def calculate_levels(self, current_price, recommendation, score):
        """Calculate target and stop loss (same logic as main system)"""
        if current_price <= 0:
            return None, None
            
        if "BUY" in recommendation:
            if score >= 75:  # Strong Buy
                target_pct = 0.25  # 25% target
                stop_pct = 0.05   # 5% stop loss
            elif score >= 60:  # Buy
                target_pct = 0.20  # 20% target
                stop_pct = 0.06   # 6% stop loss
            else:  # Weak Buy
                target_pct = 0.15  # 15% target
                stop_pct = 0.07   # 7% stop loss
            
            target_price = current_price * (1 + target_pct)
            stop_loss = current_price * (1 - stop_pct)
            
        elif "SELL" in recommendation:
            target_price = current_price * 0.85  # 15% downside target
            stop_loss = current_price * 1.05     # 5% upside stop loss
            
        else:  # HOLD
            target_price = current_price * 1.10  # 10% upside
            stop_loss = current_price * 0.90     # 10% downside
        
        return round(target_price, 2), round(stop_loss, 2)
    
    def create_reason_summary(self, breakdown, score):
        """Create reason summary from breakdown"""
        reasons = []
        
        # Top contributing factors
        for category, data in breakdown.items():
            if data['weighted'] > 5:
                reasons.append(f"{category.title()}: +{data['weighted']:.1f}")
            elif data['weighted'] < -3:
                reasons.append(f"{category.title()}: {data['weighted']:.1f}")
        
        if not reasons:
            reasons.append(f"Mixed signals (Score: {score:.1f})")
        
        return "; ".join(reasons[:3])  # Top 3 reasons
    
    def generate_sandbox_summary(self, results, threshold, start_time):
        """Generate comprehensive summary report"""
        duration_minutes = (datetime.now() - start_time).total_seconds() / 60
        
        print(f"\n{'='*100}")
        print(f"📊 SANDBOX ANALYSIS SUMMARY")
        print(f"{'='*100}")
        print(f"🎯 Threshold Used: {threshold}")
        print(f"⏰ Analysis Duration: {duration_minutes:.1f} minutes")
        print(f"📈 Total Stocks Analyzed: {len(results)}")
        
        # Count by tier
        strong_stocks = [r for r in results if r['recommendation_tier'] == 'STRONG']
        weak_stocks = [r for r in results if r['recommendation_tier'] == 'WEAK']
        hold_stocks = [r for r in results if r['recommendation_tier'] == 'HOLD']
        
        print(f"\n📋 RECOMMENDATIONS BY TIER:")
        print(f"   🟢 STRONG: {len(strong_stocks)} stocks")
        print(f"   🟡 WEAK:   {len(weak_stocks)} stocks")
        print(f"   ⚪ HOLD:   {len(hold_stocks)} stocks")
        
        # Show top STRONG recommendations
        if strong_stocks:
            print(f"\n🏆 TOP 10 STRONG RECOMMENDATIONS:")
            strong_sorted = sorted(strong_stocks, key=lambda x: x['total_score'], reverse=True)[:10]
            
            for i, stock in enumerate(strong_sorted, 1):
                # Get price from the correct location
                price = stock.get('friday_price', stock['stock_info'].get('current_price', 0))
                sector = stock['stock_info'].get('sector', 'Unknown')
                print(f"   {i:2d}. {stock['symbol']:<12} Score: {stock['total_score']:5.1f} "
                      f"Price: ₹{price:7.2f} Sector: {sector}")
        
        # Sector analysis
        if results:
            print(f"\n🏭 SECTOR ANALYSIS (STRONG recommendations):")
            if strong_stocks:
                sector_counts = {}
                for stock in strong_stocks:
                    sector = stock['stock_info']['sector']
                    sector_counts[sector] = sector_counts.get(sector, 0) + 1
                
                for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"   📊 {sector:<25} {count:2d} stocks")
        
        print(f"\n✅ Sandbox analysis completed! Database: {self.sandbox_db}")
    
    def get_sandbox_strong_performance(self):
        """Get current performance of STRONG recommendations (like daily_monitor.py)"""
        conn = sqlite3.connect(self.sandbox_db)
        
        # Get STRONG recommendations
        query = '''
            SELECT id, symbol, company_name, friday_price, sector, score
            FROM sandbox_recommendations 
            WHERE recommendation_tier = 'STRONG' 
            AND status = 'ACTIVE' 
            AND is_sold = 0
            ORDER BY score DESC
        '''
        
        strong_recs = pd.read_sql_query(query, conn)
        conn.close()
        
        if strong_recs.empty:
            return None
        
        performance_data = []
        total_invested = 0
        total_current_value = 0
        
        print(f"📊 Updating performance for {len(strong_recs)} STRONG recommendations...")
        
        for _, rec in strong_recs.iterrows():
            symbol = rec['symbol']
            friday_price = rec['friday_price']
            
            try:
                # Get current price
                ticker = yf.Ticker(f"{symbol}.NS")
                current_data = ticker.history(period="2d")
                
                if not current_data.empty:
                    current_price = current_data['Close'].iloc[-1]
                    price_change_pct = ((current_price - friday_price) / friday_price) * 100
                    money_change = current_price - friday_price
                    
                    # Calculate day change if possible
                    day_change_pct = 0
                    if len(current_data) >= 2:
                        yesterday_close = current_data['Close'].iloc[-2]
                        day_change_pct = ((current_price - yesterday_close) / yesterday_close) * 100
                    
                    performance_data.append({
                        'symbol': symbol,
                        'company_name': rec['company_name'],
                        'friday_price': friday_price,
                        'current_price': current_price,
                        'change_pct': price_change_pct,
                        'money_change': money_change,
                        'day_change_pct': day_change_pct,
                        'sector': rec['sector'],
                        'score': rec['score']
                    })
                    
                    # Portfolio calculation (assuming 1 share each)
                    total_invested += friday_price
                    total_current_value += current_price
                
                time.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                print(f"❌ Error getting price for {symbol}: {str(e)}")
        
        if performance_data:
            total_pnl = total_current_value - total_invested
            total_return_pct = (total_pnl / total_invested) * 100
            
            return {
                'stocks': performance_data,
                'total_invested': total_invested,
                'total_current_value': total_current_value,
                'total_pnl': total_pnl,
                'total_return_pct': total_return_pct,
                'count': len(performance_data)
            }
        
        return None
    
    def show_sandbox_performance_report(self):
        """Show detailed performance report (like daily_monitor.py)"""
        print(f"\n{'='*100}")
        print(f"💰 SANDBOX STRONG RECOMMENDATIONS PERFORMANCE")
        print(f"{'='*100}")
        print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🧪 Database: {self.sandbox_db}")
        
        performance = self.get_sandbox_strong_performance()
        
        if not performance:
            print("📝 No STRONG recommendations found in sandbox")
            return
        
        # Portfolio Summary
        print(f"\n📊 PORTFOLIO SUMMARY ({performance['count']} stocks):")
        print(f"{'='*70}")
        print(f"💵 Total Invested:  ₹{performance['total_invested']:>12,.2f}")
        print(f"💰 Current Value:   ₹{performance['total_current_value']:>12,.2f}")
        
        pnl_emoji = "📈" if performance['total_pnl'] >= 0 else "📉"
        return_emoji = "🟢" if performance['total_return_pct'] >= 0 else "🔴"
        
        print(f"{pnl_emoji} Total P&L:      ₹{performance['total_pnl']:>+12,.2f}")
        print(f"{return_emoji} Total Return:   {performance['total_return_pct']:>+11.2f}%")
        
        # Individual Stock Performance
        print(f"\n📋 INDIVIDUAL STOCK PERFORMANCE:")
        print(f"{'='*110}")
        print(f"{'Stock':<12} {'Score':<6} {'Friday':<10} {'Current':<10} {'Total %':<10} {'Day %':<8} {'P&L (₹)':<10} {'Status'}")
        print(f"{'-'*110}")
        
        # Sort by performance
        sorted_stocks = sorted(performance['stocks'], key=lambda x: x['change_pct'], reverse=True)
        
        for stock in sorted_stocks:
            emoji = "🟢" if stock['change_pct'] >= 0 else "🔴"
            status = "Profit" if stock['change_pct'] >= 0 else "Loss"
            
            # Day change emoji
            day_emoji = "📈" if stock['day_change_pct'] > 0 else "📉" if stock['day_change_pct'] < 0 else "➖"
            
            print(f"{stock['symbol']:<12} "
                  f"{stock['score']:<6.1f} "
                  f"₹{stock['friday_price']:<9.2f} "
                  f"₹{stock['current_price']:<9.2f} "
                  f"{stock['change_pct']:>+8.2f}% "
                  f"{day_emoji}{stock['day_change_pct']:>+6.2f}% "
                  f"₹{stock['money_change']:>+8.2f} "
                  f"{emoji} {status}")
        
        # Performance Breakdown
        winners = [s for s in sorted_stocks if s['change_pct'] > 0]
        losers = [s for s in sorted_stocks if s['change_pct'] < 0]
        
        print(f"\n📈 PERFORMANCE BREAKDOWN:")
        print(f"{'='*50}")
        print(f"🟢 Winners: {len(winners)} stocks")
        print(f"🔴 Losers:  {len(losers)} stocks")
        print(f"📊 Win Rate: {len(winners)/len(sorted_stocks)*100:.1f}%")
        
        if winners:
            best_performer = max(winners, key=lambda x: x['change_pct'])
            print(f"🏆 Best:    {best_performer['symbol']} ({best_performer['change_pct']:+.2f}%)")
        
        if losers:
            worst_performer = min(losers, key=lambda x: x['change_pct'])
            print(f"⚠️  Worst:   {worst_performer['symbol']} ({worst_performer['change_pct']:+.2f}%)")
        
        # Sector Performance
        print(f"\n🏭 SECTOR PERFORMANCE:")
        print(f"{'='*50}")
        sector_performance = {}
        for stock in sorted_stocks:
            sector = stock['sector']
            if sector not in sector_performance:
                sector_performance[sector] = {'total_return': 0, 'count': 0}
            sector_performance[sector]['total_return'] += stock['change_pct']
            sector_performance[sector]['count'] += 1
        
        for sector, data in sector_performance.items():
            avg_return = data['total_return'] / data['count']
            sector_emoji = "🟢" if avg_return > 0 else "🔴"
            print(f"{sector_emoji} {sector:<25} {avg_return:+6.2f}% ({data['count']} stocks)")

    def populate_historical_fridays_optimized(self, num_fridays=4, limit=None, force_refresh=False, update_mode='safe'):
        """
        Populate historical Friday analysis using the optimized one-API-call-per-stock method.
        
        Args:
            num_fridays: Number of historical Fridays to populate
            limit: Limit number of stocks to analyze
            force_refresh: If True, clears all existing data first
            update_mode: 'safe' (skip existing), 'check' (warn on differences), 'force' (overwrite all)
        """
        print(f"\n{'='*100}")
        print(f"📊 POPULATING HISTORICAL FRIDAY ANALYSIS (OPTIMIZED)")
        print(f"{'='*100}")
        print(f"📅 Number of Fridays: {num_fridays} | Limit: {limit or 'All stocks'}")
        print(f"🔄 Force Refresh: {force_refresh} | Update Mode: {update_mode}")

        start_time = datetime.now()

        # Get stock list
        stock_symbols = self.get_nse_stock_list_from_api(limit=limit)
        total_stocks = len(stock_symbols)
        print(f"📊 Analyzing {total_stocks} stocks for the last {num_fridays} Fridays...")

        # Get Friday dates as datetime.date objects
        friday_dates = [self.get_nth_last_friday(i) for i in range(1, num_fridays + 1)]
        friday_date_strs = [d.strftime('%Y-%m-%d') for d in friday_dates]

        if force_refresh:
            print(f"🗑️  Clearing existing data for the last {num_fridays} Fridays...")
            for date_str in friday_date_strs:
                self.db.clear_friday_analysis_data(date_str)
            print("✅ Cleared data.")

        processed = 0
        total_records_added = 0
        skipped_existing = 0
        different_data_count = 0
        different_stocks = []

        for symbol in stock_symbols:
            processed += 1
            try:
                print(f"📊 {symbol:<12}", end=" ", flush=True)

                # Convert date objects to datetime objects for the analyzer
                friday_datetime_objects = [datetime.combine(d, datetime.min.time()) for d in friday_dates]
                analysis_results = self.analyze_stock_for_multiple_fridays(symbol, friday_datetime_objects)

                if not analysis_results:
                    print("❌ Analysis failed")
                    continue

                # Fetch company info once per stock
                ticker = yf.Ticker(f"{symbol}.NS")
                info = ticker.info
                company_name = info.get('longName', symbol)
                sector = info.get('sector', 'Unknown')
                market_cap = info.get('marketCap', 0)
                
                saved_count = 0
                skipped_count = 0
                different_count = 0
                
                for date_str, result in analysis_results.items():
                    record_data = {
                        'symbol': symbol,
                        'company_name': company_name,
                        'friday_date': date_str,
                        'friday_price': result['price'],
                        'total_score': result['total_score'],
                        'recommendation': result['recommendation'],
                        'risk_level': 'N/A',
                        'sector': sector,
                        'market_cap': market_cap,
                        'trend_score': result['scores']['trend'],
                        'momentum_score': result['scores']['momentum'],
                        'rsi_score': result['scores']['rsi'],
                        'volume_score': result['scores']['volume'],
                        'price_action_score': result['scores']['price'],
                        'ma_50': result['indicators']['ma_50'],
                        'ma_200': result['indicators']['ma_200'],
                        'rsi_value': result['indicators']['rsi'],
                        'macd_value': result['indicators']['macd'],
                        'macd_signal': result['indicators']['macd_signal'],
                        'volume_ratio': result['indicators']['volume_ratio'],
                        'price_change_1d': result['indicators']['price_change_1d'],
                        'price_change_5d': result['indicators']['price_change_5d'],
                        'trend_raw': result['raw_scores']['trend'],
                        'momentum_raw': result['raw_scores']['momentum'],
                        'rsi_raw': result['raw_scores']['rsi'],
                        'volume_raw': result['raw_scores']['volume'],
                        'price_raw': result['raw_scores']['price']
                    }
                    
                    # Use safe insert method
                    allow_overwrite = (update_mode == 'force') or force_refresh
                    status = self.db.insert_friday_analysis_record_safe(record_data, allow_overwrite)
                    
                    if status == 'inserted':
                        saved_count += 1
                    elif status == 'skipped':
                        skipped_count += 1
                    elif status == 'overwritten':
                        saved_count += 1
                    elif status == 'different':
                        different_count += 1
                        different_stocks.append(f"{symbol} ({date_str})")
                
                total_records_added += saved_count
                skipped_existing += skipped_count
                different_data_count += different_count
                
                # Status message
                if different_count > 0:
                    print(f"⚠️  {different_count} different, {saved_count} saved, {skipped_count} skipped")
                elif saved_count > 0:
                    print(f"✅ Saved {saved_count} records")
                else:
                    print(f"⏭️  Skipped {skipped_count} existing records")

                if processed % 20 == 0:
                    progress = (processed / total_stocks) * 100
                    print(f"\n📊 Progress: {processed}/{total_stocks} ({progress:.1f}%) | Added: {total_records_added} | Skipped: {skipped_existing} | Different: {different_data_count}")

                time.sleep(random.uniform(0.02, 0.05))

            except Exception as e:
                print(f"❌ Error processing {symbol}: {e}")
                continue

        duration_minutes = (datetime.now() - start_time).total_seconds() / 60
        
        print(f"\n✅ Historical Friday analysis population completed!")
        print(f"📊 Records Added: {total_records_added}")
        print(f"⏭️  Records Skipped (existing): {skipped_existing}")
        print(f"⚠️  Records with Different Data: {different_data_count}")
        print(f"⏰ Duration: {duration_minutes:.1f} minutes")
        
        # Warn about different data
        if different_data_count > 0:
            print(f"\n🚨 WARNING: Found {different_data_count} records with different historical data!")
            print("📋 This suggests potential issues with data consistency.")
            print("🔍 Different data found for:")
            for stock_date in different_stocks[:10]:  # Show first 10
                print(f"   • {stock_date}")
            if len(different_stocks) > 10:
                print(f"   • ... and {len(different_stocks) - 10} more")
            print("\n💡 Options to handle this:")
            print("   1. Use update_mode='force' to overwrite all data")
            print("   2. Investigate why historical data is changing")
            print("   3. Use force_refresh=True to clear and rebuild all data")

    def get_friday_strong_stocks_from_table_by_date(self, friday_date, threshold=67, limit=None):
        """
        Get STRONG stocks from friday_stocks_analysis table for a specific date
        
        Args:
            friday_date: Date in string format 'YYYY-MM-DD' or datetime object
            threshold: Minimum score threshold for STRONG stocks
            limit: Maximum number of stocks to return (None for all)
            
        Returns:
            List of stock dictionaries with analysis data
        """
        if isinstance(friday_date, str):
            friday_date_str = friday_date
        else:
            friday_date_str = friday_date.strftime('%Y-%m-%d')
            
        return self.db.get_friday_strong_stocks_from_table(friday_date_str, threshold, limit)

    def run_dynamic_threshold_analysis(self, start_friday_n=4, threshold=67, limit=None):
        """
        Dynamic threshold analysis from any past Friday to today - NO DATABASE WRITES
        
        This is the core functionality requested:
        1. Find STRONG stocks from any past Friday using dynamic threshold
        2. Track performance across consecutive Fridays to today
        3. Automatically sell when performance is bad
        4. Generate comprehensive report with sell decisions
        """
        print(f"\n{'='*100}")
        print(f"🎯 DYNAMIC THRESHOLD ANALYSIS (READ-ONLY)")
        print(f"{'='*100}")
        
        # Get Friday sequence (chronological order)
        friday_sequence = self.get_friday_sequence(start_friday_n, periods=start_friday_n)
        start_date = friday_sequence[0][0]
        
        print(f"📅 Analysis Period: {start_date.strftime('%Y-%m-%d')} to Today")
        print(f"🎯 Threshold: {threshold}")
        print(f"📊 Friday Sequence:")
        for i, (date, name) in enumerate(friday_sequence, 1):
            print(f"   {i}. {name}: {date.strftime('%Y-%m-%d %A')}")
        
        # Step 1: Get STRONG recommendations from start Friday (READ FROM DB)
        start_friday_date = start_date
        print(f"\n📊 Step 1: Finding STRONG stocks from {start_friday_date.strftime('%Y-%m-%d')}")
        
        initial_stocks = self.get_friday_strong_stocks_from_table_by_date(
            start_friday_date, threshold, limit
        )
        
        if not initial_stocks:
            print(f"❌ No STRONG stocks found for {start_friday_date}")
            return
        
        # Prepare positions (IN MEMORY - NO DB WRITES)
        positions = {}
        for stock in initial_stocks:
            positions[stock['symbol']] = {
                'symbol': stock['symbol'],
                'entry_price': stock['friday_price'],
                'entry_score': stock['friday_score'],
                'sector': stock.get('sector', 'UNKNOWN'),
                'company_name': stock['company_name'],
                'is_active': True,
                'entry_date': start_friday_date,
                'performance_history': []
            }
        
        print(f"✅ Found {len(positions)} STRONG stocks to track")
        
        # Step 2: Track performance across all periods (IN MEMORY)
        print(f"\n📊 Step 2: Tracking performance across {len(friday_sequence)} periods + Today")
        
        # Track through each Friday period
        for period_idx, (period_date, period_name) in enumerate(friday_sequence[1:], 2):
            print(f"\n🔍 Period {period_idx}: {period_name} ({period_date.strftime('%Y-%m-%d')})")
            self._process_period_in_memory(positions, period_date, period_name, threshold)
        
        # Track today's performance
        print(f"\n🔍 Final Period: Today ({datetime.now().strftime('%Y-%m-%d')})")
        self._process_period_in_memory(positions, datetime.now().date(), "Today", threshold)
        
        # Step 3: Generate comprehensive report (NO DB WRITES)
        print(f"\n📊 Step 3: Generating comprehensive analysis report")
        self._generate_dynamic_analysis_report(positions, start_friday_date, threshold)
        
        return positions
    
    def _process_period_in_memory(self, positions, period_date, period_name, threshold):
        """Process performance for a specific period - IN MEMORY ONLY"""
        active_count = sum(1 for pos in positions.values() if pos['is_active'])
        
        if active_count == 0:
            print(f"   📝 No active positions to track")
            return
        
        print(f"   📊 Tracking {active_count} active positions")
        sells_count = 0
        
        for symbol, pos in positions.items():
            if not pos['is_active']:
                continue
                
            try:
                # Get current price and score
                current_price, current_score = self.get_stock_price_and_score(symbol, period_date, period_name)
                
                if current_price == 0:
                    continue
                
                # Calculate return
                return_pct = ((current_price - pos['entry_price']) / pos['entry_price'] * 100) if pos['entry_price'] > 0 else 0
                
                # Record performance
                performance_record = {
                    'date': period_date,
                    'period_name': period_name,
                    'price': current_price,
                    'score': current_score,
                    'return_pct': return_pct,
                    'is_sold': False
                }
                
                # Check if should sell (score below threshold)
                should_sell = current_score < threshold if current_score is not None else False
                
                if should_sell and period_name != "Today":  # Don't auto-sell on today
                    # Sell the position (IN MEMORY)
                    pnl = current_price - pos['entry_price']
                    days_held = (period_date - pos['entry_date']).days
                    
                    pos['is_active'] = False
                    pos['sell_date'] = period_date
                    pos['sell_price'] = current_price
                    pos['sell_score'] = current_score
                    pos['sell_reason'] = f"Score dropped below {threshold}"
                    pos['total_pnl'] = pnl
                    pos['total_return_pct'] = return_pct
                    pos['days_held'] = days_held
                    
                    performance_record['is_sold'] = True
                    sells_count += 1
                    print(f"   🔴 SOLD {symbol}: Score {current_score:.1f} < {threshold} | P&L: ₹{pnl:+.2f} ({return_pct:+.2f}%)")
                
                pos['performance_history'].append(performance_record)
                
            except Exception as e:
                print(f"   ❌ Error processing {symbol}: {str(e)}")
                continue
        
        if sells_count > 0:
            print(f"   📊 Sold {sells_count} positions due to score threshold")
    
    def _generate_dynamic_analysis_report(self, positions, start_date, threshold):
        """Generate comprehensive analysis report - NO DB OPERATIONS"""
        print(f"\n{'='*100}")
        print(f"📊 DYNAMIC THRESHOLD ANALYSIS REPORT")
        print(f"{'='*100}")
        print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to Today")
        print(f"🎯 Threshold: {threshold}")
        print(f"📈 Total Positions: {len(positions)}")
        
        # Position Summary
        active_positions = [pos for pos in positions.values() if pos['is_active']]
        sold_positions = [pos for pos in positions.values() if not pos['is_active']]
        
        print(f"\n📊 POSITION SUMMARY:")
        print(f"🟢 Active Positions: {len(active_positions)}")
        print(f"🔴 Sold Positions: {len(sold_positions)}")
        
        # P&L Summary
        total_invested = sum(pos['entry_price'] for pos in positions.values())
        
        # Calculate current value
        total_current_value = 0
        for pos in positions.values():
            if pos['is_active'] and pos['performance_history']:
                # Use latest price for active positions
                total_current_value += pos['performance_history'][-1]['price']
            elif not pos['is_active']:
                # Use sell price for sold positions
                total_current_value += pos.get('sell_price', pos['entry_price'])
            else:
                total_current_value += pos['entry_price']
        
        total_pnl = total_current_value - total_invested
        total_return_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        print(f"\n💰 P&L SUMMARY:")
        print(f"💵 Total Invested:    ₹{total_invested:,.2f}")
        print(f"💰 Current Value:     ₹{total_current_value:,.2f}")
        print(f"🟢 Total P&L:         ₹{total_pnl:+,.2f}")
        print(f"📊 Total Return:      {total_return_pct:+.2f}%")
        
        # Show sold positions
        if sold_positions:
            print(f"\n🔴 SOLD POSITIONS:")
            print(f"{'Symbol':<12} {'Entry':<8} {'Sell':<8} {'P&L':<10} {'Return':<8} {'Days':<5} {'Reason'}")
            print("-" * 70)
            
            for pos in sold_positions:
                print(f"{pos['symbol']:<12} "
                      f"₹{pos['entry_price']:<7.2f} "
                      f"₹{pos.get('sell_price', 0):<7.2f} "
                      f"₹{pos.get('total_pnl', 0):>+8.2f} "
                      f"{pos.get('total_return_pct', 0):>+6.2f}% "
                      f"{pos.get('days_held', 0):<5} "
                      f"{pos.get('sell_reason', 'N/A')}")
        
        # Show active positions current status
        if active_positions:
            print(f"\n🟢 ACTIVE POSITIONS (Current Status):")
            print(f"{'Symbol':<12} {'Entry':<8} {'Current':<8} {'P&L':<10} {'Return':<8} {'Sector'}")
            print("-" * 75)
            
            for pos in active_positions:
                if pos['performance_history']:
                    current_price = pos['performance_history'][-1]['price']
                    current_pnl = current_price - pos['entry_price']
                    current_return = ((current_price - pos['entry_price']) / pos['entry_price'] * 100) if pos['entry_price'] > 0 else 0
                    
                    print(f"{pos['symbol']:<12} "
                          f"₹{pos['entry_price']:<7.2f} "
                          f"₹{current_price:<7.2f} "
                          f"₹{current_pnl:>+8.2f} "
                          f"{current_return:>+6.2f}% "
                          f"{pos['sector']}")
        
        # Performance Statistics
        all_positions = list(positions.values())
        winners = [pos for pos in all_positions if pos.get('total_return_pct', 0) > 0 or 
                  (pos['is_active'] and pos['performance_history'] and 
                   ((pos['performance_history'][-1]['price'] - pos['entry_price']) / pos['entry_price'] * 100) > 0)]
        
        print(f"\n📊 PERFORMANCE STATISTICS:")
        print(f"🟢 Winners: {len(winners)} positions")
        print(f"🔴 Others:  {len(all_positions) - len(winners)} positions")
        print(f"📊 Win Rate: {len(winners)/len(all_positions)*100:.1f}%")
        
        print(f"\n✅ Dynamic threshold analysis completed! (Read-only mode)")

def main():
    """Main function for sandbox analyzer - Simplified version"""
    analyzer = SandboxAnalyzer()
    
    print("🎯 SIMPLIFIED SANDBOX ANALYZER")
    print("=" * 50)
    print("1. One-time Data Population (Populate historical Fridays)")
    print("2. Dynamic Threshold Analysis (Any past Friday → Today)")
    print("3. Exit")
    
    choice = input("\nSelect option (1/2/3): ").strip()
    
    if choice == '1':
        # One-time data population with smart duplicate handling
        try:
            num_fridays = int(input("Enter number of historical Fridays to populate (default 8): ") or "8")
            limit = input("Enter stock limit (press Enter for all): ").strip()
            limit = int(limit) if limit else None
            
            print("\n📋 Update Mode Options:")
            print("   safe   - Skip existing data (recommended for weekly updates)")
            print("   check  - Warn if historical data differs (for debugging)")  
            print("   force  - Overwrite all data (use with caution)")
            update_mode = input("Select update mode (safe/check/force) [default: safe]: ").strip() or "safe"
            
            force_refresh = False
            if update_mode not in ['safe', 'check', 'force']:
                print("Invalid update mode, using 'safe'")
                update_mode = 'safe'
            elif update_mode == 'force':
                confirm = input("⚠️  Force mode will overwrite existing data. Continue? (y/N): ").strip().lower()
                if confirm != 'y':
                    print("Operation cancelled.")
                    return
            
            analyzer.populate_historical_fridays_optimized(
                num_fridays=num_fridays, 
                limit=limit, 
                force_refresh=force_refresh,
                update_mode=update_mode
            )
            
        except ValueError:
            print("Invalid input")
    
    elif choice == '2':
        # Dynamic threshold analysis
        try:
            start_friday_n = int(input("Enter which Friday to start from (1=last, 2=2nd last, etc.): "))
            threshold = float(input("Enter threshold (e.g., 67): "))
            limit = input("Enter stock limit (press Enter for all): ").strip()
            limit = int(limit) if limit else None
            
            # Use existing backtest logic but without database writes
            analyzer.run_dynamic_threshold_analysis(start_friday_n=start_friday_n, threshold=threshold, limit=limit)
            
        except ValueError:
            print("Invalid input")
    
    elif choice == '3':
        print("👋 Goodbye!")
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main() 