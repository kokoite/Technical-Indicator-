# Low Level Design (LLD) - Stock Monitoring & Recommendation System

## 1. Detailed Component Design

### 1.1 Daily Monitor Component (`daily_monitor.py`)

#### 1.1.1 Class Structure
```python
class DailyMonitor:
    def __init__(self):
        self.manager = AdvancedRecommendationManager()
        self.screener = EnhancedStrategyScreener()
        self.db_name = "stock_recommendations.db"
        self.todays_sales = []
        self.todays_promotions = []
```

#### 1.1.2 Key Methods Implementation

##### Monitor STRONG Recommendations
```python
def monitor_strong_recommendations(self):
    """
    Batch monitoring of STRONG recommendations with optimized API calls
    
    Algorithm:
    1. Get all STRONG recommendations from database
    2. Batch fetch current prices (single API call)
    3. Apply selling criteria in order of priority:
       - Hard score check (score < 50)
       - 7% stop loss (immediate sell)
       - 5% loss + weak indicators (score < 35)
    4. Update database and add to sold watchlist
    
    Performance: 10x faster than individual requests
    """
    strong_recs = self.manager.get_recommendations_by_tier('STRONG')
    symbols = strong_recs['symbol'].tolist()
    yahoo_symbols = [f"{symbol}.NS" for symbol in symbols]
    
    # Single batch API call
    batch_data = yf.download(" ".join(yahoo_symbols), period="1d", 
                            group_by='ticker', auto_adjust=True)
    
    for _, rec in strong_recs.iterrows():
        current_price = self._extract_price_from_batch(batch_data, rec['symbol'])
        price_change_pct = ((current_price - rec['entry_price']) / rec['entry_price']) * 100
        
        # Get current score for hard score check
        current_score = self._get_current_score(rec['symbol'], current_price)
        
        # Apply selling criteria
        if current_score < 50:  # Hard score check
            self._execute_sell(rec['symbol'], current_price, "Hard score deterioration")
        elif price_change_pct <= -7:  # 7% stop loss
            self._execute_sell(rec['symbol'], current_price, "7% stop loss")
        elif price_change_pct <= -5 and current_score < 35:  # 5% + weak indicators
            self._execute_sell(rec['symbol'], current_price, "5% loss + weak indicators")
```

##### Check WEAK Promotions
```python
def check_weak_promotions(self):
    """
    Check WEAK recommendations for promotion to STRONG
    
    Promotion Criteria:
    1. Price up >= 2% since Friday
    2. Re-analysis score >= 70
    
    Process:
    1. Get WEAK recommendations with valid Friday prices
    2. Batch fetch current prices
    3. Check price movement since Friday
    4. Re-analyze stocks meeting price criteria
    5. Promote if score >= 70
    """
    weak_recs = self.manager.get_recommendations_by_tier('WEAK')
    valid_weak_recs = weak_recs[
        (weak_recs['last_friday_price'].notna()) & 
        (weak_recs['last_friday_price'] != 0)
    ]
    
    # Batch price fetch and promotion logic
    for _, rec in valid_weak_recs.iterrows():
        price_change_since_friday = self._calculate_friday_change(rec)
        
        if price_change_since_friday >= 2.0:
            new_analysis = self._reanalyze_stock(rec)
            if new_analysis['total_score'] >= 70:
                self.manager.promote_weak_to_strong(rec['symbol'], new_analysis)
```

#### 1.1.3 Performance Optimizations
- **Batch API Calls**: Single yfinance call for multiple stocks
- **Database Connection Pooling**: Efficient connection management
- **Memory Management**: Process large datasets in chunks
- **Error Handling**: Continue processing on individual stock failures

### 1.2 Friday Analyzer Component (`friday_analyzer.py`)

#### 1.2.1 Class Structure
```python
class FridayAnalyzer:
    def __init__(self):
        self.manager = AdvancedRecommendationManager()
        self.weekly_system = WeeklyAnalysisSystem()
        self.db_name = "stock_recommendations.db"
```

#### 1.2.2 Cleanup Algorithm Implementation
```python
def cleanup_strong_recommendations(self):
    """
    Aggressive cleanup of underperforming STRONG positions on Friday
    
    Cleanup Criteria (in order of priority):
    1. 5% loss after 1 week
    2. 3% loss after 2 weeks  
    3. < 2% gain after 30 days (stagnation)
    
    Algorithm:
    1. Get all STRONG recommendations
    2. Calculate days held and current performance
    3. Apply cleanup criteria
    4. Execute sells and add to watchlist
    """
    strong_recs = self.manager.get_recommendations_by_tier('STRONG')
    
    for _, rec in strong_recs.iterrows():
        days_held = self._calculate_days_held(rec['recommendation_date'])
        return_pct = self._calculate_current_return(rec)
        
        should_cleanup = False
        cleanup_reason = ""
        
        if return_pct <= -5 and days_held >= 7:
            should_cleanup = True
            cleanup_reason = f"Weekly cleanup: {return_pct:.2f}% loss after {days_held} days"
        elif return_pct <= -3 and days_held >= 14:
            should_cleanup = True
            cleanup_reason = f"Bi-weekly cleanup: {return_pct:.2f}% loss after {days_held} days"
        elif days_held >= 30 and return_pct < 2:
            should_cleanup = True
            cleanup_reason = f"Monthly cleanup: Only {return_pct:.2f}% gain after {days_held} days"
        
        if should_cleanup:
            self.manager.sell_strong_recommendation(rec['symbol'], current_price, cleanup_reason)
```

### 1.3 Technical Indicator Calculator (`stock_indicator_calculator.py`)

#### 1.3.1 Optimized Indicator Calculation
```python
def calculate_all_indicators_from_data(data):
    """
    Calculate all technical indicators from single dataset
    
    Optimization: Single API call + multiple indicator calculations
    Performance: 9x faster than individual indicator calls
    
    Indicators Calculated:
    - 50-day and 200-day DMA with trend analysis
    - Weekly MACD with crossover detection
    - Weekly RSI with condition analysis
    - OBV and VPT volume indicators
    - Price action and volatility metrics
    """
    if data.empty or len(data) < 50:
        return None
    
    results = {}
    
    # DMA calculations with trend analysis
    results['50_day_dma'] = calculate_dma_from_data(data, 50)
    results['200_day_dma'] = calculate_dma_from_data(data, 200)
    
    # Weekly resampling for momentum indicators
    weekly_data = data.resample('W-FRI').agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 
        'Close': 'last', 'Volume': 'sum'
    }).dropna()
    
    # MACD with fallback implementation
    results['weekly_macd'] = calculate_weekly_macd_from_data(data)
    results['weekly_rsi'] = calculate_weekly_rsi_from_data(data)
    
    # Volume indicators
    results['obv'] = calculate_obv_from_data(data)
    results['vpt'] = calculate_vpt_from_data(data)
    
    # Price action metrics
    results['weekly_prices'] = calculate_weekly_prices_from_data(data)
    results['5_day_price_change'] = calculate_price_change_from_data(data, 5)
    results['10_day_price_change'] = calculate_price_change_from_data(data, 10)
    results['6_month_price_change'] = calculate_price_change_from_data(data, 180)
    
    return results
```

#### 1.3.2 DMA Calculation with Trend Analysis
```python
def calculate_dma_from_data(data, days):
    """
    Calculate DMA with comprehensive trend analysis
    
    Returns:
    - current_value: Latest DMA value
    - weekly_dma_values: 26 weeks of DMA data
    - weekly_positions: Price position relative to DMA
    - trend: Overall trend direction
    - 6-month statistics: min, max, average
    """
    df = data.copy()
    dma_column_name = f'{days}DMA'
    df.loc[:, dma_column_name] = df['Close'].shift(1).rolling(window=days).mean()
    
    # Weekly resampling
    weekly_dma = df[dma_column_name].resample('W-FRI').last().dropna().tail(26)
    weekly_prices = df['Close'].resample('W-FRI').last().dropna().tail(26)
    
    # Position analysis (above/below DMA)
    weekly_positions = []
    for i in range(len(weekly_dma)):
        if i < len(weekly_prices):
            price = weekly_prices.iloc[i]
            dma_val = weekly_dma.iloc[i]
            weekly_positions.append('above' if price > dma_val else 'below')
    
    # Trend determination
    trend = 'uptrend' if weekly_dma.iloc[-1] > weekly_dma.iloc[0] else 'downtrend'
    
    return {
        'current_value': weekly_dma.iloc[-1],
        'weekly_dma_values': weekly_dma.tolist(),
        'weekly_positions': weekly_positions,
        'trend': trend,
        'max_6m': weekly_dma.max(),
        'min_6m': weekly_dma.min(),
        'avg_6m': weekly_dma.mean()
    }
```

### 1.4 Buy/Sell Signal Analyzer (`buy_sell_signal_analyzer.py`)

#### 1.4.1 Weighted Scoring Algorithm
```python
class BuySellSignalAnalyzer:
    def __init__(self):
        # Signal weights (total = 100)
        self.weights = {
            'trend_alignment': 25,      # DMA trends and price position
            'momentum': 20,             # MACD signals
            'rsi_condition': 15,        # RSI overbought/oversold
            'volume_confirmation': 25,  # OBV/VPT trends
            'price_action': 15         # Recent price movements
        }
```

#### 1.4.2 Trend Analysis Implementation
```python
def analyze_trend_signals(self, results):
    """
    Analyze trend-based signals with weighted scoring
    
    Scoring Logic:
    - 50-DMA uptrend: +8 points, downtrend: -5 points
    - 200-DMA uptrend: +7 points, downtrend: -3 points
    - Price > 50-DMA: +5 points, Price < 50-DMA: -3 points
    - Golden Cross (50>200): +5 points, Death Cross: -5 points
    
    Max Score: +25, Min Score: -25
    """
    score = 0
    signals = []
    
    # 50-day DMA analysis
    if results['50_day_dma'] and isinstance(results['50_day_dma'], dict):
        dma_50 = results['50_day_dma']
        if dma_50['trend'] == 'uptrend':
            score += 8
            signals.append("✅ 50-DMA Uptrend (+8)")
        else:
            score -= 5
            signals.append("❌ 50-DMA Downtrend (-5)")
    
    # 200-day DMA analysis
    if results['200_day_dma'] and isinstance(results['200_day_dma'], dict):
        dma_200 = results['200_day_dma']
        if dma_200['trend'] == 'uptrend':
            score += 7
            signals.append("✅ 200-DMA Uptrend (+7)")
        else:
            score -= 3
            signals.append("❌ 200-DMA Downtrend (-3)")
    
    # Price vs DMA position
    if (results['weekly_prices'] and results['50_day_dma']):
        current_price = results['weekly_prices']['current_price']
        dma_50_val = results['50_day_dma']['current_value']
        
        if current_price > dma_50_val:
            score += 5
            signals.append("✅ Price > 50-DMA (+5)")
        else:
            score -= 3
            signals.append("❌ Price < 50-DMA (-3)")
    
    # Golden/Death Cross
    if (results['50_day_dma'] and results['200_day_dma']):
        dma_50_val = results['50_day_dma']['current_value']
        dma_200_val = results['200_day_dma']['current_value']
        
        if dma_50_val > dma_200_val:
            score += 5
            signals.append("✅ 50-DMA > 200-DMA (Golden Cross) (+5)")
        else:
            score -= 5
            signals.append("❌ 50-DMA < 200-DMA (Death Cross) (-5)")
    
    return min(max(score, -25), 25), signals
```

#### 1.4.3 Final Score Calculation
```python
def calculate_overall_score_silent(self, symbol):
    """
    Calculate comprehensive weighted score
    
    Process:
    1. Get technical indicators (single API call)
    2. Analyze each category (trend, momentum, RSI, volume, price)
    3. Apply category weights
    4. Sum to final score (0-100)
    5. Determine recommendation and risk level
    """
    results = calculate_all_indicators(symbol)
    if results is None:
        return None
    
    # Analyze each category
    trend_score, trend_signals = self.analyze_trend_signals(results)
    momentum_score, momentum_signals = self.analyze_momentum_signals(results)
    rsi_score, rsi_signals = self.analyze_rsi_signals(results)
    volume_score, volume_signals = self.analyze_volume_signals(results)
    price_score, price_signals = self.analyze_price_action_signals(results)
    
    # Calculate weighted scores
    weighted_trend = (trend_score / 25) * self.weights['trend_alignment']
    weighted_momentum = (momentum_score / 20) * self.weights['momentum']
    weighted_rsi = (rsi_score / 15) * self.weights['rsi_condition']
    weighted_volume = (volume_score / 25) * self.weights['volume_confirmation']
    weighted_price = (price_score / 15) * self.weights['price_action']
    
    total_score = (weighted_trend + weighted_momentum + weighted_rsi + 
                  weighted_volume + weighted_price)
    
    # Determine recommendation
    if total_score >= 75:
        recommendation = "🟢 STRONG BUY"
        risk_level = "Low"
    elif total_score >= 60:
        recommendation = "🟢 BUY"
        risk_level = "Low-Medium"
    elif total_score >= 40:
        recommendation = "🟡 WEAK BUY"
        risk_level = "Medium"
    elif total_score >= 20:
        recommendation = "⚪ HOLD"
        risk_level = "Medium-High"
    else:
        recommendation = "🔴 SELL"
        risk_level = "High"
    
    return {
        'total_score': total_score,
        'recommendation': recommendation,
        'risk_level': risk_level,
        'breakdown': {
            'trend': {'raw': trend_score, 'weighted': weighted_trend, 'signals': trend_signals},
            'momentum': {'raw': momentum_score, 'weighted': weighted_momentum, 'signals': momentum_signals},
            'rsi': {'raw': rsi_score, 'weighted': weighted_rsi, 'signals': rsi_signals},
            'volume': {'raw': volume_score, 'weighted': weighted_volume, 'signals': volume_signals},
            'price': {'raw': price_score, 'weighted': weighted_price, 'signals': price_signals}
        }
    }
```

### 1.5 Advanced Recommendation Manager (`advanced_recommendation_manager.py`)

#### 1.5.1 Tiered Recommendation System
```python
def save_tiered_recommendation(self, symbol, analysis_result, stock_info, tier=None, force_update=False):
    """
    Save recommendation with automatic tier classification
    
    Tier Classification:
    - STRONG: Score >= 70 (Active monitoring, strict stop-loss)
    - WEAK: Score 50-69 (Promotion monitoring, Friday price tracking)
    - HOLD: Score < 50 (Passive monitoring)
    
    Features:
    - Duplicate prevention with score-based updates
    - Automatic target/stop-loss calculation
    - Force update for Friday analysis
    """
    # Determine tier based on score
    if tier is None:
        score = analysis_result['total_score']
        if score >= 70:
            tier = 'STRONG'
        elif score >= 50:
            tier = 'WEAK'
        else:
            tier = 'HOLD'
    
    # Calculate target and stop loss
    target_price, stop_loss = self.calculate_levels(
        current_price, analysis_result['recommendation'], analysis_result['total_score']
    )
    
    # Handle duplicates with intelligent updates
    try:
        # Insert new recommendation
        cursor.execute('''INSERT INTO recommendations ...''')
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            # Update existing if better score or force update
            if force_update or analysis_result['total_score'] > existing_score:
                cursor.execute('''UPDATE recommendations SET ...''')
```

#### 1.5.2 Promotion Logic Implementation
```python
def promote_weak_to_strong(self, symbol, new_analysis, current_price=None):
    """
    Promote WEAK recommendation to STRONG
    
    Promotion Criteria:
    1. Price movement >= 2% since Friday
    2. Re-analysis score >= 70
    
    Process:
    1. Update tier to STRONG
    2. Set new entry price (current price)
    3. Calculate new target/stop loss
    4. Set promotion date
    """
    target_price, stop_loss = self.calculate_levels(
        current_price, new_analysis['recommendation'], new_analysis['total_score']
    )
    
    cursor.execute('''
        UPDATE recommendations 
        SET recommendation_tier = 'STRONG',
            promotion_date = ?,
            score = ?,
            entry_price = ?,
            target_price = ?,
            stop_loss = ?
        WHERE symbol = ? AND recommendation_tier = 'WEAK' AND status = 'ACTIVE'
    ''', (datetime.now().strftime('%Y-%m-%d'), new_analysis['total_score'],
          current_price, target_price, stop_loss, symbol.replace('.NS', '')))
```

#### 1.5.3 Selling Logic with Watchlist Management
```python
def sell_strong_recommendation(self, symbol, current_price, reason="Stop loss hit"):
    """
    Sell STRONG recommendation and add to watchlist
    
    Process:
    1. Calculate realized returns
    2. Update recommendation as sold
    3. Add to sold stocks watchlist for re-entry monitoring
    
    Watchlist Purpose: Monitor sold stocks for re-entry when score >= 60
    """
    # Get recommendation details
    entry_price, company_name, sector, original_score = self._get_recommendation_details(symbol)
    
    # Calculate returns
    return_pct = ((current_price - entry_price) / entry_price) * 100
    money_made = current_price - entry_price
    
    # Update as sold
    cursor.execute('''
        UPDATE recommendations 
        SET is_sold = 1, sell_date = ?, sell_price = ?, 
            realized_return_pct = ?, money_made = ?, status = 'SOLD', reason = ?
        WHERE symbol = ? AND recommendation_tier = 'STRONG' AND status = 'ACTIVE'
    ''', (datetime.now().strftime('%Y-%m-%d'), current_price, return_pct, 
          money_made, reason, symbol.replace('.NS', '')))
    
    # Add to sold watchlist
    self.add_to_sold_watchlist(symbol, company_name, sector, current_price, 
                              reason, entry_price, original_score)
```

### 1.6 Database Operations Implementation

#### 1.6.1 Connection Management
```python
class DatabaseManager:
    def __init__(self, db_name):
        self.db_name = db_name
    
    def get_connection(self):
        """Get database connection with proper error handling"""
        try:
            conn = sqlite3.connect(self.db_name)
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
            return conn
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise
    
    def execute_with_retry(self, query, params=None, max_retries=3):
        """Execute query with retry logic for database locks"""
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    conn.commit()
                    return cursor.fetchall()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                raise
```

#### 1.6.2 Batch Operations
```python
def batch_update_performance(self, recommendations):
    """
    Batch update performance data for multiple recommendations
    
    Optimization: Single transaction for multiple updates
    Performance: Significantly faster than individual updates
    """
    with self.get_connection() as conn:
        cursor = conn.cursor()
        
        # Prepare batch data
        batch_updates = []
        for rec_id, current_price, return_pct in recommendations:
            batch_updates.append((
                rec_id, current_price, return_pct,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        # Execute batch update
        cursor.executemany('''
            INSERT OR REPLACE INTO performance_tracking 
            (recommendation_id, current_price, return_pct, last_updated)
            VALUES (?, ?, ?, ?)
        ''', batch_updates)
        
        conn.commit()
        return len(batch_updates)
```

### 1.7 Error Handling and Resilience

#### 1.7.1 API Error Handling
```python
def fetch_with_fallback(self, symbols, max_retries=3):
    """
    Fetch data with multiple fallback strategies
    
    Fallback Strategy:
    1. Primary Yahoo Finance API
    2. Alternative Yahoo Finance endpoint
    3. NSE data sources
    4. Cached database data
    """
    for attempt in range(max_retries):
        try:
            # Primary API call
            data = yf.download(symbols, period="1d", group_by='ticker')
            if not data.empty:
                return data
        except Exception as e:
            print(f"API attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    
    # Fallback to cached data
    return self.get_cached_data(symbols)
```

#### 1.7.2 Data Validation
```python
def validate_stock_data(self, data):
    """
    Comprehensive data validation
    
    Validation Rules:
    - Price range: 50-1000 INR
    - Score range: 0-100
    - Date format validation
    - Required field presence
    """
    if not isinstance(data, dict):
        raise ValueError("Data must be dictionary")
    
    # Price validation
    if 'current_price' in data:
        price = data['current_price']
        if not (50 <= price <= 1000):
            raise ValueError(f"Price {price} outside valid range 50-1000")
    
    # Score validation
    if 'total_score' in data:
        score = data['total_score']
        if not (0 <= score <= 100):
            raise ValueError(f"Score {score} outside valid range 0-100")
    
    # Date validation
    if 'recommendation_date' in data:
        try:
            datetime.strptime(data['recommendation_date'], '%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid date format, expected YYYY-MM-DD")
    
    return True
```

### 1.8 Performance Monitoring and Logging

#### 1.8.1 Performance Metrics
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
    
    def time_operation(self, operation_name):
        """Decorator for timing operations"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    self.metrics[operation_name] = execution_time
                    print(f"⏱️ {operation_name}: {execution_time:.2f}s")
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    print(f"❌ {operation_name} failed after {execution_time:.2f}s: {e}")
                    raise
            return wrapper
        return decorator
    
    def get_performance_summary(self):
        """Get performance summary"""
        if not self.metrics:
            return "No performance data available"
        
        total_time = sum(self.metrics.values())
        avg_time = total_time / len(self.metrics)
        
        return {
            'total_operations': len(self.metrics),
            'total_time': total_time,
            'average_time': avg_time,
            'slowest_operation': max(self.metrics.items(), key=lambda x: x[1]),
            'fastest_operation': min(self.metrics.items(), key=lambda x: x[1])
        }
```

#### 1.8.2 Structured Logging
```python
import logging
from datetime import datetime

class StructuredLogger:
    def __init__(self, name, level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Console handler with formatting
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_operation(self, operation, symbol=None, details=None):
        """Log operation with structured data"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'symbol': symbol,
            'details': details
        }
        self.logger.info(f"Operation: {log_data}")
    
    def log_error(self, operation, error, symbol=None):
        """Log error with context"""
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'symbol': symbol,
            'error': str(error),
            'error_type': type(error).__name__
        }
        self.logger.error(f"Error: {error_data}")
```

This Low Level Design provides detailed implementation specifications for all major components, including algorithms, data structures, error handling, and performance optimizations used in your stock monitoring and recommendation system.