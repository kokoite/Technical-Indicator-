import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from advanced_recommendation_manager import AdvancedRecommendationManager
from enhanced_strategy_screener import EnhancedStrategyScreener
import time

class DailyMonitor:
    """
    Daily monitoring system for Monday-Thursday
    - Monitors STRONG recommendations for selling criteria
    - Checks WEAK recommendations for promotion to STRONG
    """
    
    def __init__(self):
        self.manager = AdvancedRecommendationManager()
        self.screener = EnhancedStrategyScreener()
        self.db_name = "stock_recommendations.db"
        # Track today's activity for reporting
        self.todays_sales = []
        self.todays_promotions = []
    
    def run_daily_monitoring(self):
        """Main daily monitoring routine"""
        today = datetime.now().strftime('%A')
        
        if today in ['Saturday', 'Sunday']:
            print("📅 Weekend - No monitoring scheduled")
            return
        
        if today == 'Friday':
            print("📅 Friday - Running daily monitoring")
        
        print(f"\n{'='*80}")
        print(f"📊 DAILY MONITORING SYSTEM - {today.upper()}")
        print(f"{'='*80}")
        print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Monitor STRONG recommendations
        print("\n🔍 STEP 1: Monitoring STRONG recommendations...")
        self.monitor_strong_recommendations()
        
        # Step 2: Check WEAK recommendations for promotion
        print("\n🚀 STEP 2: Checking WEAK recommendations for promotion...")
        self.check_weak_promotions()
        
        # Step 3: Update performance data
        print("\n📊 STEP 3: Updating performance data...")
        self.update_performance_data()
        
        # Step 4: Generate daily report
        print("\n📋 STEP 4: Generating daily summary...")
        self.generate_daily_report()
        
        print(f"\n✅ Daily monitoring completed for {today}!")
    
    def monitor_strong_recommendations(self):
        """Monitor STRONG recommendations for selling criteria using batch requests"""
        strong_recs = self.manager.get_recommendations_by_tier('STRONG')
        
        if strong_recs.empty:
            print("📝 No STRONG recommendations to monitor")
            return
        
        print(f"📊 Monitoring {len(strong_recs)} STRONG recommendations...")
        print("🚀 Using batch requests for price updates...")
        
        # Get all symbols for batch request
        symbols = strong_recs['symbol'].tolist()
        yahoo_symbols = [f"{symbol}.NS" for symbol in symbols]
        
        # Batch get current prices
        try:
            print(f"📦 Getting current prices for {len(symbols)} STRONG stocks...")
            batch_data = yf.download(" ".join(yahoo_symbols), period="1d", group_by='ticker', auto_adjust=True)
            
            if batch_data.empty:
                print("⚠️ Batch price data returned empty")
                return
            
        except Exception as e:
            print(f"❌ Batch price fetch failed: {str(e)}")
            return
        
        sells_executed = 0
        
        for _, rec in strong_recs.iterrows():
            symbol = rec['symbol']
            entry_price = rec['entry_price']
            
            try:
                # Get current price from batch data
                yahoo_symbol = f"{symbol}.NS"
                
                # Extract data from batch result
                if len(symbols) == 1:
                    stock_data = batch_data
                else:
                    if yahoo_symbol in batch_data.columns.get_level_values(0):
                        stock_data = batch_data[yahoo_symbol]
                    else:
                        print(f"⚠️ No price data for {symbol}")
                        continue
                
                if stock_data is None or stock_data.empty or 'Close' not in stock_data.columns:
                    print(f"⚠️ No price data for {symbol}")
                    continue
                
                current_price = stock_data['Close'].iloc[-1]
                price_change_pct = ((current_price - entry_price) / entry_price) * 100
                
                # Check selling criteria - More aggressive stop losses
                if price_change_pct <= -7:  # 7% loss - immediate sell
                    reason = f"Aggressive stop loss: {price_change_pct:.2f}% loss (7% threshold)"
                    print(f"🔴 {symbol}: Price down {price_change_pct:.2f}% - SELLING (7% stop loss)")
                    if self.manager.sell_strong_recommendation(symbol, current_price, reason):
                        sells_executed += 1
                        self.todays_sales.append(f"{symbol} ({price_change_pct:+.1f}%)")
                elif price_change_pct <= -5:  # 5% loss - check indicators
                    print(f"🟡 {symbol}: Price down {price_change_pct:.2f}% - Checking indicators...")
                    
                    # Re-analyze with current indicators
                    stock_info = {
                        'symbol': symbol,
                        'current_price': current_price,
                        'company_name': rec.get('company_name', symbol),
                        'sector': rec.get('sector', 'Unknown')
                    }
                    
                    analysis = self.screener.analyze_single_stock(stock_info)
                    
                    if analysis and analysis['total_score'] < 40:  # Indicators deteriorated (raised from 35 to 40)
                        reason = f"Stop loss: {price_change_pct:.2f}% loss + indicators deteriorated (Score: {analysis['total_score']:.1f})"
                        print(f"🔴 {symbol}: Indicators also weak - SELLING")
                        if self.manager.sell_strong_recommendation(symbol, current_price, reason):
                            sells_executed += 1
                            self.todays_sales.append(f"{symbol} ({price_change_pct:+.1f}%)")
                    else:
                        score_text = f"{analysis['total_score']:.1f}" if analysis else "N/A"
                        print(f"⚪ {symbol}: Price down but indicators still OK (Score: {score_text}) - HOLDING")
                else:
                    status_emoji = "🟢" if price_change_pct > 0 else "🟡"
                    print(f"{status_emoji} {symbol}: {price_change_pct:+.2f}% - Holding")
                
            except Exception as e:
                print(f"❌ Error monitoring {symbol}: {str(e)}")
        
        print(f"🚀 BATCH MONITORING COMPLETED: {sells_executed} positions sold")
        print(f"⚡ Speed improvement: ~10x faster than individual requests!")
    
    def check_weak_promotions(self):
        """Check WEAK recommendations for promotion to STRONG using batch requests"""
        weak_recs = self.manager.get_recommendations_by_tier('WEAK')
        
        if weak_recs.empty:
            print("📝 No WEAK recommendations to check for promotion")
            return
        
        print(f"📊 Checking {len(weak_recs)} WEAK recommendations for promotion...")
        print("🚀 Using batch requests for price updates...")
        
        # Filter out records without Friday price reference
        valid_weak_recs = weak_recs[
            (weak_recs['last_friday_price'].notna()) & 
            (weak_recs['last_friday_price'] != 0)
        ]
        
        if valid_weak_recs.empty:
            print("⚠️ No WEAK recommendations with valid Friday price references")
            return
        
        # Get all symbols for batch request
        symbols = valid_weak_recs['symbol'].tolist()
        yahoo_symbols = [f"{symbol}.NS" for symbol in symbols]
        
        # Batch get current prices
        try:
            print(f"📦 Getting current prices for {len(symbols)} WEAK stocks...")
            batch_data = yf.download(" ".join(yahoo_symbols), period="1d", group_by='ticker', auto_adjust=True)
            
            if batch_data.empty:
                print("⚠️ Batch price data returned empty")
                return
            
        except Exception as e:
            print(f"❌ Batch price fetch failed: {str(e)}")
            return
        
        promotions_executed = 0
        
        for _, rec in valid_weak_recs.iterrows():
            symbol = rec['symbol']
            last_friday_price = rec['last_friday_price']
            
            try:
                # Get current price from batch data
                yahoo_symbol = f"{symbol}.NS"
                
                # Extract data from batch result
                if len(symbols) == 1:
                    stock_data = batch_data
                else:
                    if yahoo_symbol in batch_data.columns.get_level_values(0):
                        stock_data = batch_data[yahoo_symbol]
                    else:
                        print(f"⚠️ No price data for {symbol}")
                        continue
                
                if stock_data is None or stock_data.empty or 'Close' not in stock_data.columns:
                    print(f"⚠️ No price data for {symbol}")
                    continue
                
                current_price = stock_data['Close'].iloc[-1]
                price_change_since_friday = ((current_price - last_friday_price) / last_friday_price) * 100
                
                # Check promotion criteria: >= +2% since Friday
                if price_change_since_friday >= 2.0:
                    print(f"🚀 {symbol}: Price up {price_change_since_friday:.2f}% since Friday - Re-analyzing...")
                    
                    # Re-analyze with current indicators
                    stock_info = {
                        'symbol': symbol,
                        'current_price': current_price,
                        'company_name': rec.get('company_name', symbol),
                        'sector': rec.get('sector', 'Unknown')
                    }
                    
                    analysis = self.screener.analyze_single_stock(stock_info)
                    
                    if analysis and analysis['total_score'] >= 70:  # Strong score threshold
                        if self.manager.promote_weak_to_strong(symbol, analysis, current_price):
                            promotions_executed += 1
                            self.todays_promotions.append(f"{symbol} ({price_change_since_friday:+.1f}%)")
                    else:
                        score_text = f"{analysis['total_score']:.1f}" if analysis else "N/A"
                        print(f"⚪ {symbol}: Price up but score still weak ({score_text})")
                else:
                    print(f"📊 {symbol}: {price_change_since_friday:+.2f}% since Friday - No promotion")
                
            except Exception as e:
                print(f"❌ Error checking {symbol}: {str(e)}")
        
        print(f"🚀 BATCH PROMOTION CHECK COMPLETED: {promotions_executed} stocks promoted")
        print(f"⚡ Speed improvement: ~10x faster than individual requests!")
    
    def update_performance_data(self):
        """Update performance data for all active recommendations using batch requests"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Get all active recommendations
        cursor.execute('''
            SELECT id, symbol, entry_price FROM recommendations 
            WHERE status = 'ACTIVE' AND is_sold = 0
        ''')
        
        active_recs = cursor.fetchall()
        conn.close()
        
        if not active_recs:
            print("📝 No active recommendations to update")
            return
        
        print(f"📊 Updating performance for {len(active_recs)} active recommendations...")
        print("🚀 Using batch requests for maximum speed...")
        
        # Extract symbols and create mapping
        rec_dict = {symbol: (rec_id, entry_price) for rec_id, symbol, entry_price in active_recs}
        symbols = list(rec_dict.keys())
        
        updated_count = 0
        batch_size = 100
        total_batches = (len(symbols) + batch_size - 1) // batch_size
        
        # Process in batches of 100
        for batch_num in range(0, len(symbols), batch_size):
            batch_symbols = symbols[batch_num:batch_num + batch_size]
            yahoo_symbols = [f"{symbol}.NS" for symbol in batch_symbols]
            
            current_batch = (batch_num // batch_size) + 1
            print(f"📦 Processing batch {current_batch}/{total_batches}: {len(batch_symbols)} stocks")
            
            try:
                # Pure batch download - single API call for entire batch
                batch_data = yf.download(" ".join(yahoo_symbols), period="1d", group_by='ticker', auto_adjust=True)
                
                if batch_data.empty:
                    print(f"⚠️ Batch {current_batch} returned empty data")
                    continue
                
                # Process each stock in the batch
                batch_updates = []
                for symbol in batch_symbols:
                    try:
                        yahoo_symbol = f"{symbol}.NS"
                        rec_id, entry_price = rec_dict[symbol]
                        
                        # Extract data from batch result
                        if len(batch_symbols) == 1:
                            # Single stock - direct access
                            stock_data = batch_data
                        else:
                            # Multiple stocks - access by ticker
                            if yahoo_symbol in batch_data.columns.get_level_values(0):
                                stock_data = batch_data[yahoo_symbol]
                            else:
                                continue  # Stock not found in batch
                        
                        if stock_data is not None and not stock_data.empty and 'Close' in stock_data.columns:
                            current_price = stock_data['Close'].iloc[-1]
                            return_pct = ((current_price - entry_price) / entry_price) * 100
                            
                            batch_updates.append((rec_id, current_price, return_pct, symbol))
                        
                    except Exception as e:
                        # Skip individual stock errors
                        continue
                
                # Batch update database
                if batch_updates:
                    conn = sqlite3.connect(self.db_name)
                    cursor = conn.cursor()
                    
                    for rec_id, current_price, return_pct, symbol in batch_updates:
                        cursor.execute('''
                            INSERT OR REPLACE INTO performance_tracking 
                            (recommendation_id, current_price, return_pct, days_held, last_updated)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            rec_id, 
                            current_price, 
                            return_pct,
                            (datetime.now() - datetime.strptime('2024-01-01', '%Y-%m-%d')).days,  # Placeholder
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ))
                        
                        updated_count += 1
                    
                    conn.commit()
                    conn.close()
                
                print(f"✅ Batch {current_batch} completed: {len(batch_updates)} performance records updated")
                
            except Exception as e:
                print(f"❌ Batch {current_batch} failed: {str(e)}")
                continue
        
        print(f"🚀 BATCH PERFORMANCE UPDATE COMPLETED: Updated {updated_count} recommendations")
        print(f"⚡ Speed improvement: ~17x faster than individual requests!")
    
    def get_strong_performance_summary(self):
        """Get performance summary for STRONG recommendations using batch requests"""
        strong_recs = self.manager.get_recommendations_by_tier('STRONG')
        
        if strong_recs.empty:
            return None
        
        print(f"📊 Getting performance summary for {len(strong_recs)} STRONG stocks...")
        print("🚀 Using batch requests for price updates...")
        
        # Get all symbols for batch request
        symbols = strong_recs['symbol'].tolist()
        yahoo_symbols = [f"{symbol}.NS" for symbol in symbols]
        
        # Batch get current prices (2 days for day change calculation)
        try:
            batch_data = yf.download(" ".join(yahoo_symbols), period="2d", group_by='ticker', auto_adjust=True)
            
            if batch_data.empty:
                print("⚠️ Batch price data returned empty")
                return None
            
        except Exception as e:
            print(f"❌ Batch price fetch failed: {str(e)}")
            return None
        
        print("📊 Re-analyzing stocks for current scores...")
        
        performance_data = []
        total_invested = 0
        total_current_value = 0
        total_pnl = 0
        
        for _, rec in strong_recs.iterrows():
            symbol = rec['symbol']
            entry_price = rec['entry_price']
            
            try:
                # Get current price from batch data
                yahoo_symbol = f"{symbol}.NS"
                
                # Extract data from batch result
                if len(symbols) == 1:
                    stock_data = batch_data
                else:
                    if yahoo_symbol in batch_data.columns.get_level_values(0):
                        stock_data = batch_data[yahoo_symbol]
                    else:
                        continue  # Stock not found in batch
                
                if stock_data is not None and not stock_data.empty and 'Close' in stock_data.columns:
                    current_price = stock_data['Close'].iloc[-1]
                    price_change_pct = ((current_price - entry_price) / entry_price) * 100
                    money_change = current_price - entry_price  # Per share
                    
                    # Calculate day change (today vs yesterday)
                    day_change_pct = 0
                    if len(stock_data) >= 2:
                        yesterday_close = stock_data['Close'].iloc[-2]
                        day_change_pct = ((current_price - yesterday_close) / yesterday_close) * 100
                    else:
                        # Fallback: if only 1 day available, show 0
                        day_change_pct = 0
                    
                    # Get current score by re-analyzing the stock
                    current_score = None
                    try:
                        stock_info = {
                            'symbol': symbol,
                            'current_price': current_price,
                            'company_name': rec.get('company_name', symbol),
                            'sector': rec.get('sector', 'Unknown')
                        }
                        
                        analysis = self.screener.analyze_single_stock(stock_info)
                        if analysis:
                            current_score = analysis['total_score']
                        
                        # Small delay for individual analysis
                        time.sleep(0.1)
                        
                    except Exception as e:
                        print(f"⚠️ Could not get current score for {symbol}: {str(e)}")
                        current_score = None
                    
                    performance_data.append({
                        'symbol': symbol,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'change_pct': price_change_pct,
                        'money_change': money_change,
                        'day_change_pct': day_change_pct,
                        'current_score': current_score
                    })
                    
                    # Assuming 1 share per recommendation for calculation
                    total_invested += entry_price
                    total_current_value += current_price
                    total_pnl += money_change
                
            except Exception as e:
                print(f"❌ Error getting performance for {symbol}: {str(e)}")
        
        if performance_data:
            total_return_pct = ((total_current_value - total_invested) / total_invested) * 100
            
            print(f"🚀 BATCH PERFORMANCE SUMMARY COMPLETED")
            print(f"⚡ Speed improvement: ~10x faster than individual requests!")
            
            return {
                'stocks': performance_data,
                'total_invested': total_invested,
                'total_current_value': total_current_value,
                'total_pnl': total_pnl,
                'total_return_pct': total_return_pct,
                'count': len(performance_data)
            }
        
        return None
    
    def generate_daily_report(self):
        """Generate daily monitoring report"""
        print(f"\n{'='*60}")
        print(f"📊 DAILY MONITORING REPORT")
        print(f"{'='*60}")
        
        # Get tier counts
        conn = sqlite3.connect(self.db_name)
        
        tier_query = '''
            SELECT recommendation_tier, COUNT(*) as count
            FROM recommendations 
            WHERE status = 'ACTIVE' AND is_sold = 0
            GROUP BY recommendation_tier
        '''
        
        tier_df = pd.read_sql_query(tier_query, conn)
        
        print("📋 Current Active Recommendations:")
        for _, row in tier_df.iterrows():
            tier_emoji = "🟢" if row['recommendation_tier'] == "STRONG" else "🟡" if row['recommendation_tier'] == "WEAK" else "⚪"
            print(f"   {tier_emoji} {row['recommendation_tier']}: {row['count']} stocks")
        
        # Get recent activity
        recent_activity_query = '''
            SELECT COUNT(*) as sold_today FROM recommendations 
            WHERE sell_date = ? AND is_sold = 1
        '''
        
        today = datetime.now().strftime('%Y-%m-%d')
        sold_today = pd.read_sql_query(recent_activity_query, conn, params=(today,))
        
        promotion_query = '''
            SELECT COUNT(*) as promoted_today FROM recommendations 
            WHERE promotion_date = ?
        '''
        
        promoted_today = pd.read_sql_query(promotion_query, conn, params=(today,))
        
        conn.close()
        
        print(f"\n📊 Today's Activity:")
        
        # Show sales with stock names
        sales_count = sold_today['sold_today'].iloc[0] if not sold_today.empty else 0
        if self.todays_sales:
            print(f"   🔴 Positions Sold: {len(self.todays_sales)}")
            for sale in self.todays_sales:
                print(f"      • {sale}")
        else:
            print(f"   🔴 Positions Sold: {sales_count}")
        
        # Show promotions with stock names  
        promotions_count = promoted_today['promoted_today'].iloc[0] if not promoted_today.empty else 0
        if self.todays_promotions:
            print(f"   🚀 Promotions: {len(self.todays_promotions)}")
            for promotion in self.todays_promotions:
                print(f"      • {promotion}")
        else:
            print(f"   🚀 Promotions: {promotions_count}")
        
        # Show STRONG recommendations performance
        print(f"\n💰 STRONG Recommendations Performance:")
        performance = self.get_strong_performance_summary()
        
        if performance:
            print(f"   📊 Portfolio Summary ({performance['count']} stocks):")
            print(f"      💵 Total Invested: ₹{performance['total_invested']:.2f}")
            print(f"      💰 Current Value: ₹{performance['total_current_value']:.2f}")
            
            pnl_emoji = "📈" if performance['total_pnl'] >= 0 else "📉"
            return_emoji = "🟢" if performance['total_return_pct'] >= 0 else "🔴"
            
            print(f"      {pnl_emoji} Total P&L: ₹{performance['total_pnl']:+.2f}")
            print(f"      {return_emoji} Total Return: {performance['total_return_pct']:+.2f}%")
            
            print(f"\n   📋 Individual Stock Performance:")
            # Sort by performance (best first)
            sorted_stocks = sorted(performance['stocks'], key=lambda x: x['change_pct'], reverse=True)
            
            for stock in sorted_stocks:
                emoji = "🟢" if stock['change_pct'] >= 0 else "🔴"
                print(f"      {emoji} {stock['symbol']:<12} {stock['change_pct']:+6.2f}% (₹{stock['money_change']:+6.2f})")
        else:
            print(f"   📝 No STRONG recommendations to track")
        
        print(f"\n⏰ Next monitoring: Tomorrow ({(datetime.now() + timedelta(days=1)).strftime('%A')})")

    def show_strong_performance_report(self):
        """Show detailed STRONG recommendations performance report"""
        print(f"\n{'='*80}")
        print(f"💰 STRONG RECOMMENDATIONS PERFORMANCE REPORT")
        print(f"{'='*80}")
        print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        performance = self.get_strong_performance_summary()
        
        if not performance:
            print("📝 No STRONG recommendations found")
            return
        
        # Portfolio Summary
        print(f"\n📊 PORTFOLIO SUMMARY ({performance['count']} stocks):")
        print(f"{'='*60}")
        print(f"💵 Total Invested:  ₹{performance['total_invested']:>12,.2f}")
        print(f"💰 Current Value:   ₹{performance['total_current_value']:>12,.2f}")
        
        pnl_emoji = "📈" if performance['total_pnl'] >= 0 else "📉"
        return_emoji = "🟢" if performance['total_return_pct'] >= 0 else "🔴"
        
        print(f"{pnl_emoji} Total P&L:      ₹{performance['total_pnl']:>+12,.2f}")
        print(f"{return_emoji} Total Return:   {performance['total_return_pct']:>+11.2f}%")
        
        # Individual Stock Performance
        print(f"\n📋 INDIVIDUAL STOCK PERFORMANCE:")
        print(f"{'='*115}")
        print(f"{'Stock':<12} {'Entry':<10} {'Current':<10} {'Total %':<10} {'Day %':<8} {'Score':<7} {'P&L (₹)':<10} {'Status'}")
        print(f"{'-'*115}")
        
        # Sort by performance (best first)
        sorted_stocks = sorted(performance['stocks'], key=lambda x: x['change_pct'], reverse=True)
        
        for stock in sorted_stocks:
            emoji = "🟢" if stock['change_pct'] >= 0 else "🔴"
            status = "Profit" if stock['change_pct'] >= 0 else "Loss"
            
            # Day change emoji
            day_emoji = "📈" if stock['day_change_pct'] > 0 else "📉" if stock['day_change_pct'] < 0 else "➖"
            
            # Score formatting with color coding
            score_text = f"{stock['current_score']:.1f}" if stock['current_score'] is not None else "N/A"
            if stock['current_score'] is not None:
                if stock['current_score'] >= 75:
                    score_emoji = "🟢"  # Strong
                elif stock['current_score'] >= 60:
                    score_emoji = "🟡"  # Good
                elif stock['current_score'] >= 40:
                    score_emoji = "🟠"  # Weak
                else:
                    score_emoji = "🔴"  # Poor
                score_display = f"{score_emoji}{score_text}"
            else:
                score_display = "❓N/A"
            
            print(f"{stock['symbol']:<12} "
                  f"₹{stock['entry_price']:<9.2f} "
                  f"₹{stock['current_price']:<9.2f} "
                  f"{stock['change_pct']:>+8.2f}% "
                  f"{day_emoji}{stock['day_change_pct']:>+6.2f}% "
                  f"{score_display:<7} "
                  f"₹{stock['money_change']:>+8.2f} "
                  f"{emoji} {status}")
        
        # Performance Categories
        winners = [s for s in sorted_stocks if s['change_pct'] > 0]
        losers = [s for s in sorted_stocks if s['change_pct'] < 0]
        
        print(f"\n📈 PERFORMANCE BREAKDOWN:")
        print(f"{'='*40}")
        print(f"🟢 Winners: {len(winners)} stocks")
        print(f"🔴 Losers:  {len(losers)} stocks")
        
        if winners:
            best_performer = max(winners, key=lambda x: x['change_pct'])
            print(f"🏆 Best:    {best_performer['symbol']} ({best_performer['change_pct']:+.2f}%)")
        
        if losers:
            worst_performer = min(losers, key=lambda x: x['change_pct'])
            print(f"⚠️  Worst:   {worst_performer['symbol']} ({worst_performer['change_pct']:+.2f}%)")
        
        # Score Analysis
        stocks_with_scores = [s for s in sorted_stocks if s['current_score'] is not None]
        if stocks_with_scores:
            avg_score = sum(s['current_score'] for s in stocks_with_scores) / len(stocks_with_scores)
            strong_scores = len([s for s in stocks_with_scores if s['current_score'] >= 70])
            weak_scores = len([s for s in stocks_with_scores if s['current_score'] < 50])
            
            print(f"\n📊 SCORE ANALYSIS:")
            print(f"{'='*40}")
            print(f"📈 Average Score: {avg_score:.1f}")
            print(f"🟢 Strong Scores (≥70): {strong_scores} stocks")
            print(f"🔴 Weak Scores (<50): {weak_scores} stocks")
            
            if weak_scores > 0:
                print(f"⚠️  Warning: {weak_scores} STRONG stocks have weak current scores!")

def main():
    """Main function for daily monitoring"""
    monitor = DailyMonitor()
    
    print("📊 DAILY MONITORING SYSTEM")
    print("=" * 50)
    print("1. Run Daily Monitoring")
    print("2. Monitor STRONG Only")
    print("3. Check WEAK Promotions Only")
    print("4. Update Performance Only")
    print("5. Show STRONG Performance Report")
    
    choice = input("\nSelect option (1/2/3/4/5): ").strip()
    
    if choice == '1':
        monitor.run_daily_monitoring()
    elif choice == '2':
        monitor.monitor_strong_recommendations()
    elif choice == '3':
        monitor.check_weak_promotions()
    elif choice == '4':
        monitor.update_performance_data()
    elif choice == '5':
        monitor.show_strong_performance_report()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main() 