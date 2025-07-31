# Database Entity-Relationship Diagrams

## 1. Complete Database Schema Overview

```mermaid
erDiagram
    recommendations {
        int id PK
        string symbol
        string company_name
        date recommendation_date
        string recommendation
        real score
        string risk_level
        real entry_price
        real target_price
        real stop_loss
        string sector
        int market_cap
        string reason
        real trend_score
        real momentum_score
        real rsi_score
        real volume_score
        real price_action_score
        string recommendation_tier
        real last_friday_price
        string status
        date promotion_date
        date sell_date
        real sell_price
        real realized_return_pct
        real money_made
        boolean is_sold
        timestamp created_at
    }
    
    performance_tracking {
        int id PK
        int recommendation_id FK
        real current_price
        real return_pct
        int days_held
        timestamp last_updated
    }
    
    sold_stocks_watchlist {
        int id PK
        string symbol UK
        string company_name
        string sector
        date sell_date
        real sell_price
        string sell_reason
        real original_entry_price
        real original_score
        date last_check_date
        real last_check_score
        timestamp created_at
    }
    
    weekly_summaries {
        int id PK
        date analysis_date
        int total_stocks_analyzed
        int actionable_stocks
        int strong_buy_count
        int buy_count
        int weak_buy_count
        real avg_score
        string best_stock
        real best_score
        real analysis_duration_minutes
        string top_sector
        timestamp created_at
    }
    
    nse_stocks {
        string symbol PK
        string name
        string isin
        string series
        date date_of_listing
        timestamp last_updated
    }
    
    stocks {
        string symbol PK
        string company_name
        real current_price
        real market_cap
        string sector
        timestamp last_updated
    }
    
    recommendations ||--o{ performance_tracking : tracks
    recommendations ||--o| sold_stocks_watchlist : "creates when sold"
    nse_stocks ||--o{ stocks : "provides metadata"
```

## 2. Main Recommendations Table Schema

```mermaid
erDiagram
    recommendations {
        int id PK "Auto-increment primary key"
        string symbol "Stock symbol without .NS suffix"
        string company_name "Full company name"
        date recommendation_date "Date recommendation was made"
        string recommendation "BUY/SELL/HOLD recommendation"
        real score "Total weighted score 0-100"
        string risk_level "Low/Medium/High risk assessment"
        real entry_price "Price when recommendation made"
        real target_price "Calculated target price"
        real stop_loss "Calculated stop loss price"
        string sector "Company sector"
        int market_cap "Market capitalization"
        string reason "Summary of recommendation reason"
        real trend_score "Weighted trend analysis score"
        real momentum_score "Weighted momentum score"
        real rsi_score "Weighted RSI score"
        real volume_score "Weighted volume score"
        real price_action_score "Weighted price action score"
        string recommendation_tier "STRONG/WEAK/HOLD tier"
        real last_friday_price "Reference price for WEAK promotions"
        string status "ACTIVE/SOLD/CLOSED status"
        date promotion_date "Date promoted from WEAK to STRONG"
        date sell_date "Date position was sold"
        real sell_price "Price at which position was sold"
        real realized_return_pct "Realized return percentage"
        real money_made "Money made/lost per share"
        boolean is_sold "Flag indicating if position is sold"
        timestamp created_at "Record creation timestamp"
    }
```

## 3. Performance Tracking Schema

```mermaid
erDiagram
    performance_tracking {
        int id PK "Auto-increment primary key"
        int recommendation_id FK "Foreign key to recommendations"
        real current_price "Current market price"
        real return_pct "Current return percentage"
        int days_held "Number of days position held"
        timestamp last_updated "Last update timestamp"
    }
    
    recommendations {
        int id PK
        string symbol
        real entry_price
        string status
    }
    
    performance_tracking ||--|| recommendations : "tracks performance of"
```

## 4. Sold Stocks Watchlist Schema

```mermaid
erDiagram
    sold_stocks_watchlist {
        int id PK "Auto-increment primary key"
        string symbol UK "Stock symbol - unique constraint"
        string company_name "Company name for reference"
        string sector "Company sector"
        date sell_date "Date when stock was sold"
        real sell_price "Price at which stock was sold"
        string sell_reason "Reason for selling"
        real original_entry_price "Original entry price"
        real original_score "Original recommendation score"
        date last_check_date "Last re-entry check date"
        real last_check_score "Last calculated score"
        timestamp created_at "Record creation timestamp"
    }
```

## 5. Weekly Analysis Summary Schema

```mermaid
erDiagram
    weekly_summaries {
        int id PK "Auto-increment primary key"
        date analysis_date "Date of weekly analysis"
        int total_stocks_analyzed "Total stocks processed"
        int actionable_stocks "Stocks meeting minimum criteria"
        int strong_buy_count "Number of STRONG BUY recommendations"
        int buy_count "Number of BUY recommendations"
        int weak_buy_count "Number of WEAK BUY recommendations"
        real avg_score "Average score of actionable stocks"
        string best_stock "Best performing stock symbol"
        real best_score "Highest score achieved"
        real analysis_duration_minutes "Time taken for analysis"
        string top_sector "Best performing sector"
        timestamp created_at "Record creation timestamp"
    }
```

## 6. NSE Stocks Master Data Schema

```mermaid
erDiagram
    nse_stocks {
        string symbol PK "NSE stock symbol"
        string name "Official company name"
        string isin "ISIN number"
        string series "Trading series (EQ/BE/etc)"
        date date_of_listing "Stock listing date"
        timestamp last_updated "Last data refresh timestamp"
    }
```

## 7. Stock Scanner Database Schema

```mermaid
erDiagram
    stocks {
        string symbol PK "Stock symbol"
        string company_name "Company name"
        real current_price "Current market price"
        real market_cap "Market capitalization"
        string sector "Business sector"
        timestamp last_updated "Last price update"
    }
```

## 8. Data Relationships and Flow

```mermaid
erDiagram
    %% Main recommendation lifecycle
    nse_stocks ||--o{ recommendations : "stock metadata"
    recommendations ||--o{ performance_tracking : "daily performance updates"
    recommendations ||--o| sold_stocks_watchlist : "sold positions monitoring"
    
    %% Weekly analysis tracking
    weekly_summaries ||--o{ recommendations : "summarizes weekly batches"
    
    %% External data integration
    stocks ||--o{ recommendations : "current price data"
    
    %% Key constraints and relationships
    recommendations {
        string symbol "References nse_stocks.symbol"
        string recommendation_tier "STRONG/WEAK/HOLD"
        string status "ACTIVE/SOLD/CLOSED"
        boolean is_sold "Triggers watchlist creation"
    }
    
    performance_tracking {
        int recommendation_id "FK to recommendations.id"
        real return_pct "Calculated from entry vs current price"
    }
    
    sold_stocks_watchlist {
        string symbol "Unique - one entry per sold stock"
        real last_check_score "For re-entry evaluation"
    }
```

## 9. Database Indexes and Constraints

```mermaid
erDiagram
    indexes_and_constraints {
        string table_name
        string constraint_type
        string constraint_details
    }
    
    indexes_and_constraints {
        recommendations "PRIMARY KEY" "id (auto-increment)"
        recommendations "UNIQUE INDEX" "symbol + recommendation_tier + status"
        recommendations "INDEX" "recommendation_date"
        recommendations "INDEX" "recommendation_tier"
        recommendations "INDEX" "status"
        recommendations "INDEX" "is_sold"
        performance_tracking "PRIMARY KEY" "id (auto-increment)"
        performance_tracking "FOREIGN KEY" "recommendation_id -> recommendations.id"
        performance_tracking "INDEX" "recommendation_id"
        sold_stocks_watchlist "PRIMARY KEY" "id (auto-increment)"
        sold_stocks_watchlist "UNIQUE" "symbol"
        sold_stocks_watchlist "INDEX" "sell_date"
        nse_stocks "PRIMARY KEY" "symbol"
        nse_stocks "INDEX" "symbol"
        stocks "PRIMARY KEY" "symbol"
        weekly_summaries "PRIMARY KEY" "id (auto-increment)"
        weekly_summaries "INDEX" "analysis_date"
    }
```

## 10. Data Object Models

### Recommendation Data Object
```python
class RecommendationData:
    id: int
    symbol: str
    company_name: str
    recommendation_date: date
    recommendation: str  # "🟢 STRONG BUY", "🟢 BUY", "🟡 WEAK BUY", "⚪ HOLD", "🔴 SELL"
    score: float  # 0-100
    risk_level: str  # "Low", "Medium", "High"
    entry_price: float
    target_price: float
    stop_loss: float
    sector: str
    market_cap: int
    reason: str
    
    # Signal breakdown scores
    trend_score: float
    momentum_score: float
    rsi_score: float
    volume_score: float
    price_action_score: float
    
    # Tier management
    recommendation_tier: str  # "STRONG", "WEAK", "HOLD"
    last_friday_price: float
    status: str  # "ACTIVE", "SOLD", "CLOSED"
    
    # Lifecycle tracking
    promotion_date: Optional[date]
    sell_date: Optional[date]
    sell_price: Optional[float]
    realized_return_pct: Optional[float]
    money_made: Optional[float]
    is_sold: bool
    created_at: datetime
```

### Performance Tracking Data Object
```python
class PerformanceData:
    id: int
    recommendation_id: int
    current_price: float
    return_pct: float
    days_held: int
    last_updated: datetime
```

### Sold Stock Watchlist Data Object
```python
class SoldStockWatchlistData:
    id: int
    symbol: str
    company_name: str
    sector: str
    sell_date: date
    sell_price: float
    sell_reason: str
    original_entry_price: float
    original_score: float
    last_check_date: Optional[date]
    last_check_score: Optional[float]
    created_at: datetime
```

### Technical Analysis Data Object
```python
class TechnicalAnalysisData:
    # Moving Averages
    dma_50: Dict[str, Any]  # current_value, trend, weekly_data
    dma_200: Dict[str, Any]
    
    # Momentum Indicators
    weekly_macd: Dict[str, Any]  # macd_line, signal_line, crossovers
    
    # Oscillators
    weekly_rsi: Dict[str, Any]  # current_value, conditions, weekly_data
    
    # Volume Indicators
    obv: Dict[str, Any]  # current_value, trend_percentage, weekly_data
    vpt: Dict[str, Any]
    
    # Price Action
    weekly_prices: Dict[str, Any]  # closes, changes, volatility
    price_change_5d: float
    price_change_10d: float
    price_change_6m: float
```

### Signal Analysis Data Object
```python
class SignalAnalysisData:
    total_score: float  # 0-100
    recommendation: str
    risk_level: str
    
    breakdown: Dict[str, Dict[str, Any]] = {
        'trend': {
            'raw': float,
            'weighted': float,
            'signals': List[str]
        },
        'momentum': {
            'raw': float,
            'weighted': float,
            'signals': List[str]
        },
        'rsi': {
            'raw': float,
            'weighted': float,
            'signals': List[str]
        },
        'volume': {
            'raw': float,
            'weighted': float,
            'signals': List[str]
        },
        'price': {
            'raw': float,
            'weighted': float,
            'signals': List[str]
        }
    }
```

## 11. Database Transaction Patterns

```mermaid
sequenceDiagram
    participant App as Application
    participant DB as Database
    participant Perf as Performance Table
    participant Watch as Watchlist Table
    
    Note over App,Watch: New Recommendation Flow
    App->>DB: BEGIN TRANSACTION
    App->>DB: INSERT recommendation
    DB-->>App: recommendation_id
    App->>DB: COMMIT
    
    Note over App,Watch: Daily Monitoring Flow
    App->>DB: BEGIN TRANSACTION
    App->>DB: SELECT active recommendations
    App->>Perf: UPDATE/INSERT performance
    App->>DB: UPDATE recommendation status
    App->>Watch: INSERT if sold
    App->>DB: COMMIT
    
    Note over App,Watch: Promotion Flow
    App->>DB: BEGIN TRANSACTION
    App->>DB: UPDATE tier WEAK->STRONG
    App->>DB: UPDATE entry_price
    App->>DB: SET promotion_date
    App->>DB: COMMIT
    
    Note over App,Watch: Sell Flow
    App->>DB: BEGIN TRANSACTION
    App->>DB: UPDATE is_sold=1, sell_date, sell_price
    App->>DB: CALCULATE realized_return_pct
    App->>Watch: INSERT into watchlist
    App->>DB: COMMIT
```

This comprehensive ER diagram documentation shows all the database schemas, relationships, data objects, and transaction patterns used in your stock monitoring and recommendation system.