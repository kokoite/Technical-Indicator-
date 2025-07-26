import numpy
import numpy as np
# Fix for pandas_ta compatibility with newer numpy versions
numpy.NaN = numpy.nan
np.NaN = np.nan
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Enable interactive mode for matplotlib
plt.ion()

# Configure matplotlib for better interactivity
plt.rcParams['figure.figsize'] = [16, 12]
plt.rcParams['toolbar'] = 'toolmanager'

# ========== OPTIMIZED FUNCTIONS THAT USE PRE-FETCHED DATA ==========

def calculate_dma_from_data(data, days):
    """Calculate DMA from pre-fetched data"""
    try:
        if data.empty or len(data) < days:
            return None
            
        # Create a copy to avoid SettingWithCopyWarning
        df = data.copy()
        dma_column_name = f'{days}DMA'
        df.loc[:, dma_column_name] = df['Close'].shift(1).rolling(window=days).mean()
        
        last_dma = df[dma_column_name].dropna().iloc[-1]
        weekly_dma = df[dma_column_name].resample('W-FRI').last().dropna()
        dma_weekly = weekly_dma.tail(26)
        
        if len(dma_weekly) < 2:
            return {
                'current_value': last_dma,
                'weekly_dma_values': [],
                'weekly_positions': [],
                'weekly_dates': [],
                'weekly_data_points': 0,
                'max_6m': last_dma,
                'min_6m': last_dma,
                'avg_6m': last_dma,
                'trend': 'neutral'
            }
        
        weekly_prices = df['Close'].resample('W-FRI').last().dropna().tail(26)
        weekly_positions = []
        for i in range(len(dma_weekly)):
            if i < len(weekly_prices):
                price = weekly_prices.iloc[i]
                dma_val = dma_weekly.iloc[i]
                if price > dma_val:
                    weekly_positions.append('above')
                elif price < dma_val:
                    weekly_positions.append('below')
                else:
                    weekly_positions.append('at')
            else:
                weekly_positions.append('unknown')
        
        trend = 'uptrend' if dma_weekly.iloc[-1] > dma_weekly.iloc[0] else 'downtrend'
        
        return {
            'current_value': last_dma,
            'weekly_dma_values': dma_weekly.tolist(),
            'weekly_positions': weekly_positions,
            'weekly_dates': dma_weekly.index.strftime('%Y-%m-%d').tolist(),
            'weekly_data_points': len(dma_weekly),
            'max_6m': dma_weekly.max(),
            'min_6m': dma_weekly.min(),
            'avg_6m': dma_weekly.mean(),
            'trend': trend
        }
    except Exception:
        return None

def calculate_weekly_macd_from_data(data):
    """Calculate MACD from pre-fetched data"""
    try:
        import pandas_ta as ta
        
        # Resample to weekly data first
        weekly_data = data.resample('W-FRI').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        
        if weekly_data.empty:
            return None
            
        macd_data = ta.macd(close=weekly_data['Close'], fast=12, slow=26, signal=9)
        if macd_data is None or macd_data.empty:
            return None
            
        last_macd = macd_data['MACD_12_26_9'].dropna().iloc[-1]
        last_signal = macd_data['MACDs_12_26_9'].dropna().iloc[-1]
        
        macd_weekly = macd_data['MACD_12_26_9'].dropna().tail(26)
        signal_weekly = macd_data['MACDs_12_26_9'].dropna().tail(26)
        
        weekly_crossovers = []
        if len(macd_weekly) > 1 and len(signal_weekly) > 1:
            for i in range(1, min(len(macd_weekly), len(signal_weekly))):
                try:
                    prev_macd = macd_weekly.iloc[i-1]
                    curr_macd = macd_weekly.iloc[i]
                    prev_signal = signal_weekly.iloc[i-1]
                    curr_signal = signal_weekly.iloc[i]
                    
                    if prev_macd <= prev_signal and curr_macd > curr_signal:
                        weekly_crossovers.append('bullish_crossover')
                    elif prev_macd >= prev_signal and curr_macd < curr_signal:
                        weekly_crossovers.append('bearish_crossover')
                    else:
                        weekly_crossovers.append('no_crossover')
                except (IndexError, KeyError):
                    weekly_crossovers.append('no_crossover')
        
        return {
            'macd_line': last_macd,
            'signal_line': last_signal,
            'weekly_macd_values': macd_weekly.tolist(),
            'weekly_signal_values': signal_weekly.tolist(),
            'weekly_crossovers': weekly_crossovers,
            'weekly_dates': macd_weekly.index.strftime('%Y-%m-%d').tolist(),
            'weekly_data_points': len(macd_weekly)
        }
    except Exception:
        return None

def calculate_weekly_rsi_from_data(data):
    """Calculate RSI from pre-fetched data"""
    try:
        import pandas_ta as ta
        
        # Resample to weekly data
        weekly_data = data.resample('W-FRI').agg({
            'Close': 'last'
        }).dropna()
        
        rsi_series = ta.rsi(close=weekly_data['Close'], length=14)
        if rsi_series is None or rsi_series.empty:
            return None
            
        last_rsi = rsi_series.dropna().iloc[-1]
        rsi_weekly = rsi_series.dropna().tail(26)
        
        weekly_conditions = []
        for rsi_val in rsi_weekly:
            if rsi_val >= 70:
                weekly_conditions.append('overbought')
            elif rsi_val <= 30:
                weekly_conditions.append('oversold')
            elif rsi_val >= 50:
                weekly_conditions.append('bullish')
            else:
                weekly_conditions.append('bearish')
        
        return {
            'current_value': last_rsi,
            'weekly_rsi_values': rsi_weekly.tolist(),
            'weekly_conditions': weekly_conditions,
            'weekly_dates': rsi_weekly.index.strftime('%Y-%m-%d').tolist(),
            'weekly_data_points': len(rsi_weekly),
            'max_6m': rsi_weekly.max(),
            'min_6m': rsi_weekly.min(),
            'avg_6m': rsi_weekly.mean()
        }
    except Exception:
        return None

def calculate_obv_from_data(data):
    """Calculate OBV from pre-fetched data"""
    try:
        df = data[["Close", "Volume"]].copy()
        df["Direction"] = np.sign(df["Close"].diff())
        df["Adj_Vol"] = df["Volume"] * df["Direction"]
        df["OBV"] = df["Adj_Vol"].fillna(0).cumsum()
        df["OBV_MA120"] = df["OBV"].rolling(window=120).mean()
        
        weekly_obv = df["OBV"].resample('W-FRI').last().dropna()
        weekly_obv_ma120 = df["OBV_MA120"].resample('W-FRI').last().dropna()
        
        last_6_months = weekly_obv.tail(26)
        last_6_months_ma120 = weekly_obv_ma120.tail(26)
        
        if len(last_6_months) < 2:
            return None
            
        current_obv = last_6_months.iloc[-1]
        six_months_ago_obv = last_6_months.iloc[0]
        current_obv_ma120 = last_6_months_ma120.iloc[-1] if len(last_6_months_ma120) > 0 else None
        
        trend_change = current_obv - six_months_ago_obv
        trend_percentage = (trend_change / abs(six_months_ago_obv)) * 100 if six_months_ago_obv != 0 else 0
        
        return {
            'current_value': current_obv,
            'trend_change': trend_change,
            'trend_percentage': trend_percentage,
            'weekly_obv_values': last_6_months.tolist(),
            'weekly_dates': last_6_months.index.strftime('%Y-%m-%d').tolist(),
            'weekly_data_points': len(last_6_months),
            'obv_ma120': current_obv_ma120
        }
    except Exception:
        return None

def calculate_vpt_from_data(data):
    """Calculate VPT from pre-fetched data"""
    try:
        df = data[["Close", "Volume"]].copy()
        df["Close_prev"] = df["Close"].shift(1)
        df["VPT"] = (df["Volume"] * ((df["Close"] - df["Close_prev"]) / df["Close_prev"])).cumsum()
        df["VPT_MA120"] = df["VPT"].rolling(window=120).mean()
        
        weekly_vpt = df["VPT"].resample('W-FRI').last().dropna()
        weekly_vpt_ma120 = df["VPT_MA120"].resample('W-FRI').last().dropna()
        
        last_6_months = weekly_vpt.tail(26)
        last_6_months_ma120 = weekly_vpt_ma120.tail(26)
        
        if len(last_6_months) < 2:
            return None
            
        current_vpt = last_6_months.iloc[-1]
        six_months_ago_vpt = last_6_months.iloc[0]
        current_vpt_ma120 = last_6_months_ma120.iloc[-1] if len(last_6_months_ma120) > 0 else None
        
        trend_change = current_vpt - six_months_ago_vpt
        trend_percentage = (trend_change / abs(six_months_ago_vpt)) * 100 if six_months_ago_vpt != 0 else 0
        
        return {
            'current_value': current_vpt,
            'trend_change': trend_change,
            'trend_percentage': trend_percentage,
            'weekly_vpt_values': last_6_months.tolist(),
            'weekly_dates': last_6_months.index.strftime('%Y-%m-%d').tolist(),
            'weekly_data_points': len(last_6_months),
            'vpt_ma120': current_vpt_ma120
        }
    except Exception:
        return None

def calculate_price_change_from_data(data, days):
    """Calculate price change from pre-fetched data"""
    try:
        if data.empty or len(data) < days:
            return None
            
        data_copy = data.copy()
        data_copy['Price_Change'] = data_copy['Close'].pct_change(periods=days) * 100
        last_change = data_copy['Price_Change'].dropna().iloc[-1]
        return last_change
    except Exception:
        return None

def calculate_weekly_prices_from_data(data):
    """Calculate weekly prices from pre-fetched data"""
    try:
        if data.empty:
            return None
        
        # Resample to weekly data
        weekly_data = data.resample('W-FRI').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        # Get last 6 months (approximately 26 weeks)
        weekly_6m = weekly_data.tail(26)
        
        if len(weekly_6m) < 2:
            return None
        
        # Calculate weekly price changes
        weekly_changes = []
        for i in range(len(weekly_6m)):
            if i == 0:
                weekly_changes.append(0.0)
            else:
                prev_close = weekly_6m['Close'].iloc[i-1]
                curr_close = weekly_6m['Close'].iloc[i]
                change_pct = ((curr_close - prev_close) / prev_close) * 100
                weekly_changes.append(change_pct)
        
        return {
            'weekly_closes': weekly_6m['Close'].tolist(),
            'weekly_highs': weekly_6m['High'].tolist(),
            'weekly_lows': weekly_6m['Low'].tolist(),
            'weekly_changes': weekly_changes,
            'weekly_volumes': weekly_6m['Volume'].tolist(),
            'weekly_dates': weekly_6m.index.strftime('%Y-%m-%d').tolist(),
            'current_price': weekly_6m['Close'].iloc[-1],
            'max_6m': weekly_6m['High'].max(),
            'min_6m': weekly_6m['Low'].min(),
            'avg_6m': weekly_6m['Close'].mean(),
            'volatility_6m': np.std(weekly_changes),
            'weekly_data_points': len(weekly_6m)
        }
    except Exception:
        return None

# ========== LEGACY FUNCTIONS (keeping for backward compatibility) ==========

def calculate_weekly_prices(symbol):
    """
    LEGACY: Calculates 6 months of weekly price data with statistics.
    """
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1y")
        return calculate_weekly_prices_from_data(data)
    except Exception:
        return None

def calculate_all_indicators_from_data(data):
    """
    Calculate all technical indicators from provided historical data
    This is for historically accurate backtesting with clipped data
    
    Args:
        data: pandas DataFrame with historical price data (OHLCV)
        
    Returns:
        dict: All calculated indicators or None if insufficient data
    """
    try:
        if data.empty or len(data) < 50:  # Need at least 50 days for basic indicators
            return None
        
        # Calculate all indicators from the provided dataset
        results = {}
        
        # Calculate DMA indicators using the provided data
        try:
            results['50_day_dma'] = calculate_dma_from_data(data, 50)
            results['200_day_dma'] = calculate_dma_from_data(data, 200)
        except Exception as e:
            print(f"DMA calculation failed: {e}")
            return None
        
        # Calculate MACD using the provided data
        try:
            results['weekly_macd'] = calculate_weekly_macd_from_data(data)
        except Exception as e:
            print(f"MACD calculation failed: {e}")
            return None
        
        # Calculate RSI using the provided data
        try:
            results['weekly_rsi'] = calculate_weekly_rsi_from_data(data)
        except Exception as e:
            print(f"RSI calculation failed: {e}")
            return None
        
        # Calculate Volume indicators using the provided data
        try:
            results['obv'] = calculate_obv_from_data(data)
            results['vpt'] = calculate_vpt_from_data(data)
        except Exception as e:
            print(f"Volume analysis failed: {e}")
            return None
        
        # Calculate Price Action indicators using the provided data
        try:
            results['5_day_price_change'] = calculate_price_change_from_data(data, 5)
            results['10_day_price_change'] = calculate_price_change_from_data(data, 10)
            results['6_month_price_change'] = calculate_price_change_from_data(data, 180)
            results['weekly_prices'] = calculate_weekly_prices_from_data(data)
        except Exception as e:
            print(f"Price action analysis failed: {e}")
            return None
        
        return results
        
    except Exception as e:
        print(f"Overall calculation failed: {e}")
        return None

def calculate_all_indicators(symbol):
    """
    Optimized: Fetch data ONCE and calculate all indicators from the same dataset.
    This reduces API calls from 9 per stock to 1 per stock - 9x faster!
    """
    try:
        # SINGLE API CALL - Fetch 2 years of data once
        stock = yf.Ticker(symbol)
        data = stock.history(period="2y")
        
        if data.empty:
            return None
        
        # Use the new function to calculate indicators from data
        return calculate_all_indicators_from_data(data)
        
    except Exception as e:
        return None

def calculate_all_indicators_legacy(symbol):
    """
    Legacy version: Calculate all indicators with individual API calls
    Kept for reference but not recommended for use
    """
    try:
        # SINGLE API CALL - Fetch 2 years of data once
        stock = yf.Ticker(symbol)
        data = stock.history(period="2y")
        
        if data.empty:
            return None
        
        # Now calculate all indicators from this single dataset
        results = {}
        
        # Calculate DMA indicators using the fetched data
        results['50_day_dma'] = calculate_dma_from_data(data, 50)
        results['200_day_dma'] = calculate_dma_from_data(data, 200)
        
        # Calculate MACD using the fetched data
        results['weekly_macd'] = calculate_weekly_macd_from_data(data)
        
        # Calculate RSI using the fetched data
        results['weekly_rsi'] = calculate_weekly_rsi_from_data(data)
        
        # Calculate OBV using the fetched data
        results['obv'] = calculate_obv_from_data(data)
        
        # Calculate VPT using the fetched data
        results['vpt'] = calculate_vpt_from_data(data)
        
        # Calculate Price Changes using the fetched data
        results['5_day_price_change'] = calculate_price_change_from_data(data, 5)
        results['10_day_price_change'] = calculate_price_change_from_data(data, 10)
        results['6_month_price_change'] = calculate_price_change_from_data(data, 180)
        
        # Calculate Weekly Price Data using the fetched data
        results['weekly_prices'] = calculate_weekly_prices_from_data(data)
        
        return results
        
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {str(e)}")
        return None

def create_comprehensive_charts(symbol, results):
    """
    Creates comprehensive charts for all indicators for a given stock.
    """
    # Set up the figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'{symbol} - Technical Analysis Dashboard', fontsize=16, fontweight='bold')
    
    # Convert dates to datetime objects for plotting
    def convert_dates(date_strings):
        return [datetime.strptime(date, '%Y-%m-%d') for date in date_strings]
    
    # Plot 1: Price with Moving Averages
    ax1 = axes[0, 0]
    if results['weekly_prices'] is not None:
        price_data = results['weekly_prices']
        dates = convert_dates(price_data['weekly_dates'])
        
        ax1.plot(dates, price_data['weekly_closes'], 'b-', linewidth=2, label='Close Price')
        ax1.fill_between(dates, price_data['weekly_lows'], price_data['weekly_highs'], 
                        alpha=0.3, color='lightblue', label='Weekly Range')
        
        # Add moving averages if available
        if results['50_day_dma'] is not None and isinstance(results['50_day_dma'], dict):
            dma_50 = results['50_day_dma']
            if len(dma_50['weekly_dates']) > 0:
                dma_dates = convert_dates(dma_50['weekly_dates'])
                ax1.plot(dma_dates, dma_50['weekly_dma_values'], 'orange', linewidth=2, label='50-Day DMA')
        
        if results['200_day_dma'] is not None and isinstance(results['200_day_dma'], dict):
            dma_200 = results['200_day_dma']
            if len(dma_200['weekly_dates']) > 0:
                dma_dates = convert_dates(dma_200['weekly_dates'])
                ax1.plot(dma_dates, dma_200['weekly_dma_values'], 'red', linewidth=2, label='200-Day DMA')
        
        ax1.set_title('Price Chart with Moving Averages')
        ax1.set_ylabel('Price (₹)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 2: RSI
    ax2 = axes[0, 1]
    if results['weekly_rsi'] is not None and isinstance(results['weekly_rsi'], dict):
        rsi_data = results['weekly_rsi']
        dates = convert_dates(rsi_data['weekly_dates'])
        
        ax2.plot(dates, rsi_data['weekly_rsi_values'], 'purple', linewidth=2, label='RSI')
        ax2.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='Overbought (70)')
        ax2.axhline(y=30, color='green', linestyle='--', alpha=0.7, label='Oversold (30)')
        ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.5, label='Neutral (50)')
        
        # Color the background based on RSI levels
        ax2.fill_between(dates, 70, 100, alpha=0.2, color='red', label='Overbought Zone')
        ax2.fill_between(dates, 0, 30, alpha=0.2, color='green', label='Oversold Zone')
        
        ax2.set_title('Weekly RSI')
        ax2.set_ylabel('RSI')
        ax2.set_ylim(0, 100)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 3: Volume Indicators (OBV)
    ax3 = axes[1, 0]
    if results['obv'] is not None:
        obv_data = results['obv']
        dates = convert_dates(obv_data['weekly_dates'])
        
        ax3.plot(dates, obv_data['weekly_values'], 'green', linewidth=2, label='OBV')
        ax3.fill_between(dates, obv_data['weekly_values'], alpha=0.3, color='green')
        
        # Add 120-day moving average if available
        if obv_data['weekly_ma120_values'] and len(obv_data['weekly_ma120_values']) > 0:
            ax3.plot(dates, obv_data['weekly_ma120_values'], 'red', linewidth=2, linestyle='--', label='OBV MA120')
        
        ax3.set_title('On-Balance Volume (OBV) with 120-Day MA')
        ax3.set_ylabel('OBV')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax3.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
        
        # Format y-axis to show values in millions
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
    
    # Plot 4: Volume Price Trend (VPT)
    ax4 = axes[1, 1]
    if results['vpt'] is not None:
        vpt_data = results['vpt']
        dates = convert_dates(vpt_data['weekly_dates'])
        
        ax4.plot(dates, vpt_data['weekly_values'], 'blue', linewidth=2, label='VPT')
        ax4.fill_between(dates, vpt_data['weekly_values'], alpha=0.3, color='blue')
        
        # Add 120-day moving average if available
        if vpt_data['weekly_ma120_values'] and len(vpt_data['weekly_ma120_values']) > 0:
            ax4.plot(dates, vpt_data['weekly_ma120_values'], 'red', linewidth=2, linestyle='--', label='VPT MA120')
        
        ax4.set_title('Volume Price Trend (VPT) with 120-Day MA')
        ax4.set_ylabel('VPT')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax4.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)
        
        # Format y-axis to show values in thousands
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e3:.1f}K'))
    
    plt.tight_layout()
    
    # Enable interactive navigation
    for ax in axes.flat:
        ax.format_coord = lambda x, y: f'Date: {mdates.num2date(x).strftime("%Y-%m-%d")}, Value: {y:.2f}'
    
    # Save the chart
    filename = f'{symbol}_technical_analysis.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Chart saved as: {filename}")
    
    # Show the chart with interactive controls
    print("📊 Interactive Chart Controls:")
    print("   🔍 Zoom: Click and drag to zoom into an area")
    print("   📐 Pan: Right-click and drag to pan")
    print("   🏠 Home: Press 'h' to return to original view")
    print("   ⬅️ Back: Press left arrow to go back")
    print("   ➡️ Forward: Press right arrow to go forward")
    print("   💾 Save: Press 's' to save current view")
    print("   ❌ Close: Close the window or press 'q' to quit")
    
    plt.show(block=False)
    input("Press Enter to continue to next stock or close the chart...")

def create_macd_chart(symbol, results):
    """
    Creates a dedicated MACD chart if MACD data is available.
    """
    if results['weekly_macd'] is not None and 'weekly_macd_values' in results['weekly_macd']:
        macd_data = results['weekly_macd']
        dates = [datetime.strptime(date, '%Y-%m-%d') for date in macd_data['weekly_dates']]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        fig.suptitle(f'{symbol} - MACD Analysis', fontsize=14, fontweight='bold')
        
        # MACD Line and Signal Line
        ax1.plot(dates, macd_data['weekly_macd_values'], 'blue', linewidth=2, label='MACD Line')
        ax1.plot(dates, macd_data['weekly_signal_values'], 'red', linewidth=2, label='Signal Line')
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # Highlight crossovers
        for i, (date, crossover) in enumerate(zip(dates, macd_data['weekly_crossovers'])):
            if crossover == 'bullish_cross':
                ax1.scatter(date, macd_data['weekly_macd_values'][i], color='green', s=100, marker='^', zorder=5)
            elif crossover == 'bearish_cross':
                ax1.scatter(date, macd_data['weekly_macd_values'][i], color='red', s=100, marker='v', zorder=5)
        
        ax1.set_title('MACD Line vs Signal Line')
        ax1.set_ylabel('MACD')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # MACD Histogram
        histogram = [macd - signal for macd, signal in zip(macd_data['weekly_macd_values'], macd_data['weekly_signal_values'])]
        colors = ['green' if h >= 0 else 'red' for h in histogram]
        ax2.bar(dates, histogram, color=colors, alpha=0.7, width=1)
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        ax2.set_title('MACD Histogram')
        ax2.set_ylabel('Histogram')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Enable interactive navigation
        for ax in [ax1, ax2]:
            ax.format_coord = lambda x, y: f'Date: {mdates.num2date(x).strftime("%Y-%m-%d")}, Value: {y:.4f}'
        
        # Save the chart
        filename = f'{symbol}_macd_analysis.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"MACD chart saved as: {filename}")
        
        print("📊 Interactive MACD Chart - Same controls as main chart")
        plt.show(block=False)
        input("Press Enter to continue...")

def print_indicator_results(symbol, results):
    """
    Prints the indicator results in a formatted way with enhanced data.
    """
    print(f"\n{'='*70}")
    print(f"TECHNICAL INDICATORS FOR {symbol}")
    print(f"{'='*70}")
    
    # Moving Averages
    if results['50_day_dma'] is not None and isinstance(results['50_day_dma'], dict):
        dma_50 = results['50_day_dma']
        print(f"50-Day DMA:              {dma_50['current_value']:.2f} (Trend: {dma_50['trend']})")
        print(f"50-Day DMA 6M Range:     {dma_50['min_6m']:.2f} - {dma_50['max_6m']:.2f}")
    elif results['50_day_dma'] is not None:
        print(f"50-Day DMA:              {results['50_day_dma']:.2f}")
    else:
        print("50-Day DMA:              N/A")
    
    if results['200_day_dma'] is not None and isinstance(results['200_day_dma'], dict):
        dma_200 = results['200_day_dma']
        print(f"200-Day DMA:             {dma_200['current_value']:.2f} (Trend: {dma_200['trend']})")
        print(f"200-Day DMA 6M Range:    {dma_200['min_6m']:.2f} - {dma_200['max_6m']:.2f}")
    elif results['200_day_dma'] is not None:
        print(f"200-Day DMA:             {results['200_day_dma']:.2f}")
    else:
        print("200-Day DMA:             N/A")
    
    # Enhanced MACD with Signal Line
    if results['weekly_macd'] is not None:
        macd_data = results['weekly_macd']
        print(f"Weekly MACD Line:        {macd_data['macd_line']:.4f}")
        print(f"Weekly MACD Signal:      {macd_data['signal_line']:.4f}")
        print(f"MACD Crossover:          {macd_data['crossover'].upper()}")
        
        # Show recent MACD crossovers
        print("Recent MACD Signals (Last 8 weeks):")
        recent_macd = macd_data['weekly_macd_values'][-8:]
        recent_signal = macd_data['weekly_signal_values'][-8:]
        recent_crossovers = macd_data['weekly_crossovers'][-8:]
        recent_dates = macd_data['weekly_dates'][-8:]
        
        for date, macd_val, signal_val, crossover in zip(recent_dates, recent_macd, recent_signal, recent_crossovers):
            signal_indicator = ""
            if crossover == 'bullish_cross':
                signal_indicator = " 🟢 BULLISH CROSS"
            elif crossover == 'bearish_cross':
                signal_indicator = " 🔴 BEARISH CROSS"
            print(f"  {date}: MACD={macd_val:.3f}, Signal={signal_val:.3f}{signal_indicator}")
    else:
        print("Weekly MACD:             N/A")
    
    # Enhanced RSI with Weekly Data
    if results['weekly_rsi'] is not None and isinstance(results['weekly_rsi'], dict):
        rsi_data = results['weekly_rsi']
        print(f"Weekly RSI:              {rsi_data['current_value']:.2f}")
        print(f"RSI 6M Range:            {rsi_data['min_6m']:.2f} - {rsi_data['max_6m']:.2f} (Avg: {rsi_data['avg_6m']:.2f})")
        
        # Show recent RSI conditions
        print("Recent RSI Conditions (Last 8 weeks):")
        recent_rsi = rsi_data['weekly_rsi_values'][-8:]
        recent_conditions = rsi_data['weekly_conditions'][-8:]
        recent_dates = rsi_data['weekly_dates'][-8:]
        
        for date, rsi_val, condition in zip(recent_dates, recent_rsi, recent_conditions):
            condition_indicator = ""
            if condition == 'overbought':
                condition_indicator = " 🔴 OVERBOUGHT"
            elif condition == 'oversold':
                condition_indicator = " 🟢 OVERSOLD"
            print(f"  {date}: RSI={rsi_val:.1f} ({condition}){condition_indicator}")
    elif results['weekly_rsi'] is not None:
        print(f"Weekly RSI:              {results['weekly_rsi']:.2f}")
    else:
        print("Weekly RSI:              N/A")
    
    # Enhanced OBV with 6-month trend
    if results['obv'] is not None:
        obv_data = results['obv']
        print(f"On-Balance Volume (OBV): {obv_data['current_value']:,.0f}")
        print(f"OBV 6-Month Trend:       {obv_data['trend']} ({obv_data['trend_percentage']:+.1f}%)")
        print(f"OBV Change (6M):         {obv_data['trend_change']:+,.0f}")
        
        # Show 120-day moving average information
        if obv_data['current_ma120'] is not None:
            print(f"OBV 120-Day MA:          {obv_data['current_ma120']:,.0f}")
            print(f"OBV vs MA120:            {obv_data['ma_position'].upper()} (Signal: {'Bullish' if obv_data['ma_position'] == 'above' else 'Bearish'})")
        
        # Show recent weekly values to identify volume outbursts
        print("OBV Weekly Values (Last 8 weeks):")
        recent_values = obv_data['weekly_values'][-8:]
        recent_dates = obv_data['weekly_dates'][-8:]
        for i, (date, value) in enumerate(zip(recent_dates, recent_values)):
            week_change = ""
            if i > 0:
                change = value - recent_values[i-1]
                week_change = f" ({change:+,.0f})"
            print(f"  {date}: {value:,.0f}{week_change}")
    else:
        print("On-Balance Volume (OBV): N/A")
    
    # Enhanced VPT with 6-month trend
    if results['vpt'] is not None:
        vpt_data = results['vpt']
        print(f"Volume Price Trend (VPT): {vpt_data['current_value']:,.2f}")
        print(f"VPT 6-Month Trend:       {vpt_data['trend']} ({vpt_data['trend_percentage']:+.1f}%)")
        print(f"VPT Change (6M):         {vpt_data['trend_change']:+,.2f}")
        
        # Show 120-day moving average information
        if vpt_data['current_ma120'] is not None:
            print(f"VPT 120-Day MA:          {vpt_data['current_ma120']:,.2f}")
            print(f"VPT vs MA120:            {vpt_data['ma_position'].upper()} (Signal: {'Bullish' if vpt_data['ma_position'] == 'above' else 'Bearish'})")
        
        # Show recent weekly values to identify volume patterns
        print("VPT Weekly Values (Last 8 weeks):")
        recent_values = vpt_data['weekly_values'][-8:]
        recent_dates = vpt_data['weekly_dates'][-8:]
        for i, (date, value) in enumerate(zip(recent_dates, recent_values)):
            week_change = ""
            if i > 0:
                change = value - recent_values[i-1]
                week_change = f" ({change:+,.2f})"
            print(f"  {date}: {value:,.2f}{week_change}")
    else:
        print("Volume Price Trend (VPT): N/A")
    
    # Price Changes and Weekly Price Data
    print(f"5-Day Price Change:      {results['5_day_price_change']:.2f}%" if results['5_day_price_change'] is not None else "5-Day Price Change:      N/A")
    print(f"10-Day Price Change:     {results['10_day_price_change']:.2f}%" if results['10_day_price_change'] is not None else "10-Day Price Change:     N/A")
    print(f"6-Month Price Change:    {results['6_month_price_change']:.2f}%" if results['6_month_price_change'] is not None else "6-Month Price Change:    N/A")
    
    # Weekly Price Analysis
    if results['weekly_prices'] is not None:
        price_data = results['weekly_prices']
        print(f"Current Price:           ₹{price_data['current_price']:.2f}")
        print(f"6M Price Range:          ₹{price_data['min_6m']:.2f} - ₹{price_data['max_6m']:.2f}")
        print(f"6M Average Price:        ₹{price_data['avg_6m']:.2f}")
        print(f"6M Volatility:           {price_data['volatility_6m']:.2f}%")
        
        # Show recent weekly price movements
        print("Weekly Price Movements (Last 8 weeks):")
        recent_closes = price_data['weekly_closes'][-8:]
        recent_changes = price_data['weekly_changes'][-8:]
        recent_volumes = price_data['weekly_volumes'][-8:]
        recent_dates = price_data['weekly_dates'][-8:]
        
        for date, close, change, volume in zip(recent_dates, recent_closes, recent_changes, recent_volumes):
            change_indicator = ""
            if change > 2:
                change_indicator = " 🟢 Strong Up"
            elif change > 0:
                change_indicator = " 🟢 Up"
            elif change < -2:
                change_indicator = " 🔴 Strong Down"
            elif change < 0:
                change_indicator = " 🔴 Down"
            print(f"  {date}: ₹{close:.2f} ({change:+.2f}%) Vol: {volume:,.0f}{change_indicator}")
    else:
        print("Weekly Price Data:       N/A")

def main():
    """
    Main function to calculate and print indicators for TCS, Reliance, and LICI.
    """
    # Stock symbols for NSE (Yahoo Finance format)
    stocks = {
    
        'LICI': 'LICI.NS'
    }
    
    print("Calculating Technical Indicators for TCS, Reliance, and LICI...")
    print("This may take a few moments as we fetch data from Yahoo Finance...")
    
    for stock_name, symbol in stocks.items():
        try:
            print(f"\nFetching data for {stock_name}...")
            results = calculate_all_indicators(symbol)
            print_indicator_results(stock_name, results)
            
            # Generate charts for each stock
            print(f"\nGenerating charts for {stock_name}...")
            create_comprehensive_charts(stock_name, results)
            
            # Create MACD chart if data is available
            if results['weekly_macd'] is not None and 'weekly_macd_values' in results['weekly_macd']:
                create_macd_chart(stock_name, results)
                
        except Exception as e:
            print(f"\nError calculating indicators for {stock_name}: {e}")
    
    print(f"\n{'='*60}")
    print("Calculation completed!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main() 