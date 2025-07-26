# 📊 Weekly Technical Analysis Logic Documentation

## 🎯 Overview

This document outlines the comprehensive weekly technical analysis system used to evaluate NSE stocks for buy/sell/hold recommendations. The system analyzes **1,288 stocks** using **5 key technical categories** with a **weighted scoring approach** based on **6 months of weekly data**.

---

## 🏗️ System Architecture

### **Data Source & Frequency**
- **Data Provider:** Yahoo Finance (yfinance)
- **Analysis Frequency:** Weekly (runs once per week)
- **Data Period:** 6 months of weekly resampled data
- **Stock Universe:** ~1,288 NSE stocks (₹50 - ₹1000 price range)

### **Core Components**
1. **Stock Indicator Calculator** - Fetches and processes technical indicators
2. **Buy/Sell Signal Analyzer** - Applies weighted scoring logic
3. **Weekly Analysis System** - Manages bulk analysis of all stocks
4. **Recommendations Database** - Stores and tracks performance

---

## 📈 Technical Indicators Used

### **1. Moving Averages (DMA)**
- **50-Day DMA:** Short-term trend indicator
- **200-Day DMA:** Long-term trend indicator
- **Golden/Death Cross:** 50-DMA vs 200-DMA relationship

### **2. MACD (Moving Average Convergence Divergence)**
- **MACD Line:** 12-period EMA minus 26-period EMA
- **Signal Line:** 9-period EMA of MACD line
- **Histogram:** MACD line minus Signal line
- **Crossovers:** Bullish/Bearish signal crossovers

### **3. RSI (Relative Strength Index)**
- **Period:** 14-week RSI
- **Levels:** Overbought (>70), Oversold (<30), Neutral (30-70)
- **Trend:** Rising/falling RSI momentum

### **4. Volume Indicators**
- **OBV (On-Balance Volume):** Cumulative volume based on price direction
- **VPT (Volume Price Trend):** Volume weighted by price change percentage
- **120-Day Moving Average:** For trend comparison

### **5. Price Action**
- **Weekly Price Changes:** Last 4 weeks momentum
- **Volatility:** 6-month standard deviation of weekly changes
- **Volume Trends:** Recent volume patterns

---

## 🎯 Scoring System (100 Points Total)

### **Weight Distribution**
| Category | Weight | Max Points | Focus Area |
|----------|--------|------------|------------|
| **Trend Alignment** | 25% | 25 | DMA trends, price position |
| **Volume Confirmation** | 25% | 25 | OBV/VPT strength |
| **Momentum** | 20% | 20 | MACD signals |
| **Price Action** | 15% | 15 | Recent performance |
| **RSI Condition** | 15% | 15 | Overbought/oversold |

---

## 🔄 Category-Wise Scoring Logic

### **1. Trend Alignment (25 points)**

#### **50-Day DMA Analysis**
- **Uptrend:** +8 points
- **Downtrend:** -5 points

#### **200-Day DMA Analysis**
- **Uptrend:** +7 points
- **Downtrend:** -3 points

#### **Price vs DMA Position**
- **Price > 50-DMA:** +5 points
- **Price < 50-DMA:** -3 points

#### **Golden/Death Cross**
- **50-DMA > 200-DMA (Golden Cross):** +5 points
- **50-DMA < 200-DMA (Death Cross):** -5 points

### **2. Volume Confirmation (25 points)**

#### **OBV Analysis**
- **Strong Uptrend (>15%):** +8 points
- **Uptrend (5-15%):** +5 points
- **Strong Downtrend (<-15%):** -8 points
- **Downtrend (-15 to -5%):** -5 points

#### **OBV vs MA120 Position**
- **Above MA120:** +4 points
- **Below MA120:** -4 points

#### **VPT Analysis**
- **Strong Uptrend (>15%):** +8 points
- **Uptrend (5-15%):** +5 points
- **Strong Downtrend (<-15%):** -8 points
- **Downtrend (-15 to -5%):** -5 points

#### **VPT vs MA120 Position**
- **Above MA120:** +5 points
- **Below MA120:** -5 points

### **3. Momentum (20 points)**

#### **Recent MACD Crossover**
- **Bullish Crossover:** +12 points
- **Bearish Crossover:** -12 points

#### **MACD Histogram Strength**
- **Strong Positive (>5):** +5 points
- **Positive (0-5):** +3 points
- **Strong Negative (<-5):** -5 points
- **Negative (-5 to 0):** -3 points

#### **Recent Crossover Trend (4 weeks)**
- **More Bullish Crossovers:** +3 points
- **More Bearish Crossovers:** -3 points

### **4. RSI Condition (15 points)**

#### **RSI Level Analysis**
- **Oversold Recovery (30-45):** +10 points
- **Healthy Bullish (45-65):** +5 points
- **Getting Overbought (65-75):** -3 points
- **Severely Overbought (>75):** -8 points
- **Deep Oversold (<30):** +8 points

#### **RSI Trend (4 weeks)**
- **Rising Trend (>5%):** +2 points
- **Falling Trend (<-5%):** -2 points

### **5. Price Action (15 points)**

#### **Recent Price Performance (4 weeks)**
- **Strong Momentum (>2%):** +8 points
- **Positive Trend (0-2%):** +4 points
- **Weak Performance (<-2%):** -8 points
- **Negative Trend (-2 to 0%):** -4 points

#### **Volatility Assessment**
- **Low Volatility (<3%):** +3 points (stable)
- **High Volatility (>8%):** -3 points (risky)

#### **Volume Trend (4 weeks)**
- **Increasing Volume (>20%):** +4 points
- **Declining Volume (<-20%):** -4 points

---

## 📋 Recommendation Levels

### **Final Score Interpretation**
| Score Range | Recommendation | Risk Level | Action |
|-------------|---------------|------------|---------|
| **75-100** | 🟢 STRONG BUY | Low | Aggressive accumulation |
| **60-74** | 🟢 BUY | Low-Medium | Position building |
| **40-59** | 🟡 WEAK BUY | Medium | Cautious entry |
| **20-39** | ⚪ HOLD | Medium-High | Maintain positions |
| **0-19** | 🟡 WEAK SELL | High | Consider reducing |
| **<0** | 🔴 SELL | High | Exit positions |

---

## 🔄 Weekly Analysis Workflow

### **1. Data Collection Phase**
```
For each stock in NSE database (1,288 stocks):
├── Fetch 2 years of daily data (single API call)
├── Resample to weekly data (Friday closing)
├── Calculate all 5 technical indicators
└── Store in optimized data structure
```

### **2. Analysis Phase**
```
For each stock:
├── Apply trend analysis (25% weight)
├── Apply volume analysis (25% weight)  
├── Apply momentum analysis (20% weight)
├── Apply price action analysis (15% weight)
├── Apply RSI analysis (15% weight)
├── Calculate weighted final score
└── Generate recommendation
```

### **3. Filtering & Ranking**
```
Results Processing:
├── Filter stocks with score ≥ 35 (actionable threshold)
├── Rank by final score (highest first)
├── Group by recommendation level
└── Analyze sector performance
```

### **4. Storage & Tracking**
```
Database Operations:
├── Save recommendations with timestamps
├── Track performance over time
├── Update weekly analysis history
└── Generate performance reports
```

---

## 🎯 Key Design Principles

### **1. Weekly Focus**
- **Why Weekly:** Reduces noise, focuses on meaningful trends
- **Data Resampling:** Friday closing prices for consistency
- **6-Month Window:** Balances recency with statistical significance

### **2. Multi-Factor Approach**
- **No Single Indicator Dependency:** Combines 5 different signal types
- **Weighted Scoring:** Trend and Volume get highest weight (25% each)
- **Momentum Focus:** MACD gets 20% for timing signals

### **3. Risk Management**
- **Conservative Thresholds:** Minimum score 35 for actionable signals
- **Risk Levels:** Clear risk categorization for each recommendation
- **Performance Tracking:** Historical performance monitoring

### **4. Scalability**
- **Optimized API Usage:** 1 call per stock (9x improvement)
- **Batch Processing:** Handles 1,288 stocks efficiently
- **Rate Limiting:** Respects API limits with delays

---

## 📊 Performance Metrics

### **Success Criteria**
- **Accuracy:** % of positive returns on BUY recommendations
- **Risk-Adjusted Returns:** Sharpe ratio of recommendations
- **Sector Coverage:** Diversification across sectors
- **Timing:** Entry/exit point effectiveness

### **Tracking Methodology**
- **Weekly Performance Updates:** Track price changes post-recommendation
- **30/60/90 Day Returns:** Multiple time horizon analysis
- **Benchmark Comparison:** Performance vs NIFTY 50
- **Drawdown Analysis:** Maximum loss periods

---

## 🔧 System Optimizations

### **API Efficiency**
- **Before:** 9 API calls per stock (11,592 total calls)
- **After:** 1 API call per stock (1,288 total calls)
- **Speed Improvement:** 9x faster data fetching

### **Error Handling**
- **Robust Data Validation:** Handles missing/incomplete data
- **Timeout Management:** 30-second timeouts for stuck requests
- **Retry Logic:** Graceful handling of rate limits

### **Memory Management**
- **Batch Processing:** Processes stocks in manageable batches
- **Data Cleanup:** Releases memory between batches
- **Progressive Results:** Saves results incrementally

---

## 📈 Expected Outcomes

### **Weekly Analysis Results**
- **Typical Actionable Stocks:** 50-150 stocks per week (4-12% of universe)
- **Strong Buy Signals:** 5-20 stocks per week (top tier)
- **Sector Distribution:** Technology, Banking, Pharma typically leading

### **Performance Expectations**
- **Hit Rate Target:** 60-70% positive returns on BUY signals
- **Average Return:** 8-15% on successful recommendations
- **Risk Management:** Maximum 5-8% stop loss recommendations

---

## 🚀 Future Enhancements

### **Planned Improvements**
1. **Machine Learning Integration:** Pattern recognition for better signals
2. **Sector Rotation Analysis:** Industry-specific momentum tracking
3. **Market Regime Detection:** Bull/bear market adjustments
4. **Options Flow Integration:** Derivative market sentiment
5. **News Sentiment Analysis:** Fundamental catalyst integration

### **Technical Upgrades**
1. **Real-time Data Feeds:** Upgrade from daily to intraday data
2. **Cloud Infrastructure:** Scalable processing capabilities
3. **API Diversification:** Multiple data sources for redundancy
4. **Mobile Notifications:** Real-time alert system

---

## 📝 Conclusion

This weekly technical analysis system provides a **systematic, data-driven approach** to NSE stock evaluation. By combining **multiple technical indicators** with **weighted scoring** and **risk management principles**, it aims to identify high-probability trading opportunities while maintaining **disciplined risk control**.

The system's **weekly frequency** strikes an optimal balance between **signal quality** and **practical implementation**, making it suitable for both **individual traders** and **institutional strategies**.

---

*Last Updated: January 2025*  
*System Version: 1.0*  
*Total Stocks Analyzed: 1,288* 