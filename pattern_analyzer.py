#!/usr/bin/env python3
"""
Pattern Analyzer - Analyze score and price progression patterns across stocks
"""

import sqlite3
import pandas as pd
from typing import Dict, List, Tuple
from collections import Counter

class PatternAnalyzer:
    def __init__(self, db_path: str = "sandbox_recommendations.db"):
        self.db_path = db_path
        
    def get_stock_progression_data(self) -> pd.DataFrame:
        """Get progression data for all stocks with 4 weeks of data"""
        query = """
        WITH stock_weeks AS (
            SELECT symbol, friday_date, total_score, friday_price,
                   ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY friday_date) as week_num
            FROM friday_stocks_analysis
            WHERE symbol IN (
                SELECT symbol 
                FROM friday_stocks_analysis 
                GROUP BY symbol 
                HAVING COUNT(*) = 4
            )
        )
        SELECT symbol,
               MAX(CASE WHEN week_num = 1 THEN total_score END) as week1_score,
               MAX(CASE WHEN week_num = 2 THEN total_score END) as week2_score,
               MAX(CASE WHEN week_num = 3 THEN total_score END) as week3_score,
               MAX(CASE WHEN week_num = 4 THEN total_score END) as week4_score,
               MAX(CASE WHEN week_num = 1 THEN friday_price END) as week1_price,
               MAX(CASE WHEN week_num = 2 THEN friday_price END) as week2_price,
               MAX(CASE WHEN week_num = 3 THEN friday_price END) as week3_price,
               MAX(CASE WHEN week_num = 4 THEN friday_price END) as week4_price,
               MAX(CASE WHEN week_num = 1 THEN friday_date END) as week1_date,
               MAX(CASE WHEN week_num = 4 THEN friday_date END) as week4_date
        FROM stock_weeks
        GROUP BY symbol
        HAVING COUNT(*) = 4
        ORDER BY symbol
        """
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn)
    
    def get_detailed_stock_data(self, symbol: str) -> Dict:
        """Get detailed week-by-week data for a specific stock"""
        query = """
        SELECT friday_date, total_score, friday_price
        FROM friday_stocks_analysis 
        WHERE symbol = ?
        ORDER BY friday_date
        """
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=[symbol])
            
        if len(df) == 4:
            return {
                'week1': {'date': df.iloc[0]['friday_date'], 'score': df.iloc[0]['total_score'], 'price': df.iloc[0]['friday_price']},
                'week2': {'date': df.iloc[1]['friday_date'], 'score': df.iloc[1]['total_score'], 'price': df.iloc[1]['friday_price']},
                'week3': {'date': df.iloc[2]['friday_date'], 'score': df.iloc[2]['total_score'], 'price': df.iloc[2]['friday_price']},
                'week4': {'date': df.iloc[3]['friday_date'], 'score': df.iloc[3]['total_score'], 'price': df.iloc[3]['friday_price']}
            }
        return None
    
    def format_price_progression(self, data: Dict, pattern: str) -> str:
        """Format price progression showing each phase of the pattern"""
        if not data:
            return "No data"
            
        prices = [data['week1']['price'], data['week2']['price'], data['week3']['price'], data['week4']['price']]
        
        # Calculate phase changes
        phase1_change = ((prices[1] - prices[0]) / prices[0] * 100) if prices[0] != 0 else 0
        phase2_change = ((prices[2] - prices[1]) / prices[1] * 100) if prices[1] != 0 else 0  
        phase3_change = ((prices[3] - prices[2]) / prices[2] * 100) if prices[2] != 0 else 0
        
        # Format with pattern indicators
        phase1_indicator = pattern[0]  # D, I, or =
        phase2_indicator = pattern[1] if len(pattern) > 1 else ""
        phase3_indicator = pattern[2] if len(pattern) > 2 else ""
        
        # Create progression string
        progression = f"₹{prices[0]:.0f}"
        
        if phase1_indicator:
            arrow = "↓" if phase1_indicator == 'D' else "↑" if phase1_indicator == 'I' else "→"
            progression += f" {arrow}{phase1_change:+.1f}% ₹{prices[1]:.0f}"
            
        if phase2_indicator:
            arrow = "↓" if phase2_indicator == 'D' else "↑" if phase2_indicator == 'I' else "→"
            progression += f" {arrow}{phase2_change:+.1f}% ₹{prices[2]:.0f}"
            
        if phase3_indicator:
            arrow = "↓" if phase3_indicator == 'D' else "↑" if phase3_indicator == 'I' else "→"
            progression += f" {arrow}{phase3_change:+.1f}% ₹{prices[3]:.0f}"
            
        return progression
    
    def calculate_pattern(self, values: List[float], pattern_type: str = "score") -> str:
        """Calculate D/I pattern from a list of values"""
        if len(values) != 4:
            return "INCOMPLETE"
        
        pattern = ""
        for i in range(1, len(values)):
            if values[i] > values[i-1]:
                pattern += "I"  # Increasing
            elif values[i] < values[i-1]:
                pattern += "D"  # Decreasing
            else:
                pattern += "="  # Same
        
        return pattern
    
    def analyze_patterns(self) -> Dict:
        """Analyze all stock patterns"""
        print("🔍 Fetching stock progression data...")
        df = self.get_stock_progression_data()
        
        print(f"📊 Analyzing {len(df)} stocks with complete 4-week data...")
        
        results = []
        
        for _, row in df.iterrows():
            symbol = row['symbol']
            
            # Score progression
            scores = [row['week1_score'], row['week2_score'], row['week3_score'], row['week4_score']]
            score_pattern = self.calculate_pattern(scores, "score")
            
            # Price progression
            prices = [row['week1_price'], row['week2_price'], row['week3_price'], row['week4_price']]
            price_pattern = self.calculate_pattern(prices, "price")
            
            # Calculate absolute and percentage changes
            score_change_absolute = scores[-1] - scores[0]
            price_change_absolute = prices[-1] - prices[0]
            
            # For percentage calculation, handle edge cases properly
            if abs(scores[0]) < 0.01:  # Avoid division by very small numbers
                score_change_total = float('inf') if score_change_absolute > 0 else float('-inf') if score_change_absolute < 0 else 0
            else:
                score_change_total = (score_change_absolute / abs(scores[0]) * 100)
            
            if abs(prices[0]) < 0.01:  # Avoid division by very small numbers
                price_change_total = float('inf') if price_change_absolute > 0 else float('-inf') if price_change_absolute < 0 else 0
            else:
                price_change_total = (price_change_absolute / prices[0] * 100)
            
            # Calculate week-over-week changes
            score_changes = []
            price_changes = []
            
            for i in range(1, len(scores)):
                score_change = ((scores[i] - scores[i-1]) / scores[i-1] * 100) if scores[i-1] != 0 else 0
                price_change = ((prices[i] - prices[i-1]) / prices[i-1] * 100) if prices[i-1] != 0 else 0
                score_changes.append(score_change)
                price_changes.append(price_change)
            
            results.append({
                'symbol': symbol,
                'score_pattern': score_pattern,
                'price_pattern': price_pattern,
                'week1_score': scores[0],
                'week4_score': scores[-1],
                'week1_price': prices[0],
                'week4_price': prices[-1],
                'score_change_absolute': score_change_absolute,
                'score_change_total': score_change_total,
                'price_change_absolute': price_change_absolute,
                'price_change_total': price_change_total,
                'score_changes': score_changes,
                'price_changes': price_changes,
                'week1_date': row['week1_date'],
                'week4_date': row['week4_date']
            })
        
        return {
            'data': results,
            'df': pd.DataFrame(results)
        }
    
    def generate_pattern_summary(self, results: Dict) -> None:
        """Generate summary of patterns"""
        df = results['df']
        
        print("\n" + "="*80)
        print("📈 STOCK PROGRESSION PATTERN ANALYSIS")
        print("="*80)
        
        print(f"\n📊 **DATASET OVERVIEW:**")
        print(f"   • Total stocks analyzed: {len(df)}")
        print(f"   • Time period: {df.iloc[0]['week1_date']} → {df.iloc[0]['week4_date']}")
        print(f"   • Analysis: 4-week score and price progression patterns")
        
        # Score pattern distribution
        print(f"\n🎯 **SCORE PATTERN DISTRIBUTION:**")
        score_patterns = df['score_pattern'].value_counts()
        for pattern, count in score_patterns.head(10).items():
            percentage = (count / len(df)) * 100
            print(f"   {pattern}: {count:4d} stocks ({percentage:5.1f}%)")
        
        # Price pattern distribution  
        print(f"\n💰 **PRICE PATTERN DISTRIBUTION:**")
        price_patterns = df['price_pattern'].value_counts()
        for pattern, count in price_patterns.head(10).items():
            percentage = (count / len(df)) * 100
            print(f"   {pattern}: {count:4d} stocks ({percentage:5.1f}%)")
        
        # Best performing patterns (using absolute change to avoid infinity issues)
        print(f"\n🚀 **TOP SCORE IMPROVEMENT PATTERNS (by absolute change):**")
        top_score_patterns = df.groupby('score_pattern')['score_change_absolute'].agg(['mean', 'count']).sort_values('mean', ascending=False)
        for pattern, row in top_score_patterns.head(10).iterrows():
            if row['count'] >= 5:  # Only patterns with at least 5 stocks
                print(f"   {pattern}: {row['mean']:+6.1f} pts avg change ({int(row['count'])} stocks)")
        
        # Best performing stocks (by absolute change)
        print(f"\n⭐ **TOP SCORE IMPROVERS (by absolute points):**")
        top_improvers = df.nlargest(10, 'score_change_absolute')
        for _, stock in top_improvers.iterrows():
            # Format percentage safely
            if abs(stock['score_change_total']) == float('inf'):
                pct_str = "∞%" if stock['score_change_absolute'] > 0 else "-∞%"
            else:
                pct_str = f"{stock['score_change_total']:+6.1f}%" if abs(stock['score_change_total']) < 10000 else f"{stock['score_change_total']:+.0f}%"
            
            print(f"   {stock['symbol']:<12} {stock['score_pattern']} | {stock['week1_score']:5.1f}→{stock['week4_score']:5.1f} ({stock['score_change_absolute']:+5.1f} pts)")
        
        # Worst performing stocks (by absolute change)
        print(f"\n📉 **TOP SCORE DECLINERS (by absolute points):**")
        top_decliners = df.nsmallest(10, 'score_change_absolute')
        for _, stock in top_decliners.iterrows():
            print(f"   {stock['symbol']:<12} {stock['score_pattern']} | {stock['week1_score']:5.1f}→{stock['week4_score']:5.1f} ({stock['score_change_absolute']:+5.1f} pts)")
        
        # Pattern correlation analysis
        print(f"\n🔗 **SCORE vs PRICE PATTERN CORRELATION:**")
        correlation_data = df.groupby(['score_pattern', 'price_pattern']).size().reset_index(name='count')
        correlation_data = correlation_data.sort_values('count', ascending=False)
        
        print("   Score Pattern | Price Pattern | Count")
        print("   --------------|---------------|------")
        for _, row in correlation_data.head(15).iterrows():
            print(f"   {row['score_pattern']:<13} | {row['price_pattern']:<13} | {row['count']:4d}")
        
        # Strong stocks count only
        strong_stocks = df[df['week4_score'] >= 67].sort_values('week4_score', ascending=False)
        print(f"\n💪 **STOCKS REACHING STRONG TERRITORY (Score ≥ 67):**")
        print(f"   Total: {len(strong_stocks)} stocks")
        
        if len(strong_stocks) > 0:
            print(f"   Use Option 1 to see detailed price progression for these stocks.")

    def show_pattern_specific_stocks(self, results: Dict, target_pattern: str) -> None:
        """Show all stocks with a specific pattern"""
        df = results['df']
        pattern_stocks = df[df['score_pattern'] == target_pattern].sort_values('week4_score', ascending=False)
        
        if pattern_stocks.empty:
            print(f"❌ No stocks found with pattern '{target_pattern}'")
            return
        
        print(f"\n🎯 ALL STOCKS WITH '{target_pattern}' PATTERN:")
        print(f"   Total: {len(pattern_stocks)} stocks")
        print(f"\n   All {len(pattern_stocks)} stocks with '{target_pattern}' Pattern and Price Progression:")
        print(f"   {'Symbol':<12} {'Pattern':<7} {'Score':<5} {'Price Progression':<50} {'Total %':<8}")
        print(f"   {'-'*12} {'-'*7} {'-'*5} {'-'*50} {'-'*8}")
        
        for _, stock in pattern_stocks.iterrows():
            # Get detailed data for this stock
            detailed_data = self.get_detailed_stock_data(stock['symbol'])
            if detailed_data:
                price_progression = self.format_price_progression(detailed_data, stock['score_pattern'])
                total_price_change = ((stock['week4_price'] - stock['week1_price']) / stock['week1_price'] * 100)
                
                print(f"   {stock['symbol']:<12} {stock['score_pattern']:<7} {stock['week4_score']:5.1f} {price_progression:<50} {total_price_change:+6.1f}%")
        
        # Pattern statistics
        avg_score_change = pattern_stocks['score_change_absolute'].mean()
        avg_price_change = pattern_stocks['price_change_absolute'].mean()
        strong_count = len(pattern_stocks[pattern_stocks['week4_score'] >= 67])
        
        print(f"\n📊 **{target_pattern} PATTERN STATISTICS:**")
        print(f"   • Average score improvement: {avg_score_change:+.1f} points")
        print(f"   • Stocks reaching strong territory (≥67): {strong_count}/{len(pattern_stocks)} ({strong_count/len(pattern_stocks)*100:.1f}%)")
        print(f"   • Score range: {pattern_stocks['week4_score'].min():.1f} to {pattern_stocks['week4_score'].max():.1f}")
        
        if strong_count > 0:
            print(f"\n⭐ **STRONG STOCKS WITH {target_pattern} PATTERN:**")
            strong_pattern_stocks = pattern_stocks[pattern_stocks['week4_score'] >= 67]
            for _, stock in strong_pattern_stocks.iterrows():
                print(f"   {stock['symbol']:<12} Score: {stock['week4_score']:5.1f} | Price: ₹{stock['week4_price']:7.2f}")

    def discover_additional_patterns(self) -> None:
        """Discover additional patterns beyond our scoring system"""
        print("\n🔍 DISCOVERING ADDITIONAL PATTERNS BEYOND SCORING...")
        print("=" * 60)
        
        # Get all data for analysis
        results = self.analyze_patterns()
        df = results['df']
        
        # 1. Sector-based patterns
        self._analyze_sector_patterns()
        
        # 2. Market cap patterns
        self._analyze_market_cap_patterns()
        
        # 3. Individual indicator patterns
        self._analyze_indicator_patterns()
        
        # 4. Volume-price relationship patterns
        self._analyze_volume_price_patterns()
        
        # 5. Time-based patterns
        self._analyze_time_patterns()
        
        # 6. Correlation patterns
        self._analyze_correlation_patterns()
    
    def detect_wildcard_stocks(self) -> None:
        """Detect wildcard stocks with unusual patterns based on data exploration"""
        print("\n🎪 WILDCARD STOCK DETECTION - DATA-DRIVEN PATTERNS")
        print("=" * 70)
        
        # 1. Extreme Score Volatility Wildcards
        self._find_score_volatility_wildcards()
        
        # 2. Price-Score Disconnect Wildcards  
        self._find_price_score_disconnect_wildcards()
        
        # 3. Volume Spike Wildcards
        self._find_volume_spike_wildcards()
        
        # 4. Turnaround Story Wildcards
        self._find_turnaround_wildcards()
        
        # 5. Stealth Performer Wildcards
        self._find_stealth_performer_wildcards()
        
        # 6. Sector Misfit Wildcards
        self._find_sector_misfit_wildcards()
    
    def analyze_wildcard_intersections(self) -> None:
        """Analyze stocks that appear in multiple wildcard categories"""
        print("\n🎯 WILDCARD INTERSECTION ANALYSIS")
        print("=" * 60)
        print("Finding stocks that appear in MULTIPLE wildcard categories...")
        
        # Get all wildcard stocks by category
        wildcards = {
            'volatility': self._get_volatility_wildcards(),
            'disconnect': self._get_disconnect_wildcards(), 
            'volume_spike': self._get_volume_spike_wildcards(),
            'turnaround': self._get_turnaround_wildcards(),
            'stealth': self._get_stealth_wildcards(),
            'sector_misfit': self._get_sector_misfit_wildcards()
        }
        
        # Find intersections
        all_stocks = set()
        for category_stocks in wildcards.values():
            all_stocks.update(category_stocks)
        
        # Count appearances per stock
        stock_counts = {}
        stock_categories = {}
        
        for stock in all_stocks:
            count = 0
            categories = []
            for category, stocks in wildcards.items():
                if stock in stocks:
                    count += 1
                    categories.append(category)
            stock_counts[stock] = count
            stock_categories[stock] = categories
        
        # Display results
        print(f"\n📊 **INTERSECTION SUMMARY:**")
        print(f"   Total unique wildcard stocks: {len(all_stocks)}")
        
        # Multi-category wildcards
        multi_category = {k: v for k, v in stock_counts.items() if v > 1}
        print(f"   Stocks in multiple categories: {len(multi_category)}")
        
        if multi_category:
            print(f"\n🏆 **TOP WILDCARD INTERSECTIONS:**")
            print(f"   {'Stock':<12} {'Categories':<3} {'Wildcard Types'}")
            print(f"   {'-'*12} {'-'*10} {'-'*40}")
            
            # Sort by number of categories (descending)
            for stock, count in sorted(multi_category.items(), key=lambda x: x[1], reverse=True):
                categories_str = ', '.join([cat.replace('_', ' ').title() for cat in stock_categories[stock]])
                print(f"   {stock:<12} {count}/6       {categories_str}")
        
        # Single category dominance
        single_category = {k: v for k, v in stock_counts.items() if v == 1}
        print(f"\n📈 **SINGLE CATEGORY SPECIALISTS:**")
        print(f"   Count: {len(single_category)} stocks")
        
        # Category breakdown
        category_breakdown = {}
        for stock, categories in stock_categories.items():
            for category in categories:
                if category not in category_breakdown:
                    category_breakdown[category] = []
                category_breakdown[category].append(stock)
        
        print(f"\n📋 **CATEGORY BREAKDOWN:**")
        category_names = {
            'volatility': '🎢 Extreme Volatility',
            'disconnect': '🔀 Price-Score Disconnect', 
            'volume_spike': '📊 Volume Spike',
            'turnaround': '🔄 Turnaround Story',
            'stealth': '🥷 Stealth Performer',
            'sector_misfit': '🎭 Sector Misfit'
        }
        
        for category, stocks in category_breakdown.items():
            print(f"   {category_names[category]:<25}: {len(stocks)} stocks")
        
        # Recommend top picks
        if multi_category:
            print(f"\n💎 **RECOMMENDED WILDCARD PICKS:**")
            top_picks = sorted(multi_category.items(), key=lambda x: x[1], reverse=True)[:5]
            
            for i, (stock, count) in enumerate(top_picks, 1):
                categories_str = ', '.join([cat.replace('_', ' ').title() for cat in stock_categories[stock]])
                print(f"   {i}. **{stock}** ({count}/6 categories): {categories_str}")
                
                # Get some key metrics for this stock
                self._show_stock_wildcard_summary(stock)
    
    def _find_score_volatility_wildcards(self) -> None:
        """Find stocks with extreme score changes - high volatility wildcards"""
        print("\n🎢 **EXTREME SCORE VOLATILITY WILDCARDS:**")
        print("   (Stocks with score swings ≥60 points - high risk/reward)")
        
        query = """
        SELECT 
            symbol,
            MIN(total_score) as min_score,
            MAX(total_score) as max_score,
            MAX(total_score) - MIN(total_score) as score_range,
            MIN(friday_price) as min_price,
            MAX(friday_price) as max_price,
            (MAX(friday_price) - MIN(friday_price)) / MIN(friday_price) * 100 as price_change_pct,
            sector,
            COUNT(*) as weeks
        FROM friday_stocks_analysis 
        GROUP BY symbol 
        HAVING COUNT(*) = 4 AND score_range >= 60
        ORDER BY score_range DESC 
        LIMIT 10
        """
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            print(f"   {'Symbol':<12} {'Score Range':<12} {'Price Change':<12} {'Sector':<15} {'Risk Level'}")
            print(f"   {'-'*12} {'-'*12} {'-'*12} {'-'*15} {'-'*10}")
            
            for _, row in df.iterrows():
                risk = "🔥 EXTREME" if row['score_range'] > 75 else "⚠️ HIGH"
                print(f"   {row['symbol']:<12} {row['min_score']:4.0f}→{row['max_score']:4.0f} ({row['score_range']:2.0f})   {row['price_change_pct']:+8.1f}%     {row['sector'][:14]:<15} {risk}")
    
    def _find_price_score_disconnect_wildcards(self) -> None:
        """Find stocks where price and score move in opposite directions"""
        print("\n🔀 **PRICE-SCORE DISCONNECT WILDCARDS:**")
        print("   (Market sentiment vs technical analysis conflicts)")
        
        query = """
        SELECT 
            symbol,
            friday_date,
            total_score,
            friday_price,
            price_change_1d,
            volume_ratio,
            sector,
            CASE 
                WHEN total_score > 50 AND price_change_1d < -5 THEN 'Strong Tech, Weak Price'
                WHEN total_score < 0 AND price_change_1d > 5 THEN 'Weak Tech, Strong Price'
                WHEN total_score > 30 AND price_change_1d < -8 THEN 'Good Tech, Bad Price'
                WHEN total_score < -10 AND price_change_1d > 8 THEN 'Bad Tech, Good Price'
            END as disconnect_type
        FROM friday_stocks_analysis 
        WHERE (total_score > 50 AND price_change_1d < -5) 
           OR (total_score < 0 AND price_change_1d > 5)
           OR (total_score > 30 AND price_change_1d < -8)
           OR (total_score < -10 AND price_change_1d > 8)
        ORDER BY ABS(total_score - price_change_1d * 5) DESC
        LIMIT 12
        """
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            print(f"   {'Symbol':<12} {'Date':<12} {'Score':<6} {'Price Δ':<8} {'Vol Ratio':<8} {'Pattern'}")
            print(f"   {'-'*12} {'-'*12} {'-'*6} {'-'*8} {'-'*8} {'-'*20}")
            
            for _, row in df.iterrows():
                print(f"   {row['symbol']:<12} {row['friday_date']:<12} {row['total_score']:5.1f}  {row['price_change_1d']:+6.1f}%  {row['volume_ratio']:6.2f}x  {row['disconnect_type']}")
    
    def _find_volume_spike_wildcards(self) -> None:
        """Find stocks with extreme volume spikes"""
        print("\n📊 **VOLUME SPIKE WILDCARDS:**")
        print("   (Unusual volume activity - potential breakouts or breakdowns)")
        
        query = """
        SELECT 
            symbol,
            friday_date,
            total_score,
            friday_price,
            volume_ratio,
            price_change_1d,
            rsi_value,
            sector,
            CASE 
                WHEN volume_ratio > 10 THEN '🚨 EXTREME'
                WHEN volume_ratio > 5 THEN '⚠️ VERY HIGH'
                WHEN volume_ratio > 3 THEN '📈 HIGH'
            END as volume_level
        FROM friday_stocks_analysis 
        WHERE volume_ratio > 3.0
        ORDER BY volume_ratio DESC 
        LIMIT 15
        """
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            print(f"   {'Symbol':<12} {'Date':<12} {'Vol Ratio':<9} {'Price Δ':<8} {'Score':<6} {'Level'}")
            print(f"   {'-'*12} {'-'*12} {'-'*9} {'-'*8} {'-'*6} {'-'*10}")
            
            for _, row in df.iterrows():
                print(f"   {row['symbol']:<12} {row['friday_date']:<12} {row['volume_ratio']:7.1f}x  {row['price_change_1d']:+6.1f}%  {row['total_score']:5.1f}  {row['volume_level']}")
    
    def _find_turnaround_wildcards(self) -> None:
        """Find potential turnaround stories - stocks improving from very low scores"""
        print("\n🔄 **TURNAROUND STORY WILDCARDS:**")
        print("   (Stocks recovering from deep negative scores)")
        
        query = """
        WITH stock_progression AS (
            SELECT 
                symbol,
                MIN(total_score) as worst_score,
                MAX(total_score) as best_score,
                MAX(total_score) - MIN(total_score) as improvement,
                sector,
                AVG(friday_price) as avg_price,
                COUNT(*) as weeks
            FROM friday_stocks_analysis 
            GROUP BY symbol 
            HAVING COUNT(*) = 4
        )
        SELECT *
        FROM stock_progression
        WHERE worst_score < -20 AND improvement > 40
        ORDER BY improvement DESC
        LIMIT 10
        """
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            print(f"   {'Symbol':<12} {'Worst→Best':<12} {'Improvement':<12} {'Sector':<15} {'Avg Price'}")
            print(f"   {'-'*12} {'-'*12} {'-'*12} {'-'*15} {'-'*10}")
            
            for _, row in df.iterrows():
                print(f"   {row['symbol']:<12} {row['worst_score']:4.0f}→{row['best_score']:4.0f}      {row['improvement']:8.0f} pts    {row['sector'][:14]:<15} ₹{row['avg_price']:7.0f}")
    
    def _find_stealth_performer_wildcards(self) -> None:
        """Find quiet but consistent performers"""
        print("\n🥷 **STEALTH PERFORMER WILDCARDS:**")
        print("   (Low volume but consistent score improvements)")
        
        query = """
        WITH stock_consistency AS (
            SELECT 
                symbol,
                AVG(volume_ratio) as avg_volume,
                MIN(total_score) as min_score,
                MAX(total_score) as max_score,
                MAX(total_score) - MIN(total_score) as improvement,
                (MAX(total_score) - MIN(total_score)) as score_volatility,
                sector,
                AVG(friday_price) as avg_price
            FROM friday_stocks_analysis 
            GROUP BY symbol 
            HAVING COUNT(*) = 4
        )
        SELECT *
        FROM stock_consistency
        WHERE avg_volume < 1.5 AND improvement > 25 AND max_score > 40
        ORDER BY improvement DESC
        LIMIT 10
        """
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            print(f"   {'Symbol':<12} {'Improvement':<12} {'Avg Volume':<11} {'Max Score':<9} {'Sector'}")
            print(f"   {'-'*12} {'-'*12} {'-'*11} {'-'*9} {'-'*15}")
            
            for _, row in df.iterrows():
                print(f"   {row['symbol']:<12} {row['improvement']:8.0f} pts    {row['avg_volume']:7.2f}x     {row['max_score']:6.1f}     {row['sector'][:14]}")
    
    def _find_sector_misfit_wildcards(self) -> None:
        """Find stocks performing opposite to their sector trend"""
        print("\n🎭 **SECTOR MISFIT WILDCARDS:**")
        print("   (Stocks performing against sector trends)")
        
        query = """
        WITH sector_avg AS (
            SELECT 
                sector,
                AVG(total_score) as sector_avg_score
            FROM friday_stocks_analysis 
            WHERE friday_date = (SELECT MAX(friday_date) FROM friday_stocks_analysis)
            AND sector IS NOT NULL
            GROUP BY sector
        ),
        stock_performance AS (
            SELECT 
                f.symbol,
                f.total_score,
                f.sector,
                s.sector_avg_score,
                f.total_score - s.sector_avg_score as deviation_from_sector,
                f.friday_price,
                f.volume_ratio
            FROM friday_stocks_analysis f
            JOIN sector_avg s ON f.sector = s.sector
            WHERE f.friday_date = (SELECT MAX(friday_date) FROM friday_stocks_analysis)
        )
        SELECT *
        FROM stock_performance
        WHERE ABS(deviation_from_sector) > 30
        ORDER BY ABS(deviation_from_sector) DESC
        LIMIT 12
        """
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            print(f"   {'Symbol':<12} {'Stock Score':<11} {'Sector Avg':<11} {'Deviation':<10} {'Sector'}")
            print(f"   {'-'*12} {'-'*11} {'-'*11} {'-'*10} {'-'*15}")
            
            for _, row in df.iterrows():
                direction = "📈 Above" if row['deviation_from_sector'] > 0 else "📉 Below"
                print(f"   {row['symbol']:<12} {row['total_score']:8.1f}     {row['sector_avg_score']:8.1f}     {row['deviation_from_sector']:+7.1f}    {row['sector'][:14]}")

    def _analyze_sector_patterns(self) -> None:
        """Analyze patterns by sector"""
        print("\n📊 **SECTOR-BASED PATTERNS:**")
        
        query = """
        SELECT sector, 
               AVG(total_score) as avg_score,
               COUNT(*) as stock_count,
               AVG(friday_price) as avg_price,
               COUNT(CASE WHEN total_score >= 67 THEN 1 END) as strong_count
        FROM friday_stocks_analysis 
        WHERE sector IS NOT NULL AND sector != ''
        GROUP BY sector
        ORDER BY avg_score DESC
        """
        
        with sqlite3.connect(self.db_path) as conn:
            sector_df = pd.read_sql_query(query, conn)
        
        print(f"   {'Sector':<20} {'Avg Score':<10} {'Strong %':<8} {'Stocks':<7} {'Avg Price':<10}")
        print(f"   {'-'*20} {'-'*10} {'-'*8} {'-'*7} {'-'*10}")
        
        for _, row in sector_df.iterrows():
            strong_pct = (row['strong_count'] / row['stock_count'] * 100) if row['stock_count'] > 0 else 0
            print(f"   {row['sector'][:19]:<20} {row['avg_score']:8.1f}   {strong_pct:6.1f}%  {int(row['stock_count']):5d}   ₹{row['avg_price']:8.0f}")
    
    def _analyze_market_cap_patterns(self) -> None:
        """Analyze patterns by market cap tiers"""
        print("\n💰 **MARKET CAP PATTERNS:**")
        
        query = """
        SELECT 
            CASE 
                WHEN market_cap >= 100000 THEN 'Large Cap (≥1L Cr)'
                WHEN market_cap >= 50000 THEN 'Mid Cap (50K-1L Cr)'
                WHEN market_cap >= 10000 THEN 'Small Cap (10K-50K Cr)'
                WHEN market_cap > 0 THEN 'Micro Cap (<10K Cr)'
                ELSE 'Unknown'
            END as cap_tier,
            AVG(total_score) as avg_score,
            COUNT(*) as stock_count,
            AVG(friday_price) as avg_price,
            COUNT(CASE WHEN total_score >= 67 THEN 1 END) as strong_count
        FROM friday_stocks_analysis 
        WHERE market_cap IS NOT NULL
        GROUP BY cap_tier
        ORDER BY 
            CASE cap_tier
                WHEN 'Large Cap (≥1L Cr)' THEN 1
                WHEN 'Mid Cap (50K-1L Cr)' THEN 2
                WHEN 'Small Cap (10K-50K Cr)' THEN 3
                WHEN 'Micro Cap (<10K Cr)' THEN 4
                ELSE 5
            END
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cap_df = pd.read_sql_query(query, conn)
        
        print(f"   {'Market Cap Tier':<20} {'Avg Score':<10} {'Strong %':<8} {'Stocks':<7} {'Avg Price':<10}")
        print(f"   {'-'*20} {'-'*10} {'-'*8} {'-'*7} {'-'*10}")
        
        for _, row in cap_df.iterrows():
            strong_pct = (row['strong_count'] / row['stock_count'] * 100) if row['stock_count'] > 0 else 0
            print(f"   {row['cap_tier']:<20} {row['avg_score']:8.1f}   {strong_pct:6.1f}%  {int(row['stock_count']):5d}   ₹{row['avg_price']:8.0f}")
    
    def _analyze_indicator_patterns(self) -> None:
        """Analyze individual technical indicator patterns"""
        print("\n📈 **INDIVIDUAL INDICATOR PATTERNS:**")
        
        # RSI patterns
        query = """
        SELECT 
            CASE 
                WHEN rsi_value < 30 THEN 'Oversold (<30)'
                WHEN rsi_value < 50 THEN 'Bearish (30-50)'
                WHEN rsi_value < 70 THEN 'Bullish (50-70)'
                WHEN rsi_value >= 70 THEN 'Overbought (≥70)'
                ELSE 'Unknown'
            END as rsi_tier,
            AVG(total_score) as avg_score,
            COUNT(*) as stock_count,
            COUNT(CASE WHEN total_score >= 67 THEN 1 END) as strong_count
        FROM friday_stocks_analysis 
        WHERE rsi_value IS NOT NULL
        GROUP BY rsi_tier
        ORDER BY avg_score DESC
        """
        
        with sqlite3.connect(self.db_path) as conn:
            rsi_df = pd.read_sql_query(query, conn)
        
        print("   RSI Tier Patterns:")
        print(f"   {'RSI Range':<15} {'Avg Score':<10} {'Strong %':<8} {'Stocks':<7}")
        print(f"   {'-'*15} {'-'*10} {'-'*8} {'-'*7}")
        
        for _, row in rsi_df.iterrows():
            strong_pct = (row['strong_count'] / row['stock_count'] * 100) if row['stock_count'] > 0 else 0
            print(f"   {row['rsi_tier']:<15} {row['avg_score']:8.1f}   {strong_pct:6.1f}%  {int(row['stock_count']):5d}")
    
    def _analyze_volume_price_patterns(self) -> None:
        """Analyze volume-price relationship patterns"""
        print("\n📊 **VOLUME-PRICE RELATIONSHIP PATTERNS:**")
        
        query = """
        SELECT 
            CASE 
                WHEN volume_ratio >= 2.0 THEN 'Very High Vol (≥2x)'
                WHEN volume_ratio >= 1.5 THEN 'High Vol (1.5-2x)'
                WHEN volume_ratio >= 1.0 THEN 'Normal Vol (1-1.5x)'
                WHEN volume_ratio < 1.0 THEN 'Low Vol (<1x)'
                ELSE 'Unknown'
            END as volume_tier,
            CASE 
                WHEN price_change_1d >= 5 THEN 'Strong Up (≥5%)'
                WHEN price_change_1d >= 2 THEN 'Up (2-5%)'
                WHEN price_change_1d >= -2 THEN 'Flat (±2%)'
                WHEN price_change_1d >= -5 THEN 'Down (-2 to -5%)'
                WHEN price_change_1d < -5 THEN 'Strong Down (<-5%)'
                ELSE 'Unknown'
            END as price_move,
            AVG(total_score) as avg_score,
            COUNT(*) as stock_count
        FROM friday_stocks_analysis 
        WHERE volume_ratio IS NOT NULL AND price_change_1d IS NOT NULL
        GROUP BY volume_tier, price_move
        HAVING stock_count >= 10
        ORDER BY avg_score DESC
        """
        
        with sqlite3.connect(self.db_path) as conn:
            vol_price_df = pd.read_sql_query(query, conn)
        
        print(f"   {'Volume Tier':<18} {'Price Move':<15} {'Avg Score':<10} {'Stocks':<7}")
        print(f"   {'-'*18} {'-'*15} {'-'*10} {'-'*7}")
        
        for _, row in vol_price_df.head(15).iterrows():
            print(f"   {row['volume_tier']:<18} {row['price_move']:<15} {row['avg_score']:8.1f}   {int(row['stock_count']):5d}")
    
    def _analyze_time_patterns(self) -> None:
        """Analyze time-based patterns"""
        print("\n📅 **TIME-BASED PATTERNS:**")
        
        query = """
        SELECT friday_date,
               AVG(total_score) as avg_score,
               COUNT(*) as stock_count,
               COUNT(CASE WHEN total_score >= 67 THEN 1 END) as strong_count,
               AVG(friday_price) as avg_price
        FROM friday_stocks_analysis 
        GROUP BY friday_date
        ORDER BY friday_date
        """
        
        with sqlite3.connect(self.db_path) as conn:
            time_df = pd.read_sql_query(query, conn)
        
        print(f"   {'Date':<12} {'Avg Score':<10} {'Strong %':<8} {'Stocks':<7} {'Market Trend':<12}")
        print(f"   {'-'*12} {'-'*10} {'-'*8} {'-'*7} {'-'*12}")
        
        prev_avg_score = None
        for _, row in time_df.iterrows():
            strong_pct = (row['strong_count'] / row['stock_count'] * 100) if row['stock_count'] > 0 else 0
            
            if prev_avg_score:
                trend = "📈 Improving" if row['avg_score'] > prev_avg_score else "📉 Declining" if row['avg_score'] < prev_avg_score else "➖ Flat"
            else:
                trend = "➖ Baseline"
            
            print(f"   {row['friday_date']:<12} {row['avg_score']:8.1f}   {strong_pct:6.1f}%  {int(row['stock_count']):5d}   {trend}")
            prev_avg_score = row['avg_score']
    
    def _analyze_correlation_patterns(self) -> None:
        """Analyze correlation between different metrics"""
        print("\n🔗 **CORRELATION PATTERNS:**")
        
        query = """
        SELECT symbol, total_score, friday_price, volume_ratio, rsi_value, 
               ma_50, ma_200, price_change_1d, price_change_5d, market_cap
        FROM friday_stocks_analysis 
        WHERE friday_date = (SELECT MAX(friday_date) FROM friday_stocks_analysis)
        AND rsi_value IS NOT NULL AND volume_ratio IS NOT NULL
        """
        
        with sqlite3.connect(self.db_path) as conn:
            corr_df = pd.read_sql_query(query, conn)
        
        if not corr_df.empty:
            # Calculate correlations
            numeric_cols = ['total_score', 'friday_price', 'volume_ratio', 'rsi_value', 
                          'price_change_1d', 'price_change_5d', 'market_cap']
            corr_matrix = corr_df[numeric_cols].corr()
            
            print("   Key Correlations with Total Score:")
            score_corr = corr_matrix['total_score'].sort_values(key=abs, ascending=False)
            
            for metric, correlation in score_corr.items():
                if metric != 'total_score' and abs(correlation) > 0.1:
                    strength = "Strong" if abs(correlation) > 0.5 else "Moderate" if abs(correlation) > 0.3 else "Weak"
                    direction = "Positive" if correlation > 0 else "Negative"
                    print(f"   {metric:<15}: {correlation:+6.3f} ({strength} {direction})")

    def _get_volatility_wildcards(self) -> set:
        """Get stocks with extreme score volatility"""
        query = """
        SELECT symbol
        FROM (
            SELECT 
                symbol,
                MAX(total_score) - MIN(total_score) as score_range
            FROM friday_stocks_analysis 
            GROUP BY symbol 
            HAVING COUNT(*) = 4 AND score_range >= 60
        )
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        return set(df['symbol'].tolist())
    
    def _get_disconnect_wildcards(self) -> set:
        """Get stocks with price-score disconnects"""
        query = """
        SELECT DISTINCT symbol
        FROM friday_stocks_analysis 
        WHERE (total_score > 50 AND price_change_1d < -5) 
           OR (total_score < 0 AND price_change_1d > 5)
           OR (total_score > 30 AND price_change_1d < -8)
           OR (total_score < -10 AND price_change_1d > 8)
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        return set(df['symbol'].tolist())
    
    def _get_volume_spike_wildcards(self) -> set:
        """Get stocks with volume spikes"""
        query = """
        SELECT DISTINCT symbol
        FROM friday_stocks_analysis 
        WHERE volume_ratio > 3.0
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        return set(df['symbol'].tolist())
    
    def _get_turnaround_wildcards(self) -> set:
        """Get turnaround story stocks"""
        query = """
        SELECT symbol
        FROM (
            SELECT 
                symbol,
                MIN(total_score) as worst_score,
                MAX(total_score) - MIN(total_score) as improvement
            FROM friday_stocks_analysis 
            GROUP BY symbol 
            HAVING COUNT(*) = 4 AND worst_score < -20 AND improvement > 40
        )
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        return set(df['symbol'].tolist())
    
    def _get_stealth_wildcards(self) -> set:
        """Get stealth performer stocks"""
        query = """
        SELECT symbol
        FROM (
            SELECT 
                symbol,
                AVG(volume_ratio) as avg_volume,
                MAX(total_score) as max_score,
                MAX(total_score) - MIN(total_score) as improvement
            FROM friday_stocks_analysis 
            GROUP BY symbol 
            HAVING COUNT(*) = 4 AND avg_volume < 1.5 AND improvement > 25 AND max_score > 40
        )
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        return set(df['symbol'].tolist())
    
    def _get_sector_misfit_wildcards(self) -> set:
        """Get sector misfit stocks"""
        query = """
        WITH sector_avg AS (
            SELECT 
                sector,
                AVG(total_score) as sector_avg_score
            FROM friday_stocks_analysis 
            WHERE friday_date = (SELECT MAX(friday_date) FROM friday_stocks_analysis)
            AND sector IS NOT NULL
            GROUP BY sector
        )
        SELECT f.symbol
        FROM friday_stocks_analysis f
        JOIN sector_avg s ON f.sector = s.sector
        WHERE f.friday_date = (SELECT MAX(friday_date) FROM friday_stocks_analysis)
        AND ABS(f.total_score - s.sector_avg_score) > 30
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        return set(df['symbol'].tolist())
    
    def _show_stock_wildcard_summary(self, symbol: str) -> None:
        """Show key metrics for a wildcard stock"""
        query = """
        SELECT 
            MIN(total_score) as min_score,
            MAX(total_score) as max_score,
            AVG(volume_ratio) as avg_volume,
            MIN(friday_price) as min_price,
            MAX(friday_price) as max_price,
            sector
        FROM friday_stocks_analysis 
        WHERE symbol = ?
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=[symbol])
        
        if not df.empty:
            row = df.iloc[0]
            price_change = (row['max_price'] - row['min_price']) / row['min_price'] * 100
            print(f"      📈 Score: {row['min_score']:.0f}→{row['max_score']:.0f} | Price: {price_change:+.1f}% | Vol: {row['avg_volume']:.1f}x | {row['sector']}")

def main():
    """Main function to run pattern analysis"""
    analyzer = PatternAnalyzer()
    
    print("🎯 STOCK PROGRESSION PATTERN ANALYZER")
    print("=" * 50)
    print("1. Show Strong Stocks (Score ≥ 67) with Price Progression")
    print("2. Show All Stocks with Specific Pattern (e.g., DII)")
    print("3. Full Analysis Summary")
    print("4. Discover Additional Patterns (Sector, Market Cap, etc.)")
    print("5. Detect Wildcard Stocks")
    print("6. Analyze Wildcard Intersections")
    print("7. Exit")
    
    choice = input("\nSelect option (1/2/3/4/5/6/7): ").strip()
    
    if choice == '1':
        # Show strong stocks with detailed progression
        print("\n🔍 Analyzing strong stocks...")
        results = analyzer.analyze_patterns()
        df = results['df']
        strong_stocks = df[df['week4_score'] >= 67].sort_values('week4_score', ascending=False)
        
        if strong_stocks.empty:
            print("❌ No strong stocks found (Score ≥ 67)")
            return
        
        print(f"\n💪 **STOCKS REACHING STRONG TERRITORY (Score ≥ 67):**")
        print(f"   Total: {len(strong_stocks)} stocks")
        print(f"\n   All {len(strong_stocks)} Strong Stocks with Price Progression:")
        print(f"   {'Symbol':<12} {'Pattern':<7} {'Score':<5} {'Price Progression':<50} {'Total %':<8}")
        print(f"   {'-'*12} {'-'*7} {'-'*5} {'-'*50} {'-'*8}")
        
        for _, stock in strong_stocks.iterrows():
            # Get detailed data for this stock
            detailed_data = analyzer.get_detailed_stock_data(stock['symbol'])
            if detailed_data:
                price_progression = analyzer.format_price_progression(detailed_data, stock['score_pattern'])
                total_price_change = ((stock['week4_price'] - stock['week1_price']) / stock['week1_price'] * 100)
                
                print(f"   {stock['symbol']:<12} {stock['score_pattern']:<7} {stock['week4_score']:5.1f} {price_progression:<50} {total_price_change:+6.1f}%")
    
    elif choice == '2':
        # Show stocks with specific pattern
        print("\n📋 Available patterns: DII, III, IID, DID, IDI, DDI, DDD, IDD, etc.")
        target_pattern = input("Enter pattern to analyze (e.g., DII): ").strip().upper()
        
        if not target_pattern:
            print("❌ No pattern specified")
            return
        
        print(f"\n🔍 Analyzing all stocks with '{target_pattern}' pattern...")
        results = analyzer.analyze_patterns()
        analyzer.show_pattern_specific_stocks(results, target_pattern)
    
    elif choice == '3':
        # Full analysis summary
        print("\n🔍 Running full analysis...")
        results = analyzer.analyze_patterns()
        analyzer.generate_pattern_summary(results)
        
        print(f"\n💡 **INSIGHTS:**")
        print(f"   • Look for 'III' patterns - consistent improvement")
        print(f"   • 'DII' patterns show recovery potential")
        print(f"   • High score changes indicate momentum shifts")
        print(f"   • Cross-reference with price patterns for confirmation")
    
    elif choice == '4':
        # Discover additional patterns
        print("\n🔍 Running advanced pattern discovery...")
        analyzer.discover_additional_patterns()
    
    elif choice == '5':
        # Detect wildcard stocks
        print("\n🔍 Running wildcard stock detection...")
        analyzer.detect_wildcard_stocks()
    
    elif choice == '6':
        # Analyze wildcard intersections
        print("\n🔍 Analyzing wildcard intersections...")
        analyzer.analyze_wildcard_intersections()
    
    elif choice == '7':
        print("👋 Goodbye!")
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main() 