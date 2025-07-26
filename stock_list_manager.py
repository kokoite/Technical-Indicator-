"""
Stock List Manager - Manages NSE stock list with database persistence
"""

import csv
import io
import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import List, Optional, Set, Dict, Any
import requests

class StockListManager:
    """Manages fetching and caching of NSE stock lists with database persistence"""
    
    def __init__(self, db_path: str = "sandbox_recommendations.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create nse_stocks table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS nse_stocks (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                isin TEXT,
                series TEXT,
                date_of_listing DATE,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create index for faster lookups
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_nse_stocks_symbol 
            ON nse_stocks(symbol)
            ''')
            
            conn.commit()
    
    def get_stock_list(self, force_refresh: bool = False) -> List[str]:
        """Get list of NSE stocks with database caching and fallbacks"""
        # Try database first if not forcing refresh
        if not force_refresh:
            db_stocks = self._load_from_database()
            if db_stocks:
                return db_stocks
        
        # Try different sources to fetch fresh data
        sources = [
            self._fetch_from_nse,
            self._fetch_from_nse_alternative,
            self._fetch_nse_indices,
            self._get_curated_list
        ]
        
        for source in sources:
            try:
                print(f"🔍 Trying {source.__name__}...")
                stocks_data = source(return_full_data=True) if source.__name__ in ['_fetch_from_nse', '_fetch_from_nse_alternative'] else source()
                
                if isinstance(stocks_data, list) and len(stocks_data) > 10:
                    # If we have full data (from NSE), save it to database
                    if source.__name__ in ['_fetch_from_nse', '_fetch_from_nse_alternative']:
                        self._save_to_database(stocks_data)
                        return sorted([s['SYMBOL'].strip() for s in stocks_data 
                                    if s.get('SYMBOL') and s.get(' SERIES', '').strip() == 'EQ'])
                    else:
                        # For other sources that only return symbols
                        return sorted(stocks_data)
                        
            except Exception as e:
                print(f"⚠️ {source.__name__} failed: {e}")
        
        return self._get_basic_list()
    
    def _fetch_from_nse(self, return_full_data: bool = False) -> List[Dict[str, str]]:
        """
        Fetch from NSE website - primary method
        
        Args:
            return_full_data: If True, returns full stock data instead of just symbols
            
        Returns:
            List of stock data dictionaries or list of symbols based on return_full_data
        """
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/csv',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        response = requests.get(
            f"{url}?v={int(time.time())}",
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        
        # Parse the full CSV data
        content = response.content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        stocks_data = []
        for row in reader:
            if row.get(' SERIES', '').strip() == 'EQ':
                stocks_data.append(dict(row))
        
        if not stocks_data:
            raise ValueError("No stocks found in NSE response")
            
        print(f"✅ Fetched {len(stocks_data)} stocks from NSE website")
        
        if return_full_data:
            return stocks_data
        return [s['SYMBOL'].strip() for s in stocks_data]
    
    def _fetch_from_nse_alternative(self, return_full_data: bool = False) -> List[Dict[str, str]]:
        """
        Alternative method to fetch from NSE website
        
        Args:
            return_full_data: If True, returns full stock data instead of just symbols
            
        Returns:
            List of stock data dictionaries or list of symbols based on return_full_data
        """
        url = "https://www1.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/csv',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        session = requests.Session()
        session.get("https://www1.nseindia.com/", headers=headers)  # Get cookies
        
        response = session.get(
            url,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        
        # Parse the full CSV data
        content = response.content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        stocks_data = []
        for row in reader:
            if row.get(' SERIES', '').strip() == 'EQ':
                stocks_data.append(dict(row))
        
        if not stocks_data:
            raise ValueError("No stocks found in NSE alternative response")
            
        print(f"✅ Fetched {len(stocks_data)} stocks from NSE alternative URL")
        
        if return_full_data:
            return stocks_data
        return [s['SYMBOL'].strip() for s in stocks_data]
    
    def _fetch_nse_indices(self) -> List[str]:
        """Fetch from NSE indices as fallback"""
        try:
            import nsepython as nse
            
            indices = ['NIFTY 50', 'NIFTY NEXT 50', 'NIFTY 500']
            stocks = set()
            
            for idx in indices:
                try:
                    data = nse.nse_get_index_quote(idx)
                    if data and 'data' in data:
                        for stock in data['data']:
                            if 'symbol' in stock and isinstance(stock['symbol'], str):
                                stocks.add(stock['symbol'].strip())
                    time.sleep(0.5)  # Be nice to the server
                except Exception as e:
                    print(f"⚠️ Failed to fetch {idx}: {e}")
            
            if not stocks:
                raise ValueError("No stocks found in NSE indices")
                
            stocks = list(stocks)
            print(f"✅ Fetched {len(stocks)} unique stocks from NSE indices")
            return stocks
            
        except ImportError:
            print("ℹ️ nsepython not installed, skipping indices method")
            return []
        except Exception as e:
            print(f"⚠️ Error in _fetch_nse_indices: {e}")
            return []
    
    def _get_curated_list(self) -> List[str]:
        """Curated list of liquid stocks"""
        return [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'BHARTIARTL', 
            'SBIN', 'ITC', 'LT', 'HCLTECH', 'AXISBANK', 'MARUTI', 'ASIANPAINT',
            'NESTLEIND', 'BAJFINANCE', 'WIPRO', 'ULTRACEMCO', 'TITAN', 'POWERGRID',
            'NTPC', 'TECHM', 'SUNPHARMA', 'COALINDIA', 'TATAMOTORS', 'JSWSTEEL',
            'GRASIM', 'HINDALCO', 'INDUSINDBK', 'BAJAJFINSV', 'CIPLA', 'DRREDDY',
            'EICHERMOT', 'BRITANNIA', 'DIVISLAB', 'TATACONSUM', 'HEROMOTOCO',
            'APOLLOHOSP', 'ADANIENT', 'UPL', 'BPCL', 'ONGC', 'IOC', 'TATASTEEL'
        ]
    
    def _get_basic_list(self) -> List[str]:
        """Minimal fallback list"""
        return ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK']
    
    def _load_from_database(self) -> Optional[List[str]]:
        """Load stock symbols from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT symbol FROM nse_stocks ORDER BY symbol")
                stocks = [row[0] for row in cursor.fetchall()]
                
                if stocks:
                    print(f"📊 Loaded {len(stocks)} stocks from database")
                    return stocks
        except Exception as e:
            print(f"⚠️ Error loading from database: {e}")
        return None
    
    def _save_to_database(self, stocks_data: List[Dict[str, Any]]) -> None:
        """Save stocks data to the database"""
        if not stocks_data:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute("DELETE FROM nse_stocks")
            
            # Insert new data
            cursor.executemany('''
            INSERT OR REPLACE INTO nse_stocks 
            (symbol, name, isin, series, date_of_listing, last_updated)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', [
                (
                    stock.get('SYMBOL', '').strip(),
                    stock.get('NAME OF COMPANY', '').strip(),
                    stock.get('ISIN NUMBER', '').strip(),
                    stock.get(' SERIES', '').strip(),
                    stock.get(' DATE OF LISTING', '').strip() or None
                )
                for stock in stocks_data
                if stock.get('SYMBOL') and stock.get(' SERIES', '').strip() == 'EQ'
            ])
            
            conn.commit()
            print(f"💾 Saved {cursor.rowcount} stocks to database")

# Singleton instance
stock_list_manager = StockListManager()

def get_nse_stock_list(force_refresh: bool = False) -> List[str]:
    """Get NSE stock list with caching"""
    return stock_list_manager.get_stock_list(force_refresh)

if __name__ == "__main__":
    # Simple test when run directly
    print("🔍 Testing StockListManager...")
    manager = StockListManager()
    stocks = manager.get_stock_list(force_refresh=True)
    print(f"✅ Got {len(stocks)} stocks")
    print(f"Sample: {stocks[:20]}...")
