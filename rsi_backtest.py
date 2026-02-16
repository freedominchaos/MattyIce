#!/usr/bin/env python3
"""
RSI Backtest: Weekly vs Monthly RSI < 35
Compares entry signals at weekly vs monthly RSI thresholds for LEAP-style trades
"""

import yfinance as yf
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configuration
RSI_PERIOD = 14
RSI_THRESHOLD = 35
INITIAL_CASH = 100000

# S&P 500 tickers (sample)
TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JNJ', 'V',
    'PG', 'JPM', 'UNH', 'HD', 'MA', 'DIS', 'PYPL', 'ADBE', 'NFLX', 'INTC',
    'VZ', 'T', 'PFE', 'MRK', 'KO', 'PEP', 'WMT', 'TMO', 'COST', 'NKE',
    'ABBV', 'CVX', 'XOM', 'LLY', 'QCOM', 'AVGO', 'TXN', 'LOW', 'NEE', 'UPS'
]


def calculate_rsi(prices, period=14):
    """Calculate RSI from price series"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


class RSIStrategy(Strategy):
    """RSI-based strategy"""
    rsi_threshold = RSI_THRESHOLD
    hold_days = 21
    rsi_col = 'RSI_Weekly'
    
    def init(self):
        self.rsi = self.I(lambda: getattr(self.data, self.rsi_col))
        self.entry_bar = None
    
    def next(self):
        if len(self.data) < RSI_PERIOD:
            return
        
        rsi = self.rsi[-1]
        
        if pd.isna(rsi):
            return
        
        # Entry
        if not self.position and rsi < self.rsi_threshold:
            self.buy()
            self.entry_bar = len(self.data)
        
        # Exit after hold period
        elif self.position:
            bars_held = len(self.data) - self.entry_bar
            if bars_held >= self.hold_days:
                self.position.close()


def run_backtest_for_ticker(ticker, timeframe, hold_days):
    """Run backtest for a single ticker"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5y")
        
        if hist is None or len(hist) < 200:
            return None
        
        df = hist.copy()
        
        # Calculate RSI
        df['RSI_Daily'] = calculate_rsi(df['Close'], RSI_PERIOD)
        
        # Weekly RSI
        weekly = df['Close'].resample('W').last()
        weekly_rsi = calculate_rsi(weekly, RSI_PERIOD)
        df['RSI_Weekly'] = weekly_rsi.reindex(df.index, method='ffill')
        
        # Monthly RSI
        monthly = df['Close'].resample('ME').last()
        monthly_rsi = calculate_rsi(monthly, RSI_PERIOD)
        df['RSI_Monthly'] = monthly_rsi.reindex(df.index, method='ffill')
        
        df = df.dropna()
        
        if len(df) < 100:
            return None
        
        # Run backtest
        bt = Backtest(
            df,
            RSIStrategy,
            cash=INITIAL_CASH,
            commission=0.001,
            exclusive_orders=True
        )
        
        bt._strategy.rsi_threshold = RSI_THRESHOLD
        bt._strategy.hold_days = hold_days
        bt._strategy.rsi_col = f'RSI_{timeframe.capitalize()}'
        
        stats = bt.run()
        return stats
    except Exception as e:
        return None


def run_all_backtests():
    """Run backtests for all tickers and configurations"""
    print("="*70)
    print("RSI BACKTEST: Weekly vs Monthly RSI < 35")
    print("="*70)
    
    # Test configurations
    configs = [
        ('weekly', 21),
        ('weekly', 42),
        ('weekly', 63),
        ('monthly', 21),
        ('monthly', 42),
        ('monthly', 63),
    ]
    
    all_results = {}
    
    for timeframe, hold_days in configs:
        key = f"{timeframe}_{hold_days}"
        all_results[key] = {
            'timeframe': timeframe,
            'hold_days': hold_days,
            'returns': [],
            'trades': 0,
            'wins': 0
        }
    
    total_tickers = len(TICKERS)
    
    for i, ticker in enumerate(TICKERS):
        print(f"\n[{i+1}/{total_tickers}] {ticker}...", end=" ")
        
        for timeframe, hold_days in configs:
            key = f"{timeframe}_{hold_days}"
            stats = run_backtest_for_ticker(ticker, timeframe, hold_days)
            
            if stats is not None and stats['# Trades'] > 0:
                all_results[key]['returns'].append(stats['Return [%]'])
                all_results[key]['trades'] += stats['# Trades']
                all_results[key]['wins'] += int(stats['# Trades'] * stats['Win Rate [%]'] / 100)
        
        print("OK")
    
    # Calculate summary
    print("\n" + "="*70)
    print("SUMMARY: Weekly vs Monthly RSI < 35")
    print("="*70)
    
    print("\n{:<12} {:>10} {:>10} {:>10} {:>10} {:>10}".format(
        'Config', 'Trades', 'Avg Ret%', 'Win Rate%', 'Max DD%', 'Sharpe'))
    print("-" * 70)
    
    summary = []
    for key, data in all_results.items():
        if data['returns']:
            avg_return = np.mean(data['returns'])
            win_rate = (data['wins'] / data['trades'] * 100) if data['trades'] > 0 else 0
            summary.append({
                'timeframe': data['timeframe'],
                'hold_days': data['hold_days'],
                'trades': data['trades'],
                'avg_return': avg_return,
                'win_rate': win_rate
            })
            print("{:<12} {:>10} {:>10.2f} {:>10.1f}".format(
                f"{data['timeframe']} {data['hold_days']}d",
                data['trades'], avg_return, win_rate))
    
    # Compare weekly vs monthly
    weekly_results = [s for s in summary if s['timeframe'] == 'weekly']
    monthly_results = [s for s in summary if s['timeframe'] == 'monthly']
    
    if weekly_results and monthly_results:
        weekly_avg = np.mean([r['avg_return'] for r in weekly_results])
        monthly_avg = np.mean([r['avg_return'] for r in monthly_results])
        
        print(f"\n📊 AVERAGE ACROSS ALL HOLD PERIODS:")
        print(f"  Weekly RSI < 35:  {weekly_avg:+.2f}%")
        print(f"  Monthly RSI < 35: {monthly_avg:+.2f}%")
        
        if weekly_avg > monthly_avg:
            diff = weekly_avg - monthly_avg
            print(f"\n✅ Weekly RSI < 35 OUTPERFORMS by {diff:.2f}%")
        else:
            diff = monthly_avg - weekly_avg
            print(f"\n✅ Monthly RSI < 35 OUTPERFORMS by {diff:.2f}%")
        
        # Best configuration
        best = max(summary, key=lambda x: x['avg_return'])
        print(f"\n🏆 BEST CONFIGURATION:")
        print(f"  {best['timeframe'].upper()} RSI, {best['hold_days']} day hold")
        print(f"  Avg Return: {best['avg_return']:+.2f}% | Trades: {best['trades']}")


if __name__ == "__main__":
    run_all_backtests()
