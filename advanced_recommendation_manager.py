import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from enhanced_strategy_screener import EnhancedStrategyScreener
import time

class AdvancedRecommendationManager:
    """
    Advanced tier-based recommendation management system
    Handles STRONG/WEAK/HOLD recommendations with promotion/selling logic
    """
    
    def __init__(self):
        self.db_name = "stock_recommendations.db"
        self.screener = EnhancedStrategyScreener()
    
    def save_tiered_recommendation(self, symbol, analysis_result, stock_info, tier=None):
        """Save recommendation with tier classification"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Determine tier based on score if not explicitly provided
            if tier is None:
                score = analysis_result['total_score']
                if score >= 70:
                    tier = 'STRONG'
                elif score >= 50:
                    tier = 'WEAK'
                else:
                    tier = 'HOLD'
            
            # Get current stock price
            current_price = stock_info.get('current_price', 0)
            if current_price == 0:
                ticker = yf.Ticker(f"{symbol}.NS" if not symbol.endswith('.NS') else symbol)
                hist = ticker.history(period="1d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
            
            # Calculate target and stop loss
            target_price, stop_loss = self.calculate_levels(current_price, analysis_result['recommendation'], analysis_result['total_score'])
            
            # Insert recommendation with tier and duplicate handling
            try:
                cursor.execute('''
                    INSERT INTO recommendations 
                    (symbol, company_name, recommendation_date, recommendation, score, risk_level,
                     entry_price, target_price, stop_loss, sector, market_cap, reason,
                     trend_score, momentum_score, rsi_score, volume_score, price_action_score,
                     recommendation_tier, last_friday_price, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol.replace('.NS', ''),
                    stock_info.get('company_name', symbol),
                    datetime.now().strftime('%Y-%m-%d'),
                    analysis_result['recommendation'],
                    analysis_result['total_score'],
                    analysis_result['risk_level'],
                    current_price,
                    target_price,
                    stop_loss,
                    stock_info.get('sector', 'Unknown'),
                    stock_info.get('market_cap', 0),
                    self.create_reason_summary(analysis_result['breakdown'], analysis_result['total_score']),
                    analysis_result['breakdown']['trend']['weighted'],
                    analysis_result['breakdown']['momentum']['weighted'],
                    analysis_result['breakdown']['rsi']['weighted'],
                    analysis_result['breakdown']['volume']['weighted'],
                    analysis_result['breakdown']['price']['weighted'],
                    tier,
                    current_price,  # Set as Friday price initially
                    'ACTIVE'
                ))
                
                recommendation_id = cursor.lastrowid
                conn.commit()
                
                tier_emoji = "🟢" if tier == "STRONG" else "🟡" if tier == "WEAK" else "⚪"
                print(f"✅ {tier_emoji} {tier} Recommendation saved: {symbol} - {analysis_result['recommendation']} (Score: {analysis_result['total_score']:.1f})")
                
                return recommendation_id
                
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    # Handle duplicate - update if better score
                    clean_symbol = symbol.replace('.NS', '')
                    cursor.execute('''
                        SELECT id, score FROM recommendations 
                        WHERE symbol = ? AND recommendation_tier = ? AND status = 'ACTIVE' AND is_sold = 0
                    ''', (clean_symbol, tier))
                    
                    existing = cursor.fetchone()
                    if existing and analysis_result['total_score'] > existing[1]:
                        # Update with better score
                        cursor.execute('''
                            UPDATE recommendations SET
                            score = ?, recommendation = ?, entry_price = ?, target_price = ?, stop_loss = ?,
                            reason = ?, trend_score = ?, momentum_score = ?, rsi_score = ?, 
                            volume_score = ?, price_action_score = ?, recommendation_date = ?
                            WHERE id = ?
                        ''', (
                            analysis_result['total_score'], analysis_result['recommendation'], 
                            current_price, target_price, stop_loss,
                            self.create_reason_summary(analysis_result['breakdown'], analysis_result['total_score']),
                            analysis_result['breakdown']['trend']['weighted'],
                            analysis_result['breakdown']['momentum']['weighted'],
                            analysis_result['breakdown']['rsi']['weighted'],
                            analysis_result['breakdown']['volume']['weighted'], 
                            analysis_result['breakdown']['price']['weighted'], 
                            datetime.now().strftime('%Y-%m-%d'),
                            existing[0]
                        ))
                        
                        conn.commit()
                        
                        tier_emoji = "🟢" if tier == "STRONG" else "🟡" if tier == "WEAK" else "⚪"
                        print(f"🔄 {tier_emoji} {tier} Updated existing recommendation: {symbol} - (Score: {existing[1]:.1f} → {analysis_result['total_score']:.1f})")
                        
                        return existing[0]
                    else:
                        tier_emoji = "🟢" if tier == "STRONG" else "🟡" if tier == "WEAK" else "⚪"
                        print(f"⚠️ {tier_emoji} {tier} Skipped duplicate: {symbol} - (Score: {analysis_result['total_score']:.1f}) - existing score is better")
                        return None
                else:
                    raise e
            
        except Exception as e:
            print(f"❌ Error saving recommendation for {symbol}: {str(e)}")
            return None
        finally:
            conn.close()
    
    def calculate_levels(self, current_price, recommendation, score):
        """Calculate target and stop loss levels"""
        if "BUY" in recommendation:
            # For buy recommendations
            target_multiplier = 1.15 if score >= 70 else 1.10  # 15% or 10% target
            stop_multiplier = 0.90  # 10% stop loss
            
            target_price = current_price * target_multiplier
            stop_loss = current_price * stop_multiplier
        else:
            # For sell recommendations
            target_multiplier = 0.85 if score >= 70 else 0.90  # 15% or 10% target down
            stop_multiplier = 1.10  # 10% stop loss up
            
            target_price = current_price * target_multiplier
            stop_loss = current_price * stop_multiplier
        
        return target_price, stop_loss
    
    def create_reason_summary(self, breakdown, score):
        """Create a summary of the recommendation reason"""
        reasons = []
        
        # Check strongest signals
        if breakdown['trend']['weighted'] >= 8:
            reasons.append("Strong trend signals")
        if breakdown['momentum']['weighted'] >= 8:
            reasons.append("Positive momentum")
        if breakdown['volume']['weighted'] >= 8:
            reasons.append("Volume confirmation")
        
        if not reasons:
            reasons.append(f"Technical score: {score:.1f}")
        
        return "; ".join(reasons)
    
    def promote_weak_to_strong(self, symbol, new_analysis, current_price=None):
        """Promote a WEAK recommendation to STRONG if criteria met"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Get current price if not provided
            if current_price is None:
                ticker = yf.Ticker(f"{symbol}.NS" if not symbol.endswith('.NS') else symbol)
                hist = ticker.history(period="1d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                else:
                    current_price = 0
            
            # Calculate new target and stop loss based on current price
            target_price, stop_loss = self.calculate_levels(current_price, new_analysis['recommendation'], new_analysis['total_score'])
            
            cursor.execute('''
                UPDATE recommendations 
                SET recommendation_tier = 'STRONG',
                    promotion_date = ?,
                    score = ?,
                    recommendation = ?,
                    entry_price = ?,
                    target_price = ?,
                    stop_loss = ?
                WHERE symbol = ? AND recommendation_tier = 'WEAK' AND status = 'ACTIVE'
            ''', (
                datetime.now().strftime('%Y-%m-%d'),
                new_analysis['total_score'],
                new_analysis['recommendation'],
                current_price,
                target_price,
                stop_loss,
                symbol.replace('.NS', '')
            ))
            
            if cursor.rowcount > 0:
                conn.commit()
                print(f"🚀 PROMOTED: {symbol} from WEAK to STRONG (Score: {new_analysis['total_score']:.1f}, New Entry: ₹{current_price:.2f})")
                return True
            
        except Exception as e:
            print(f"❌ Error promoting {symbol}: {str(e)}")
        finally:
            conn.close()
        
        return False
    
    def sell_strong_recommendation(self, symbol, current_price, reason="Stop loss hit"):
        """Mark a STRONG recommendation as sold"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Get the recommendation details
            cursor.execute('''
                SELECT entry_price FROM recommendations 
                WHERE symbol = ? AND recommendation_tier = 'STRONG' AND status = 'ACTIVE'
            ''', (symbol.replace('.NS', ''),))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            entry_price = result[0]
            
            # Calculate returns
            return_pct = ((current_price - entry_price) / entry_price) * 100
            money_made = current_price - entry_price  # For 1 stock
            
            # Update recommendation as sold
            cursor.execute('''
                UPDATE recommendations 
                SET is_sold = 1,
                    sell_date = ?,
                    sell_price = ?,
                    realized_return_pct = ?,
                    money_made = ?,
                    status = 'SOLD',
                    reason = ?
                WHERE symbol = ? AND recommendation_tier = 'STRONG' AND status = 'ACTIVE'
            ''', (
                datetime.now().strftime('%Y-%m-%d'),
                current_price,
                return_pct,
                money_made,
                reason,
                symbol.replace('.NS', '')
            ))
            
            if cursor.rowcount > 0:
                conn.commit()
                profit_emoji = "💰" if return_pct > 0 else "📉"
                print(f"🔴 SOLD: {symbol} - {return_pct:+.2f}% (₹{money_made:+.2f}) {profit_emoji} - {reason}")
                return True
                
        except Exception as e:
            print(f"❌ Error selling {symbol}: {str(e)}")
        finally:
            conn.close()
        
        return False
    
    def get_recommendations_by_tier(self, tier, days_back=None):
        """Get recommendations by tier - monitors ALL active positions regardless of age"""
        conn = sqlite3.connect(self.db_name)
        
        if days_back is not None:
            # Optional time filter (for specific use cases like display_tier_summary)
            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            query = '''
                SELECT symbol, recommendation, score, entry_price, recommendation_date,
                       sector, last_friday_price, target_price, stop_loss, company_name
                FROM recommendations 
                WHERE recommendation_tier = ? 
                AND recommendation_date >= ?
                AND status = 'ACTIVE'
                AND is_sold = 0
                ORDER BY score DESC
            '''
            df = pd.read_sql_query(query, conn, params=(tier, cutoff_date))
        else:
            # Default: ALL active unrealized positions (regardless of age)
            query = '''
                SELECT symbol, recommendation, score, entry_price, recommendation_date,
                       sector, last_friday_price, target_price, stop_loss, company_name
                FROM recommendations 
                WHERE recommendation_tier = ? 
                AND status = 'ACTIVE'
                AND is_sold = 0
                ORDER BY score DESC
            '''
            df = pd.read_sql_query(query, conn, params=(tier,))
        
        conn.close()
        return df
    
    def get_performance_summary(self):
        """Get comprehensive performance summary with realized vs unrealized"""
        conn = sqlite3.connect(self.db_name)
        
        # Realized returns (sold stocks)
        realized_query = '''
            SELECT COUNT(*) as count, 
                   AVG(realized_return_pct) as avg_return,
                   SUM(money_made) as total_money_made,
                   MIN(realized_return_pct) as worst_return,
                   MAX(realized_return_pct) as best_return
            FROM recommendations 
            WHERE is_sold = 1
        '''
        
        realized_df = pd.read_sql_query(realized_query, conn)
        
        # Unrealized returns (current holdings)
        unrealized_query = '''
            SELECT r.symbol, r.entry_price, r.recommendation_tier, r.sector,
                   pt.current_price, pt.return_pct
            FROM recommendations r
            LEFT JOIN performance_tracking pt ON r.id = pt.recommendation_id
            WHERE r.status = 'ACTIVE' AND r.is_sold = 0
        '''
        
        unrealized_df = pd.read_sql_query(unrealized_query, conn)
        conn.close()
        
        return {
            'realized': realized_df,
            'unrealized': unrealized_df
        }
    
    def display_tier_summary(self):
        """Display summary of all tiers"""
        print(f"\n{'='*80}")
        print(f"📊 ADVANCED RECOMMENDATION SYSTEM SUMMARY")
        print(f"{'='*80}")
        
        for tier in ['STRONG', 'WEAK', 'HOLD']:
            df = self.get_recommendations_by_tier(tier, days_back=7)
            tier_emoji = "🟢" if tier == "STRONG" else "🟡" if tier == "WEAK" else "⚪"
            
            print(f"\n{tier_emoji} {tier} RECOMMENDATIONS: {len(df)} stocks")
            
            if not df.empty:
                avg_score = df['score'].mean()
                print(f"   Average Score: {avg_score:.1f}")
                
                # Show top 3 for each tier
                for i, (_, row) in enumerate(df.head(3).iterrows(), 1):
                    print(f"   {i}. {row['symbol']} - Score: {row['score']:.1f} - {row['recommendation']}")

def main():
    """Test the advanced recommendation manager"""
    manager = AdvancedRecommendationManager()
    
    print("🎯 ADVANCED RECOMMENDATION MANAGER")
    print("=" * 50)
    print("1. Display Tier Summary")
    print("2. Test Promotion Logic")
    print("3. Performance Summary")
    
    choice = input("\nSelect option (1/2/3): ").strip()
    
    if choice == '1':
        manager.display_tier_summary()
    elif choice == '2':
        print("Testing promotion logic...")
        # This would be called by daily_monitor.py
    elif choice == '3':
        performance = manager.get_performance_summary()
        print("\n📊 Performance Summary:")
        print(f"Realized trades: {performance['realized']['count'].iloc[0] if not performance['realized'].empty else 0}")
        print(f"Active positions: {len(performance['unrealized'])}")

if __name__ == "__main__":
    main() 