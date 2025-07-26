"""
Extended History Analyzer

This module provides extended historical data analysis capabilities for backtesting.
It extends the base SandboxAnalyzer with methods to work with longer historical periods.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from buy_sell_signal_analyzer import BuySellSignalAnalyzer
from stock_indicator_calculator import calculate_all_indicators_from_data

class ExtendedHistoryAnalyzer:
    """
    Extended History Analyzer that provides additional functionality for working with
    longer historical data periods for backtesting purposes.
    """
    
    def __init__(self):
        self.historical_years = 2  # Default to 2 years of historical data
    
    def get_extended_historical_data(self, symbol, years=2, end_date=None):
        """
        Fetch extended historical data for a given symbol.
        
        Args:
            symbol (str): Stock symbol (without .NS suffix)
            years (int): Number of years of historical data to fetch
            end_date (str, optional): End date in 'YYYY-MM-DD' format. Defaults to today.
            
        Returns:
            pandas.DataFrame: Historical data with indicators
        """
        yahoo_symbol = f"{symbol}.NS"
        end_date = pd.to_datetime(end_date) if end_date else datetime.now()
        start_date = (end_date - pd.DateOffset(years=years)).strftime('%Y-%m-%d')
        end_date = end_date.strftime('%Y-%m-%d')
        
        try:
            # Fetch data from Yahoo Finance
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if data.empty:
                print(f"⚠️ No historical data found for {symbol}")
                return None
                
            # Calculate indicators
            data = calculate_all_indicators_from_data(data)
            
            return data
            
        except Exception as e:
            print(f"❌ Error fetching data for {symbol}: {str(e)}")
            return None
    
    def analyze_stock_with_extended_history(self, symbol, analysis_date=None, years=2):
        """
        Analyze a stock with extended historical data.
        
        Args:
            symbol (str): Stock symbol (without .NS suffix)
            analysis_date (str, optional): Date to analyze as of (YYYY-MM-DD). Defaults to today.
            years (int): Number of years of historical data to use
            
        Returns:
            dict: Analysis results
        """
        # Get historical data up to analysis date
        data = self.get_extended_historical_data(symbol, years=years, end_date=analysis_date)
        
        if data is None or data.empty:
            return None
            
        # Get the latest data point (or the one closest to analysis_date)
        latest_data = data.iloc[-1]
        
        # Calculate scores based on indicators
        scores = {
            'trend': 100 if latest_data.get('trend', 0) > 0 else 0,
            'momentum': 100 if latest_data.get('momentum', 0) > 0 else 0,
            'volatility': 100 if latest_data.get('volatility', 0) < 1.5 else 0,
            'volume': 100 if latest_data.get('volume_ratio', 1) > 1.2 else 50,
            'rsi': 100 if 30 < latest_data.get('rsi', 50) < 70 else 0
        }
        
        # Calculate total score (weighted average)
        weights = {
            'trend': 0.3,
            'momentum': 0.3,
            'volatility': 0.2,
            'volume': 0.1,
            'rsi': 0.1
        }
        
        total_score = sum(scores[k] * weights[k] for k in scores)
        
        # Generate recommendation
        if total_score >= 80:
            recommendation = "STRONG_BUY"
        elif total_score >= 60:
            recommendation = "BUY"
        elif total_score >= 40:
            recommendation = "HOLD"
        elif total_score >= 20:
            recommendation = "WEAK_SELL"
        else:
            recommendation = "STRONG_SELL"
        
        return {
            'symbol': symbol,
            'analysis_date': analysis_date or datetime.now().strftime('%Y-%m-%d'),
            'price': latest_data['Close'],
            'total_score': round(total_score, 2),
            'recommendation': recommendation,
            'indicators': {
                'ma_50': latest_data.get('ma_50'),
                'ma_200': latest_data.get('ma_200'),
                'rsi': latest_data.get('rsi'),
                'macd': latest_data.get('macd'),
                'macd_signal': latest_data.get('macd_signal'),
                'volume_ratio': latest_data.get('volume_ratio')
            },
            'scores': scores
        }
