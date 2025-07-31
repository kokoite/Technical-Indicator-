"""
Sandbox Database Manager - Handles all database operations for the sandbox analyzer
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple


class SandboxDatabase:
    """Manages all database operations for the sandbox analyzer"""
    
    def __init__(self, db_path: str = "sandbox_recommendations.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize sandbox database with all required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main recommendations table (same structure as main system)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sandbox_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                company_name TEXT,
                analysis_date TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                friday_price REAL NOT NULL,
                current_price REAL,
                target_price REAL,
                stop_loss REAL,
                sector TEXT,
                market_cap INTEGER,
                reason TEXT,
                trend_score REAL,
                momentum_score REAL,
                rsi_score REAL,
                volume_score REAL,
                price_action_score REAL,
                recommendation_tier TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE',
                is_sold INTEGER DEFAULT 0,
                sell_date TEXT,
                sell_price REAL,
                sell_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Performance tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sandbox_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_id INTEGER,
                current_price REAL,
                return_pct REAL,
                days_held INTEGER,
                last_updated TEXT,
                FOREIGN KEY (recommendation_id) REFERENCES sandbox_recommendations (id)
            )
        ''')
        
        # Analysis metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sandbox_analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                threshold_used REAL,
                total_stocks_analyzed INTEGER,
                strong_count INTEGER,
                weak_count INTEGER,
                hold_count INTEGER,
                analysis_duration_minutes REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Friday stocks analysis table - stores all stocks' Friday analysis data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS friday_stocks_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                company_name TEXT,
                friday_date TEXT NOT NULL,
                friday_price REAL NOT NULL,
                total_score REAL NOT NULL,
                recommendation TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                sector TEXT,
                market_cap INTEGER,
                
                -- Technical indicator scores as of Friday
                trend_score REAL,
                momentum_score REAL,
                rsi_score REAL,
                volume_score REAL,
                price_action_score REAL,
                
                -- Individual indicator values as of Friday
                ma_50 REAL,
                ma_200 REAL,
                rsi_value REAL,
                macd_value REAL,
                macd_signal REAL,
                volume_ratio REAL,
                price_change_1d REAL,
                price_change_5d REAL,
                
                -- Breakdown details
                trend_raw REAL,
                momentum_raw REAL,
                rsi_raw REAL,
                volume_raw REAL,
                price_raw REAL,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, friday_date)
            )
        ''')
        
        # Multi-period backtesting table - tracks performance across multiple periods
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                entry_price REAL NOT NULL,
                entry_score REAL NOT NULL,
                threshold_used REAL NOT NULL,
                sector TEXT,
                
                -- Position status
                is_active INTEGER DEFAULT 1,
                sell_date TEXT,
                sell_price REAL,
                sell_score REAL,
                sell_reason TEXT,
                
                -- P&L tracking
                total_pnl REAL DEFAULT 0,
                total_return_pct REAL DEFAULT 0,
                days_held INTEGER DEFAULT 0,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(backtest_id, symbol)
            )
        ''')
        
        # Performance tracking across periods
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                period_date TEXT NOT NULL,
                period_name TEXT NOT NULL,
                price REAL NOT NULL,
                score REAL,
                return_pct REAL,
                is_sold INTEGER DEFAULT 0,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (backtest_id, symbol) REFERENCES backtest_positions (backtest_id, symbol)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Sandbox database initialized")
    
    def clear_sandbox_data(self):
        """Clear previous sandbox data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM sandbox_recommendations")
        cursor.execute("DELETE FROM sandbox_performance")
        
        conn.commit()
        conn.close()
        print("🧹 Cleared previous sandbox data")
    
    def save_sandbox_results(self, results: List[Dict], threshold: float, start_time: datetime):
        """Save analysis results to sandbox database"""
        if not results:
            print("📝 No results to save")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        strong_count = weak_count = hold_count = 0
        
        for result in results:
            tier = result['recommendation_tier']
            stock_info = result['stock_info']
            
            # Count by tier
            if tier == 'STRONG':
                strong_count += 1
            elif tier == 'WEAK':
                weak_count += 1
            else:
                hold_count += 1
            
            # Get Friday price from stock_info
            friday_price = stock_info.get('friday_price', stock_info.get('current_price', 0))
            
            # Calculate target and stop loss
            target_price, stop_loss = self._calculate_levels(
                friday_price, 
                result['recommendation'], 
                result['total_score']
            )
            
            # Create reason summary
            reason = self._create_reason_summary(result['breakdown'], result['total_score'])
            
            # Insert recommendation
            cursor.execute('''
                INSERT INTO sandbox_recommendations 
                (symbol, company_name, analysis_date, recommendation, score, risk_level,
                 friday_price, current_price, target_price, stop_loss, sector, market_cap, reason,
                 trend_score, momentum_score, rsi_score, volume_score, price_action_score,
                 recommendation_tier, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['symbol'],
                stock_info['company_name'],
                datetime.now().strftime('%Y-%m-%d'),
                result['recommendation'],
                result['total_score'],
                result['risk_level'],
                friday_price,
                friday_price,
                target_price,
                stop_loss,
                stock_info['sector'],
                stock_info.get('market_cap', 0),
                reason,
                result['breakdown']['trend']['weighted'],
                result['breakdown']['momentum']['weighted'],
                result['breakdown']['rsi']['weighted'],
                result['breakdown']['volume']['weighted'],
                result['breakdown']['price']['weighted'],
                tier,
                'ACTIVE'
            ))
        
        # Save analysis run metadata
        duration_minutes = (datetime.now() - start_time).total_seconds() / 60
        cursor.execute('''
            INSERT INTO sandbox_analysis_runs 
            (run_date, threshold_used, total_stocks_analyzed, strong_count, weak_count, hold_count, analysis_duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            threshold,
            len(results),
            strong_count,
            weak_count,
            hold_count,
            duration_minutes
        ))
        
        conn.commit()
        conn.close()
        
        print(f"💾 Saved {len(results)} recommendations to sandbox database")
    
    def save_friday_to_today_results(self, results: List[Dict], threshold: float, start_time: datetime):
        """Save Friday-to-today analysis results to sandbox database"""
        if not results:
            print("📝 No results to save")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        strong_count = weak_count = hold_count = 0
        
        for result in results:
            current_tier = result['current_tier']
            
            # Count by current tier
            if current_tier == 'STRONG':
                strong_count += 1
            elif current_tier == 'WEAK':
                weak_count += 1
            else:
                hold_count += 1
            
            # Calculate target and stop loss based on current price
            target_price, stop_loss = self._calculate_levels(
                result['current_price'], 
                result['current_recommendation'], 
                result['current_score']
            )
            
            # Create reason summary for current analysis
            reason = self._create_reason_summary(result['current_analysis']['breakdown'], result['current_score'])
            
            # Insert recommendation with both Friday and current data
            cursor.execute('''
                INSERT INTO sandbox_recommendations 
                (symbol, company_name, analysis_date, recommendation, score, risk_level,
                 friday_price, current_price, target_price, stop_loss, sector, market_cap, reason,
                 trend_score, momentum_score, rsi_score, volume_score, price_action_score,
                 recommendation_tier, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['symbol'],
                result['company_name'],
                datetime.now().strftime('%Y-%m-%d'),
                result['current_recommendation'],
                result['current_score'],
                result['current_analysis']['risk_level'],
                result['friday_price'],
                result['current_price'],
                target_price,
                stop_loss,
                result['sector'],
                result.get('market_cap', 0),
                reason,
                result['current_analysis']['breakdown']['trend']['weighted'],
                result['current_analysis']['breakdown']['momentum']['weighted'],
                result['current_analysis']['breakdown']['rsi']['weighted'],
                result['current_analysis']['breakdown']['volume']['weighted'],
                result['current_analysis']['breakdown']['price']['weighted'],
                current_tier,
                'ACTIVE'
            ))
        
        # Save analysis run metadata
        duration_minutes = (datetime.now() - start_time).total_seconds() / 60
        cursor.execute('''
            INSERT INTO sandbox_analysis_runs 
            (run_date, threshold_used, total_stocks_analyzed, strong_count, weak_count, hold_count, analysis_duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            threshold,
            len(results),
            strong_count,
            weak_count,
            hold_count,
            duration_minutes
        ))
        
        conn.commit()
        conn.close()
        
        print(f"💾 Saved {len(results)} Friday-to-today analysis results to sandbox database")
    
    def get_friday_strong_stocks_from_table(self, friday_date_str: str, threshold: float = 67, limit: Optional[int] = None) -> List[Dict]:
        """Get STRONG stocks from friday_stocks_analysis table by threshold"""
        conn = sqlite3.connect(self.db_path)
        
        # Build query
        query = '''
            SELECT symbol, company_name, friday_price, total_score, recommendation, risk_level,
                   sector, market_cap, trend_score, momentum_score, rsi_score, volume_score, price_action_score,
                   ma_50, ma_200, rsi_value, macd_value, macd_signal, volume_ratio, price_change_1d, price_change_5d,
                   trend_raw, momentum_raw, rsi_raw, volume_raw, price_raw
            FROM friday_stocks_analysis 
            WHERE friday_date = ? AND total_score >= ?
            ORDER BY total_score DESC
        '''
        
        params = [friday_date_str, threshold]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        friday_strong_df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if friday_strong_df.empty:
            return []
        
        # Convert to list of dictionaries
        friday_strong_stocks = []
        for _, row in friday_strong_df.iterrows():
            # Reconstruct breakdown structure for compatibility
            breakdown = {
                'trend': {'weighted': row['trend_score'], 'raw': row['trend_raw'], 'details': {'ma_50': row['ma_50'], 'ma_200': row['ma_200']}},
                'momentum': {'weighted': row['momentum_score'], 'raw': row['momentum_raw'], 'details': {'macd': row['macd_value'], 'signal': row['macd_signal']}},
                'rsi': {'weighted': row['rsi_score'], 'raw': row['rsi_raw'], 'details': {'rsi_value': row['rsi_value']}},
                'volume': {'weighted': row['volume_score'], 'raw': row['volume_raw'], 'details': {'volume_ratio': row['volume_ratio']}},
                'price': {'weighted': row['price_action_score'], 'raw': row['price_raw'], 'details': {'change_1d': row['price_change_1d'], 'change_5d': row['price_change_5d']}}
            }
            
            stock_data = {
                'symbol': row['symbol'],
                'friday_score': row['total_score'],
                'friday_price': row['friday_price'],
                'friday_recommendation': row['recommendation'],
                'friday_analysis': {
                    'total_score': row['total_score'],
                    'recommendation': row['recommendation'],
                    'risk_level': row['risk_level'],
                    'breakdown': breakdown
                },
                'company_name': row['company_name'],
                'sector': row['sector'],
                'market_cap': row['market_cap']
            }
            friday_strong_stocks.append(stock_data)
        
        print(f"📋 Retrieved {len(friday_strong_stocks)} STRONG stocks (score >= {threshold}) from Friday analysis table")
        return friday_strong_stocks
    
    def get_strong_recommendations_performance(self) -> Optional[Dict]:
        """Get current performance of STRONG recommendations"""
        conn = sqlite3.connect(self.db_path)
        
        # Get STRONG recommendations
        query = '''
            SELECT id, symbol, company_name, friday_price, sector, score
            FROM sandbox_recommendations 
            WHERE recommendation_tier = 'STRONG' 
            AND status = 'ACTIVE' 
            AND is_sold = 0
            ORDER BY score DESC
        '''
        
        strong_recs = pd.read_sql_query(query, conn)
        conn.close()
        
        if strong_recs.empty:
            return None
        
        return strong_recs.to_dict('records')
    
    def insert_friday_analysis_record(self, record_data: Dict):
        """Insert a single record into friday_stocks_analysis table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO friday_stocks_analysis 
            (symbol, company_name, friday_date, friday_price, total_score, recommendation, risk_level,
             sector, market_cap, trend_score, momentum_score, rsi_score, volume_score, price_action_score,
             ma_50, ma_200, rsi_value, macd_value, macd_signal, volume_ratio, price_change_1d, price_change_5d,
             trend_raw, momentum_raw, rsi_raw, volume_raw, price_raw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record_data['symbol'], record_data['company_name'], record_data['friday_date'],
            record_data['friday_price'], record_data['total_score'], record_data['recommendation'],
            record_data['risk_level'], record_data['sector'], record_data['market_cap'],
            record_data['trend_score'], record_data['momentum_score'], record_data['rsi_score'],
            record_data['volume_score'], record_data['price_action_score'],
            record_data['ma_50'], record_data['ma_200'], record_data['rsi_value'],
            record_data['macd_value'], record_data['macd_signal'], record_data['volume_ratio'],
            record_data['price_change_1d'], record_data['price_change_5d'],
            record_data['trend_raw'], record_data['momentum_raw'], record_data['rsi_raw'],
            record_data['volume_raw'], record_data['price_raw']
        ))
        
        conn.commit()
        conn.close()
    
    def check_friday_analysis_exists(self, friday_date_str: str) -> int:
        """Check if Friday analysis already exists for a date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM friday_stocks_analysis WHERE friday_date = ?", (friday_date_str,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def clear_friday_analysis_data(self, friday_date_str: str):
        """Clear existing Friday analysis data for a specific date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM friday_stocks_analysis WHERE friday_date = ?", (friday_date_str,))
        conn.commit()
        conn.close()
    
    def initialize_backtest_positions(self, backtest_id: str, positions: List[Dict], threshold: float, entry_date_str: str):
        """Initialize positions in backtest_positions table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear any existing positions for this backtest
        cursor.execute('DELETE FROM backtest_positions WHERE backtest_id = ?', (backtest_id,))
        cursor.execute('DELETE FROM backtest_performance WHERE backtest_id = ?', (backtest_id,))
        
        for pos in positions:
            try:
                cursor.execute('''
                    INSERT INTO backtest_positions 
                    (backtest_id, symbol, entry_date, entry_price, entry_score, 
                     threshold_used, sector, is_active, total_pnl, total_return_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, 0)
                ''', (
                    backtest_id,
                    pos['symbol'],
                    entry_date_str,
                    float(pos['entry_price']),
                    float(pos['entry_score']),
                    float(threshold),
                    pos.get('sector', 'UNKNOWN')
                ))
            except Exception as e:
                print(f"⚠️ Error initializing position for {pos.get('symbol', 'UNKNOWN')}: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        print(f"💾 Initialized {len(positions)} positions in backtest {backtest_id} as of {entry_date_str}")
    
    def get_active_backtest_positions(self, backtest_id: str) -> List[Tuple]:
        """Get active positions for a backtest"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, entry_price, entry_score FROM backtest_positions 
            WHERE backtest_id = ? AND is_active = 1
        ''', (backtest_id,))
        
        positions = cursor.fetchall()
        conn.close()
        return positions
    
    def update_backtest_position_sold(self, backtest_id: str, symbol: str, sell_data: Dict):
        """Update a backtest position as sold"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE backtest_positions 
            SET is_active = 0, sell_date = ?, sell_price = ?, sell_score = ?, 
                sell_reason = ?, total_pnl = ?, total_return_pct = ?, days_held = ?
            WHERE backtest_id = ? AND symbol = ?
        ''', (
            sell_data['sell_date'],
            sell_data['sell_price'],
            sell_data['sell_score'],
            sell_data['sell_reason'],
            sell_data['total_pnl'],
            sell_data['total_return_pct'],
            sell_data['days_held'],
            backtest_id,
            symbol
        ))
        
        conn.commit()
        conn.close()
    
    def insert_backtest_performance_record(self, backtest_id: str, symbol: str, performance_data: Dict):
        """Insert a performance record for backtesting"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO backtest_performance 
            (backtest_id, symbol, period_date, period_name, price, score, return_pct, is_sold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            backtest_id,
            symbol,
            performance_data['period_date'],
            performance_data['period_name'],
            performance_data['price'],
            performance_data['score'],
            performance_data['return_pct'],
            performance_data['is_sold']
        ))
        
        conn.commit()
        conn.close()
    
    def get_backtest_data(self, backtest_id: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Get backtest positions and performance data"""
        conn = sqlite3.connect(self.db_path)
        
        # Get all positions
        positions_df = pd.read_sql_query('''
            SELECT * FROM backtest_positions WHERE backtest_id = ?
        ''', conn, params=[backtest_id])
        
        # Get performance data
        performance_df = pd.read_sql_query('''
            SELECT * FROM backtest_performance WHERE backtest_id = ?
            ORDER BY symbol, period_date
        ''', conn, params=[backtest_id])
        
        conn.close()
        return positions_df, performance_df
    
    def get_backtest_entry_date(self, backtest_id: str, symbol: str) -> Optional[str]:
        """Get entry date for a backtest position"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT entry_date FROM backtest_positions 
                WHERE backtest_id = ? AND symbol = ?
            ''', (backtest_id, symbol))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
        except:
            return None
    
    def _calculate_levels(self, current_price: float, recommendation: str, score: float) -> Tuple[Optional[float], Optional[float]]:
        """Calculate target and stop loss levels"""
        if current_price <= 0:
            return None, None
            
        if "BUY" in recommendation:
            if score >= 75:  # Strong Buy
                target_pct = 0.25  # 25% target
                stop_pct = 0.05   # 5% stop loss
            elif score >= 60:  # Buy
                target_pct = 0.20  # 20% target
                stop_pct = 0.06   # 6% stop loss
            else:  # Weak Buy
                target_pct = 0.15  # 15% target
                stop_pct = 0.07   # 7% stop loss
            
            target_price = current_price * (1 + target_pct)
            stop_loss = current_price * (1 - stop_pct)
            
        elif "SELL" in recommendation:
            target_price = current_price * 0.85  # 15% downside target
            stop_loss = current_price * 1.05     # 5% upside stop loss
            
        else:  # HOLD
            target_price = current_price * 1.10  # 10% upside
            stop_loss = current_price * 0.90     # 10% downside
        
        return round(target_price, 2), round(stop_loss, 2)
    
    def _create_reason_summary(self, breakdown: Dict, score: float) -> str:
        """Create reason summary from breakdown"""
        reasons = []
        
        # Top contributing factors
        for category, data in breakdown.items():
            if data['weighted'] > 5:
                reasons.append(f"{category.title()}: +{data['weighted']:.1f}")
            elif data['weighted'] < -3:
                reasons.append(f"{category.title()}: {data['weighted']:.1f}")
        
        if not reasons:
            reasons.append(f"Mixed signals (Score: {score:.1f})")
        
        return "; ".join(reasons[:3])  # Top 3 reasons

    def check_existing_data_difference(self, record_data: Dict) -> bool:
        """
        Check if new data differs from existing data for the same symbol and date.
        Returns True if data is different, False if same or doesn't exist.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT friday_price, total_score, trend_score, momentum_score, rsi_score, 
                       volume_score, price_action_score, ma_50, ma_200, rsi_value
                FROM friday_stocks_analysis 
                WHERE symbol = ? AND friday_date = ?
            ''', (record_data['symbol'], record_data['friday_date']))
            
            existing = cursor.fetchone()
            if not existing:
                return False  # No existing data, so no difference
            
            # Compare key values (allowing small floating point differences)
            tolerance = 0.01
            
            existing_values = {
                'friday_price': existing[0],
                'total_score': existing[1], 
                'trend_score': existing[2],
                'momentum_score': existing[3],
                'rsi_score': existing[4],
                'volume_score': existing[5],
                'price_action_score': existing[6],
                'ma_50': existing[7],
                'ma_200': existing[8],
                'rsi_value': existing[9]
            }
            
            new_values = {
                'friday_price': record_data['friday_price'],
                'total_score': record_data['total_score'],
                'trend_score': record_data['trend_score'], 
                'momentum_score': record_data['momentum_score'],
                'rsi_score': record_data['rsi_score'],
                'volume_score': record_data['volume_score'],
                'price_action_score': record_data['price_action_score'],
                'ma_50': record_data['ma_50'],
                'ma_200': record_data['ma_200'],
                'rsi_value': record_data['rsi_value']
            }
            
            # Check for significant differences
            for key in existing_values:
                old_val = existing_values[key] or 0
                new_val = new_values[key] or 0
                if abs(old_val - new_val) > tolerance:
                    return True
                    
            return False

    def insert_friday_analysis_record_safe(self, record_data: Dict, allow_overwrite: bool = False) -> str:
        """
        Safely insert Friday analysis record with duplicate protection.
        
        Args:
            record_data: The record data to insert
            allow_overwrite: If True, allows overwriting existing data
            
        Returns:
            str: Status message ('inserted', 'skipped', 'overwritten', 'different')
        """
        # Check if data already exists and is different
        is_different = self.check_existing_data_difference(record_data)
        
        if is_different and not allow_overwrite:
            return 'different'  # Signal that data is different
            
        # Check if record already exists (same data)
        existing_count = self.check_record_exists(record_data['symbol'], record_data['friday_date'])
        
        if existing_count > 0 and not is_different and not allow_overwrite:
            return 'skipped'  # Same data already exists
            
        # Insert or replace the record
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO friday_stocks_analysis 
                (symbol, company_name, friday_date, friday_price, total_score, recommendation, risk_level,
                 sector, market_cap, trend_score, momentum_score, rsi_score, volume_score, price_action_score,
                 ma_50, ma_200, rsi_value, macd_value, macd_signal, volume_ratio, price_change_1d, price_change_5d,
                 trend_raw, momentum_raw, rsi_raw, volume_raw, price_raw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record_data['symbol'], record_data['company_name'], record_data['friday_date'],
                record_data['friday_price'], record_data['total_score'], record_data['recommendation'],
                record_data['risk_level'], record_data['sector'], record_data['market_cap'],
                record_data['trend_score'], record_data['momentum_score'], record_data['rsi_score'],
                record_data['volume_score'], record_data['price_action_score'],
                record_data['ma_50'], record_data['ma_200'], record_data['rsi_value'],
                record_data['macd_value'], record_data['macd_signal'], record_data['volume_ratio'],
                record_data['price_change_1d'], record_data['price_change_5d'],
                record_data['trend_raw'], record_data['momentum_raw'], record_data['rsi_raw'],
                record_data['volume_raw'], record_data['price_raw']
            ))
            conn.commit()
            
        return 'overwritten' if existing_count > 0 else 'inserted'

    def check_record_exists(self, symbol: str, friday_date: str) -> int:
        """Check if a record exists for given symbol and date"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM friday_stocks_analysis WHERE symbol = ? AND friday_date = ?", 
                          (symbol, friday_date))
            return cursor.fetchone()[0]
    
    def get_available_friday_dates(self) -> List[Tuple[str, int]]:
        """
        Get all available Friday dates with stock counts from the database
        
        Returns:
            List of tuples: (friday_date, stock_count) ordered by date DESC
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT friday_date, COUNT(*) as stock_count
                FROM friday_stocks_analysis 
                GROUP BY friday_date
                ORDER BY friday_date DESC
            """)
            return cursor.fetchall()
    
    def get_date_range(self) -> Dict[str, str]:
        """Get the available date range from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    MIN(friday_date) as min_date,
                    MAX(friday_date) as max_date
                FROM friday_stocks_analysis
            """)
            result = cursor.fetchone()
            
        if result and result[0]:
            return {
                'min_date': result[0],
                'max_date': result[1]
            }
        else:
            return {'min_date': None, 'max_date': None}
    
    def get_friday_baseline_for_date(self, target_date: str = None) -> pd.DataFrame:
        """Get Friday baseline data relative to target date"""
        if target_date is None:
            # Use latest Friday if no date specified
            query = """
            SELECT 
                symbol,
                friday_date,
                total_score,
                friday_price,
                volume_ratio,
                rsi_value,
                price_change_1d,
                trend_score,
                momentum_score,
                rsi_score,
                volume_score,
                price_action_score,
                sector,
                recommendation
            FROM friday_stocks_analysis 
            WHERE friday_date = (SELECT MAX(friday_date) FROM friday_stocks_analysis)
            ORDER BY symbol
            """
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn)
        else:
            # Check if target_date is a Friday by seeing if it exists in our Friday data
            from datetime import datetime
            target_dt = datetime.strptime(target_date, '%Y-%m-%d')
            is_friday = target_dt.weekday() == 4  # Friday is weekday 4
            
            with sqlite3.connect(self.db_path) as conn:
                # Check if target_date exists in our Friday data
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM friday_stocks_analysis WHERE friday_date = ?", (target_date,))
                target_is_friday_in_db = cursor.fetchone()[0] > 0
                
                if is_friday and target_is_friday_in_db:
                    # Target date IS a Friday with data - get the PREVIOUS Friday for comparison
                    print(f"🗓️  Target date {target_date} is a Friday - using previous Friday as baseline")
                    query = """
                    SELECT 
                        symbol,
                        friday_date,
                        total_score,
                        friday_price,
                        volume_ratio,
                        rsi_value,
                        price_change_1d,
                        trend_score,
                        momentum_score,
                        rsi_score,
                        volume_score,
                        price_action_score,
                        sector,
                        recommendation
                    FROM friday_stocks_analysis 
                    WHERE friday_date = (
                        SELECT MAX(friday_date) 
                        FROM friday_stocks_analysis 
                        WHERE friday_date < ?
                    )
                    ORDER BY symbol
                    """
                    return pd.read_sql_query(query, conn, params=[target_date])
                else:
                    # Target date is NOT a Friday or has no data - get most recent Friday before or on target date
                    query = """
                    SELECT 
                        symbol,
                        friday_date,
                        total_score,
                        friday_price,
                        volume_ratio,
                        rsi_value,
                        price_change_1d,
                        trend_score,
                        momentum_score,
                        rsi_score,
                        volume_score,
                        price_action_score,
                        sector,
                        recommendation
                    FROM friday_stocks_analysis 
                    WHERE friday_date = (
                        SELECT MAX(friday_date) 
                        FROM friday_stocks_analysis 
                        WHERE friday_date <= ?
                    )
                    ORDER BY symbol
                    """
                    return pd.read_sql_query(query, conn, params=[target_date])
    
    def get_next_friday_date(self, target_date: str) -> Optional[str]:
        """Get the next available Friday date after target_date"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT friday_date 
                FROM friday_stocks_analysis 
                WHERE friday_date >= ?
                ORDER BY friday_date ASC
                LIMIT 1
            """, (target_date,))
            result = cursor.fetchone()
            
        return result[0] if result else None
    
    def get_stock_data_for_date(self, symbol: str, friday_date: str) -> Optional[Dict]:
        """Get stock data for a specific Friday date"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    symbol,
                    friday_date,
                    total_score,
                    friday_price,
                    volume_ratio,
                    rsi_value,
                    price_change_1d,
                    trend_score,
                    momentum_score,
                    rsi_score,
                    volume_score,
                    price_action_score,
                    recommendation
                FROM friday_stocks_analysis 
                WHERE symbol = ? AND friday_date = ?
            """, (symbol, friday_date))
            result = cursor.fetchone()
            
        if result:
            return {
                'symbol': result[0],
                'friday_date': result[1],
                'total_score': result[2],
                'friday_price': result[3],
                'volume_ratio': result[4],
                'rsi_value': result[5],
                'price_change_1d': result[6],
                'trend_score': result[7],
                'momentum_score': result[8],
                'rsi_score': result[9],
                'volume_score': result[10],
                'price_action_score': result[11],
                'recommendation': result[12]
            }
        else:
            return None


# Singleton instance for easy access
sandbox_db = SandboxDatabase() 