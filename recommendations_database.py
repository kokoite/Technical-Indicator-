import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from buy_sell_signal_analyzer import BuySellSignalAnalyzer

class RecommendationsDatabase:
    """
    Database system to track stock recommendations with dates and performance
    """
    
    def __init__(self, db_name="stock_recommendations.db"):
        self.db_name = db_name
        self.analyzer = BuySellSignalAnalyzer()
        self.init_database()
    
    def init_database(self):
        """Initialize the recommendations database with all necessary tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Main recommendations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                company_name TEXT,
                recommendation_date TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                entry_price REAL NOT NULL,
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
                status TEXT DEFAULT 'ACTIVE',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Performance tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recommendation_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_id INTEGER NOT NULL,
                check_date TEXT NOT NULL,
                current_price REAL NOT NULL,
                return_pct REAL NOT NULL,
                days_held INTEGER NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (recommendation_id) REFERENCES recommendations (id)
            )
        ''')
        
        # Summary statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_date TEXT NOT NULL,
                total_recommendations INTEGER,
                buy_recommendations INTEGER,
                sell_recommendations INTEGER,
                hold_recommendations INTEGER,
                avg_score REAL,
                best_performer TEXT,
                worst_performer TEXT,
                overall_success_rate REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Recommendations database initialized successfully")
    
    def save_recommendation(self, symbol, analysis_result, stock_info=None):
        """Save a new recommendation to the database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Extract data from analysis result
        recommendation = analysis_result['recommendation']
        score = analysis_result['total_score']
        risk_level = analysis_result['risk_level']
        breakdown = analysis_result['breakdown']
        
        # Get current stock info if not provided
        if not stock_info:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                stock_info = {
                    'company_name': info.get('longName', symbol.replace('.NS', '')),
                    'sector': info.get('sector', 'Unknown'),
                    'market_cap': info.get('marketCap', 0)
                }
                current_price = ticker.history(period="1d")['Close'].iloc[-1]
            except:
                stock_info = {'company_name': symbol, 'sector': 'Unknown', 'market_cap': 0}
                current_price = 0
        else:
            current_price = stock_info.get('current_price', 0)
        
        # Calculate target and stop loss based on recommendation
        target_price, stop_loss = self.calculate_levels(current_price, recommendation, score)
        
        # Create reason summary
        reason = self.create_reason_summary(breakdown, score)
        
        # Determine tier based on score
        if score >= 70:
            tier = 'STRONG'
        elif score >= 50:
            tier = 'WEAK'
        else:
            tier = 'HOLD'
        
        # Insert recommendation with duplicate handling
        try:
            cursor.execute('''
                INSERT INTO recommendations 
                (symbol, company_name, recommendation_date, recommendation, score, risk_level,
                 entry_price, target_price, stop_loss, sector, market_cap, reason,
                 trend_score, momentum_score, rsi_score, volume_score, price_action_score, recommendation_tier, last_friday_price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol.replace('.NS', ''),
                stock_info['company_name'],
                datetime.now().strftime('%Y-%m-%d'),
                recommendation,
                score,
                risk_level,
                current_price,
                target_price,
                stop_loss,
                stock_info['sector'],
                stock_info.get('market_cap', 0),
                reason,
                breakdown['trend']['weighted'],
                breakdown['momentum']['weighted'],
                breakdown['rsi']['weighted'],
                breakdown['volume']['weighted'],
                breakdown['price']['weighted'],
                tier,
                current_price,  # Set as Friday price initially
                'ACTIVE'
            ))
            
            recommendation_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Recommendation saved: {symbol} - {recommendation} (Score: {score:.1f})")
            return recommendation_id
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                # Duplicate prevention - update existing recommendation if score is better
                clean_symbol = symbol.replace('.NS', '')
                cursor.execute('''
                    SELECT id, score FROM recommendations 
                    WHERE symbol = ? AND recommendation_tier = ? AND status = 'ACTIVE' AND is_sold = 0
                ''', (clean_symbol, tier))
                
                existing = cursor.fetchone()
                if existing and score > existing[1]:
                    # Update with better score
                    cursor.execute('''
                        UPDATE recommendations SET
                        score = ?, recommendation = ?, entry_price = ?, target_price = ?, stop_loss = ?,
                        reason = ?, trend_score = ?, momentum_score = ?, rsi_score = ?, 
                        volume_score = ?, price_action_score = ?, recommendation_date = ?
                        WHERE id = ?
                    ''', (
                        score, recommendation, current_price, target_price, stop_loss,
                        reason, breakdown['trend']['weighted'], breakdown['momentum']['weighted'],
                        breakdown['rsi']['weighted'], breakdown['volume']['weighted'], 
                        breakdown['price']['weighted'], datetime.now().strftime('%Y-%m-%d'),
                        existing[0]
                    ))
                    
                    conn.commit()
                    conn.close()
                    
                    print(f"🔄 Updated existing recommendation: {symbol} - {recommendation} (Score: {existing[1]:.1f} → {score:.1f})")
                    return existing[0]
                else:
                    conn.close()
                    print(f"⚠️ Skipped duplicate: {symbol} - {recommendation} (Score: {score:.1f}) - existing score is better")
                    return None
            else:
                conn.close()
                raise e
    
    def calculate_levels(self, current_price, recommendation, score):
        """Calculate target price and stop loss based on recommendation strength"""
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
    
    def create_reason_summary(self, breakdown, score):
        """Create a concise reason for the recommendation"""
        reasons = []
        
        # Check strongest signals
        for category, data in breakdown.items():
            weighted_score = data['weighted']
            if weighted_score >= 15:
                reasons.append(f"Strong {category.title()}")
            elif weighted_score <= -10:
                reasons.append(f"Weak {category.title()}")
        
        if not reasons:
            if score >= 60:
                reasons.append("Multiple positive signals")
            elif score <= 20:
                reasons.append("Multiple negative signals")
            else:
                reasons.append("Mixed signals")
        
        return "; ".join(reasons[:3])  # Top 3 reasons
    
    def update_performance(self, days_back=30):
        """Update performance for all active recommendations"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Get active recommendations from last N days
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT id, symbol, recommendation_date, recommendation, entry_price, target_price, stop_loss
            FROM recommendations 
            WHERE recommendation_date >= ? AND status = 'ACTIVE'
        ''', (cutoff_date,))
        
        recommendations = cursor.fetchall()
        
        print(f"📊 Updating performance for {len(recommendations)} active recommendations...")
        
        for rec in recommendations:
            rec_id, symbol, rec_date, recommendation, entry_price, target_price, stop_loss = rec
            
            try:
                # Get current price
                ticker = yf.Ticker(f"{symbol}.NS")
                current_data = ticker.history(period="5d")
                if current_data.empty:
                    continue
                    
                current_price = current_data['Close'].iloc[-1]
                
                # Calculate performance
                return_pct = ((current_price - entry_price) / entry_price) * 100
                
                # Calculate days held
                rec_datetime = datetime.strptime(rec_date, '%Y-%m-%d')
                days_held = (datetime.now() - rec_datetime).days
                
                # Determine status
                status = self.determine_status(current_price, entry_price, target_price, stop_loss, recommendation)
                
                # Insert performance record
                cursor.execute('''
                    INSERT OR REPLACE INTO recommendation_performance
                    (recommendation_id, check_date, current_price, return_pct, days_held, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (rec_id, datetime.now().strftime('%Y-%m-%d'), current_price, return_pct, days_held, status))
                
                # Update recommendation status if target hit or stop loss triggered
                if status in ['TARGET_HIT', 'STOP_LOSS_HIT']:
                    cursor.execute('''
                        UPDATE recommendations SET status = 'CLOSED' WHERE id = ?
                    ''', (rec_id,))
                
            except Exception as e:
                print(f"❌ Error updating {symbol}: {str(e)}")
        
        conn.commit()
        conn.close()
        print("✅ Performance update completed")
    
    def determine_status(self, current_price, entry_price, target_price, stop_loss, recommendation):
        """Determine current status of recommendation"""
        if target_price and stop_loss:
            if "BUY" in recommendation:
                if current_price >= target_price:
                    return "TARGET_HIT"
                elif current_price <= stop_loss:
                    return "STOP_LOSS_HIT"
                else:
                    return "ACTIVE"
            elif "SELL" in recommendation:
                if current_price <= target_price:
                    return "TARGET_HIT"
                elif current_price >= stop_loss:
                    return "STOP_LOSS_HIT"
                else:
                    return "ACTIVE"
        
        return "ACTIVE"
    
    def get_recommendations(self, days_back=None, status='ALL'):
        """Get recommendations from database - ALL active positions by default"""
        conn = sqlite3.connect(self.db_name)
        
        if days_back is not None:
            # Optional time filter for specific use cases
            query = '''
                SELECT r.*, rp.current_price, rp.return_pct, rp.days_held, rp.status as current_status
                FROM recommendations r
                LEFT JOIN recommendation_performance rp ON r.id = rp.recommendation_id
                WHERE r.recommendation_date >= ?
            '''
            
            if status != 'ALL':
                query += f" AND r.status = '{status}'"
                
            query += " ORDER BY r.recommendation_date DESC, r.score DESC"
            
            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            df = pd.read_sql_query(query, conn, params=(cutoff_date,))
        else:
            # Default: ALL recommendations (with optional status filter)
            query = '''
                SELECT r.*, rp.current_price, rp.return_pct, rp.days_held, rp.status as current_status
                FROM recommendations r
                LEFT JOIN recommendation_performance rp ON r.id = rp.recommendation_id
            '''
            
            where_conditions = []
            if status != 'ALL':
                where_conditions.append(f"r.status = '{status}'")
            
            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)
                
            query += " ORDER BY r.recommendation_date DESC, r.score DESC"
            
            df = pd.read_sql_query(query, conn)
        
        conn.close()
        return df
    
    def display_recommendations(self, days_back=None):
        """Display recommendations in a formatted table"""
        df = self.get_recommendations(days_back)
        
        if df.empty:
            print("📝 No recommendations found in the specified period")
            return
        
        print(f"\n{'='*120}")
        print(f"📊 STOCK RECOMMENDATIONS - LAST {days_back} DAYS")
        print(f"{'='*120}")
        
        # Display header
        print(f"{'Date':<12} {'Symbol':<12} {'Company':<25} {'Rec':<15} {'Score':<6} {'Entry':<8} {'Current':<8} {'Return':<8} {'Status':<12}")
        print(f"{'-'*120}")
        
        for _, row in df.iterrows():
            date = row['recommendation_date']
            symbol = row['symbol']
            company = (row['company_name'][:24] + "...") if len(str(row['company_name'])) > 24 else row['company_name']
            rec = row['recommendation'][:14]
            score = f"{row['score']:.1f}"
            entry = f"₹{row['entry_price']:.0f}" if pd.notna(row['entry_price']) else "N/A"
            current = f"₹{row['current_price']:.0f}" if pd.notna(row['current_price']) else "N/A"
            return_pct = f"{row['return_pct']:+.1f}%" if pd.notna(row['return_pct']) else "N/A"
            status = row['current_status'] if pd.notna(row['current_status']) else "PENDING"
            
            print(f"{date:<12} {symbol:<12} {company:<25} {rec:<15} {score:<6} {entry:<8} {current:<8} {return_pct:<8} {status:<12}")
    
    def analyze_performance(self, days_back=30):
        """Analyze overall strategy performance"""
        df = self.get_recommendations(days_back)
        
        if df.empty:
            print("📝 No data available for performance analysis")
            return
        
        # Calculate statistics
        total_recs = len(df)
        buy_recs = len(df[df['recommendation'].str.contains('BUY', na=False)])
        sell_recs = len(df[df['recommendation'].str.contains('SELL', na=False)])
        hold_recs = len(df[df['recommendation'].str.contains('HOLD', na=False)])
        
        # Performance metrics
        valid_returns = df[df['return_pct'].notna()]
        if not valid_returns.empty:
            avg_return = valid_returns['return_pct'].mean()
            best_return = valid_returns['return_pct'].max()
            worst_return = valid_returns['return_pct'].min()
            positive_returns = len(valid_returns[valid_returns['return_pct'] > 0])
            success_rate = (positive_returns / len(valid_returns)) * 100
            
            best_stock = valid_returns.loc[valid_returns['return_pct'].idxmax(), 'symbol']
            worst_stock = valid_returns.loc[valid_returns['return_pct'].idxmin(), 'symbol']
        else:
            avg_return = best_return = worst_return = success_rate = 0
            best_stock = worst_stock = "N/A"
        
        print(f"\n{'='*60}")
        print(f"📈 STRATEGY PERFORMANCE ANALYSIS - LAST {days_back} DAYS")
        print(f"{'='*60}")
        print(f"📊 Total Recommendations: {total_recs}")
        print(f"   • 🟢 Buy: {buy_recs}")
        print(f"   • 🔴 Sell: {sell_recs}")
        print(f"   • ⚪ Hold: {hold_recs}")
        print(f"\n💹 Performance Metrics:")
        print(f"   • Average Return: {avg_return:+.2f}%")
        print(f"   • Best Return: {best_return:+.2f}% ({best_stock})")
        print(f"   • Worst Return: {worst_return:+.2f}% ({worst_stock})")
        print(f"   • Success Rate: {success_rate:.1f}%")
        
        # Save to strategy performance table
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO strategy_performance 
            (analysis_date, total_recommendations, buy_recommendations, sell_recommendations, 
             hold_recommendations, avg_score, best_performer, worst_performer, overall_success_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().strftime('%Y-%m-%d'),
            total_recs, buy_recs, sell_recs, hold_recs,
            df['score'].mean() if not df.empty else 0,
            best_stock, worst_stock, success_rate
        ))
        conn.commit()
        conn.close()

def main():
    """Test the recommendations database system"""
    db = RecommendationsDatabase()
    
    print("🎯 Recommendations Database System Ready!")
    print("📊 Use this system to track all your stock recommendations with dates and performance")

if __name__ == "__main__":
    main() 