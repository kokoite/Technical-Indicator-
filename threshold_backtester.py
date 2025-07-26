import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from buy_sell_signal_analyzer import BuySellSignalAnalyzer
from sandbox_analyzer import SandboxAnalyzer
import time

class ThresholdBacktester:
    """
    Enhanced backtesting tool using sandbox analysis for clean testing environment
    """
    
    def __init__(self):
        self.db_name = "stock_recommendations.db"  # Original database
        self.sandbox_db = "sandbox_recommendations.db"  # Sandbox database
        self.analyzer = BuySellSignalAnalyzer()
        self.sandbox_analyzer = SandboxAnalyzer()
    
    def get_friday_recommendations(self, threshold=70):
        """Get recommendations from most recent date with specified threshold"""
        conn = sqlite3.connect(self.db_name)
        
        # Get the most recent recommendation date
        date_query = '''
            SELECT recommendation_date, COUNT(*) as count
            FROM recommendations 
            WHERE status = 'ACTIVE'
            AND (is_sold = 0 OR is_sold IS NULL)
            GROUP BY recommendation_date
            ORDER BY recommendation_date DESC
            LIMIT 1
        '''
        
        date_result = pd.read_sql_query(date_query, conn)
        
        if date_result.empty:
            print("❌ No active recommendations found")
            conn.close()
            return None
        
        recent_date = date_result['recommendation_date'].iloc[0]
        print(f"📅 Analyzing recommendations from: {recent_date} ({date_result['count'].iloc[0]} stocks)")
        
        # Get all recommendations from that date
        query = '''
            SELECT symbol, company_name, score, entry_price, recommendation_tier, sector
            FROM recommendations 
            WHERE recommendation_date = ?
            AND status = 'ACTIVE'
            AND (is_sold = 0 OR is_sold IS NULL)
            ORDER BY score DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(recent_date,))
        conn.close()
        
        if df.empty:
            print(f"❌ No recommendations found for {recent_date}")
            return None
        
        # Apply new threshold
        df['new_tier'] = df['score'].apply(lambda x: 
            'STRONG' if x >= threshold else 
            'WEAK' if x >= 50 else 
            'HOLD'
        )
        
        return df, recent_date
    
    def calculate_performance_since_friday(self, recommendations_df, friday_date):
        """Calculate performance from Friday to today"""
        if recommendations_df is None or recommendations_df.empty:
            return None
        
        performance_data = []
        
        print(f"📊 Calculating performance for {len(recommendations_df)} stocks...")
        
        for _, rec in recommendations_df.iterrows():
            symbol = rec['symbol']
            friday_price = rec['entry_price']
            original_tier = rec['recommendation_tier']
            new_tier = rec['new_tier']
            score = rec['score']
            
            try:
                # Get current price
                ticker = yf.Ticker(f"{symbol}.NS")
                current_data = ticker.history(period="5d")
                
                if not current_data.empty:
                    current_price = current_data['Close'].iloc[-1]
                    
                    # Calculate performance
                    price_change = current_price - friday_price
                    price_change_pct = (price_change / friday_price) * 100
                    
                    performance_data.append({
                        'symbol': symbol,
                        'company_name': rec['company_name'],
                        'score': score,
                        'original_tier': original_tier,
                        'new_tier': new_tier,
                        'friday_price': friday_price,
                        'current_price': current_price,
                        'price_change': price_change,
                        'price_change_pct': price_change_pct,
                        'sector': rec['sector']
                    })
                
                time.sleep(0.1)  # API rate limit
                
            except Exception as e:
                print(f"❌ Error getting price for {symbol}: {str(e)}")
        
        return pd.DataFrame(performance_data)
    
    def analyze_threshold_performance(self, threshold=67):
        """Main function to analyze performance with different threshold"""
        print(f"\n{'='*80}")
        print(f"🎯 THRESHOLD BACKTESTING ANALYSIS")
        print(f"{'='*80}")
        print(f"Testing threshold: {threshold} (vs current 70)")
        
        # Get Friday recommendations with new threshold
        result = self.get_friday_recommendations(threshold)
        if result is None:
            return
        
        recommendations_df, friday_date = result
        
        # Calculate performance
        performance_df = self.calculate_performance_since_friday(recommendations_df, friday_date)
        
        if performance_df is None or performance_df.empty:
            print("❌ No performance data available")
            return
        
        # Analyze results
        self.generate_threshold_report(performance_df, threshold, friday_date)
        
        # Generate detailed STRONG recommendations report
        self.generate_strong_recommendations_report(performance_df, threshold, friday_date)
        
        return performance_df
    
    def generate_threshold_report(self, performance_df, threshold, friday_date):
        """Generate comprehensive threshold analysis report"""
        print(f"\n📊 THRESHOLD ANALYSIS REPORT")
        print(f"{'='*60}")
        print(f"📅 Period: {friday_date} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"🎯 Tested Threshold: {threshold} (Current system uses 70)")
        
        # Overall statistics
        total_stocks = len(performance_df)
        avg_performance = performance_df['price_change_pct'].mean()
        positive_stocks = len(performance_df[performance_df['price_change_pct'] > 0])
        negative_stocks = len(performance_df[performance_df['price_change_pct'] < 0])
        
        print(f"\n📈 OVERALL PERFORMANCE:")
        print(f"   Total stocks analyzed: {total_stocks}")
        print(f"   Average performance: {avg_performance:+.2f}%")
        print(f"   Positive performers: {positive_stocks} ({positive_stocks/total_stocks*100:.1f}%)")
        print(f"   Negative performers: {negative_stocks} ({negative_stocks/total_stocks*100:.1f}%)")
        
        # Performance by new tier classification
        print(f"\n🏆 PERFORMANCE BY NEW TIER (Threshold: {threshold}):")
        
        for tier in ['STRONG', 'WEAK', 'HOLD']:
            tier_data = performance_df[performance_df['new_tier'] == tier]
            if not tier_data.empty:
                tier_avg = tier_data['price_change_pct'].mean()
                tier_count = len(tier_data)
                tier_positive = len(tier_data[tier_data['price_change_pct'] > 0])
                
                tier_emoji = "🟢" if tier == "STRONG" else "🟡" if tier == "WEAK" else "⚪"
                print(f"   {tier_emoji} {tier}: {tier_count} stocks, Avg: {tier_avg:+.2f}%, Winners: {tier_positive}/{tier_count}")
        
        # Compare with original tier classification
        print(f"\n🔄 COMPARISON WITH ORIGINAL SYSTEM (Threshold: 70):")
        
        for tier in ['STRONG', 'WEAK', 'HOLD']:
            original_data = performance_df[performance_df['original_tier'] == tier]
            if not original_data.empty:
                orig_avg = original_data['price_change_pct'].mean()
                orig_count = len(original_data)
                orig_positive = len(original_data[original_data['price_change_pct'] > 0])
                
                tier_emoji = "🟢" if tier == "STRONG" else "🟡" if tier == "WEAK" else "⚪"
                print(f"   {tier_emoji} {tier} (Original): {orig_count} stocks, Avg: {orig_avg:+.2f}%, Winners: {orig_positive}/{orig_count}")
        
        # Show stocks that would change tier
        print(f"\n🔄 STOCKS THAT WOULD CHANGE TIER:")
        tier_changes = performance_df[performance_df['original_tier'] != performance_df['new_tier']]
        
        if not tier_changes.empty:
            for _, stock in tier_changes.iterrows():
                change_emoji = "⬆️" if stock['new_tier'] == 'STRONG' else "⬇️"
                print(f"   {change_emoji} {stock['symbol']}: {stock['original_tier']} → {stock['new_tier']} "
                      f"(Score: {stock['score']:.1f}, Performance: {stock['price_change_pct']:+.2f}%)")
        else:
            print("   No tier changes with this threshold")
        
        # Top and bottom performers
        print(f"\n🏆 TOP 10 PERFORMERS:")
        top_performers = performance_df.nlargest(10, 'price_change_pct')
        for _, stock in top_performers.iterrows():
            tier_emoji = "🟢" if stock['new_tier'] == "STRONG" else "🟡" if stock['new_tier'] == "WEAK" else "⚪"
            print(f"   {tier_emoji} {stock['symbol']:<12} {stock['price_change_pct']:+6.2f}% "
                  f"(Score: {stock['score']:.1f}, {stock['new_tier']})")
        
        print(f"\n📉 BOTTOM 10 PERFORMERS:")
        bottom_performers = performance_df.nsmallest(10, 'price_change_pct')
        for _, stock in bottom_performers.iterrows():
            tier_emoji = "🟢" if stock['new_tier'] == "STRONG" else "🟡" if stock['new_tier'] == "WEAK" else "⚪"
            print(f"   {tier_emoji} {stock['symbol']:<12} {stock['price_change_pct']:+6.2f}% "
                  f"(Score: {stock['score']:.1f}, {stock['new_tier']})")
    
    def generate_strong_recommendations_report(self, performance_df, threshold, friday_date):
        """Generate detailed report specifically for STRONG recommendations"""
        strong_stocks = performance_df[performance_df['new_tier'] == 'STRONG']
        
        if strong_stocks.empty:
            print(f"\n❌ No STRONG recommendations found with threshold {threshold}")
            return
        
        print(f"\n{'='*80}")
        print(f"📊 DETAILED STRONG RECOMMENDATIONS REPORT")
        print(f"{'='*80}")
        print(f"🎯 Threshold: {threshold} | Period: {friday_date} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"📈 Total STRONG stocks: {len(strong_stocks)}")
        
        # Performance statistics
        avg_performance = strong_stocks['price_change_pct'].mean()
        median_performance = strong_stocks['price_change_pct'].median()
        best_performance = strong_stocks['price_change_pct'].max()
        worst_performance = strong_stocks['price_change_pct'].min()
        positive_count = len(strong_stocks[strong_stocks['price_change_pct'] > 0])
        win_rate = (positive_count / len(strong_stocks)) * 100
        
        print(f"\n📊 PERFORMANCE STATISTICS:")
        print(f"   Average Return: {avg_performance:+.2f}%")
        print(f"   Median Return:  {median_performance:+.2f}%")
        print(f"   Best Return:    {best_performance:+.2f}%")
        print(f"   Worst Return:   {worst_performance:+.2f}%")
        print(f"   Win Rate:       {win_rate:.1f}% ({positive_count}/{len(strong_stocks)})")
        
        # Risk analysis
        volatility = strong_stocks['price_change_pct'].std()
        risk_adjusted_return = avg_performance / volatility if volatility != 0 else 0
        
        print(f"\n⚖️ RISK ANALYSIS:")
        print(f"   Volatility (Std Dev): {volatility:.2f}%")
        print(f"   Risk-Adjusted Return: {risk_adjusted_return:.2f}")
        
        # Performance categories
        excellent = strong_stocks[strong_stocks['price_change_pct'] >= 5]
        good = strong_stocks[(strong_stocks['price_change_pct'] >= 2) & (strong_stocks['price_change_pct'] < 5)]
        moderate = strong_stocks[(strong_stocks['price_change_pct'] >= 0) & (strong_stocks['price_change_pct'] < 2)]
        poor = strong_stocks[strong_stocks['price_change_pct'] < 0]
        
        print(f"\n📈 PERFORMANCE CATEGORIES:")
        print(f"   🟢 Excellent (≥5%):  {len(excellent)} stocks ({len(excellent)/len(strong_stocks)*100:.1f}%)")
        print(f"   🟡 Good (2-5%):       {len(good)} stocks ({len(good)/len(strong_stocks)*100:.1f}%)")
        print(f"   ⚪ Moderate (0-2%):   {len(moderate)} stocks ({len(moderate)/len(strong_stocks)*100:.1f}%)")
        print(f"   🔴 Poor (<0%):        {len(poor)} stocks ({len(poor)/len(strong_stocks)*100:.1f}%)")
        
        # Sector analysis
        print(f"\n🏭 SECTOR ANALYSIS:")
        sector_performance = strong_stocks.groupby('sector').agg({
            'price_change_pct': ['mean', 'count'],
            'symbol': 'count'
        }).round(2)
        
        for sector in sector_performance.index:
            sector_avg = sector_performance.loc[sector, ('price_change_pct', 'mean')]
            sector_count = sector_performance.loc[sector, ('price_change_pct', 'count')]
            sector_emoji = "🟢" if sector_avg > 2 else "🟡" if sector_avg > 0 else "🔴"
            print(f"   {sector_emoji} {sector:<20} {sector_avg:+6.2f}% ({sector_count} stocks)")
        
        # Score vs Performance analysis
        print(f"\n📊 SCORE vs PERFORMANCE ANALYSIS:")
        score_ranges = [
            (threshold, threshold+2, f"{threshold}-{threshold+2}"),
            (threshold+2, threshold+5, f"{threshold+2}-{threshold+5}"),
            (threshold+5, 100, f"{threshold+5}+")
        ]
        
        for min_score, max_score, label in score_ranges:
            range_stocks = strong_stocks[
                (strong_stocks['score'] >= min_score) & 
                (strong_stocks['score'] < max_score)
            ]
            if not range_stocks.empty:
                range_avg = range_stocks['price_change_pct'].mean()
                range_count = len(range_stocks)
                range_emoji = "🟢" if range_avg > 2 else "🟡" if range_avg > 0 else "🔴"
                print(f"   {range_emoji} Score {label}: {range_avg:+6.2f}% ({range_count} stocks)")
        
        # Detailed stock list
        print(f"\n📋 DETAILED STRONG RECOMMENDATIONS LIST:")
        print(f"{'Rank':<4} {'Symbol':<12} {'Score':<6} {'Return':<8} {'Sector':<20} {'Status'}")
        print(f"{'-'*80}")
        
        # Sort by performance
        strong_sorted = strong_stocks.sort_values('price_change_pct', ascending=False)
        
        for idx, (_, stock) in enumerate(strong_sorted.iterrows(), 1):
            status_emoji = "🟢" if stock['price_change_pct'] > 2 else \
                          "🟡" if stock['price_change_pct'] > 0 else "🔴"
            
            sector_short = (stock['sector'][:19] + "..") if len(str(stock['sector'])) > 19 else stock['sector']
            
            print(f"{idx:<4} {stock['symbol']:<12} {stock['score']:<6.1f} "
                  f"{stock['price_change_pct']:+6.2f}% {sector_short:<20} {status_emoji}")
        
        # Comparison with original system
        original_strong = performance_df[performance_df['original_tier'] == 'STRONG']
        if not original_strong.empty:
            orig_avg = original_strong['price_change_pct'].mean()
            orig_win_rate = (len(original_strong[original_strong['price_change_pct'] > 0]) / len(original_strong)) * 100
            
            print(f"\n🔄 COMPARISON WITH ORIGINAL SYSTEM:")
            print(f"   New Threshold ({threshold}):     {len(strong_stocks)} stocks, {avg_performance:+.2f}% avg, {win_rate:.1f}% win rate")
            print(f"   Original Threshold (70): {len(original_strong)} stocks, {orig_avg:+.2f}% avg, {orig_win_rate:.1f}% win rate")
            
            improvement = avg_performance - orig_avg
            improvement_emoji = "🟢" if improvement > 0 else "🔴" if improvement < 0 else "⚪"
            print(f"   {improvement_emoji} Performance Difference: {improvement:+.2f}%")
        
        # Investment simulation
        print(f"\n💰 INVESTMENT SIMULATION (₹10,000 per stock):")
        total_investment = len(strong_stocks) * 10000
        total_returns = sum(stock['price_change_pct'] * 100 for _, stock in strong_stocks.iterrows())
        total_value = total_investment + total_returns
        portfolio_return = (total_value - total_investment) / total_investment * 100
        
        print(f"   Total Investment: ₹{total_investment:,}")
        print(f"   Total Value:      ₹{total_value:,.0f}")
        print(f"   Total P&L:        ₹{total_returns:+,.0f}")
        print(f"   Portfolio Return: {portfolio_return:+.2f}%")
        
        # Recommendations
        print(f"\n💡 ANALYSIS RECOMMENDATIONS:")
        if win_rate >= 80 and avg_performance >= 2:
            print("   🟢 EXCELLENT: This threshold shows strong performance - consider adopting")
        elif win_rate >= 70 and avg_performance >= 1:
            print("   🟡 GOOD: This threshold shows decent performance - worth considering")
        elif win_rate >= 60:
            print("   ⚪ MODERATE: This threshold shows mixed results - needs more analysis")
        else:
            print("   🔴 POOR: This threshold shows weak performance - not recommended")
    
    def compare_multiple_thresholds(self, thresholds=[65, 67, 70, 72, 75]):
        """Compare performance across multiple thresholds"""
        print(f"\n{'='*80}")
        print(f"🎯 MULTI-THRESHOLD COMPARISON")
        print(f"{'='*80}")
        
        results_summary = []
        
        for threshold in thresholds:
            print(f"\n🔍 Testing threshold: {threshold}")
            
            # Get recommendations with this threshold
            result = self.get_friday_recommendations(threshold)
            if result is None:
                continue
            
            recommendations_df, friday_date = result
            performance_df = self.calculate_performance_since_friday(recommendations_df, friday_date)
            
            if performance_df is None or performance_df.empty:
                continue
            
            # Calculate summary stats for STRONG tier only
            strong_stocks = performance_df[performance_df['new_tier'] == 'STRONG']
            
            if not strong_stocks.empty:
                strong_avg = strong_stocks['price_change_pct'].mean()
                strong_count = len(strong_stocks)
                strong_positive = len(strong_stocks[strong_stocks['price_change_pct'] > 0])
                strong_win_rate = (strong_positive / strong_count) * 100
                
                results_summary.append({
                    'threshold': threshold,
                    'strong_count': strong_count,
                    'strong_avg_return': strong_avg,
                    'strong_win_rate': strong_win_rate
                })
        
        # Display comparison
        print(f"\n📊 THRESHOLD COMPARISON SUMMARY:")
        print(f"{'Threshold':<10} {'Count':<8} {'Avg Return':<12} {'Win Rate':<10} {'Rating'}")
        print(f"{'-'*60}")
        
        for result in results_summary:
            rating = "🟢 Excellent" if result['strong_win_rate'] > 70 and result['strong_avg_return'] > 2 else \
                    "🟡 Good" if result['strong_win_rate'] > 60 and result['strong_avg_return'] > 1 else \
                    "🔴 Poor"
            
            print(f"{result['threshold']:<10} {result['strong_count']:<8} "
                  f"{result['strong_avg_return']:+8.2f}% {result['strong_win_rate']:>7.1f}% {rating}")
        
        return results_summary
    
    def run_sandbox_threshold_test(self, threshold=67, stock_limit=100):
        """
        NEW: Run threshold test using sandbox analysis
        This creates a clean testing environment separate from main database
        """
        print(f"\n{'='*100}")
        print(f"🧪 SANDBOX THRESHOLD TESTING")
        print(f"{'='*100}")
        print(f"🎯 Testing threshold: {threshold}")
        print(f"📊 Stock limit: {stock_limit if stock_limit else 'All stocks'}")
        print(f"🗄️  Using sandbox database for clean testing")
        
        # Run sandbox analysis with specified threshold
        print(f"\n🔬 Running sandbox analysis...")
        results = self.sandbox_analyzer.run_full_sandbox_analysis(
            threshold=threshold, 
            limit=stock_limit,
            batch_size=20
        )
        
        if not results:
            print("❌ No results from sandbox analysis")
            return None
        
        # Show performance report
        print(f"\n📊 Generating performance report...")
        self.sandbox_analyzer.show_sandbox_performance_report()
        
        return results
    
    def compare_sandbox_thresholds(self, thresholds=[65, 67, 70, 72, 75], stock_limit=50):
        """
        NEW: Compare multiple thresholds using sandbox analysis
        Much faster and cleaner than using existing database
        """
        print(f"\n{'='*100}")
        print(f"🧪 SANDBOX MULTI-THRESHOLD COMPARISON")
        print(f"{'='*100}")
        print(f"📊 Testing thresholds: {thresholds}")
        print(f"📈 Stock limit per test: {stock_limit}")
        
        comparison_results = []
        
        for i, threshold in enumerate(thresholds):
            print(f"\n{'='*60}")
            print(f"🔍 TEST {i+1}/{len(thresholds)}: Threshold {threshold}")
            print(f"{'='*60}")
            
            # Run sandbox analysis for this threshold
            results = self.sandbox_analyzer.run_full_sandbox_analysis(
                threshold=threshold,
                limit=stock_limit,
                batch_size=15
            )
            
            if not results:
                print(f"❌ No results for threshold {threshold}")
                continue
            
            # Calculate performance metrics
            strong_stocks = [r for r in results if r['recommendation_tier'] == 'STRONG']
            
            if strong_stocks:
                # Get current performance
                performance = self.sandbox_analyzer.get_sandbox_strong_performance()
                
                if performance:
                    comparison_results.append({
                        'threshold': threshold,
                        'strong_count': len(strong_stocks),
                        'total_return_pct': performance['total_return_pct'],
                        'win_rate': len([s for s in performance['stocks'] if s['change_pct'] > 0]) / len(performance['stocks']) * 100,
                        'avg_score': sum(s['total_score'] for s in strong_stocks) / len(strong_stocks),
                        'best_performer': max(performance['stocks'], key=lambda x: x['change_pct'])['change_pct'],
                        'worst_performer': min(performance['stocks'], key=lambda x: x['change_pct'])['change_pct']
                    })
            
            # Small delay between tests
            print("⏳ Cooling down before next test...")
            time.sleep(3)
        
        # Generate comparison report
        self.generate_sandbox_comparison_report(comparison_results)
        
        return comparison_results
    
    def generate_sandbox_comparison_report(self, results):
        """Generate comprehensive comparison report from sandbox tests"""
        if not results:
            print("❌ No results to compare")
            return
        
        print(f"\n{'='*100}")
        print(f"📊 SANDBOX THRESHOLD COMPARISON REPORT")
        print(f"{'='*100}")
        
        # Summary table
        print(f"\n📋 COMPARISON SUMMARY:")
        print(f"{'Threshold':<10} {'Count':<8} {'Return%':<10} {'Win%':<8} {'Score':<8} {'Best%':<8} {'Worst%':<8} {'Rating'}")
        print(f"{'-'*80}")
        
        for result in sorted(results, key=lambda x: x['total_return_pct'], reverse=True):
            # Rating based on return and win rate
            if result['total_return_pct'] > 3 and result['win_rate'] > 80:
                rating = "🟢 Excellent"
            elif result['total_return_pct'] > 1 and result['win_rate'] > 70:
                rating = "🟡 Good"
            elif result['total_return_pct'] > 0 and result['win_rate'] > 60:
                rating = "⚪ Fair"
            else:
                rating = "🔴 Poor"
            
            print(f"{result['threshold']:<10} "
                  f"{result['strong_count']:<8} "
                  f"{result['total_return_pct']:+7.2f}% "
                  f"{result['win_rate']:>6.1f}% "
                  f"{result['avg_score']:>6.1f} "
                  f"{result['best_performer']:+6.2f}% "
                  f"{result['worst_performer']:+6.2f}% "
                  f"{rating}")
        
        # Find best threshold
        best_threshold = max(results, key=lambda x: x['total_return_pct'])
        
        print(f"\n🏆 BEST PERFORMING THRESHOLD:")
        print(f"   🎯 Threshold: {best_threshold['threshold']}")
        print(f"   📈 Return: {best_threshold['total_return_pct']:+.2f}%")
        print(f"   🎯 Win Rate: {best_threshold['win_rate']:.1f}%")
        print(f"   📊 Strong Count: {best_threshold['strong_count']}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if best_threshold['total_return_pct'] > 3:
            print(f"   ✅ Threshold {best_threshold['threshold']} shows excellent performance")
            print(f"   🚀 Consider adopting this threshold for better returns")
        elif best_threshold['total_return_pct'] > 1:
            print(f"   🟡 Threshold {best_threshold['threshold']} shows good performance")
            print(f"   📈 Worth considering for implementation")
        else:
            print(f"   ⚠️  All thresholds show modest performance")
            print(f"   🔍 Consider testing with different stock sets or timeframes")

def main():
    """Main function to run threshold backtesting"""
    backtester = ThresholdBacktester()
    
    print("🎯 ENHANCED THRESHOLD BACKTESTING TOOL")
    print("=" * 60)
    print("📊 LEGACY METHODS (using existing database):")
    print("1. Test specific threshold (67) - Legacy")
    print("2. Compare multiple thresholds - Legacy")
    print("3. Custom threshold test - Legacy")
    print()
    print("🧪 NEW SANDBOX METHODS (clean testing environment):")
    print("4. Sandbox Threshold Test (Quick - 50 stocks)")
    print("5. Sandbox Threshold Test (Medium - 100 stocks)")
    print("6. Sandbox Multi-Threshold Comparison")
    print("7. Custom Sandbox Analysis")
    
    choice = input("\nSelect option (1-7): ").strip()
    
    if choice == '1':
        # Legacy: Test threshold 67
        performance_df = backtester.analyze_threshold_performance(67)
        
    elif choice == '2':
        # Legacy: Compare multiple thresholds
        results = backtester.compare_multiple_thresholds([65, 67, 70, 72, 75])
        
    elif choice == '3':
        # Legacy: Custom threshold
        try:
            custom_threshold = float(input("Enter threshold value (e.g., 67): "))
            performance_df = backtester.analyze_threshold_performance(custom_threshold)
        except ValueError:
            print("Invalid threshold value")
    
    elif choice == '4':
        # NEW: Sandbox test - Quick (50 stocks)
        backtester.run_sandbox_threshold_test(threshold=67, stock_limit=50)
        
    elif choice == '5':
        # NEW: Sandbox test - Medium (100 stocks)
        backtester.run_sandbox_threshold_test(threshold=67, stock_limit=100)
        
    elif choice == '6':
        # NEW: Sandbox multi-threshold comparison
        backtester.compare_sandbox_thresholds(
            thresholds=[65, 67, 70, 72, 75], 
            stock_limit=50
        )
        
    elif choice == '7':
        # NEW: Custom sandbox analysis
        try:
            threshold = float(input("Enter threshold (e.g., 67): "))
            limit = input("Enter stock limit (press Enter for 100): ").strip()
            limit = int(limit) if limit else 100
            
            backtester.run_sandbox_threshold_test(threshold=threshold, stock_limit=limit)
            
        except ValueError:
            print("Invalid input values")
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main() 