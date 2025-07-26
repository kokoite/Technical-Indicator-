import yfinance as yf
import pandas as pd
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
import random
from nsetools import Nse
import sqlite3
import os

warnings.filterwarnings('ignore')

# Database configuration
DB_NAME = 'nse_stock_scanner.db'

def init_database():
    """Initialize SQLite database and create tables if they don't exist"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Create scans table for scan metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_date TEXT NOT NULL,
                scan_duration_seconds REAL NOT NULL,
                total_stocks_scanned INTEGER NOT NULL,
                stocks_in_range INTEGER NOT NULL,
                stocks_above_1000 INTEGER NOT NULL,
                stocks_below_50 INTEGER NOT NULL,
                errors INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create stocks table with unique constraint on symbol for latest data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                company_name TEXT NOT NULL,
                current_price REAL NOT NULL,
                price_change REAL NOT NULL,
                price_change_pct REAL NOT NULL,
                volume INTEGER NOT NULL,
                market_cap INTEGER,
                sector TEXT,
                industry TEXT,
                pe_ratio REAL,
                book_value REAL,
                dividend_yield REAL,
                high_52w REAL,
                low_52w REAL,
                beta REAL,
                employees INTEGER,
                currency TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Check if last_updated column exists, if not add it
        cursor.execute("PRAGMA table_info(stocks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'last_updated' not in columns:
            cursor.execute('ALTER TABLE stocks ADD COLUMN last_updated TEXT')
            print("📝 Added last_updated column to existing stocks table")
        
        # Create unique index on symbol if it doesn't exist
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_stocks_symbol 
            ON stocks(symbol)
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {str(e)}")
        return False

def save_stock_immediately(stock_data, scan_id):
    """Save individual stock data immediately with update-or-insert logic"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check if stock already exists
        cursor.execute('SELECT id FROM stocks WHERE symbol = ?', (stock_data['symbol'],))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing stock
            cursor.execute('''
                UPDATE stocks SET 
                scan_id = ?, company_name = ?, current_price = ?, price_change = ?,
                price_change_pct = ?, volume = ?, market_cap = ?, sector = ?, 
                industry = ?, pe_ratio = ?, book_value = ?, dividend_yield = ?,
                high_52w = ?, low_52w = ?, beta = ?, employees = ?, currency = ?,
                last_updated = ?
                WHERE symbol = ?
            ''', (
                scan_id,
                stock_data['company_name'],
                stock_data['current_price'],
                stock_data['price_change'],
                stock_data['price_change_pct'],
                stock_data['volume'],
                stock_data.get('market_cap', 0),
                stock_data.get('sector', 'Unknown'),
                stock_data.get('industry', 'Unknown'),
                stock_data.get('pe_ratio', 0),
                stock_data.get('book_value', 0),
                stock_data.get('dividend_yield', 0),
                stock_data['high_52w'],
                stock_data['low_52w'],
                stock_data.get('beta', 0),
                stock_data.get('employees', 0),
                stock_data.get('currency', 'INR'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                stock_data['symbol']
            ))
        else:
            # Insert new stock
            cursor.execute('''
                INSERT INTO stocks 
                (scan_id, symbol, company_name, current_price, price_change,
                 price_change_pct, volume, market_cap, sector, industry, pe_ratio,
                 book_value, dividend_yield, high_52w, low_52w, beta, employees,
                 currency, last_updated, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                scan_id,
                stock_data['symbol'],
                stock_data['company_name'],
                stock_data['current_price'],
                stock_data['price_change'],
                stock_data['price_change_pct'],
                stock_data['volume'],
                stock_data.get('market_cap', 0),
                stock_data.get('sector', 'Unknown'),
                stock_data.get('industry', 'Unknown'),
                stock_data.get('pe_ratio', 0),
                stock_data.get('book_value', 0),
                stock_data.get('dividend_yield', 0),
                stock_data['high_52w'],
                stock_data['low_52w'],
                stock_data.get('beta', 0),
                stock_data.get('employees', 0),
                stock_data.get('currency', 'INR'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error saving stock {stock_data['symbol']}: {str(e)}")
        return False

def save_scan_metadata(scan_metadata):
    """Save scan metadata and return scan_id"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO scans (scan_date, scan_duration_seconds, total_stocks_scanned,
                             stocks_in_range, stocks_above_1000, stocks_below_50, errors, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            scan_metadata['scan_date'].strftime('%Y-%m-%d %H:%M:%S'),
            scan_metadata['scan_duration_seconds'],
            scan_metadata['total_stocks_scanned'],
            scan_metadata['stocks_in_range'],
            scan_metadata['stocks_above_1000'],
            scan_metadata['stocks_below_50'],
            scan_metadata['errors'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        scan_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return scan_id
        
    except Exception as e:
        print(f"❌ Error saving scan metadata: {str(e)}")
        return None

def retry_failed_stocks(failed_stocks, scan_id):
    """Retry failed stocks with shorter delays"""
    if not failed_stocks:
        return []
    
    print(f"\n🔄 Retrying {len(failed_stocks)} failed stocks with shorter delays...")
    recovered_stocks = []
    
    for i, symbol in enumerate(failed_stocks):
        try:
            # Short delay between retries
            time.sleep(random.uniform(0.1, 0.3))
            
            stock_data, current_price, in_range = get_stock_info(symbol, retry_count=0)
            
            if stock_data and in_range:
                recovered_stocks.append(stock_data)
                # Save immediately
                if save_stock_immediately(stock_data, scan_id):
                    print(f"✅ RETRY SUCCESS: {symbol} - ₹{current_price:.2f} (SAVED TO DB)")
                else:
                    print(f"✅ RETRY SUCCESS: {symbol} - ₹{current_price:.2f} (DB SAVE FAILED)")
            elif current_price:
                if current_price > 1000:
                    print(f"📈 RETRY HIGH: {symbol} - ₹{current_price:.2f} (Above ₹1000)")
                else:
                    print(f"📉 RETRY LOW: {symbol} - ₹{current_price:.2f} (Below ₹50)")
            else:
                print(f"❌ RETRY FAILED: {symbol} (Still no data)")
                
            # Progress update every 10 retries
            if (i + 1) % 10 == 0:
                print(f"🔄 Retry progress: {i + 1}/{len(failed_stocks)} | Recovered: {len(recovered_stocks)}")
                
        except Exception as e:
            print(f"❌ RETRY ERROR: {symbol} - {str(e)}")
    
    print(f"🎯 Retry completed: {len(recovered_stocks)} stocks recovered")
    return recovered_stocks

def get_nse_stock_list():
    try:
        print("🔄 Fetching complete NSE stock list...")
        nse = Nse()
        all_stock_codes = nse.get_stock_codes()
        nse_stocks = [f"{stock}.NS" for stock in all_stock_codes]
        print(f"✅ Successfully fetched {len(nse_stocks)} NSE stocks")
        return nse_stocks
    except Exception as e:
        print(f"❌ Error fetching NSE stock list: {str(e)}")
        print("📋 Falling back to major stocks list...")
        return [
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
            'ICICIBANK.NS', 'KOTAKBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ASIANPAINT.NS',
            'ITC.NS', 'AXISBANK.NS', 'LT.NS', 'DMART.NS', 'SUNPHARMA.NS',
            'TITAN.NS', 'ULTRACEMCO.NS', 'ONGC.NS', 'NESTLEIND.NS', 'BAJFINANCE.NS',
            'M&M.NS', 'WIPRO.NS', 'JSWSTEEL.NS', 'HCLTECH.NS', 'POWERGRID.NS',
            'TATAMOTORS.NS', 'NTPC.NS', 'TECHM.NS', 'HINDALCO.NS', 'COALINDIA.NS'
        ]

def get_stock_info(symbol, retry_count=0):
    try:
        time.sleep(random.uniform(0.2, 0.8))
        stock = yf.Ticker(symbol)
        hist = stock.history(period="5d")
        if hist.empty:
            return None, None, False
        current_price = hist['Close'].iloc[-1]
        in_range = (50 <= current_price <= 1000)
        info = stock.info
        volume = hist['Volume'].iloc[-1] if not hist.empty else 0
        high_52w = hist['High'].rolling(window=min(252, len(hist))).max().iloc[-1]
        low_52w = hist['Low'].rolling(window=min(252, len(hist))).min().iloc[-1]
        price_change = 0
        price_change_pct = 0
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            price_change = current_price - prev_close
            price_change_pct = (price_change / prev_close) * 100
        stock_data = {
            'symbol': symbol,
            'company_name': info.get('longName', symbol.replace('.NS', '')),
            'current_price': current_price,
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'volume': volume,
            'market_cap': info.get('marketCap', 0),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'pe_ratio': info.get('trailingPE', 0),
            'book_value': info.get('bookValue', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'high_52w': high_52w,
            'low_52w': low_52w,
            'beta': info.get('beta', 0),
            'employees': info.get('fullTimeEmployees', 0),
            'currency': info.get('currency', 'INR')
        }
        return stock_data if in_range else None, current_price, in_range
    except Exception as e:
        if "429" in str(e) or "rate limit" in str(e).lower():
            if retry_count < 3:
                wait_time = (2 ** retry_count) + random.uniform(0, 1)
                print(f"⏳ Rate limited for {symbol}, retrying in {wait_time:.1f}s (attempt {retry_count + 1}/3)")
                time.sleep(wait_time)
                return get_stock_info(symbol, retry_count + 1)
            else:
                print(f"❌ Rate limit exceeded for {symbol} after 3 retries")
                return None, None, False
        else:
            print(f"❌ Error processing {symbol}: {str(e)}")
            return None, None, False

def format_number(num):
    if num == 0 or num is None:
        return "N/A"
    if num >= 10000000:
        return f"₹{num/10000000:.1f}Cr"
    elif num >= 100000:
        return f"₹{num/100000:.1f}L"
    else:
        return f"₹{num:.0f}"

def format_volume(vol):
    if vol == 0 or vol is None:
        return "N/A"
    if vol >= 10000000:
        return f"{vol/10000000:.1f}Cr"
    elif vol >= 100000:
        return f"{vol/100000:.1f}L"
    else:
        return f"{vol:.0f}"

def scan_nse_stocks():
    print("=" * 100)
    print("🔍 NSE STOCK PRICE SCANNER (₹50 - ₹1000)")
    print("=" * 100)
    
    # Initialize database
    if not init_database():
        print("⚠️  Database initialization failed, continuing without database storage...")
        scan_id = None
    else:
        # Create scan record immediately
        scan_start_time = datetime.now()
        temp_metadata = {
            'scan_date': scan_start_time,
            'scan_duration_seconds': 0,
            'total_stocks_scanned': 0,
            'stocks_in_range': 0,
            'stocks_above_1000': 0,
            'stocks_below_50': 0,
            'errors': 0
        }
        scan_id = save_scan_metadata(temp_metadata)
        print(f"📝 Scan started with ID: {scan_id}")
    
    scan_start_time = datetime.now()
    print(f"⏰ Scan started at: {scan_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    stock_list = get_nse_stock_list()
    print(f"📊 Scanning {len(stock_list)} NSE stocks...\n")

    valid_stocks = []
    failed_stocks = []
    processed_count = in_range_count = high_price_count = low_price_count = error_count = 0
    db_save_count = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_symbol = {executor.submit(get_stock_info, symbol): symbol for symbol in stock_list}
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                stock_data, current_price, in_range = future.result()
                processed_count += 1
                
                if current_price is not None:
                    if in_range:
                        valid_stocks.append(stock_data)
                        in_range_count += 1
                        
                        # Save immediately to database
                        if scan_id and save_stock_immediately(stock_data, scan_id):
                            db_save_count += 1
                            print(f"✅ FOUND & SAVED: {symbol} - ₹{current_price:.2f} (DB: {db_save_count})")
                        else:
                            print(f"✅ FOUND: {symbol} - ₹{current_price:.2f} (DB SAVE FAILED)")
                            
                    elif current_price > 1000:
                        high_price_count += 1
                        print(f"📈 HIGH: {symbol} - ₹{current_price:.2f} (Above ₹1000)")
                    else:
                        low_price_count += 1
                        print(f"📉 LOW:  {symbol} - ₹{current_price:.2f} (Below ₹50)")
                else:
                    error_count += 1
                    failed_stocks.append(symbol)
                    print(f"❌ ERROR: {symbol} (Added to retry list)")
                    
                if processed_count % 20 == 0:
                    print(f"📊 Progress: {processed_count}/{len(stock_list)} | Found: {in_range_count} | DB Saved: {db_save_count} | High: {high_price_count} | Low: {low_price_count} | Errors: {error_count}")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ Error with {symbol}: {str(e)}")
                processed_count += 1
                error_count += 1
                failed_stocks.append(symbol)

    # Retry failed stocks
    if scan_id:
        recovered_stocks = retry_failed_stocks(failed_stocks, scan_id)
        valid_stocks.extend(recovered_stocks)
        in_range_count += len(recovered_stocks)

    scan_end_time = datetime.now()
    scan_duration = scan_end_time - scan_start_time
    
    print("\n🎯 Scan completed.")
    print(f"✅ In-range: {in_range_count}, 💾 DB Saved: {db_save_count}, 📈 Above ₹1000: {high_price_count}, 📉 Below ₹50: {low_price_count}, ❌ Errors: {len(failed_stocks)}")
    print(f"⏰ Finished at: {scan_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Duration: {scan_duration.total_seconds():.1f} seconds")
    
    # Update final scan metadata
    if scan_id:
        final_metadata = {
            'scan_date': scan_start_time,
            'scan_duration_seconds': scan_duration.total_seconds(),
            'total_stocks_scanned': len(stock_list),
            'stocks_in_range': in_range_count,
            'stocks_above_1000': high_price_count,
            'stocks_below_50': low_price_count,
            'errors': len(failed_stocks)
        }
        
        # Update the scan record with final stats
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE scans SET 
                scan_duration_seconds = ?,
                total_stocks_scanned = ?,
                stocks_in_range = ?,
                stocks_above_1000 = ?,
                stocks_below_50 = ?,
                errors = ?
                WHERE id = ?
            ''', (
                final_metadata['scan_duration_seconds'],
                final_metadata['total_stocks_scanned'],
                final_metadata['stocks_in_range'],
                final_metadata['stocks_above_1000'],
                final_metadata['stocks_below_50'],
                final_metadata['errors'],
                scan_id
            ))
            conn.commit()
            conn.close()
            print(f"📝 Scan metadata updated (ID: {scan_id})")
        except Exception as e:
            print(f"❌ Error updating scan metadata: {str(e)}")
    
    # Display summary
    if valid_stocks:
        print(f"\n📋 Found {len(valid_stocks)} stocks in price range (₹50 - ₹1000):")
        print("-" * 80)
        for stock in valid_stocks[:10]:  # Show first 10 stocks
            print(f"  {stock['symbol']:<15} | {stock['company_name']:<30} | ₹{stock['current_price']:.2f}")
        if len(valid_stocks) > 10:
            print(f"  ... and {len(valid_stocks) - 10} more stocks")
    else:
        print("\n📝 No stocks found in the specified price range")
    
    print("=" * 100)

if __name__ == "__main__":
    scan_nse_stocks()
