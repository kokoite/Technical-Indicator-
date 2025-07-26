import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time

class EnhancedPerformanceTracker:
    """
    Enhanced performance tracking system for the advanced recommendation system
    Provides separate reports for realized vs unrealized returns
    """
    
    def __init__(self):
        self.db_name = "stock_recommendations.db"
    
    def update_all_performance(self, days_back=None):
        """Update performance for ALL active recommendations regardless of age"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        if days_back is not None:
            # Optional time filter for specific use cases
            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT id, symbol, entry_price, recommendation_date
                FROM recommendations 
                WHERE recommendation_date >= ? AND status = 'ACTIVE' AND is_sold = 0
                ORDER BY recommendation_date DESC
            ''', (cutoff_date,))
        else:
            # Default: ALL active unrealized positions
            cursor.execute('''
                SELECT id, symbol, entry_price, recommendation_date
                FROM recommendations 
                WHERE status = 'ACTIVE' AND is_sold = 0
                ORDER BY recommendation_date DESC
            ''')
        
        recommendations = cursor.fetchall()
        conn.close()
        
        if not recommendations:
            print("📝 No active recommendations to update")
            return
        
        print(f"🔄 Updating performance for {len(recommendations)} active recommendations...")
        
        updated_count = 0
        
        for rec_id, symbol, entry_price, rec_date in recommendations:
            try:
                # Get current price
                ticker = yf.Ticker(f"{symbol}.NS")
                current_data = ticker.history(period="1d")
                
                if not current_data.empty:
                    current_price = current_data['Close'].iloc[-1]
                    return_pct = ((current_price - entry_price) / entry_price) * 100
                    
                    # Calculate days held
                    rec_date_obj = datetime.strptime(rec_date, '%Y-%m-%d')
                    days_held = (datetime.now() - rec_date_obj).days
                    
                    # Update performance tracking
                    conn = sqlite3.connect(self.db_name)
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO performance_tracking 
                        (recommendation_id, current_price, return_pct, days_held, last_updated)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (rec_id, current_price, return_pct, days_held, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    
                    conn.commit()
                    conn.close()
                    
                    updated_count += 1
                
                time.sleep(0.1)  # API rate limit
                
            except Exception as e:
                print(f"❌ Error updating {symbol}: {str(e)}")
        
        print(f"✅ Updated performance for {updated_count} recommendations")
    
    def get_realized_performance_report(self):
        """Generate realized performance report (sold positions)"""
        conn = sqlite3.connect(self.db_name)
        
        query = '''
            SELECT symbol, recommendation_tier, entry_price, sell_price, 
                   realized_return_pct, money_made, sell_date, 
                   recommendation_date, recommendation, sector
            FROM recommendations 
            WHERE is_sold = 1
            ORDER BY sell_date DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def get_unrealized_performance_report(self):
        """Generate unrealized performance report (current holdings)"""
        conn = sqlite3.connect(self.db_name)
        
        query = '''
            SELECT r.symbol, r.recommendation_tier, r.entry_price, r.recommendation_date,
                   r.recommendation, r.sector, r.score, pt.current_price, 
                   pt.return_pct, pt.days_held, pt.last_updated
            FROM recommendations r
            LEFT JOIN performance_tracking pt ON r.id = pt.recommendation_id
            WHERE r.status = 'ACTIVE' AND r.is_sold = 0
            ORDER BY pt.return_pct DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def display_realized_report(self):
        """Display comprehensive realized performance report"""
        df = self.get_realized_performance_report()
        
        print(f"\n{'='*100}")
        print(f"💰 REALIZED PERFORMANCE REPORT (Sold Positions)")
        print(f"{'='*100}")
        
        if df.empty:
            print("📝 No realized trades yet")
            return
        
        # Overall Statistics
        total_trades = len(df)
        avg_return = df['realized_return_pct'].mean()
        total_money_made = df['money_made'].sum()
        best_trade = df.loc[df['realized_return_pct'].idxmax()]
        worst_trade = df.loc[df['realized_return_pct'].idxmin()]
        positive_trades = len(df[df['realized_return_pct'] > 0])
        success_rate = (positive_trades / total_trades) * 100
        
        print(f"📊 OVERALL REALIZED PERFORMANCE:")
        print(f"   • Total Completed Trades: {total_trades}")
        print(f"   • Average Return: {avg_return:+.2f}%")
        print(f"   • Total Money Made: ₹{total_money_made:+.2f}")
        print(f"   • Success Rate: {success_rate:.1f}% ({positive_trades}/{total_trades})")
        print(f"   • Best Trade: {best_trade['symbol']} ({best_trade['realized_return_pct']:+.2f}%)")
        print(f"   • Worst Trade: {worst_trade['symbol']} ({worst_trade['realized_return_pct']:+.2f}%)")
        
        # Performance by Tier
        tier_performance = df.groupby('recommendation_tier').agg({
            'realized_return_pct': ['mean', 'count'],
            'money_made': 'sum'
        }).round(2)
        
        print(f"\n📊 PERFORMANCE BY TIER:")
        for tier in ['STRONG', 'WEAK', 'HOLD']:
            if tier in tier_performance.index:
                tier_data = tier_performance.loc[tier]
                tier_emoji = "🟢" if tier == "STRONG" else "🟡" if tier == "WEAK" else "⚪"
                avg_return = tier_data[('realized_return_pct', 'mean')]
                count = int(tier_data[('realized_return_pct', 'count')])
                total_money = tier_data[('money_made', 'sum')]
                
                print(f"   {tier_emoji} {tier}: {avg_return:+.2f}% avg ({count} trades) - ₹{total_money:+.2f}")
        
        # Recent Trades
        print(f"\n📋 RECENT REALIZED TRADES (Last 10):")
        print(f"{'Date':<12} {'Symbol':<12} {'Tier':<6} {'Return':<8} {'Money':<10} {'Reason'}")
        print(f"{'-'*65}")
        
        for _, row in df.head(10).iterrows():
            tier_emoji = "🟢" if row['recommendation_tier'] == "STRONG" else "🟡"
            date = row['sell_date']
            symbol = row['symbol']
            return_pct = f"{row['realized_return_pct']:+.2f}%"
            money = f"₹{row['money_made']:+.2f}"
            
            print(f"{date:<12} {symbol:<12} {tier_emoji:<6} {return_pct:<8} {money:<10}")
    
    def display_unrealized_report(self):
        """Display comprehensive unrealized performance report"""
        df = self.get_unrealized_performance_report()
        
        print(f"\n{'='*100}")
        print(f"📊 UNREALIZED PERFORMANCE REPORT (Current Holdings)")
        print(f"{'='*100}")
        
        if df.empty:
            print("📝 No current holdings")
            return
        
        # Filter out rows without performance data
        valid_df = df[df['return_pct'].notna()]
        
        if valid_df.empty:
            print("📝 No performance data available for current holdings")
            return
        
        # Overall Statistics
        total_positions = len(valid_df)
        avg_return = valid_df['return_pct'].mean()
        total_unrealized_value = (valid_df['current_price'] - valid_df['entry_price']).sum()
        best_position = valid_df.loc[valid_df['return_pct'].idxmax()]
        worst_position = valid_df.loc[valid_df['return_pct'].idxmin()]
        positive_positions = len(valid_df[valid_df['return_pct'] > 0])
        success_rate = (positive_positions / total_positions) * 100
        
        print(f"📊 OVERALL UNREALIZED PERFORMANCE:")
        print(f"   • Total Active Positions: {total_positions}")
        print(f"   • Average Unrealized Return: {avg_return:+.2f}%")
        print(f"   • Total Unrealized Value: ₹{total_unrealized_value:+.2f}")
        print(f"   • Current Success Rate: {success_rate:.1f}% ({positive_positions}/{total_positions})")
        print(f"   • Best Position: {best_position['symbol']} ({best_position['return_pct']:+.2f}%)")
        print(f"   • Worst Position: {worst_position['symbol']} ({worst_position['return_pct']:+.2f}%)")
        
        # Performance by Tier
        tier_performance = valid_df.groupby('recommendation_tier').agg({
            'return_pct': ['mean', 'count'],
            'current_price': lambda x: ((x - valid_df.loc[x.index, 'entry_price']).sum())
        }).round(2)
        
        print(f"\n📊 UNREALIZED PERFORMANCE BY TIER:")
        for tier in ['STRONG', 'WEAK', 'HOLD']:
            tier_data = valid_df[valid_df['recommendation_tier'] == tier]
            if not tier_data.empty:
                tier_emoji = "🟢" if tier == "STRONG" else "🟡" if tier == "WEAK" else "⚪"
                avg_return = tier_data['return_pct'].mean()
                count = len(tier_data)
                unrealized_value = (tier_data['current_price'] - tier_data['entry_price']).sum()
                
                print(f"   {tier_emoji} {tier}: {avg_return:+.2f}% avg ({count} positions) - ₹{unrealized_value:+.2f}")
        
        # Top Performers
        print(f"\n🏆 TOP 10 UNREALIZED PERFORMERS:")
        print(f"{'Symbol':<12} {'Tier':<6} {'Entry':<8} {'Current':<8} {'Return':<8} {'Days':<5} {'Sector'}")
        print(f"{'-'*70}")
        
        for _, row in valid_df.head(10).iterrows():
            tier_emoji = "🟢" if row['recommendation_tier'] == "STRONG" else "🟡" if row['recommendation_tier'] == "WEAK" else "⚪"
            symbol = row['symbol']
            entry = f"₹{row['entry_price']:.0f}"
            current = f"₹{row['current_price']:.0f}"
            return_pct = f"{row['return_pct']:+.2f}%"
            days = f"{row['days_held']}"
            sector = row['sector'][:12] if row['sector'] else "Unknown"
            
            print(f"{symbol:<12} {tier_emoji:<6} {entry:<8} {current:<8} {return_pct:<8} {days:<5} {sector}")
        
        # Bottom Performers
        print(f"\n📉 BOTTOM 5 UNREALIZED PERFORMERS:")
        print(f"{'Symbol':<12} {'Tier':<6} {'Entry':<8} {'Current':<8} {'Return':<8} {'Days':<5} {'Sector'}")
        print(f"{'-'*70}")
        
        for _, row in valid_df.tail(5).iterrows():
            tier_emoji = "🟢" if row['recommendation_tier'] == "STRONG" else "🟡" if row['recommendation_tier'] == "WEAK" else "⚪"
            symbol = row['symbol']
            entry = f"₹{row['entry_price']:.0f}"
            current = f"₹{row['current_price']:.0f}"
            return_pct = f"{row['return_pct']:+.2f}%"
            days = f"{row['days_held']}"
            sector = row['sector'][:12] if row['sector'] else "Unknown"
            
            print(f"{symbol:<12} {tier_emoji:<6} {entry:<8} {current:<8} {return_pct:<8} {days:<5} {sector}")
    
    def generate_combined_report(self):
        """Generate combined performance report"""
        print(f"\n{'='*100}")
        print(f"📊 COMPREHENSIVE PERFORMANCE ANALYSIS")
        print(f"{'='*100}")
        print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Update performance first
        self.update_all_performance()
        
        # Display both reports
        self.display_realized_report()
        self.display_unrealized_report()
        
        # Combined Summary
        realized_df = self.get_realized_performance_report()
        unrealized_df = self.get_unrealized_performance_report()
        unrealized_valid = unrealized_df[unrealized_df['return_pct'].notna()]
        
        print(f"\n{'='*60}")
        print(f"📊 COMBINED PERFORMANCE SUMMARY")
        print(f"{'='*60}")
        
        if not realized_df.empty:
            realized_money = realized_df['money_made'].sum()
            print(f"💰 Total Realized Profit: ₹{realized_money:+.2f}")
        
        if not unrealized_valid.empty:
            unrealized_money = (unrealized_valid['current_price'] - unrealized_valid['entry_price']).sum()
            print(f"📊 Total Unrealized Profit: ₹{unrealized_money:+.2f}")
        
        if not realized_df.empty and not unrealized_valid.empty:
            total_profit = realized_money + unrealized_money
            print(f"🎯 Total Portfolio Performance: ₹{total_profit:+.2f}")

def main():
    """Main function for performance tracking"""
    tracker = EnhancedPerformanceTracker()
    
    print("📊 ENHANCED PERFORMANCE TRACKER")
    print("=" * 50)
    print("1. Update All Performance Data")
    print("2. Realized Performance Report")
    print("3. Unrealized Performance Report")
    print("4. Combined Performance Report")
    
    choice = input("\nSelect option (1/2/3/4): ").strip()
    
    if choice == '1':
        tracker.update_all_performance()
    elif choice == '2':
        tracker.display_realized_report()
    elif choice == '3':
        tracker.display_unrealized_report()
    elif choice == '4':
        tracker.generate_combined_report()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main() 