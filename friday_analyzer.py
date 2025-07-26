import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from advanced_recommendation_manager import AdvancedRecommendationManager
from weekly_analysis_system import WeeklyAnalysisSystem
import time

class FridayAnalyzer:
    """
    Friday comprehensive analysis system
    - Clean up underperforming STRONG recommendations
    - Run full weekly analysis for new recommendations
    - Update Friday reference prices for WEAK recommendations
    - Generate weekly performance report
    """
    
    def __init__(self):
        self.manager = AdvancedRecommendationManager()
        self.weekly_system = WeeklyAnalysisSystem()
        self.db_name = "stock_recommendations.db"
    
    def run_friday_analysis(self, force_run=False):
        """Main Friday analysis routine
        
        Args:
            force_run (bool): If True, run the analysis for the most recent Friday
        """
        today = datetime.now()
        today_str = today.strftime('%A')
        
        if today_str != 'Friday' and not force_run:
            print(f"📅 Today is {today_str} - This script is designed for Friday analysis")
            print("📊 For daily monitoring, use daily_monitor.py")
            print("💡 Use force_run=True to run for the most recent Friday")
            return
            
        if today_str != 'Friday' and force_run:
            # Find the most recent Friday
            days_since_friday = (today.weekday() - 4) % 7
            last_friday = today - timedelta(days=days_since_friday)
            print(f"📅 Today is {today_str} - Running analysis for last Friday ({last_friday.strftime('%Y-%m-%d')})")
        else:
            print(f"📅 Running Friday analysis for today ({today.strftime('%Y-%m-%d')})")
        
        print(f"\n{'='*100}")
        print(f"📊 FRIDAY COMPREHENSIVE ANALYSIS SYSTEM")
        print(f"{'='*100}")
        print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Clean up underperforming STRONG recommendations
        print("\n🧹 STEP 1: Cleaning up underperforming STRONG recommendations...")
        self.cleanup_strong_recommendations()
        
        # Step 2: Update Friday reference prices for WEAK recommendations
        print("\n📅 STEP 2: Updating Friday reference prices...")
        self.update_friday_prices()
        
        # Step 3: Run full weekly analysis for new recommendations
        print("\n🎯 STEP 3: Running full weekly analysis...")
        self.run_weekly_analysis()
        
        # Step 4: Generate comprehensive weekly report
        print("\n📊 STEP 4: Generating weekly performance report...")
        self.generate_weekly_report()
        
        print(f"\n✅ Friday analysis completed! Ready for next week's monitoring.")
    
    def cleanup_strong_recommendations(self):
        """Clean up underperforming STRONG recommendations"""
        strong_recs = self.manager.get_recommendations_by_tier('STRONG')
        
        if strong_recs.empty:
            print("📝 No STRONG recommendations to clean up")
            return
        
        print(f"🧹 Reviewing {len(strong_recs)} STRONG recommendations for cleanup...")
        
        cleaned_count = 0
        
        for _, rec in strong_recs.iterrows():
            symbol = rec['symbol']
            entry_price = rec['entry_price']
            recommendation_date = rec['recommendation_date']
            
            # Calculate days held
            rec_date = datetime.strptime(recommendation_date, '%Y-%m-%d')
            days_held = (datetime.now() - rec_date).days
            
            try:
                # Get current price
                ticker = yf.Ticker(f"{symbol}.NS")
                current_data = ticker.history(period="1d")
                
                if current_data.empty:
                    print(f"⚠️ No price data for {symbol}")
                    continue
                
                current_price = current_data['Close'].iloc[-1]
                return_pct = ((current_price - entry_price) / entry_price) * 100
                
                # Cleanup criteria: More aggressive on Fridays
                should_cleanup = False
                cleanup_reason = ""
                
                if return_pct <= -5 and days_held >= 7:  # 5% loss after 1 week
                    should_cleanup = True
                    cleanup_reason = f"Weekly cleanup: {return_pct:.2f}% loss after {days_held} days"
                elif return_pct <= -3 and days_held >= 14:  # 3% loss after 2 weeks
                    should_cleanup = True
                    cleanup_reason = f"Bi-weekly cleanup: {return_pct:.2f}% loss after {days_held} days"
                elif days_held >= 30 and return_pct < 2:  # No growth after 30 days
                    should_cleanup = True
                    cleanup_reason = f"Monthly cleanup: Only {return_pct:.2f}% gain after {days_held} days"
                
                if should_cleanup:
                    if self.manager.sell_strong_recommendation(symbol, current_price, cleanup_reason):
                        cleaned_count += 1
                else:
                    status_emoji = "🟢" if return_pct > 5 else "🟡" if return_pct > 0 else "🔴"
                    print(f"{status_emoji} {symbol}: {return_pct:+.2f}% ({days_held}d) - Keeping")
                
                time.sleep(0.2)  # API delay
                
            except Exception as e:
                print(f"❌ Error reviewing {symbol}: {str(e)}")
        
        print(f"🧹 Cleanup complete: {cleaned_count} underperforming positions removed")
    
    def update_friday_prices(self):
        """Update Friday reference prices for WEAK and HOLD recommendations"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Get WEAK and HOLD recommendations
        cursor.execute('''
            SELECT id, symbol FROM recommendations 
            WHERE recommendation_tier IN ('WEAK', 'HOLD') 
            AND status = 'ACTIVE' AND is_sold = 0
        ''')
        
        recommendations = cursor.fetchall()
        conn.close()
        
        if not recommendations:
            print("📝 No WEAK/HOLD recommendations to update")
            return
        
        print(f"📅 Updating Friday prices for {len(recommendations)} WEAK/HOLD recommendations...")
        
        updated_count = 0
        
        for rec_id, symbol in recommendations:
            try:
                # Get current Friday price
                ticker = yf.Ticker(f"{symbol}.NS")
                current_data = ticker.history(period="1d")
                
                if not current_data.empty:
                    friday_price = current_data['Close'].iloc[-1]
                    
                    # Update Friday price in database
                    conn = sqlite3.connect(self.db_name)
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        UPDATE recommendations 
                        SET last_friday_price = ?
                        WHERE id = ?
                    ''', (friday_price, rec_id))
                    
                    conn.commit()
                    conn.close()
                    
                    updated_count += 1
                    print(f"✅ {symbol}: Updated Friday price to ₹{friday_price:.2f}")
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Error updating {symbol}: {str(e)}")
        
        print(f"📅 Updated Friday prices for {updated_count} recommendations")
    
    def run_weekly_analysis(self):
        """Run full weekly analysis and save tiered recommendations"""
        print("🎯 Running comprehensive weekly analysis...")
        
        # Use existing weekly analysis system but with tier classification
        results = self.weekly_system.run_full_weekly_analysis(min_score=35, batch_size=100)
        
        if not results:
            print("📝 No new recommendations from weekly analysis")
            return
        
        print(f"\n💾 Classifying and saving {len(results)} recommendations by tier...")
        
        strong_count = weak_count = hold_count = 0
        
        for result in results:
            score = result['total_score']
            stock_info = result['stock_info']
            symbol = f"{result['symbol']}.NS"
            
            # Classify by tier based on score
            if score >= 70:
                tier = 'STRONG'
                strong_count += 1
            elif score >= 50:
                tier = 'WEAK'
                weak_count += 1
            else:
                tier = 'HOLD'
                hold_count += 1
            
            # Save with tier classification
            self.manager.save_tiered_recommendation(symbol, result, stock_info, tier)
        
        print(f"\n📊 New recommendations saved:")
        print(f"   🟢 STRONG: {strong_count} recommendations")
        print(f"   🟡 WEAK: {weak_count} recommendations")
        print(f"   ⚪ HOLD: {hold_count} recommendations")
    
    def generate_weekly_report(self):
        """Generate comprehensive weekly performance report"""
        print(f"\n{'='*80}")
        print(f"📊 WEEKLY PERFORMANCE REPORT")
        print(f"{'='*80}")
        
        # Get performance summary
        performance = self.manager.get_performance_summary()
        realized_df = performance['realized']
        unrealized_df = performance['unrealized']
        
        # Realized Performance (Sold stocks)
        print(f"\n💰 REALIZED PERFORMANCE (Sold Positions):")
        if not realized_df.empty and realized_df['count'].iloc[0] > 0:
            count = realized_df['count'].iloc[0]
            avg_return = realized_df['avg_return'].iloc[0]
            total_money = realized_df['total_money_made'].iloc[0]
            best_return = realized_df['best_return'].iloc[0]
            worst_return = realized_df['worst_return'].iloc[0]
            
            print(f"   📊 Total Trades: {count}")
            print(f"   📈 Average Return: {avg_return:+.2f}%")
            print(f"   💵 Total Money Made: ₹{total_money:+.2f}")
            print(f"   🏆 Best Trade: {best_return:+.2f}%")
            print(f"   📉 Worst Trade: {worst_return:+.2f}%")
        else:
            print("   📝 No realized trades yet")
        
        # Unrealized Performance (Current holdings)
        print(f"\n📊 UNREALIZED PERFORMANCE (Current Holdings):")
        if not unrealized_df.empty:
            valid_unrealized = unrealized_df[unrealized_df['return_pct'].notna()]
            
            if not valid_unrealized.empty:
                total_positions = len(valid_unrealized)
                avg_unrealized = valid_unrealized['return_pct'].mean()
                positive_positions = len(valid_unrealized[valid_unrealized['return_pct'] > 0])
                success_rate = (positive_positions / total_positions) * 100
                
                print(f"   📊 Active Positions: {total_positions}")
                print(f"   📈 Average Unrealized Return: {avg_unrealized:+.2f}%")
                print(f"   ✅ Positive Positions: {positive_positions} ({success_rate:.1f}%)")
                
                # Show top and bottom performers
                if len(valid_unrealized) >= 5:
                    print(f"\n🏆 TOP 5 UNREALIZED PERFORMERS:")
                    top_5 = valid_unrealized.nlargest(5, 'return_pct')
                    for i, (_, row) in enumerate(top_5.iterrows(), 1):
                        tier_emoji = "🟢" if row['recommendation_tier'] == "STRONG" else "🟡"
                        print(f"   {i}. {row['symbol']}: {row['return_pct']:+.2f}% {tier_emoji}")
            else:
                print("   📝 No performance data available for current holdings")
        else:
            print("   📝 No current holdings")
        
        # Tier Distribution
        self.show_tier_distribution()
        
        # Weekly Activity Summary
        self.show_weekly_activity()
    
    def show_tier_distribution(self):
        """Show current tier distribution"""
        conn = sqlite3.connect(self.db_name)
        
        tier_query = '''
            SELECT recommendation_tier, COUNT(*) as count,
                   AVG(score) as avg_score
            FROM recommendations 
            WHERE status = 'ACTIVE' AND is_sold = 0
            GROUP BY recommendation_tier
            ORDER BY 
                CASE recommendation_tier 
                    WHEN 'STRONG' THEN 1 
                    WHEN 'WEAK' THEN 2 
                    ELSE 3 
                END
        '''
        
        tier_df = pd.read_sql_query(tier_query, conn)
        conn.close()
        
        print(f"\n📋 CURRENT TIER DISTRIBUTION:")
        total_active = tier_df['count'].sum()
        
        for _, row in tier_df.iterrows():
            tier = row['recommendation_tier']
            count = row['count']
            avg_score = row['avg_score']
            percentage = (count / total_active) * 100 if total_active > 0 else 0
            
            tier_emoji = "🟢" if tier == "STRONG" else "🟡" if tier == "WEAK" else "⚪"
            print(f"   {tier_emoji} {tier}: {count} stocks ({percentage:.1f}%) - Avg Score: {avg_score:.1f}")
    
    def show_weekly_activity(self):
        """Show this week's activity summary"""
        conn = sqlite3.connect(self.db_name)
        
        # Get week's date range
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
        
        # Weekly activity
        activity_query = '''
            SELECT 
                COUNT(CASE WHEN is_sold = 1 AND sell_date >= ? THEN 1 END) as sold_this_week,
                COUNT(CASE WHEN promotion_date >= ? THEN 1 END) as promoted_this_week,
                COUNT(CASE WHEN recommendation_date >= ? THEN 1 END) as new_this_week
            FROM recommendations
        '''
        
        activity_df = pd.read_sql_query(activity_query, conn, params=(week_start, week_start, week_start))
        conn.close()
        
        print(f"\n📅 THIS WEEK'S ACTIVITY ({week_start} to {today.strftime('%Y-%m-%d')}):")
        if not activity_df.empty:
            sold = activity_df['sold_this_week'].iloc[0]
            promoted = activity_df['promoted_this_week'].iloc[0]
            new_recs = activity_df['new_this_week'].iloc[0]
            
            print(f"   🔴 Positions Sold: {sold}")
            print(f"   🚀 WEAK → STRONG Promotions: {promoted}")
            print(f"   ✨ New Recommendations: {new_recs}")
        
        print(f"\n⏰ Next Analysis: Monday (Daily monitoring resumes)")

def main():
    """Main function for Friday analysis"""
    analyzer = FridayAnalyzer()
    
    print("📊 FRIDAY COMPREHENSIVE ANALYSIS SYSTEM")
    print("=" * 60)
    print("1. Run Full Friday Analysis")
    print("2. Run for Most Recent Friday")
    print("3. Cleanup STRONG Only")
    print("4. Update Friday Prices Only")
    print("5. Run Weekly Analysis Only")
    print("6. Generate Report Only")
    
    choice = input("\nSelect option (1/2/3/4/5/6): ").strip()
    
    if choice == '1':
        analyzer.run_friday_analysis()
    elif choice == '2':
        analyzer.run_friday_analysis(force_run=True)
    elif choice == '3':
        analyzer.cleanup_strong_recommendations()
    elif choice == '4':
        analyzer.update_friday_prices()
    elif choice == '5':
        analyzer.run_weekly_analysis()
    elif choice == '6':
        analyzer.generate_weekly_report()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main() 