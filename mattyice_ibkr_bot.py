#!/usr/bin/env python3
"""
MattyIce Trading Bot - IBKR Integration
=====================================
Option selling bot based on @MarketMovesMatt's strategy
Integrated with Interactive Brokers via their API

NOTE: Requires IBKR TWS or IB Gateway running
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Try importing ib_async (works with Python 3.10+)
# For Python 3.9, use the HTTP client approach below
try:
    import ib_async
    IB_ASYNC_AVAILABLE = True
except ImportError:
    IB_ASYNC_AVAILABLE = False
    print("ib_async not available - using HTTP client approach")

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

# Trading parameters (from MarketMovesMatt)
TICKERS = ['TQQQ', 'SOXL', 'NVDL', 'TSLL', 'TNA', 'QQQ']
MIN_IV = 50  # Minimum IV to sell
DTE_TARGET = 30  # Days to expiration
PROFIT_TARGET = 0.05  # 5% premium
TAKE_PROFIT = 0.50  # Close at 50% profit
POSITION_SIZE = 0.25  # 25% max per position
MAX_POSITIONS = 4
RSI_PERIOD = 14
RSI_ENTRY = 50  # RSI < 50 for red day entries

# IBKR Configuration
IBKR_HOST = os.getenv('IBKR_HOST', '127.0.0.1')
IBKR_PORT = int(os.getenv('IBKR_PORT', 7497))  # Paper trading port
IBKR_CLIENT_ID = int(os.getenv('IBKR_CLIENT_ID', 1))

# Account
INITIAL_CAPITAL = 50000


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def get_stock_data(ticker):
    """Get stock data and indicators"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        
        if hist.empty or len(hist) < 50:
            return None
        
        # Calculate indicators
        hist['RSI'] = calculate_rsi(hist['Close'])
        hist['EMA_9'] = hist['Close'].ewm(span=9, adjust=False).mean()
        hist['EMA_21'] = hist['Close'].ewm(span=21, adjust=False).mean()
        
        # Get latest values
        latest = hist.iloc[-1]
        
        return {
            'price': latest['Close'],
            'rsi': latest['RSI'],
            'ema_9': latest['EMA_9'],
            'ema_21': latest['EMA_21'],
            'trend': 'bullish' if latest['EMA_9'] > latest['EMA_21'] else 'bearish',
            'is_red_day': latest['Close'] < hist['Close'].iloc[-2] if len(hist) > 1 else False
        }
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


def get_options_chain(ticker):
    """Get option chains for a ticker"""
    # This would connect to IBKR to get real-time options data
    # For now, return mock data structure
    return {
        'calls': [],
        'puts': [],
        'expirations': []
    }


# ============================================================================
# IBKR CONNECTION
# ============================================================================

class IBKRClient:
    """Interactive Brokers API Client"""
    
    def __init__(self, host=IBKR_HOST, port=IBKR_PORT, client_id=IBKR_CLIENT_ID):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
        self.account_value = 0
        self.positions = []
        self.orders = []
    
    async def connect(self):
        """Connect to IBKR"""
        if IB_ASYNC_AVAILABLE:
            try:
                self.ib = ib_async.IB()
                await self.ib.connectAsync(self.host, self.port, self.client_id)
                self.connected = True
                print(f"Connected to IBKR at {self.host}:{self.port}")
                return True
            except Exception as e:
                print(f"Failed to connect: {e}")
                return False
        else:
            print("ib_async not available - running in simulation mode")
            return False
    
    async def disconnect(self):
        """Disconnect from IBKR"""
        if self.connected:
            await self.ib.disconnectAsync()
            self.connected = False
    
    async def get_account_value(self):
        """Get account cash value"""
        if not self.connected:
            return INITIAL_CAPITAL
        
        try:
            # Get account summary
            account = await self.ib.accountSummaryAsync()
            for item in account:
                if item.tag == 'NetLiquidation':
                    self.account_value = float(item.value)
                    return self.account_value
        except Exception as e:
            print(f"Error getting account value: {e}")
        
        return INITIAL_CAPITAL
    
    async def get_positions(self):
        """Get current positions"""
        if not self.connected:
            return []
        
        try:
            positions = await self.ib.positionsAsync()
            self.positions = positions
            return positions
        except Exception as e:
            print(f"Error getting positions: {e}")
            return []
    
    async def place_order(self, ticker, quantity, strike, expiry, is_call=True):
        """Place an option order"""
        if not self.connected:
            print(f"[SIMULATION] Would place order: {quantity}x {ticker} ${strike} {'CALL' if is_call else 'PUT'} {expiry}")
            return None
        
        try:
            # Create contract
            contract = ib_async.Option(ticker, expiry, strike, 'C' if is_call else 'P', 'SMART')
            
            # Create order
            order = ib_async.Order(action='SELL', orderType='MOC', totalQuantity=quantity)
            
            # Place order
            trade = await self.ib.placeOrderAsync(contract, order)
            return trade
        except Exception as e:
            print(f"Error placing order: {e}")
            return None
    
    async def cancel_order(self, order_id):
        """Cancel an order"""
        if not self.connected:
            return
        
        try:
            await self.ib.cancelOrderAsync(order_id)
        except Exception as e:
            print(f"Error canceling order: {e}")


# ============================================================================
# TRADING STRATEGY
# ============================================================================

class MattyIceBot:
    """MarketMovesMatt Strategy Bot"""
    
    def __init__(self, client: IBKRClient):
        self.client = client
        self.watchlist = TICKERS
        self.positions = []
        self.cash = INITIAL_CAPITAL
    
    async def scan_opportunities(self):
        """Scan for trading opportunities"""
        opportunities = []
        
        for ticker in self.watchlist:
            data = get_stock_data(ticker)
            
            if not data:
                continue
            
            # Entry conditions (from his rules)
            is_red_day = data['price'] < get_stock_data(ticker + '-previous-close')
            rsi_oversold = data['rsi'] < RSI_ENTRY
            trend_bullish = data['trend'] == 'bullish'
            
            # Skip if we already have a position
            if any(p['ticker'] == ticker for p in self.positions):
                continue
            
            # Check if valid entry
            if is_red_day and rsi_oversold and trend_bullish:
                opportunities.append({
                    'ticker': ticker,
                    'price': data['price'],
                    'rsi': data['rsi'],
                    'trend': data['trend'],
                    'signal': 'SELL_PUT'
                })
        
        return opportunities
    
    async def execute_trade(self, opportunity):
        """Execute a trade based on opportunity"""
        ticker = opportunity['ticker']
        
        # Calculate position size
        account_value = await self.client.get_account_value()
        position_value = account_value * POSITION_SIZE
        
        # Calculate options details
        strike = opportunity['price'] * 0.95  # 5% OTM
        expiry = (datetime.now() + timedelta(days=DTE_TARGET)).strftime('%Y%m%d')
        
        # Estimate premium (would get from IBKR options chain)
        estimated_premium = position_value * PROFIT_TARGET
        
        print(f"\n{'='*60}")
        print(f"EXECUTING TRADE")
        print(f"{'='*60}")
        print(f"Ticker: {ticker}")
        print(f"Strike: ${strike:.2f}")
        print(f"Expiry: {expiry}")
        print(f"Premium: ~${estimated_premium:.2f}")
        
        # Place order (simulation if not connected)
        result = await self.client.place_order(
            ticker=ticker,
            quantity=1,  # 1 contract = 100 shares
            strike=strike,
            expiry=expiry,
            is_call=False  # Selling puts
        )
        
        if result:
            self.positions.append({
                'ticker': ticker,
                'strike': strike,
                'expiry': expiry,
                'entry_price': estimated_premium,
                'entry_date': datetime.now()
            })
        
        return result
    
    async def check_exits(self):
        """Check for take profit / stop loss exits"""
        # This would check current positions and exit if needed
        # For now, placeholder
        pass
    
    async def run(self):
        """Main bot loop"""
        print(f"\n{'='*60}")
        print("MATTYICE TRADING BOT")
        print(f"{'='*60}")
        
        # Connect to IBKR
        await self.client.connect()
        
        try:
            while True:
                # Get account value
                self.cash = await self.client.get_account_value()
                print(f"\nAccount Value: ${self.cash:,.2f}")
                
                # Get current positions
                self.positions = await self.client.get_positions()
                print(f"Open Positions: {len(self.positions)}")
                
                # Check exits
                await self.check_exits()
                
                # Only scan for new opportunities if under max positions
                if len(self.positions) < MAX_POSITIONS:
                    opportunities = await self.scan_opportunities()
                    print(f"Opportunities Found: {len(opportunities)}")
                    
                    for opp in opportunities:
                        print(f"  - {opp['ticker']}: {opp['signal']}")
                
                # Wait before next scan
                print("\nWaiting 1 hour before next scan...")
                await asyncio.sleep(3600)
        
        except KeyboardInterrupt:
            print("\nShutting down...")
        
        finally:
            await self.client.disconnect()


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main entry point"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  MATTYICE TRADING BOT                                       ║
║  Based on @MarketMovesMatt's Option Selling Strategy       ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize client
    client = IBKRClient()
    
    # Run bot
    bot = MattyIceBot(client)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
