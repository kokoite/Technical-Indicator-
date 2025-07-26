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
        """Monitor STRONG recommendations for selling criteria"""
        strong_recs = self.manager.get_recommendations_by_tier('STRONG')
        
        if strong_recs.empty:
            print("📝 No STRONG recommendations to monitor")
            return
        
        print(f"📊 Monitoring {len(strong_recs)} STRONG recommendations...")
        
        sells_executed = 0
        
        for _, rec in strong_recs.iterrows():
            symbol = rec['symbol']
            entry_price = rec['entry_price']
            
            try:
                # Get current price
                ticker = yf.Ticker(f"{symbol}.NS")
                current_data = ticker.history(period="1d")
                
                if current_data.empty:
                    print(f"⚠️ No price data for {symbol}")
                    continue
                
                current_price = current_data['Close'].iloc[-1]
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
                
                # Small delay to respect API limits
                time.sleep(0.2)
                
            except Exception as e:
                print(f"❌ Error monitoring {symbol}: {str(e)}")
        
        print(f"📊 Monitoring complete: {sells_executed} positions sold")
    
    def check_weak_promotions(self):
        """Check WEAK recommendations for promotion to STRONG"""
        weak_recs = self.manager.get_recommendations_by_tier('WEAK')
        
        if weak_recs.empty:
            print("📝 No WEAK recommendations to check for promotion")
            return
        
        print(f"📊 Checking {len(weak_recs)} WEAK recommendations for promotion...")
        
        promotions_executed = 0
        
        for _, rec in weak_recs.iterrows():
            symbol = rec['symbol']
            last_friday_price = rec['last_friday_price']
            
            if not last_friday_price or last_friday_price == 0:
                print(f"⚠️ {symbol}: No Friday price reference, skipping...")
                continue
            
            try:
                # Get current price
                ticker = yf.Ticker(f"{symbol}.NS")
                current_data = ticker.history(period="1d")
                
                if current_data.empty:
                    print(f"⚠️ No price data for {symbol}")
                    continue
                
                current_price = current_data['Close'].iloc[-1]
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
                
                # Small delay to respect API limits
                time.sleep(0.2)
                
            except Exception as e:
                print(f"❌ Error checking {symbol}: {str(e)}")
        
        print(f"🚀 Promotion check complete: {promotions_executed} stocks promoted")
    
    def update_performance_data(self):
        """Update performance data for all active recommendations"""
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
        
        updated_count = 0
        
        for rec_id, symbol, entry_price in active_recs:
            try:
                # Get current price
                ticker = yf.Ticker(f"{symbol}.NS")
                current_data = ticker.history(period="1d")
                
                if not current_data.empty:
                    current_price = current_data['Close'].iloc[-1]
                    return_pct = ((current_price - entry_price) / entry_price) * 100
                    
                    # Update performance tracking table
                    conn = sqlite3.connect(self.db_name)
                    cursor = conn.cursor()
                    
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
                    
                    conn.commit()
                    conn.close()
                    
                    updated_count += 1
                
                time.sleep(0.1)  # Small delay
                
            except Exception as e:
                print(f"❌ Error updating {symbol}: {str(e)}")
        
        print(f"✅ Updated performance for {updated_count} recommendations")
    
    def get_strong_performance_summary(self):
        """Get performance summary for STRONG recommendations"""
        strong_recs = self.manager.get_recommendations_by_tier('STRONG')
        
        if strong_recs.empty:
            return None
        
        performance_data = []
        total_invested = 0
        total_current_value = 0
        total_pnl = 0
        
        for _, rec in strong_recs.iterrows():
            symbol = rec['symbol']
            entry_price = rec['entry_price']
            
            try:
                # Get current price - fetch 2 days to calculate daily change
                ticker = yf.Ticker(f"{symbol}.NS")
                current_data = ticker.history(period="2d")  # Get 2 days of data
                
                if not current_data.empty:
                    current_price = current_data['Close'].iloc[-1]
                    price_change_pct = ((current_price - entry_price) / entry_price) * 100
                    money_change = current_price - entry_price  # Per share
                    
                    # Calculate day change (today vs yesterday)
                    day_change_pct = 0
                    if len(current_data) >= 2:
                        yesterday_close = current_data['Close'].iloc[-2]
                        day_change_pct = ((current_price - yesterday_close) / yesterday_close) * 100
                    else:
                        # Fallback: if only 1 day available, show 0
                        day_change_pct = 0
                    
                    performance_data.append({
                        'symbol': symbol,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'change_pct': price_change_pct,
                        'money_change': money_change,
                        'day_change_pct': day_change_pct
                    })
                    
                    # Assuming 1 share per recommendation for calculation
                    total_invested += entry_price
                    total_current_value += current_price
                    total_pnl += money_change
                
                time.sleep(0.1)  # API delay
                
            except Exception as e:
                print(f"❌ Error getting performance for {symbol}: {str(e)}")
        
        if performance_data:
            total_return_pct = ((total_current_value - total_invested) / total_invested) * 100
            
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
        print(f"{'='*95}")
        print(f"{'Stock':<12} {'Entry':<10} {'Current':<10} {'Total %':<10} {'Day %':<8} {'P&L (₹)':<10} {'Status'}")
        print(f"{'-'*95}")
        
        # Sort by performance (best first)
        sorted_stocks = sorted(performance['stocks'], key=lambda x: x['change_pct'], reverse=True)
        
        for stock in sorted_stocks:
            emoji = "🟢" if stock['change_pct'] >= 0 else "🔴"
            status = "Profit" if stock['change_pct'] >= 0 else "Loss"
            
            # Day change emoji
            day_emoji = "📈" if stock['day_change_pct'] > 0 else "📉" if stock['day_change_pct'] < 0 else "➖"
            
            print(f"{stock['symbol']:<12} "
                  f"₹{stock['entry_price']:<9.2f} "
                  f"₹{stock['current_price']:<9.2f} "
                  f"{stock['change_pct']:>+8.2f}% "
                  f"{day_emoji}{stock['day_change_pct']:>+6.2f}% "
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