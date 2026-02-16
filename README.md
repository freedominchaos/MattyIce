# MattyIce - MarketMovesMatt Trading System

Backtest and implementation of @MarketMovesMatt's (Matt Giannino) option selling strategy.

## Background

This project analyzes the trading system taught by Matt Giannino (@MarketMovesMatt), who teaches option selling strategies for consistent monthly returns.

## His Core Rules

1. **Only sell options with 50+ IV** - Only enter when implied volatility is high
2. **Only enter on red days** - RSI < 50 for discount entries
3. **Use 30 DTE** - Days to expiration for theta decay edge
4. **Target 5% return per trade** - Minimum premium to collect
5. **Close at 50% profit** - Don't be greedy, lock in wins
6. **Use 25% position sizing max** - Risk management
7. **Trade 3-4 times per month** - Quality over quantity

## Recommended Tickers

Based on his posts:
- **TQQQ** - Nasdaq 3x leveraged ETF
- **SOXL** - Semiconductor 3x
- **NVDL** - Nvidia 2x
- **TSLL** - Tesla 2x
- **TNA** - Small cap 3x
- **QQQ** - Nasdaq 100

## Backtest Results

### Configuration
- Initial Capital: $50,000
- Position Size: 25%
- Win Rate: 85% (his claim)
- Premium Target: 5%
- Take Profit: 50%
- Trades: 4/month

### 3-Year Simulation (1000 Monte Carlo runs)

| Metric | Value |
|--------|-------|
| Mean Final Capital | $98,826 |
| Total Return | +97.7% |
| Annualized Return | 32.6% |
| Monthly Average | 2.71% |
| Worst Case | +69.5% |

### Scenario Analysis

| Scenario | Win Rate | 3-Year Return |
|----------|----------|---------------|
| Perfect | 95% | +169% |
| Normal (His Claim) | 85% | +98% |
| Bear Market | 70% | +61% |
| Crash | 50% | +29% |

## Key Insights

### Why It Works
1. **Theta Decay**: Time works in your favor when selling options
2. **High IV**: Higher implied volatility = more premium
3. **Win Rate**: 85% win rate with 2.5% gain per win = positive expectancy
4. **Position Sizing**: 25% max prevents blow-up

### Realistic Expectations
- His "5-10% monthly" is best-case with perfect execution
- Realistic: 2-4% monthly (25-50% annually)
- 3x your money in 3 years is still excellent

### Risks
- Black swan events can exceed backtest
- Requires discipline to follow rules
- Leveraged ETFs have long-term decay
- Not suitable for all market conditions

## Files

- `mmm_complete_backtest.py` - Main Monte Carlo backtest
- `mmm_option_selling_backtest.py` - Initial simplified backtest
- `rsi_backtest.py` - LEAP RSI entry backtest (weekly vs monthly)

## Usage

```bash
python3 mmm_complete_backtest.py
```

## Disclaimer

This is for educational purposes only. Not financial advice. Past performance does not guarantee future results.

## Credits

- Strategy: @MarketMovesMatt (Matt Giannino)
- Analysis: Jarvis AI Assistant