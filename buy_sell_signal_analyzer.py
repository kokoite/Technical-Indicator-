import yfinance as yf
import numpy as np
from datetime import datetime
from stock_indicator_calculator import calculate_all_indicators, calculate_all_indicators_from_data

class BuySellSignalAnalyzer:
    """
    Comprehensive buy/sell signal analyzer using weighted technical indicators
    """
    
    def __init__(self):
        # Signal weights (total = 100)
        self.weights = {
            'trend_alignment': 25,      # DMA trends and price position
            'momentum': 20,             # MACD signals
            'rsi_condition': 15,        # RSI overbought/oversold
            'volume_confirmation': 25,  # OBV/VPT trends
            'price_action': 15         # Recent price movements
        }
    
    def analyze_trend_signals(self, results):
        """Analyze trend-based signals (DMAs)"""
        score = 0
        signals = []
        
        # 50-day DMA analysis
        if results['50_day_dma'] and isinstance(results['50_day_dma'], dict):
            dma_50 = results['50_day_dma']
            if dma_50['trend'] == 'uptrend':
                score += 8
                signals.append("✅ 50-DMA Uptrend (+8)")
            else:
                score -= 5
                signals.append("❌ 50-DMA Downtrend (-5)")
        
        # 200-day DMA analysis
        if results['200_day_dma'] and isinstance(results['200_day_dma'], dict):
            dma_200 = results['200_day_dma']
            if dma_200['trend'] == 'uptrend':
                score += 7
                signals.append("✅ 200-DMA Uptrend (+7)")
            else:
                score -= 3
                signals.append("❌ 200-DMA Downtrend (-3)")
        
        # Price vs DMA position
        if (results['weekly_prices'] and results['50_day_dma'] and 
            isinstance(results['50_day_dma'], dict)):
            current_price = results['weekly_prices']['current_price']
            dma_50_val = results['50_day_dma']['current_value']
            
            if current_price > dma_50_val:
                score += 5
                signals.append("✅ Price > 50-DMA (+5)")
            else:
                score -= 3
                signals.append("❌ Price < 50-DMA (-3)")
        
        # Golden/Death Cross potential
        if (results['50_day_dma'] and results['200_day_dma'] and 
            isinstance(results['50_day_dma'], dict) and isinstance(results['200_day_dma'], dict)):
            dma_50_val = results['50_day_dma']['current_value']
            dma_200_val = results['200_day_dma']['current_value']
            
            if dma_50_val > dma_200_val:
                score += 5
                signals.append("✅ 50-DMA > 200-DMA (Golden Cross) (+5)")
            else:
                score -= 5
                signals.append("❌ 50-DMA < 200-DMA (Death Cross) (-5)")
        
        return min(max(score, -25), 25), signals
    
    def analyze_momentum_signals(self, results):
        """Analyze momentum signals (MACD)"""
        score = 0
        signals = []
        
        if results['weekly_macd'] and 'weekly_macd_values' in results['weekly_macd']:
            macd_data = results['weekly_macd']
            
            # Check for recent crossovers (last crossover in weekly_crossovers)
            if 'weekly_crossovers' in macd_data and len(macd_data['weekly_crossovers']) > 0:
                recent_crossover = macd_data['weekly_crossovers'][-1]  # Most recent crossover
                
                if recent_crossover == 'bullish_crossover':
                    score += 12
                    signals.append("✅ MACD Bullish Crossover (+12)")
                elif recent_crossover == 'bearish_crossover':
                    score -= 12
                    signals.append("❌ MACD Bearish Crossover (-12)")
            
            # MACD histogram (momentum strength)
            if 'macd_line' in macd_data and 'signal_line' in macd_data:
                macd_line = macd_data['macd_line']
                signal_line = macd_data['signal_line']
                histogram = macd_line - signal_line
                
                if histogram > 5:
                    score += 5
                    signals.append("✅ Strong MACD Momentum (+5)")
                elif histogram > 0:
                    score += 3
                    signals.append("✅ Positive MACD Momentum (+3)")
                elif histogram < -5:
                    score -= 5
                    signals.append("❌ Weak MACD Momentum (-5)")
                else:
                    score -= 3
                    signals.append("❌ Negative MACD Momentum (-3)")
            
            # Recent crossovers trend (last 4 weeks)
            if 'weekly_crossovers' in macd_data and len(macd_data['weekly_crossovers']) >= 4:
                recent_crossovers = macd_data['weekly_crossovers'][-4:]  # Last 4 weeks
                bullish_count = recent_crossovers.count('bullish_crossover')
                bearish_count = recent_crossovers.count('bearish_crossover')
                
                if bullish_count > bearish_count:
                    score += 3
                    signals.append("✅ Recent Bullish MACD Trend (+3)")
                elif bearish_count > bullish_count:
                    score -= 3
                    signals.append("❌ Recent Bearish MACD Trend (-3)")
        
        return min(max(score, -20), 20), signals
    
    def analyze_rsi_signals(self, results):
        """Analyze RSI overbought/oversold conditions"""
        score = 0
        signals = []
        
        if results['weekly_rsi'] and isinstance(results['weekly_rsi'], dict):
            rsi_data = results['weekly_rsi']
            current_rsi = rsi_data['current_value']
            
            # RSI levels
            if 30 <= current_rsi <= 45:
                score += 10
                signals.append("✅ RSI Oversold Recovery (+10)")
            elif 45 < current_rsi <= 65:
                score += 5
                signals.append("✅ RSI Healthy Bullish (+5)")
            elif 65 < current_rsi <= 75:
                score -= 3
                signals.append("⚠️ RSI Getting Overbought (-3)")
            elif current_rsi > 75:
                score -= 8
                signals.append("❌ RSI Severely Overbought (-8)")
            elif current_rsi < 30:
                score += 8
                signals.append("✅ RSI Oversold - Bounce Expected (+8)")
            
            # RSI trend (last 4 weeks)
            recent_rsi = rsi_data['weekly_rsi_values'][-4:]
            if len(recent_rsi) >= 4:
                rsi_trend = (recent_rsi[-1] - recent_rsi[0]) / recent_rsi[0] * 100
                if rsi_trend > 5:
                    score += 2
                    signals.append("✅ RSI Rising Trend (+2)")
                elif rsi_trend < -5:
                    score -= 2
                    signals.append("❌ RSI Falling Trend (-2)")
        
        return min(max(score, -15), 15), signals
    
    def analyze_volume_signals(self, results):
        """Analyze volume confirmation signals (OBV/VPT)"""
        score = 0
        signals = []
        
        # OBV Analysis
        if results['obv'] and isinstance(results['obv'], dict):
            obv_data = results['obv']
            
            # OBV trend based on percentage change
            if 'trend_percentage' in obv_data:
                trend_pct = obv_data['trend_percentage']
                
                if trend_pct > 15:
                    score += 8
                    signals.append("✅ OBV Strong Uptrend (+8)")
                elif trend_pct > 5:
                    score += 5
                    signals.append("✅ OBV Uptrend (+5)")
                elif trend_pct < -15:
                    score -= 8
                    signals.append("❌ OBV Strong Downtrend (-8)")
                elif trend_pct < -5:
                    score -= 5
                    signals.append("❌ OBV Downtrend (-5)")
            
            # OBV vs MA120
            if 'current_value' in obv_data and 'obv_ma120' in obv_data:
                current_obv = obv_data['current_value']
                obv_ma120 = obv_data['obv_ma120']
                
                if obv_ma120 and current_obv > obv_ma120:
                    score += 4
                    signals.append("✅ OBV Above MA120 (+4)")
                elif obv_ma120 and current_obv < obv_ma120:
                    score -= 4
                    signals.append("❌ OBV Below MA120 (-4)")
        
        # VPT Analysis
        if results['vpt'] and isinstance(results['vpt'], dict):
            vpt_data = results['vpt']
            
            # VPT trend based on percentage change
            if 'trend_percentage' in vpt_data:
                trend_pct = vpt_data['trend_percentage']
                
                if trend_pct > 15:
                    score += 8
                    signals.append("✅ VPT Strong Uptrend (+8)")
                elif trend_pct > 5:
                    score += 5
                    signals.append("✅ VPT Uptrend (+5)")
                elif trend_pct < -15:
                    score -= 8
                    signals.append("❌ VPT Strong Downtrend (-8)")
                elif trend_pct < -5:
                    score -= 5
                    signals.append("❌ VPT Downtrend (-5)")
            
            # VPT vs MA120
            if 'current_value' in vpt_data and 'vpt_ma120' in vpt_data:
                current_vpt = vpt_data['current_value']
                vpt_ma120 = vpt_data['vpt_ma120']
                
                if vpt_ma120 and current_vpt > vpt_ma120:
                    score += 5
                    signals.append("✅ VPT Above MA120 (+5)")
                elif vpt_ma120 and current_vpt < vpt_ma120:
                    score -= 5
                    signals.append("❌ VPT Below MA120 (-5)")
        
        return min(max(score, -25), 25), signals
    
    def analyze_price_action_signals(self, results):
        """Analyze recent price action and volatility"""
        score = 0
        signals = []
        
        if results['weekly_prices']:
            price_data = results['weekly_prices']
            
            # Recent price changes
            recent_changes = price_data['weekly_changes'][-4:]  # Last 4 weeks
            avg_change = np.mean(recent_changes)
            
            if avg_change > 2:
                score += 8
                signals.append("✅ Strong Recent Price Momentum (+8)")
            elif avg_change > 0:
                score += 4
                signals.append("✅ Positive Recent Price Trend (+4)")
            elif avg_change < -2:
                score -= 8
                signals.append("❌ Weak Recent Price Performance (-8)")
            elif avg_change < 0:
                score -= 4
                signals.append("❌ Negative Recent Price Trend (-4)")
            
            # Volatility assessment
            volatility = price_data['volatility_6m']
            if volatility < 3:
                score += 3
                signals.append("✅ Low Volatility - Stable (+3)")
            elif volatility > 8:
                score -= 3
                signals.append("❌ High Volatility - Risky (-3)")
            
            # Volume trend (last 4 weeks)
            recent_volumes = price_data['weekly_volumes'][-4:]
            if len(recent_volumes) >= 4:
                volume_trend = (recent_volumes[-1] - recent_volumes[0]) / recent_volumes[0] * 100
                if volume_trend > 20:
                    score += 4
                    signals.append("✅ Increasing Volume (+4)")
                elif volume_trend < -20:
                    score -= 4
                    signals.append("❌ Declining Volume (-4)")
        
        return min(max(score, -15), 15), signals
    
    def calculate_overall_score_silent(self, symbol):
        """Calculate comprehensive buy/sell score for a stock - SILENT VERSION"""
        # Get all technical indicators
        results = calculate_all_indicators(symbol)
        
        if results is None:
            return None
        
        # Analyze each category (silently)
        trend_score, trend_signals = self.analyze_trend_signals(results)
        momentum_score, momentum_signals = self.analyze_momentum_signals(results)
        rsi_score, rsi_signals = self.analyze_rsi_signals(results)
        volume_score, volume_signals = self.analyze_volume_signals(results)
        price_score, price_signals = self.analyze_price_action_signals(results)
        
        # Calculate weighted scores
        weighted_trend = (trend_score / 25) * self.weights['trend_alignment']
        weighted_momentum = (momentum_score / 20) * self.weights['momentum']
        weighted_rsi = (rsi_score / 15) * self.weights['rsi_condition']
        weighted_volume = (volume_score / 25) * self.weights['volume_confirmation']
        weighted_price = (price_score / 15) * self.weights['price_action']
        
        total_score = (weighted_trend + weighted_momentum + weighted_rsi + 
                      weighted_volume + weighted_price)
        
        # Determine recommendation and risk level
        if total_score >= 75:
            recommendation = "🟢 STRONG BUY"
            risk_level = "Low"
        elif total_score >= 60:
            recommendation = "🟢 BUY"
            risk_level = "Low-Medium"
        elif total_score >= 40:
            recommendation = "🟡 WEAK BUY"
            risk_level = "Medium"
        elif total_score >= 20:
            recommendation = "⚪ HOLD"
            risk_level = "Medium-High"
        else:
            recommendation = "🔴 SELL"
            risk_level = "High"
        
        return {
            'total_score': total_score,
            'recommendation': recommendation,
            'risk_level': risk_level,
            'breakdown': {
                'trend': {'raw': trend_score, 'weighted': weighted_trend, 'signals': trend_signals},
                'momentum': {'raw': momentum_score, 'weighted': weighted_momentum, 'signals': momentum_signals},
                'rsi': {'raw': rsi_score, 'weighted': weighted_rsi, 'signals': rsi_signals},
                'volume': {'raw': volume_score, 'weighted': weighted_volume, 'signals': volume_signals},
                'price': {'raw': price_score, 'weighted': weighted_price, 'signals': price_signals}
            }
        }
    
    def calculate_overall_score_with_data(self, symbol, historical_data):
        """
        Calculate comprehensive buy/sell score using provided historical data
        This is for historically accurate backtesting with clipped data
        
        Args:
            symbol: Stock symbol (for reference)
            historical_data: pandas DataFrame with historical price data
            
        Returns:
            dict: Same structure as calculate_overall_score_silent but using historical data
        """
        # Calculate all technical indicators using the provided historical data
        results = calculate_all_indicators_from_data(historical_data)
        
        if results is None:
            return None
        
        # Analyze each category (same logic as original method)
        trend_score, trend_signals = self.analyze_trend_signals(results)
        momentum_score, momentum_signals = self.analyze_momentum_signals(results)
        rsi_score, rsi_signals = self.analyze_rsi_signals(results)
        volume_score, volume_signals = self.analyze_volume_signals(results)
        price_score, price_signals = self.analyze_price_action_signals(results)
        
        # Calculate weighted scores (same weights as original)
        weighted_trend = (trend_score / 25) * self.weights['trend_alignment']
        weighted_momentum = (momentum_score / 20) * self.weights['momentum']
        weighted_rsi = (rsi_score / 15) * self.weights['rsi_condition']
        weighted_volume = (volume_score / 25) * self.weights['volume_confirmation']
        weighted_price = (price_score / 15) * self.weights['price_action']
        
        total_score = (weighted_trend + weighted_momentum + weighted_rsi + 
                      weighted_volume + weighted_price)
        
        # Determine recommendation and risk level (same logic)
        if total_score >= 75:
            recommendation = "🟢 STRONG BUY"
            risk_level = "Low"
        elif total_score >= 60:
            recommendation = "🟢 BUY"
            risk_level = "Low-Medium"
        elif total_score >= 40:
            recommendation = "🟡 WEAK BUY"
            risk_level = "Medium"
        elif total_score >= 20:
            recommendation = "⚪ HOLD"
            risk_level = "Medium-High"
        else:
            recommendation = "🔴 SELL"
            risk_level = "High"
        
        return {
            'total_score': total_score,
            'recommendation': recommendation,
            'risk_level': risk_level,
            'breakdown': {
                'trend': {'raw': trend_score, 'weighted': weighted_trend, 'signals': trend_signals},
                'momentum': {'raw': momentum_score, 'weighted': weighted_momentum, 'signals': momentum_signals},
                'rsi': {'raw': rsi_score, 'weighted': weighted_rsi, 'signals': rsi_signals},
                'volume': {'raw': volume_score, 'weighted': weighted_volume, 'signals': volume_signals},
                'price': {'raw': price_score, 'weighted': weighted_price, 'signals': price_signals}
            }
        }

    def calculate_overall_score_with_indicators(self, symbol, historical_data):
        """
        Calculate comprehensive buy/sell score using provided historical data
        AND return raw indicator values needed for database storage.
        
        This combines the sophisticated analysis with raw indicator extraction
        to avoid redundant calculations in the sandbox system.
        
        Args:
            symbol: Stock symbol (for reference)
            historical_data: pandas DataFrame with historical price data
            
        Returns:
            dict: Analysis results + raw indicators for database
        """
        # Get the main analysis result
        analysis_result = self.calculate_overall_score_with_data(symbol, historical_data)
        
        if not analysis_result:
            return None
        
        # Calculate all technical indicators using the provided historical data
        from stock_indicator_calculator import calculate_all_indicators_from_data
        indicators_data = calculate_all_indicators_from_data(historical_data)
        
        if not indicators_data:
            return None
        
        # Extract raw indicator values for database storage
        latest_data = historical_data.iloc[-1]
        
        # Moving Averages (available from main system)
        ma_50 = indicators_data['50_day_dma']['current_value'] if indicators_data['50_day_dma'] else None
        ma_200 = indicators_data['200_day_dma']['current_value'] if indicators_data['200_day_dma'] else None
        
        # RSI and MACD - calculate manually if weekly versions not available
        rsi = None
        macd_value = None
        macd_signal = None
        
        if indicators_data['weekly_rsi']:
            rsi = indicators_data['weekly_rsi']['current_value']
        else:
            # Calculate daily RSI as fallback
            try:
                delta = historical_data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
            except:
                rsi = None
        
        if indicators_data['weekly_macd']:
            macd_value = indicators_data['weekly_macd']['macd_line']
            macd_signal = indicators_data['weekly_macd']['signal_line']
        else:
            # Calculate daily MACD as fallback
            try:
                exp1 = historical_data['Close'].ewm(span=12, adjust=False).mean()
                exp2 = historical_data['Close'].ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=9, adjust=False).mean()
                macd_value = macd.iloc[-1]
                macd_signal = signal.iloc[-1]
            except:
                macd_value = None
                macd_signal = None
        
        # Volume ratio (simple calculation - not in main system)
        volume_20ma = historical_data['Volume'].rolling(window=20).mean().iloc[-1]
        volume_ratio = (latest_data['Volume'] / volume_20ma) if volume_20ma > 0 else 1.0
        
        # Price changes - use main system data if available
        price_change_1d = 0
        price_change_5d = 0
        
        if indicators_data['weekly_prices'] and 'weekly_changes' in indicators_data['weekly_prices']:
            weekly_changes = indicators_data['weekly_prices']['weekly_changes']
            if len(weekly_changes) >= 1:
                price_change_1d = weekly_changes[-1]  # Most recent week change
        
        # Use direct price change calculations as fallback
        if price_change_1d == 0 and len(historical_data) >= 2:
            price_change_1d = ((latest_data['Close'] / historical_data['Close'].iloc[-2]) - 1) * 100
            
        if len(historical_data) >= 6:
            price_change_5d = ((latest_data['Close'] / historical_data['Close'].iloc[-6]) - 1) * 100
        
        # Use 5-day price change from main system if available
        if indicators_data['5_day_price_change'] is not None:
            price_change_5d = float(indicators_data['5_day_price_change'])
        
        # Combine analysis result with raw indicators
        result = analysis_result.copy()
        result['raw_indicators'] = {
            'ma_50': ma_50,
            'ma_200': ma_200,
            'rsi': rsi,
            'macd': macd_value,
            'macd_signal': macd_signal,
            'volume_ratio': volume_ratio,
            'price_change_1d': price_change_1d,
            'price_change_5d': price_change_5d,
            'friday_price': float(latest_data['Close'])
        }
        
        # Add indicator source info for debugging
        result['indicator_sources'] = {
            'ma_50': 'main_system' if ma_50 else 'none',
            'ma_200': 'main_system' if ma_200 else 'none',
            'rsi': 'main_system' if indicators_data['weekly_rsi'] else 'fallback_daily',
            'macd': 'main_system' if indicators_data['weekly_macd'] else 'fallback_daily',
            'volume_ratio': 'manual_calculation',
            'price_changes': 'main_system_and_fallback'
        }
        
        return result

    def calculate_overall_score(self, symbol):
        """Calculate comprehensive buy/sell score for a stock"""
        print(f"\n{'='*80}")
        print(f"🎯 BUY/SELL SIGNAL ANALYSIS FOR {symbol}")
        print(f"{'='*80}")
        
        # Get all technical indicators
        results = calculate_all_indicators(symbol)
        
        # Analyze each category
        trend_score, trend_signals = self.analyze_trend_signals(results)
        momentum_score, momentum_signals = self.analyze_momentum_signals(results)
        rsi_score, rsi_signals = self.analyze_rsi_signals(results)
        volume_score, volume_signals = self.analyze_volume_signals(results)
        price_score, price_signals = self.analyze_price_action_signals(results)
        
        # Calculate weighted scores
        weighted_trend = (trend_score / 25) * self.weights['trend_alignment']
        weighted_momentum = (momentum_score / 20) * self.weights['momentum']
        weighted_rsi = (rsi_score / 15) * self.weights['rsi_condition']
        weighted_volume = (volume_score / 25) * self.weights['volume_confirmation']
        weighted_price = (price_score / 15) * self.weights['price_action']
        
        total_score = (weighted_trend + weighted_momentum + weighted_rsi + 
                      weighted_volume + weighted_price)
        
        # Display analysis
        print(f"\n📊 SIGNAL BREAKDOWN:")
        print(f"{'='*50}")
        
        print(f"\n🔄 TREND ANALYSIS (Weight: {self.weights['trend_alignment']}%)")
        print(f"   Raw Score: {trend_score}/25 | Weighted: {weighted_trend:.1f}")
        for signal in trend_signals:
            print(f"   {signal}")
        
        print(f"\n⚡ MOMENTUM ANALYSIS (Weight: {self.weights['momentum']}%)")
        print(f"   Raw Score: {momentum_score}/20 | Weighted: {weighted_momentum:.1f}")
        for signal in momentum_signals:
            print(f"   {signal}")
        
        print(f"\n📈 RSI ANALYSIS (Weight: {self.weights['rsi_condition']}%)")
        print(f"   Raw Score: {rsi_score}/15 | Weighted: {weighted_rsi:.1f}")
        for signal in rsi_signals:
            print(f"   {signal}")
        
        print(f"\n📊 VOLUME ANALYSIS (Weight: {self.weights['volume_confirmation']}%)")
        print(f"   Raw Score: {volume_score}/25 | Weighted: {weighted_volume:.1f}")
        for signal in volume_signals:
            print(f"   {signal}")
        
        print(f"\n💹 PRICE ACTION (Weight: {self.weights['price_action']}%)")
        print(f"   Raw Score: {price_score}/15 | Weighted: {weighted_price:.1f}")
        for signal in price_signals:
            print(f"   {signal}")
        
        # Final recommendation
        print(f"\n{'='*50}")
        print(f"🎯 FINAL SCORE: {total_score:.1f}/100")
        
        recommendation, risk_level = self.get_recommendation(total_score)
        print(f"📋 RECOMMENDATION: {recommendation}")
        print(f"⚠️ RISK LEVEL: {risk_level}")
        
        # Add current price context
        if results['weekly_prices']:
            current_price = results['weekly_prices']['current_price']
            print(f"💰 CURRENT PRICE: ₹{current_price:.2f}")
            
            # Support and resistance levels
            price_range = results['weekly_prices']
            support = min(price_range['weekly_lows'][-4:])  # Recent 4-week low
            resistance = max(price_range['weekly_highs'][-4:])  # Recent 4-week high
            print(f"🔻 SUPPORT LEVEL: ₹{support:.2f}")
            print(f"🔺 RESISTANCE LEVEL: ₹{resistance:.2f}")
        
        print(f"{'='*80}")
        
        return {
            'total_score': total_score,
            'recommendation': recommendation,
            'risk_level': risk_level,
            'breakdown': {
                'trend': {'score': trend_score, 'weighted': weighted_trend, 'signals': trend_signals},
                'momentum': {'score': momentum_score, 'weighted': weighted_momentum, 'signals': momentum_signals},
                'rsi': {'score': rsi_score, 'weighted': weighted_rsi, 'signals': rsi_signals},
                'volume': {'score': volume_score, 'weighted': weighted_volume, 'signals': volume_signals},
                'price': {'score': price_score, 'weighted': weighted_price, 'signals': price_signals}
            }
        }
    
    def get_recommendation(self, score):
        """Convert score to buy/sell recommendation"""
        if score >= 75:
            return "🟢 STRONG BUY", "LOW"
        elif score >= 60:
            return "🟢 BUY", "LOW-MEDIUM"
        elif score >= 40:
            return "🟡 WEAK BUY / HOLD", "MEDIUM"
        elif score >= 20:
            return "⚪ HOLD", "MEDIUM"
        elif score >= 0:
            return "🟡 WEAK SELL / HOLD", "MEDIUM"
        elif score >= -20:
            return "🔴 SELL", "MEDIUM-HIGH"
        else:
            return "🔴 STRONG SELL", "HIGH"

def main():
    """Test the analyzer with LICI"""
    analyzer = BuySellSignalAnalyzer()
    
    # Analyze LICI
    result = analyzer.calculate_overall_score('LICI.NS')
    
    print(f"\n🎯 TRADING RECOMMENDATIONS:")
    print(f"{'='*50}")
    
    if result['total_score'] >= 60:
        print(f"📈 ENTRY STRATEGY:")
        print(f"   • Buy on any dip to support levels")
        print(f"   • Position size: 3-5% of portfolio")
        print(f"   • Stop loss: 5-8% below entry")
        print(f"   • Target: 15-25% gains")
    elif result['total_score'] <= 40:
        print(f"📉 EXIT STRATEGY:")
        print(f"   • Consider reducing position")
        print(f"   • Tighten stop losses")
        print(f"   • Wait for better entry points")
    else:
        print(f"⏳ HOLD STRATEGY:")
        print(f"   • Monitor for clearer signals")
        print(f"   • Watch for breakouts/breakdowns")
        print(f"   • Maintain current positions")

if __name__ == "__main__":
    main() 