import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from buy_sell_signal_analyzer import BuySellSignalAnalyzer
import pandas as pd
from datetime import datetime

class EnhancedStrategyScreener:
    """
    Enhanced strategy screener that ranks stocks using comprehensive buy/sell signals
    """
    
    def __init__(self, max_workers=3):
        self.analyzer = BuySellSignalAnalyzer()
        self.max_workers = max_workers
        self.database_file = "nse_stock_scanner.db"
    
    def get_stocks_from_db(self, limit=50, min_price=50, max_price=1000):
        """Get stocks from the NSE scanner database"""
        try:
            conn = sqlite3.connect(self.database_file)
            cursor = conn.cursor()
            
            # Get stocks within price range, ordered by market cap (larger companies first)
            cursor.execute('''
                SELECT DISTINCT symbol, company_name, current_price, market_cap, sector
                FROM stocks 
                WHERE current_price BETWEEN ? AND ?
                AND market_cap > 0
                ORDER BY market_cap DESC
                LIMIT ?
            ''', (min_price, max_price, limit))
            
            stocks = cursor.fetchall()
            conn.close()
            
            # Convert to list of dicts
            stock_list = []
            for stock in stocks:
                stock_list.append({
                    'symbol': stock[0],
                    'company_name': stock[1],
                    'current_price': stock[2],
                    'market_cap': stock[3],
                    'sector': stock[4]
                })
            
            return stock_list
            
        except Exception as e:
            print(f"❌ Error accessing database: {str(e)}")
            return []
    
    def analyze_single_stock(self, stock_info):
        """Analyze a single stock and return results"""
        symbol = stock_info['symbol']
        yahoo_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        
        try:
            print(f"🔍 Analyzing {symbol}...", end=" ")
            
            # Call analyzer without output suppression - much more reliable
            result = self.analyzer.calculate_overall_score_silent(yahoo_symbol)
            
            if result is None:
                print("❌ No data")
                return None
            
            # Add stock info to result
            result['stock_info'] = stock_info
            result['symbol'] = symbol
            
            print(f"✅ Score {result['total_score']:.1f} - {result['recommendation']}")
            return result
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return None
    
    def screen_stocks(self, limit=20, min_score=30):
        """Screen stocks and return ranked results"""
        print(f"\n{'='*80}")
        print(f"🎯 ENHANCED STRATEGY SCREENER")
        print(f"{'='*80}")
        print(f"📊 Screening top {limit} stocks from database...")
        print(f"🎯 Minimum score threshold: {min_score}")
        
        # Get stocks from database
        stocks = self.get_stocks_from_db(limit=limit)
        
        if not stocks:
            print("❌ No stocks found in database")
            return []
        
        print(f"📋 Found {len(stocks)} stocks to analyze")
        print(f"⏳ Analysis starting with {self.max_workers} workers...")
        
        results = []
        
        # Analyze stocks with threading
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_stock = {executor.submit(self.analyze_single_stock, stock): stock 
                             for stock in stocks}
            
            for future in as_completed(future_to_stock):
                result = future.result()
                if result and result['total_score'] >= min_score:
                    results.append(result)
                
                # Small delay to avoid overwhelming APIs
                time.sleep(0.5)
        
        # Sort by score descending
        results.sort(key=lambda x: x['total_score'], reverse=True)
        
        return results
    
    def display_results(self, results):
        """Display screener results in a formatted table"""
        if not results:
            print("\n❌ No stocks met the minimum score criteria")
            return
        
        print(f"\n{'='*100}")
        print(f"🏆 TOP STOCK RECOMMENDATIONS (Ranked by Signal Strength)")
        print(f"{'='*100}")
        
        # Header
        print(f"{'Rank':<4} {'Symbol':<12} {'Company':<25} {'Price':<8} {'Score':<6} {'Recommendation':<20} {'Risk':<10} {'Sector':<15}")
        print(f"{'-'*100}")
        
        # Results
        for i, result in enumerate(results, 1):
            stock = result['stock_info']
            symbol = result['symbol']
            company = stock['company_name'][:24] + "..." if len(stock['company_name']) > 24 else stock['company_name']
            price = f"₹{stock['current_price']:.0f}"
            score = f"{result['total_score']:.1f}"
            recommendation = result['recommendation'][:19]
            risk = result['risk_level']
            sector = stock['sector'][:14] if stock['sector'] else "Unknown"
            
            print(f"{i:<4} {symbol:<12} {company:<25} {price:<8} {score:<6} {recommendation:<20} {risk:<10} {sector:<15}")
        
        # Summary statistics
        print(f"\n📊 SCREENING SUMMARY:")
        print(f"{'='*50}")
        
        strong_buy = len([r for r in results if r['total_score'] >= 75])
        buy = len([r for r in results if 60 <= r['total_score'] < 75])
        weak_buy = len([r for r in results if 40 <= r['total_score'] < 60])
        
        print(f"🟢 STRONG BUY (75+):     {strong_buy} stocks")
        print(f"🟢 BUY (60-74):          {buy} stocks")
        print(f"🟡 WEAK BUY (40-59):     {weak_buy} stocks")
        
        # Top sectors
        sectors = {}
        for result in results:
            sector = result['stock_info']['sector'] or 'Unknown'
            sectors[sector] = sectors.get(sector, 0) + 1
        
        print(f"\n🏭 TOP PERFORMING SECTORS:")
        for sector, count in sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   • {sector}: {count} stocks")
    
    def detailed_analysis(self, results, top_n=5):
        """Show detailed analysis for top N stocks"""
        if not results:
            return
        
        print(f"\n{'='*100}")
        print(f"🔍 DETAILED ANALYSIS - TOP {min(top_n, len(results))} STOCKS")
        print(f"{'='*100}")
        
        for i, result in enumerate(results[:top_n], 1):
            stock = result['stock_info']
            print(f"\n{i}. {result['symbol']} - {stock['company_name']}")
            print(f"   💰 Price: ₹{stock['current_price']:.2f} | 🎯 Score: {result['total_score']:.1f}")
            print(f"   📋 {result['recommendation']} | ⚠️ Risk: {result['risk_level']}")
            
            # Show signal breakdown
            breakdown = result['breakdown']
            print(f"   📊 Signal Breakdown:")
            print(f"      • Trend: {breakdown['trend']['weighted']:.1f} ({len(breakdown['trend']['signals'])} signals)")
            print(f"      • Momentum: {breakdown['momentum']['weighted']:.1f} ({len(breakdown['momentum']['signals'])} signals)")
            print(f"      • RSI: {breakdown['rsi']['weighted']:.1f} ({len(breakdown['rsi']['signals'])} signals)")
            print(f"      • Volume: {breakdown['volume']['weighted']:.1f} ({len(breakdown['volume']['signals'])} signals)")
            print(f"      • Price Action: {breakdown['price']['weighted']:.1f} ({len(breakdown['price']['signals'])} signals)")
    
    def save_results_to_db(self, results):
        """Save results to recommendations database instead of CSV"""
        if not results:
            return
        
        from recommendations_database import RecommendationsDatabase
        db = RecommendationsDatabase()
        
        print(f"\n💾 Saving {len(results)} recommendations to database...")
        
        for result in results:
            stock_info = result['stock_info']
            symbol = f"{result['symbol']}.NS"
            
            # Save recommendation to database
            rec_id = db.save_recommendation(symbol, result, stock_info)
        
        print(f"✅ All recommendations saved to database with timestamps!")

def main():
    """Main screening function with database integration"""
    screener = EnhancedStrategyScreener(max_workers=3)
    
    # Screen stocks
    results = screener.screen_stocks(limit=30, min_score=40)
    
    # Display results
    screener.display_results(results)
    
    # Show detailed analysis for top stocks
    screener.detailed_analysis(results, top_n=5)
    
    # Save results to database instead of CSV
    screener.save_results_to_db(results)
    
    print(f"\n{'='*80}")
    print("🎯 SCREENING COMPLETED!")
    print("📊 All recommendations saved to database with date tracking!")
    print(f"{'='*80}")

if __name__ == "__main__":
    main() 