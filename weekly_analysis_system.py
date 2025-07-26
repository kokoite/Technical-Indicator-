import sqlite3
import pandas as pd
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from enhanced_strategy_screener import EnhancedStrategyScreener
from recommendations_database import RecommendationsDatabase
import numpy as np

class WeeklyAnalysisSystem:
    """
    Comprehensive weekly analysis system for all 1,288 NSE stocks
    """
    
    def __init__(self, max_workers=5):
        self.screener = EnhancedStrategyScreener(max_workers=max_workers)
        self.rec_db = RecommendationsDatabase()
        self.max_workers = max_workers
        
    def run_full_weekly_analysis(self, min_score=35, batch_size=50):
        """
        Run complete weekly analysis on all stocks in manageable batches
        """
        print(f"\n{'='*100}")
        print(f"🎯 WEEKLY ANALYSIS SYSTEM - ANALYZING ALL NSE STOCKS")
        print(f"{'='*100}")
        print(f"📊 Target: ~1,288 stocks | Minimum Score: {min_score} | Batch Size: {batch_size}")
        print(f"⚡ Workers: {self.max_workers} | Estimated Time: ~45-60 minutes")
        
        start_time = datetime.now()
        
        # Get all stocks from database
        all_stocks = self.get_all_stocks()
        total_stocks = len(all_stocks)
        
        print(f"📋 Found {total_stocks} stocks to analyze")
        print(f"🔄 Processing in batches of {batch_size} stocks...")
        
        all_results = []
        processed_count = 0
        
        # Process stocks in batches to manage memory and API limits
        for i in range(0, total_stocks, batch_size):
            batch_stocks = all_stocks[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_stocks + batch_size - 1) // batch_size
            
            print(f"\n📦 BATCH {batch_num}/{total_batches}: Processing {len(batch_stocks)} stocks...")
            
            batch_results = self.analyze_stock_batch(batch_stocks, min_score)
            all_results.extend(batch_results)
            
            processed_count += len(batch_stocks)
            
            # Progress update
            progress_pct = (processed_count / total_stocks) * 100
            elapsed_time = (datetime.now() - start_time).total_seconds() / 60
            
            print(f"✅ Batch {batch_num} completed | Progress: {processed_count}/{total_stocks} ({progress_pct:.1f}%)")
            print(f"⏰ Elapsed: {elapsed_time:.1f} min | Found: {len(all_results)} actionable stocks")
            
            # Small delay between batches to avoid overwhelming APIs
            if i + batch_size < total_stocks:
                print("⏳ Cooling down for 10 seconds...")
                time.sleep(10)
        
        # Sort all results by score
        all_results.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Save results and generate reports
        self.save_weekly_results(all_results)
        self.generate_weekly_report(all_results, start_time)
        
        return all_results
    
    def get_all_stocks(self):
        """Get all stocks from the NSE scanner database"""
        conn = sqlite3.connect("nse_stock_scanner.db")
        cursor = conn.cursor()
        
        # Get all stocks in price range, ordered by market cap
        cursor.execute('''
            SELECT DISTINCT symbol, company_name, current_price, market_cap, sector
            FROM stocks 
            WHERE current_price BETWEEN 50 AND 1000
            AND market_cap > 0
            ORDER BY market_cap DESC
        ''')
        
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
    
    def analyze_stock_batch(self, stocks, min_score):
        """Analyze a batch of stocks with threading"""
        results = []
        
        # Process stocks sequentially in small batches to avoid overwhelming APIs
        batch_size = 3  # Very small batches to avoid rate limits
        
        for i in range(0, len(stocks), batch_size):
            mini_batch = stocks[i:i+batch_size]
            
            # Process mini-batch with limited threading
            with ThreadPoolExecutor(max_workers=min(2, len(mini_batch))) as executor:
                future_to_stock = {
                    executor.submit(self.screener.analyze_single_stock, stock): stock 
                    for stock in mini_batch
                }
                
                for future in as_completed(future_to_stock):
                    try:
                        result = future.result(timeout=30)  # 30 second timeout
                        if result and result['total_score'] >= min_score:
                            results.append(result)
                        
                    except Exception as e:
                        stock = future_to_stock[future]
                        print(f"❌ Error analyzing {stock['symbol']}: {str(e)}")
            
            # Longer delay between mini-batches
            if i + batch_size < len(stocks):
                print(f"⏳ Processed {i+batch_size}/{len(stocks)} stocks, cooling down...")
                time.sleep(2)  # 2 second delay between mini-batches
        
        return results
    
    def save_weekly_results(self, results):
        """Save all weekly results to recommendations database"""
        if not results:
            print("📝 No actionable stocks found this week")
            return
        
        print(f"\n💾 Saving {len(results)} recommendations to database...")
        
        saved_count = 0
        for result in results:
            try:
                stock_info = result['stock_info']
                symbol = f"{result['symbol']}.NS"
                
                # Save recommendation to database
                rec_id = self.rec_db.save_recommendation(symbol, result, stock_info)
                saved_count += 1
                
            except Exception as e:
                print(f"❌ Error saving {result['symbol']}: {str(e)}")
        
        print(f"✅ Successfully saved {saved_count} recommendations to database")
    
    def generate_weekly_report(self, results, start_time):
        """Generate comprehensive weekly analysis report"""
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n{'='*100}")
        print(f"📊 WEEKLY ANALYSIS REPORT - {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*100}")
        
        # Analysis Summary
        print(f"⏰ Analysis Duration: {duration.total_seconds()/60:.1f} minutes")
        print(f"📈 Total Actionable Stocks: {len(results)}")
        
        if not results:
            print("📝 No actionable stocks found this week")
            return
        
        # Score Distribution
        strong_buy = len([r for r in results if r['total_score'] >= 75])
        buy = len([r for r in results if 60 <= r['total_score'] < 75])
        weak_buy = len([r for r in results if 40 <= r['total_score'] < 60])
        hold = len([r for r in results if r['total_score'] < 40])
        
        print(f"\n🎯 RECOMMENDATION DISTRIBUTION:")
        print(f"   🟢 STRONG BUY (75+):     {strong_buy} stocks")
        print(f"   🟢 BUY (60-74):          {buy} stocks") 
        print(f"   🟡 WEAK BUY (40-59):     {weak_buy} stocks")
        print(f"   ⚪ HOLD (35-39):         {hold} stocks")
        
        # Top Performers
        print(f"\n🏆 TOP 10 RECOMMENDATIONS:")
        print(f"{'Rank':<4} {'Symbol':<12} {'Score':<6} {'Recommendation':<20} {'Price':<8} {'Sector':<15}")
        print(f"{'-'*80}")
        
        for i, result in enumerate(results[:10], 1):
            stock = result['stock_info']
            print(f"{i:<4} {result['symbol']:<12} {result['total_score']:<6.1f} {result['recommendation'][:19]:<20} ₹{stock['current_price']:<7.0f} {stock['sector'][:14]}")
        
        # Sector Analysis
        sector_performance = {}
        for result in results:
            sector = result['stock_info']['sector'] or 'Unknown'
            if sector not in sector_performance:
                sector_performance[sector] = {'count': 0, 'avg_score': 0, 'total_score': 0}
            
            sector_performance[sector]['count'] += 1
            sector_performance[sector]['total_score'] += result['total_score']
            sector_performance[sector]['avg_score'] = sector_performance[sector]['total_score'] / sector_performance[sector]['count']
        
        # Sort sectors by average score
        sorted_sectors = sorted(sector_performance.items(), key=lambda x: x[1]['avg_score'], reverse=True)
        
        print(f"\n🏭 SECTOR PERFORMANCE (Top 10):")
        print(f"{'Sector':<20} {'Stocks':<6} {'Avg Score':<10} {'Performance'}")
        print(f"{'-'*50}")
        
        for sector, data in sorted_sectors[:10]:
            performance = "🟢 Strong" if data['avg_score'] >= 60 else "🟡 Moderate" if data['avg_score'] >= 45 else "🔴 Weak"
            print(f"{sector[:19]:<20} {data['count']:<6} {data['avg_score']:<10.1f} {performance}")
        
        # Save weekly summary to database
        self.save_weekly_summary(results, duration)
    
    def save_weekly_summary(self, results, duration):
        """Save weekly analysis summary to database"""
        conn = sqlite3.connect("weekly_analysis_history.db")
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_date TEXT NOT NULL,
                total_stocks_analyzed INTEGER,
                actionable_stocks INTEGER,
                strong_buy_count INTEGER,
                buy_count INTEGER,
                weak_buy_count INTEGER,
                avg_score REAL,
                best_stock TEXT,
                best_score REAL,
                analysis_duration_minutes REAL,
                top_sector TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Calculate summary stats
        if results:
            strong_buy = len([r for r in results if r['total_score'] >= 75])
            buy = len([r for r in results if 60 <= r['total_score'] < 75])
            weak_buy = len([r for r in results if 40 <= r['total_score'] < 60])
            avg_score = np.mean([r['total_score'] for r in results])
            best_stock = results[0]['symbol']
            best_score = results[0]['total_score']
            
            # Find top sector
            sectors = {}
            for result in results:
                sector = result['stock_info']['sector'] or 'Unknown'
                sectors[sector] = sectors.get(sector, 0) + 1
            top_sector = max(sectors.items(), key=lambda x: x[1])[0] if sectors else 'None'
        else:
            strong_buy = buy = weak_buy = 0
            avg_score = best_score = 0
            best_stock = top_sector = 'None'
        
        # Insert summary
        cursor.execute('''
            INSERT INTO weekly_summaries 
            (analysis_date, total_stocks_analyzed, actionable_stocks, strong_buy_count,
             buy_count, weak_buy_count, avg_score, best_stock, best_score,
             analysis_duration_minutes, top_sector)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().strftime('%Y-%m-%d'),
            1288,  # Total stocks in database
            len(results),
            strong_buy,
            buy,
            weak_buy,
            avg_score,
            best_stock,
            best_score,
            duration.total_seconds() / 60,
            top_sector
        ))
        
        conn.commit()
        conn.close()
    
    def review_performance(self, weeks_back=4):
        """Comprehensive performance review of past recommendations"""
        print(f"\n{'='*100}")
        print(f"📈 PERFORMANCE REVIEW - LAST {weeks_back} WEEKS")
        print(f"{'='*100}")
        
        # Update all performance data
        print("🔄 Updating performance data...")
        self.rec_db.update_performance(days_back=weeks_back*7)
        
        # Get performance data
        df = self.rec_db.get_recommendations(days_back=weeks_back*7)
        
        if df.empty:
            print("📝 No recommendations found for performance review")
            return
        
        # Overall Statistics
        total_recs = len(df)
        valid_returns = df[df['return_pct'].notna()]
        
        if not valid_returns.empty:
            avg_return = valid_returns['return_pct'].mean()
            median_return = valid_returns['return_pct'].median()
            best_return = valid_returns['return_pct'].max()
            worst_return = valid_returns['return_pct'].min()
            positive_returns = len(valid_returns[valid_returns['return_pct'] > 0])
            success_rate = (positive_returns / len(valid_returns)) * 100
            
            # Performance by recommendation type
            buy_performance = valid_returns[valid_returns['recommendation'].str.contains('BUY', na=False)]['return_pct'].mean()
            hold_performance = valid_returns[valid_returns['recommendation'].str.contains('HOLD', na=False)]['return_pct'].mean()
            
            print(f"\n📊 OVERALL PERFORMANCE:")
            print(f"   • Total Recommendations: {total_recs}")
            print(f"   • Average Return: {avg_return:+.2f}%")
            print(f"   • Median Return: {median_return:+.2f}%")
            print(f"   • Best Return: {best_return:+.2f}%")
            print(f"   • Worst Return: {worst_return:+.2f}%")
            print(f"   • Success Rate: {success_rate:.1f}%")
            print(f"   • Buy Signals Avg: {buy_performance:+.2f}%")
            print(f"   • Hold Signals Avg: {hold_performance:+.2f}%")
        
        # Weekly Trends
        self.analyze_weekly_trends(weeks_back)
        
        # Top/Bottom Performers
        self.show_top_bottom_performers(valid_returns)
        
        # Sector Performance Analysis
        self.analyze_sector_performance(valid_returns)
    
    def analyze_weekly_trends(self, weeks_back):
        """Analyze weekly performance trends"""
        conn = sqlite3.connect("weekly_analysis_history.db")
        
        try:
            df = pd.read_sql_query('''
                SELECT analysis_date, actionable_stocks, avg_score, best_score, top_sector
                FROM weekly_summaries 
                ORDER BY analysis_date DESC 
                LIMIT ?
            ''', conn, params=(weeks_back,))
            
            if not df.empty:
                print(f"\n📈 WEEKLY TRENDS:")
                print(f"{'Week':<12} {'Stocks':<8} {'Avg Score':<10} {'Best Score':<10} {'Top Sector'}")
                print(f"{'-'*60}")
                
                for _, row in df.iterrows():
                    print(f"{row['analysis_date']:<12} {row['actionable_stocks']:<8} {row['avg_score']:<10.1f} {row['best_score']:<10.1f} {row['top_sector']}")
                    
        except Exception as e:
            print(f"📝 Weekly trends not available: {str(e)}")
        
        conn.close()
    
    def show_top_bottom_performers(self, valid_returns):
        """Show top and bottom performing stocks"""
        if valid_returns.empty:
            return
            
        print(f"\n🏆 TOP 5 PERFORMERS:")
        top_performers = valid_returns.nlargest(5, 'return_pct')
        for _, row in top_performers.iterrows():
            print(f"   • {row['symbol']}: {row['return_pct']:+.2f}% ({row['recommendation']})")
        
        print(f"\n📉 BOTTOM 5 PERFORMERS:")
        bottom_performers = valid_returns.nsmallest(5, 'return_pct')
        for _, row in bottom_performers.iterrows():
            print(f"   • {row['symbol']}: {row['return_pct']:+.2f}% ({row['recommendation']})")
    
    def analyze_sector_performance(self, valid_returns):
        """Analyze performance by sector"""
        if valid_returns.empty:
            return
            
        sector_perf = valid_returns.groupby('sector')['return_pct'].agg(['mean', 'count']).reset_index()
        sector_perf = sector_perf[sector_perf['count'] >= 2]  # At least 2 stocks
        sector_perf = sector_perf.sort_values('mean', ascending=False)
        
        print(f"\n🏭 SECTOR PERFORMANCE:")
        print(f"{'Sector':<20} {'Avg Return':<12} {'Stocks'}")
        print(f"{'-'*40}")
        
        for _, row in sector_perf.head(10).iterrows():
            print(f"{row['sector'][:19]:<20} {row['mean']:+.2f}%      {row['count']}")

def main():
    """Main function for weekly analysis"""
    analyzer = WeeklyAnalysisSystem(max_workers=5)
    
    print("🎯 WEEKLY ANALYSIS SYSTEM")
    print("=" * 50)
    print("1. Full Weekly Analysis (All 1,288 stocks)")
    print("2. Performance Review (Last 4 weeks)")
    print("3. Both (Recommended)")
    
    choice = input("\nSelect option (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        print("\n🚀 Starting Full Weekly Analysis...")
        results = analyzer.run_full_weekly_analysis(min_score=35, batch_size=100)
    
    if choice in ['2', '3']:
        print("\n📊 Starting Performance Review...")
        analyzer.review_performance(weeks_back=4)
    
    print(f"\n{'='*100}")
    print("✅ WEEKLY ANALYSIS COMPLETED!")
    print(f"{'='*100}")

if __name__ == "__main__":
    main() 