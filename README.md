# NSE Technical Analysis System

A comprehensive Python-based system for analyzing NSE (National Stock Exchange) stocks using advanced technical indicators and machine learning-driven buy/sell signals.

## 🚀 Features

- **Advanced Technical Analysis**: Uses 25+ indicators including DMAs, MACD, RSI, OBV, VPT
- **Sophisticated Scoring System**: Weighted analysis with trend, momentum, volume, and price action signals
- **Historical Backtesting**: Analyze performance across multiple time periods
- **Dynamic Threshold Analysis**: Track stock performance with automatic sell logic
- **Efficient Data Processing**: Single API call per stock for multiple historical analyses
- **Clean Database Management**: Smart duplicate handling and data integrity checks

## 📋 Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/kokoite/Technical-Indicator-.git
cd Technical-Indicator-
python setup.py
```

### 2. Run the Sandbox Analyzer

```bash
python sandbox_analyzer.py
```

Choose from:
1. **One-time Data Population** - Populate historical Friday analysis data
2. **Dynamic Threshold Analysis** - Backtest from any past Friday to today

## 🛠 Installation

### Requirements

- Python 3.8+
- Internet connection for stock data fetching

### Dependencies

All dependencies are listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

**Core Libraries:**
- `yfinance` - Stock data fetching
- `pandas` - Data manipulation
- `numpy` - Numerical computations
- `pandas-ta` - Technical analysis indicators
- `matplotlib` - Plotting and visualization

## 📊 System Architecture

### Core Components

1. **`sandbox_analyzer.py`** - Main analysis engine
2. **`buy_sell_signal_analyzer.py`** - Sophisticated scoring system
3. **`stock_indicator_calculator.py`** - Technical indicator calculations
4. **`sandbox_database.py`** - Database management with integrity checks
5. **`stock_list_manager.py`** - NSE stock list management

### Key Features

#### 🎯 Advanced Scoring System
- **Trend Analysis (25%)**: 50-DMA, 200-DMA trends and golden/death cross detection
- **Momentum Signals (20%)**: MACD crossovers and histogram analysis
- **RSI Conditions (15%)**: Overbought/oversold with trend analysis
- **Volume Confirmation (25%)**: OBV and VPT trend analysis with MA120 positioning
- **Price Action (15%)**: Recent price movements and volatility assessment

#### 📈 Historical Analysis
- **Multi-Friday Analysis**: Analyze stocks as of any past Friday using historical data clipping
- **Single API Call Efficiency**: Fetch 2 years of data once, analyze multiple time periods
- **Data Integrity**: Smart duplicate detection and user-controlled overwrites

#### 🔄 Dynamic Backtesting
- **Read-Only Analysis**: Track performance without database writes
- **Automatic Selling**: Sell positions when scores drop below threshold
- **Comprehensive Reports**: Detailed P&L, sector analysis, and performance metrics

## 📖 Usage Examples

### Basic Stock Analysis

```python
from buy_sell_signal_analyzer import BuySellSignalAnalyzer

analyzer = BuySellSignalAnalyzer()
result = analyzer.calculate_overall_score('RELIANCE.NS')
print(f"Score: {result['total_score']}")
print(f"Recommendation: {result['recommendation']}")
```

### Historical Friday Analysis

```python
from sandbox_analyzer import SandboxAnalyzer
from datetime import datetime

analyzer = SandboxAnalyzer()
friday_date = datetime(2024, 7, 19)  # Specific Friday
results = analyzer.analyze_stock_for_multiple_fridays('TCS', [friday_date])
```

### Population with Smart Updates

```python
# Safe mode - skip existing data
analyzer.populate_historical_fridays_optimized(
    num_fridays=4, 
    limit=100, 
    update_mode='safe'
)

# Check mode - warn about data differences
analyzer.populate_historical_fridays_optimized(
    num_fridays=4, 
    update_mode='check'
)
```

## 🗄 Database Schema

### `friday_stocks_analysis` Table
- **Core Data**: symbol, company_name, friday_date, friday_price
- **Scores**: total_score, recommendation, risk_level
- **Technical Indicators**: ma_50, ma_200, rsi_value, macd_value, macd_signal
- **Component Scores**: trend_score, momentum_score, rsi_score, volume_score, price_action_score
- **Raw Metrics**: volume_ratio, price_change_1d, price_change_5d

## 🔧 Configuration

### Update Modes
- **`safe`**: Skip existing records (recommended for weekly updates)
- **`check`**: Warn if historical data differs (debugging)
- **`force`**: Overwrite all data (use with caution)

### Scoring Thresholds
- **STRONG (≥67)**: High confidence buy signals
- **WEAK (50-66)**: Moderate buy signals  
- **HOLD (20-49)**: Neutral/hold positions
- **SELL (<20)**: Sell signals

## 📊 Sample Output

```
🎯 DYNAMIC THRESHOLD ANALYSIS REPORT
==================================================
📅 Period: 2024-06-28 to Today
🎯 Threshold: 67
📈 Total Positions: 156

💰 P&L SUMMARY:
💵 Total Invested:    ₹2,34,567.00
💰 Current Value:     ₹2,67,890.00
🟢 Total P&L:         ₹+33,323.00
📊 Total Return:      +14.2%

🟢 Active Positions: 89
🔴 Sold Positions: 67
📊 Win Rate: 67.3%
```

## 🚨 Important Notes

### Data Sources
- **NSE Stock Data**: Via Yahoo Finance API
- **Rate Limiting**: Built-in delays to respect API limits
- **Data Validation**: Comprehensive error handling and data quality checks

### Performance Considerations
- **Memory Efficient**: Processes stocks individually to manage memory usage
- **API Optimized**: Single call per stock for multiple time period analysis
- **Database Optimized**: Uses proper indexing and batch operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is for educational and research purposes. Please ensure compliance with data provider terms of service.

## 🐛 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt
```

**2. Database Locked**
```bash
# Close any open database connections
# Restart the application
```

**3. API Rate Limits**
```bash
# The system includes built-in rate limiting
# If you encounter issues, increase the delay in the code
```

**4. Memory Issues with Large Datasets**
```bash
# Use the limit parameter to process fewer stocks
analyzer.populate_historical_fridays_optimized(limit=100)
```

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the code comments for detailed explanations
3. Create an issue in the GitHub repository

---

**⚠️ Disclaimer**: This system is for educational and research purposes only. Not financial advice. Always do your own research before making investment decisions. 