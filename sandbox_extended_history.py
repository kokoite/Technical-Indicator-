"""
Extended History Sandbox

This module provides extended historical data analysis capabilities for backtesting.
It extends the base SandboxAnalyzer with methods to work with longer historical periods
without modifying the core functionality.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from sandbox_analyzer import SandboxAnalyzer
from buy_sell_signal_analyzer import BuySellSignalAnalyzer
from stock_indicator_calculator import calculate_all_indicators_from_data

class ExtendedHistoryAnalyzer(SandboxAnalyzer):
    """
    Extended History Analyzer that provides additional functionality for working with
    longer historical data periods for backtesting purposes.
    """
    
    def __init__(self):
        super().__init__()
        self.historical_years = 2  # Default to 2 years of historical data
    
    def get_extended_historical_data(self, symbol, years=2, end_date=None):
        """
        Fetch extended historical data for a given symbol.
        
        Args:
            symbol (str): Stock symbol (without .NS suffix)
            years (int): Number of years of historical data to fetch
            end_date (str/datetime, optional): End date for historical data (YYYY-MM-DD format). 
                                             If None, uses current date.
            
        Returns:
            pandas.DataFrame: Historical price data or None if fetch fails
        """
        try:
            yahoo_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(yahoo_symbol)
            
            # Calculate start date based on years and end_date
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, '%Y-%m-%d')
                start_date = end_date - timedelta(days=365 * years)
                
                print(f"\n📡 Fetching {years} years of historical data for {symbol} up to {end_date.strftime('%Y-%m-%d')}...")
                data = ticker.history(start=start_date, end=end_date + timedelta(days=1), interval="1d")
            else:
                # If no end_date specified, use period-based fetching
                period = f"{years}y"
                print(f"\n📡 Fetching {years} years of historical data for {symbol}...")
                data = ticker.history(period=period, interval="1d")
            
            if data.empty:
                print(f"❌ No historical data found for {symbol}")
                return None
                
            print(f"✅ Successfully fetched {len(data)} trading days for {symbol}")
            return data
            
        except Exception as e:
            print(f"❌ Error fetching data for {symbol}: {str(e)}")
            return None
    
    def analyze_stock_with_extended_history(self, symbol, analysis_date, years=5):
        """
        Analyze a stock with extended historical data up to the analysis date.
        
        Args:
            symbol (str): Stock symbol (without .NS suffix)
            analysis_date (datetime.date): Date to analyze as of
            years (int): Number of years of historical data to use
            
        Returns:
            dict: Analysis results or None if analysis fails
        """
        try:
            # Get extended historical data
            data = self.get_extended_historical_data(symbol, years)
            if data is None:
                return None
                
            # Convert analysis_date to datetime if it's a date object
            if isinstance(analysis_date, str):
                analysis_date = datetime.strptime(analysis_date, '%Y-%m-%d').date()
            
            # Clip data to only include data up to the analysis date
            clipped_data = data[data.index.date <= analysis_date].copy()
            
            if clipped_data.empty:
                print(f"❌ No data available for {symbol} before {analysis_date}")
                return None
                
            print(f"📊 Analyzing {symbol} as of {analysis_date} with {len(clipped_data)} days of historical data")
            
            # Get company info
            yahoo_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            
            # Calculate technical indicators
            analysis_result = self.analyzer.calculate_overall_score_with_data(yahoo_symbol, clipped_data)
            
            if not analysis_result:
                return None
                
            # Get Friday's closing price
            friday_price = clipped_data['Close'].iloc[-1]
            
            return {
                'symbol': symbol,
                'company_name': info.get('longName', symbol),
                'analysis_date': analysis_date.strftime('%Y-%m-%d'),
                'price': friday_price,
                'total_score': analysis_result['total_score'],
                'recommendation': analysis_result['recommendation'],
                'risk_level': analysis_result['risk_level'],
                'sector': info.get('sector', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'breakdown': analysis_result['breakdown'],
                'data_points': len(clipped_data)
            }
            
        except Exception as e:
            print(f"❌ Error analyzing {symbol}: {str(e)}")
            return None

def test_extended_analysis(analysis_date=None, symbols=None, years=2):
    """
    Test function to demonstrate extended historical analysis
    
    Args:
        analysis_date (str): Date to analyze as of (YYYY-MM-DD format). If None, uses last Friday.
        symbols (list): List of stock symbols to analyze. If None, uses default list.
        years (int): Number of years of historical data to use
    """
    analyzer = ExtendedHistoryAnalyzer()
    
    # Set default values if not provided
    if analysis_date is None:
        # Get last Friday's date
        today = datetime.now().date()
        last_friday = today - timedelta(days=today.weekday() + 3)  # Monday=0, Sunday=6
        analysis_date = last_friday.strftime('%Y-%m-%d')
        
    if symbols is None:
        symbols = ['RELIANCE', 'TCS', 'HDFCBANK']  # Default symbols
    
    print("\n" + "="*70)
    print(f"RUNNING EXTENDED HISTORY ANALYSIS FOR {analysis_date}")
    print("="*70)
    
    for symbol in symbols:
        print(f"\n{'='*50}")
        print(f"ANALYZING {symbol} WITH EXTENDED HISTORY")
        print(f"{'='*50}")
        
        result = analyzer.analyze_stock_with_extended_history(
            symbol=symbol,
            analysis_date=analysis_date,
            years=years
        )
        
        if result:
            print(f"\n📈 Analysis Results for {result['company_name']} ({result['symbol']}) as of {result['analysis_date']}")
            print(f"💵 Price: ₹{result['price']:,.2f}")
            print(f"🏆 Recommendation: {result['recommendation']} (Score: {result['total_score']}/100)")
            print(f"📊 Data Points: {result['data_points']} trading days")
            print(f"🏢 Sector: {result['sector']}")
            print(f"💰 Market Cap: ₹{result['market_cap']/10000000:,.2f} Cr")
            
            # Print key breakdown items
            print("\nKey Indicators:")
            breakdown = result['breakdown']
            for key in ['trend_score', 'momentum_score', 'rsi_condition', 'volume_score', 'price_action_score']:
                if key in breakdown:
                    print(f"- {key.replace('_', ' ').title()}: {breakdown[key]}")
        else:
            print(f"❌ Failed to analyze {symbol}")

if __name__ == "__main__":
    import argparse
    
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Run extended historical stock analysis')
    parser.add_argument('--date', type=str, help='Analysis date (YYYY-MM-DD format)')
    parser.add_argument('--symbols', type=str, help='Comma-separated list of stock symbols')
    parser.add_argument('--years', type=int, default=2, help='Years of historical data to use (default: 2)')
    
    args = parser.parse_args()
    
    # Process symbols if provided
    symbols = None
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    
    # Run analysis with specified parameters
    test_extended_analysis(
        analysis_date=args.date,
        symbols=symbols,
        years=args.years
    )
