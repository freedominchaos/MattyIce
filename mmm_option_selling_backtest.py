#!/usr/bin/env python3
"""
MarketMovesMatt Option Selling Strategy Backtest
Based on his 8 rules:
1. Sell options with 50+ IV
2. Enter only on red days (discount entries)
3. Use 30 DTE for time decay edge
4. Target 5% return per trade minimum
5. Close at 50% profit (don't be greedy)
6. Never hold through earnings
7. Use 25% position sizing max
8. Trade 3-4 times per month
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configuration
TICKERS = ['AMZU', 'NVDL', 'SOXL', 'IREN', 'BITX']
INITIAL_CAPITAL = 50000
DTE_TARGET = 30  # Days to expiration
IV_THRESHOLD = 50  # Minimum IV to sell
PROFIT_TARGET = 0.50  # Close at 50% profit
POSITION_SIZE = 0.25  # 25% of capital per trade
MIN_RETURN = 0.02  # Minimum 2% premium to accept


def get_options_chain(ticker):
    """Get options chain for a ticker"""
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options
        
        if not expirations:
            return None, None
        
        # Find closest to 30 DTE
        target_date = datetime.now() + timedelta(days=DTE_TARGET)
        closest_exp = min(expirations, key=lambda x: abs((datetime.strptime(x, '%Y-%m-%d') - target_date).days))
        
        opt = stock.option_chain(closest_exp)
        return opt.calls, opt.puts
    except Exception as e:
        return None, None


def calculate_iv_rank(iv, hist_ivs):
    """Calculate IV rank from historical IVs"""
    if len(hist_ivs) < 30:
        return iv / 100  # Default approximation
    
    iv_low = min(hist_ivs)
    iv_high = max(hist_ivs)
    
    if iv_high == iv_low:
        return 0.5
    
    return (iv - iv_low) / (iv_high - iv_low)


def is_red_day(prices):
    """Check if today is a red day (price down)"""
    if len(prices) < 2:
        return False
    return prices[-1] < prices[-2]


def simulate_option_sell(ticker, days=365):
    """Simulate option selling strategy on a ticker"""
    print(f"\n{'='*60}")
    print(f"Backtesting {ticker} - Option Selling Strategy")
    print(f"{'='*60}")
    
    # Get historical data
    stock = yf.Ticker(ticker)
    hist = stock.history(period=f"{days}d")
    
    if hist is None or len(hist) < 100:
        print(f"Insufficient data for {ticker}")
        return None
    
    # Simulate weekly entries (this is a simplified simulation)
    # In reality, you'd need options data which is harder to get
    
    # For now, we'll simulate based on:
    # - Entry on red days
    # - Collect premium
    # - Exit at 50% profit or expiration
    
    trades = []
    capital = INITIAL_CAPITAL
    position_value = INITIAL_CAPITAL * POSITION_SIZE
    
    # Simulate over the last year with weekly checks
    for i in range(30, len(hist) - DTE_TARGET):
        # Check if red day
        if hist['Close'].iloc[i] >= hist['Close'].iloc[i-1]:
            continue  # Skip green days
        
        # Estimate premium (simplified - in reality would get from options chain)
        # Use a simple model: premium ≈ stock_price * IV * sqrt(DTE/365) * 0.3
        # This is a rough approximation
        estimated_iv = np.random.uniform(0.4, 0.8)  # Simulated IV for leveraged ETFs
        
        premium_pct = estimated_iv * np.sqrt(DTE_TARGET/365) * 0.3
        
        if premium_pct < MIN_RETURN:
            continue
        
        # Calculate premium in dollars
        premium = position_value * premium_pct
        
        # Simulate outcome (simplified - assume 70% win rate for IV selling)
        outcome = np.random.random()
        
        if outcome < 0.70:  # Win - stock stays above strike
            profit = premium
        else:  # Loss - stock below strike
            # Loss = premium - (difference below strike, capped at position value)
            loss = premium - (position_value * 0.05)  # Assume 5% ITM
            profit = -loss
        
        capital += profit
        trades.append({
            'date': hist.index[i],
            'premium': premium,
            'profit': profit,
            'return': profit / position_value
        })
        
        # Update position size for next trade
        position_value = capital * POSITION_SIZE
    
    return {
        'ticker': ticker,
        'trades': len(trades),
        'capital': capital,
        'total_return': (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100,
        'trades_data': trades
    }


def run_backtest():
    """Run full backtest across all tickers"""
    print("="*70)
    print("OPTION SELLING STRATEGY BACKTEST")
    print("Based on @MarketMovesMatt's 8 Rules")
    print("="*70)
    print(f"\nTickers: {TICKERS}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print(f"Position Size: {POSITION_SIZE*100}%")
    print(f"Target DTE: {DTE_TARGET}")
    print(f"IV Threshold: {IV_THRESHOLD}+")
    print(f"Profit Target: {PROFIT_TARGET*100}%")
    
    results = []
    
    for ticker in TICKERS:
        result = simulate_option_sell(ticker, days=365)
        if result:
            results.append(result)
            print(f"\n{ticker}:")
            print(f"  Trades: {result['trades']}")
            print(f"  Final Capital: ${result['capital']:,.2f}")
            print(f"  Return: {result['total_return']:+.2f}%")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if results:
        total_return = sum(r['total_return'] for r in results) / len(results)
        total_trades = sum(r['trades'] for r in results)
        
        print(f"\nAverage Return Across Tickers: {total_return:+.2f}%")
        print(f"Total Trades: {total_trades}")
        
        # Calculate monthly returns
        monthly_return = total_return / 12
        print(f"Monthly Average: {monthly_return:+.2f}%")
        
        # Compare to his target
        print(f"\n📊 vs MarketMovesMatt's Target (5-10% monthly):")
        if monthly_return >= 5:
            print(f"  ✅ ACHIEVED: {monthly_return:.2f}% monthly")
        else:
            print(f"  ❌ BELOW TARGET: {monthly_return:.2f}% vs 5% target")
        
        # Best performing ticker
        best = max(results, key=lambda x: x['total_return'])
        worst = min(results, key=lambda x: x['total_return'])
        
        print(f"\n🏆 Best Performer: {best['ticker']} ({best['total_return']:+.2f}%)")
        print(f"📉 Worst Performer: {worst['ticker']} ({worst['total_return']:+.2f}%)")
    
    return results


def get_live_iv():
    """Get current IV for tickers (simplified)"""
    print("\n" + "="*70)
    print("CURRENT IV ANALYSIS")
    print("="*70)
    
    for ticker in TICKERS:
        try:
            stock = yf.Ticker(ticker)
            # Get options to estimate IV
            if stock.options:
                opt = stock.option_chain(stock.options[0])
                if not opt.puts.empty:
                    # Use the ATM put's implied volatility as proxy
                    atm_puts = opt.puts[opt.puts['strike'] == opt.puts['strike'].astype(float).abs().idxmin()]
                    if not atm_puts.empty:
                        iv = atm_puts.iloc[0].get('impliedVolatility', 0) * 100
                        print(f"{ticker}: IV = {iv:.1f}%")
                    else:
                        print(f"{ticker}: IV data unavailable")
                else:
                    print(f"{ticker}: No options data")
            else:
                print(f"{ticker}: No options available")
        except Exception as e:
            print(f"{ticker}: Error - {e}")


if __name__ == "__main__":
    results = run_backtest()
    get_live_iv()
