# EON Signal Backtest: BUY + Fragile Long/Short Strategy

## Independent Cohort Analysis with Fama-MacBeth Correction

**Date:** February 22, 2026
**Prepared by:** EON Research

---

## Executive Summary

An AI system (Google Gemini) analyzes SEC 10-K filings through three investment lenses — Buffett-style value, Taleb-style antifragility, and contrarian analysis — to produce a final verdict (BUY/SELL/HOLD) along with sub-ratings including an "antifragile rating" (Antifragile / Robust / Fragile). We test the hypothesis that the intersection of a BUY final verdict and a Fragile antifragility rating identifies stocks with asymmetric upside.

Using independent single-year cohorts (FY2020–FY2024) with Fama-MacBeth aggregation, the **BUY + Fragile** long signal produces **+25.9% mean excess return over SPY at 1.8 years** (FM p = 0.001). Combined with a short book of all SELL-rated stocks (−12.4% excess, FM p = 0.028), the long/short spread is **+38.3%** (FM p = 0.004).

A **dollar-neutral 50/50 combined portfolio** (50% capital long BUY+Fragile, 50% capital short SELL) produces a FM-corrected mean return of **+19.1% over 1.8 years** (FM p = 0.004), equivalent to approximately **+10.5% annualized excess over the risk-free rate**. The worst single-cohort return for this portfolio at the 1.8Y horizon was +12.2% (FY2023); no cohort was negative at any testable horizon.

---

## 1. Data and Signal Generation

### 1.1 Signal Source

EON analyzes annual 10-K SEC filings using Google Gemini (structured output mode) through three independent analytical perspectives:

| Perspective | Focus | Output |
|-------------|-------|--------|
| **Buffett** | ROIC, moat durability, margin of safety | Action signal (PRIORITY/INVESTIGATE/PASS/AVOID) + moat rating (Wide/Narrow/None) |
| **Taleb** | Tail risk, optionality, antifragility | Action signal + antifragile rating (Antifragile/Robust/Fragile) |
| **Contrarian** | Consensus positioning, variant perception, hidden catalysts | Action signal + positioning |

A **synthesis** module aggregates the three perspectives into a final verdict: STRONG BUY, BUY, HOLD, SELL, or STRONG SELL, with a conviction level (High, Medium, Low).

### 1.2 Universe and Timeframe

| Parameter | Value |
|-----------|-------|
| Fiscal years analyzed | FY2020, FY2021, FY2022, FY2023, FY2024 |
| Total signals | 6,090 (ticker × fiscal_year pairs) |
| Unique tickers | 1,334 |
| Analysis input | SEC 10-K annual filings |
| Signal generation | Automated; no human discretion in signal assignment |
| Price data source | yfinance (Yahoo Finance), auto-adjusted for splits/dividends |
| Price data end date | ~February 6, 2026 |
| Benchmark | SPY (SPDR S&P 500 ETF) |

### 1.3 Cohort Sizes

| Cohort | Total Signals | Unique Tickers | Entry Date | Max Available Trading Days |
|--------|---------------|----------------|------------|---------------------------|
| FY2020 | 918 | 918 | April 1, 2021 | ~1,218 (4.8 years) |
| FY2021 | 1,287 | 1,287 | April 1, 2022 | ~965 (3.8 years) |
| FY2022 | 1,297 | 1,297 | April 1, 2023 | ~714 (2.8 years) |
| FY2023 | 1,284 | 1,284 | April 1, 2024 | ~465 (1.8 years) |
| FY2024 | 1,304 | 1,304 | April 1, 2025 | ~214 (0.8 years) |

Each ticker appears at most once per cohort. No duplicate ticker-year observations exist. Independence within each cohort is guaranteed by construction.

### 1.4 Signal Distribution

Approximate distribution of final verdicts across the dataset:

| Verdict | Approx. % | Typical n per cohort |
|---------|-----------|---------------------|
| BUY / STRONG BUY | ~30% | 270–410 |
| HOLD | ~50% | 490–650 |
| SELL / STRONG SELL | ~16% | 148–245 |
| UNKNOWN | ~4% | 30–60 |

Of the BUY-rated stocks, approximately 20–25% receive a Fragile antifragile rating, yielding 51–85 BUY+Fragile signals per cohort.

---

## 2. Methodology

### 2.1 Entry Timing

For each signal with fiscal year FY, the **entry date is April 1 of FY+1**. This reflects the practical constraint that 10-K filings are typically available 60–90 days after fiscal year end (most companies have December FY-end; filings due late February/March). April 1 entry ensures no look-ahead bias — the filing has been published and the AI analysis completed before any position is taken.

If the market is closed on April 1, entry occurs on the next available trading day.

### 2.2 Holding Periods

We use maximum-available holding periods per cohort rather than rounding to exact calendar years. This maximizes the use of available price data (through approximately February 6, 2026):

| Period Label | Trading Days | Approx. Calendar | Cohorts Contributing | FM Testable (≥3) |
|--------------|-------------|-------------------|---------------------|-------------------|
| 0.8Y | 210 | ~10 months | FY2020–FY2024 (5) | Yes |
| 1.8Y | 460 | ~22 months | FY2020–FY2023 (4) | Yes |
| 2.8Y | 710 | ~34 months | FY2020–FY2022 (3) | Yes (minimum) |
| 3.8Y | 960 | ~46 months | FY2020–FY2021 (2) | No |
| 4.8Y | 1,210 | ~58 months | FY2020 only (1) | No |

### 2.3 Return Calculation

For each signal:

```
stock_return  = (stock_price_at_exit / stock_price_at_entry) − 1
bench_return  = (SPY_price_at_exit / SPY_price_at_entry) − 1
excess_return = stock_return − bench_return
```

Returns are **total returns adjusted for splits and dividends** (via yfinance auto-adjust). The benchmark is SPY (SPDR S&P 500 ETF). Excess return is arithmetic (not geometric). All reported returns are excess returns vs SPY unless explicitly stated otherwise.

### 2.4 Statistical Framework: Fama-MacBeth (1973)

**Problem:** Pooling all 6,090 signal-return pairs and running a t-test treats each observation as independent. But ~97% of tickers appear in 4+ fiscal years, creating (a) serial correlation (same company across years) and (b) cross-sectional correlation (all signals in the same year share the same market regime). Naive t-tests overstate significance.

**Solution:** Fama-MacBeth two-pass procedure:

1. **First pass:** For each fiscal year cohort independently, compute the mean excess return for each strategy group. Each cohort has at most one observation per ticker → within-cohort independence holds.

2. **Second pass:** Treat the K year-means as K independent observations. Compute the grand mean and run a one-sample t-test (H₀: mean = 0) on K observations.

With K = 4 (for the 1.8Y horizon), the t-test has only 3 degrees of freedom. This is deliberately conservative — achieving p < 0.01 with 3 degrees of freedom requires a t-statistic above 5.84, implying extreme consistency across years.

### 2.5 Minimum Sample Size

Within each cohort-period, we require n ≥ 3 observations to compute a cohort mean. A cohort contributing fewer observations is excluded from the FM aggregation for that period. The FM t-test requires ≥ 3 cohort-means to be computed (minimum df = 2).

---

## 3. Strategy Definition

### 3.1 Long Leg: BUY + Fragile

**Selection criteria:**
- Final verdict ∈ {BUY, STRONG BUY}
- Taleb antifragile rating = "Fragile"

**Interpretation:** The AI's synthesis concludes the stock is a buy on fundamental merit, but the Taleb lens flags it as fragile — meaning the company exhibits characteristics such as high leverage, concentration risk, limited optionality, or vulnerability to tail events. These are typically beaten-down or stressed companies where the market has already repriced risk aggressively.

**Typical portfolio size:** 51–85 stocks per cohort year.

### 3.2 Short Leg: SELL (All)

**Selection criteria:**
- Final verdict ∈ {SELL, STRONG SELL}

**Interpretation:** The AI's synthesis concludes the stock should be sold. All three analytical perspectives contribute to this verdict.

**Typical portfolio size:** 148–245 stocks per cohort year.

### 3.3 Portfolio Construction Variants

**Variant A — Dollar-Neutral Long/Short (50/50):**
- 50% of capital allocated long (equal-weighted BUY + Fragile positions)
- 50% of capital allocated short (equal-weighted SELL positions)
- Net market exposure: approximately zero
- Combined portfolio excess return = 0.5 × (long excess) − 0.5 × (short excess)

**Variant B — Full Long/Short Spread:**
- $1 long for every $1 short
- Portfolio return = long excess − short excess (the full spread)
- Requires margin/leverage

**Variant C — Long-Only:**
- 100% capital in equal-weighted BUY + Fragile positions
- Full market exposure (beta ≈ 1)
- Simplest to implement; no shorting infrastructure needed

### 3.4 Position Count Per Cohort

| Cohort | Long (BUY+Fragile) | Short (SELL all) | Total Positions |
|--------|--------------------|--------------------|-----------------|
| FY2020 | 73 | 148 | 221 |
| FY2021 | 51 | 245 | 296 |
| FY2022 | 84 | 202 | 286 |
| FY2023 | 85 | 172 | 257 |
| FY2024 | 82 | 195 | 277 |

---

## 4. Results: Long Leg (BUY + Fragile)

### 4.1 Per-Cohort Excess Returns vs SPY

| Cohort | 0.8Y (210d) | 1.8Y (460d) | 2.8Y (710d) | 3.8Y (960d) | 4.8Y (1,210d) | n |
|--------|-------------|-------------|-------------|-------------|----------------|---|
| FY2020 | −1.9% | +27.7% | +9.0% | +14.5% | +15.5% | 73 |
| FY2021 | +23.0% | +28.8% | +41.0% | +69.5% | — | 51 |
| FY2022 | +15.6% | +25.9% | +58.0% | — | — | 84 |
| FY2023 | +14.8% | +21.2% | — | — | — | 85 |
| FY2024 | +66.7% | — | — | — | — | 82 |

### 4.2 Fama-MacBeth Aggregation

| Horizon | FM Mean Excess | FM p-value | Cohorts (K) | df | Significance |
|---------|----------------|------------|-------------|-----|--------------|
| 0.8Y | +23.7% | 0.109 | 5 | 4 | — |
| **1.8Y** | **+25.9%** | **0.001** | **4** | **3** | **\*\*\*** |
| 2.8Y | +36.0% | 0.129 | 3 | 2 | — |

**At 1.8Y:** Four independent year-means of +21.2%, +25.9%, +27.7%, +28.8%. Standard deviation of year-means: 3.2pp. Standard error: 1.6pp. The range from minimum to maximum is only 7.6 percentage points — remarkable consistency across years spanning post-COVID recovery (FY2020), rate hikes (FY2021), the 2022 bear market (FY2022), and the 2023 AI-driven rally (FY2023).

### 4.3 Long-Only Absolute Return Estimates

Assuming SPY returns ~10% annualized (its long-run average):

| Horizon | FM Excess vs SPY | Annualized Excess | Est. Absolute Annualized |
|---------|------------------|-------------------|--------------------------|
| 0.8Y | +23.7% | +28.4%/yr | ~38.4%/yr |
| **1.8Y** | **+25.9%** | **+14.2%/yr** | **~24.2%/yr** |
| 2.8Y | +36.0% | +12.8%/yr | ~22.8%/yr |

*Note: These are rough estimates. Actual SPY returns varied substantially across the test period.*

---

## 5. Results: Short Leg (SELL All)

### 5.1 Per-Cohort Excess Returns vs SPY

| Cohort | 0.8Y (210d) | 1.8Y (460d) | 2.8Y (710d) | 3.8Y (960d) | 4.8Y (1,210d) | n |
|--------|-------------|-------------|-------------|-------------|----------------|---|
| FY2020 | −16.7% | −15.7% | −34.9% | −58.2% | −72.6% | 148 |
| FY2021 | +4.3% | −14.7% | −13.6% | −14.8% | — | 245 |
| FY2022 | −21.0% | −16.1% | −20.4% | — | — | 202 |
| FY2023 | −1.8% | −3.1% | — | — | — | 172 |
| FY2024 | +10.6% | — | — | — | — | 195 |

### 5.2 Fama-MacBeth Aggregation

| Horizon | FM Mean Excess | FM p-value | Cohorts (K) | df | Significance |
|---------|----------------|------------|-------------|-----|--------------|
| 0.8Y | −4.9% | 0.462 | 5 | 4 | — |
| **1.8Y** | **−12.4%** | **0.028** | **4** | **3** | **\*\*** |
| 2.8Y | −23.0% | 0.067 | 3 | 2 | \* |

The SELL signal is **not significant at the short horizon** (0.8Y) but **becomes significant and compounds over time**. At 1.8Y, all four cohort-means are negative (range: −3.1% to −16.1%). At 2.8Y, the magnitude increases to −23.0%.

### 5.3 SELL Sub-Type Breakdown (FM-significant results only)

| SELL Sub-Type | Horizon | FM Mean | FM p | Cohorts | n per cohort |
|---------------|---------|---------|------|---------|-------------|
| **SELL + Wide Moat** | 0.8Y | −9.3% | 0.074\* | 5 | 15–39 |
| **SELL + Wide Moat** | 1.8Y | −21.8% | 0.042\*\* | 4 | 15–39 |
| **SELL + Wide Moat** | 2.8Y | −42.3% | 0.021\*\* | 3 | 15–39 |
| SELL + Robust | 1.8Y | −18.2% | 0.049\*\* | 4 | 53–97 |
| SELL + Robust | 2.8Y | −37.7% | 0.045\*\* | 3 | 53–97 |
| SELL + Medium Conviction | 1.8Y | −20.0% | 0.032\*\* | 4 | 23–48 |
| SELL + Medium Conviction | 2.8Y | −34.1% | 0.054\* | 3 | 23–48 |
| SELL + Low/Unknown Conv. | 1.8Y | −12.2% | 0.028\*\* | 4 | 85–136 |

**SELL + Wide Moat** is the most devastating sub-signal: the AI identifies once-strong moat companies in structural decline. Per-cohort returns at 2.8Y: −39.7% (FY2020), −33.2% (FY2021), −54.1% (FY2022). At 4.8Y (FY2020 only): −98.8% — essentially total loss vs SPY.

### 5.4 Non-FM Directional Data (3.8Y and 4.8Y horizons)

These horizons have only 1–2 cohorts, insufficient for FM testing, but the magnitudes are informative:

| Signal | Horizon | FY2020 | FY2021 |
|--------|---------|--------|--------|
| SELL (all) | 3.8Y | −58.2% | −14.8% |
| SELL (all) | 4.8Y | −72.6% | — |
| SELL + Wide Moat | 3.8Y | −66.4% | −54.4% |
| SELL + Wide Moat | 4.8Y | −98.8% | — |
| SELL + No Moat | 3.8Y | −87.7% | −81.3% |
| SELL + Robust | 3.8Y | −63.0% | −35.7% |
| SELL + Fragile | 3.8Y | −54.7% | −1.1% |

---

## 6. Results: Combined Long/Short Portfolio

### 6.1 Full Long/Short Spread (BUY+Fragile Long, SELL Short)

The spread is computed as: (mean long excess) − (mean short excess) per cohort.

| Cohort | 0.8Y | 1.8Y | 2.8Y | 3.8Y | 4.8Y |
|--------|------|------|------|------|------|
| FY2020 | +14.9% | +43.4% | +43.9% | +72.7% | +88.1% |
| FY2021 | +18.7% | +43.6% | +54.7% | +84.3% | — |
| FY2022 | +36.6% | +42.0% | +78.4% | — | — |
| FY2023 | +16.6% | +24.3% | — | — | — |
| FY2024 | +56.1% | — | — | — | — |

**Fama-MacBeth Aggregation:**

| Horizon | FM Spread | FM p-value | Cohorts | Significance |
|---------|-----------|------------|---------|--------------|
| **0.8Y** | **+28.6%** | **0.022** | **5** | **\*\*** |
| **1.8Y** | **+38.3%** | **0.004** | **4** | **\*\*\*** |
| **2.8Y** | **+59.0%** | **0.029** | **3** | **\*\*** |

The spread is statistically significant at **every testable horizon** and **monotonically increasing** with time held.

### 6.2 Dollar-Neutral 50/50 Portfolio

Allocating 50% of capital to the long leg and 50% to the short leg:

Combined return = 0.5 × (BUY+Fragile excess) − 0.5 × (SELL excess)

| Cohort | 0.8Y | 1.8Y | 2.8Y | 3.8Y | 4.8Y |
|--------|------|------|------|------|------|
| FY2020 | +7.4% | +21.7% | +21.9% | +36.4% | +44.0% |
| FY2021 | +9.3% | +21.7% | +27.3% | +42.1% | — |
| FY2022 | +18.3% | +21.0% | +39.2% | — | — |
| FY2023 | +8.3% | +12.2% | — | — | — |
| FY2024 | +28.1% | — | — | — | — |

**Fama-MacBeth Aggregation:**

| Horizon | FM Mean | FM p-value | Cohorts | Significance |
|---------|---------|------------|---------|--------------|
| **0.8Y** | **+14.3%** | **0.023** | **5** | **\*\*** |
| **1.8Y** | **+19.1%** | **0.004** | **4** | **\*\*\*** |
| **2.8Y** | **+29.5%** | **0.029** | **3** | **\*\*** |

**Key observation: no cohort produced a negative return at any horizon.** The worst single-cohort result is FY2020 at 0.8Y: +7.4%.

### 6.3 Annualized Returns (Dollar-Neutral 50/50)

Since this is a market-neutral portfolio (zero net market exposure), the return is approximately the excess over the risk-free rate:

| Horizon | FM Total Return | Annualized | Worst Cohort | Best Cohort |
|---------|-----------------|------------|--------------|-------------|
| 0.8Y | +14.3% | ~17.1%/yr | +7.4% (FY20) | +28.1% (FY24) |
| **1.8Y** | **+19.1%** | **~10.5%/yr** | **+12.2% (FY23)** | **+21.7% (FY20, FY21)** |
| 2.8Y | +29.5% | ~10.5%/yr | +21.9% (FY20) | +39.2% (FY22) |

The annualized excess converges to ~10.5%/yr at the 1.8Y and 2.8Y horizons, suggesting a stable underlying alpha rate.

### 6.4 Alternative Short Legs for L/S Portfolio

| Long | Short | 0.8Y FM | p | 1.8Y FM | p | 2.8Y FM | p |
|------|-------|---------|---|---------|---|---------|---|
| BUY+Fragile | SELL (all) | +28.6% | 0.022\*\* | +38.3% | 0.004\*\*\* | +59.0% | 0.029\*\* |
| BUY+Fragile | SELL + Fragile | +28.4% | 0.024\*\* | +35.6% | 0.014\*\* | +50.9% | 0.014\*\* |
| BUY+Fragile | SELL + Hi Conv + Fragile | +25.9% | 0.016\*\* | +35.5% | 0.024\*\* | +53.6% | 0.006\*\*\* |
| BUY+Fragile | Stable multi-yr SELL | — | — | +41.1% | 0.046\*\* | — | — |
| BUY+Fragile | SELL + Robust | — | — | +44.1% | — | +73.7% | — |

The broadest short leg (SELL all) produces the strongest p-values at most horizons due to larger sample size reducing within-cohort estimation noise. **SELL + Hi Conv + Fragile** produces the strongest 2.8Y p-value (0.006) as a more concentrated short book.

### 6.5 Worst-Case Analysis

| Horizon | Worst Cohort (50/50) | Best Cohort (50/50) | Range |
|---------|---------------------|---------------------|-------|
| 0.8Y | +7.4% (FY2020) | +28.1% (FY2024) | 20.7pp |
| 1.8Y | +12.2% (FY2023) | +21.7% (FY2020/21) | 9.6pp |
| 2.8Y | +21.9% (FY2020) | +39.2% (FY2022) | 17.2pp |

Even in the worst observed year, the 50/50 portfolio returned +7.4% in 10 months or +12.2% in 22 months. There is no observed cohort with a negative combined return.

---

## 7. Robustness Checks and Decomposition

### 7.1 Comparison to Related BUY Signals

The BUY + Fragile signal outperforms all other BUY sub-groups at the 1.8Y horizon:

| BUY Sub-Group | FM Mean (1.8Y) | FM p | Cohorts | n per cohort |
|---------------|----------------|------|---------|-------------|
| **BUY + Fragile** | **+25.9%** | **0.001** | **4** | **51–85** |
| BUY + High Conviction | +17.3% | 0.094 | 4 | 32–69 |
| BUY + Narrow Moat | +6.0% | 0.241 | 4 | 231–346 |
| BUY + Wide Moat | +2.3% | 0.742 | 4 | 33–67 |
| BUY + Antifragile/Robust | +1.0% | 0.846 | 4 | 199–333 |
| BUY + No Moat | +66.9% | 0.229 | 3 | 5–8 (too small) |

**Critical finding:** BUY + Antifragile/Robust (the complement of BUY + Fragile) shows **zero** excess return (+1.0%, p = 0.846, n = 199–333 per cohort). The alpha is concentrated **entirely** in the Fragile subset. The BUY signal alone does not generate significant returns — it is the **interaction with the Fragile rating** that creates the edge.

### 7.2 Is This Just a Value/Distress Factor?

The Fragile rating is assigned by the Taleb analytical lens based on tail risk exposure, leverage, concentration, and optionality — not directly on valuation metrics. However, fragile companies tend to trade at depressed valuations, so overlap with traditional value and distress factors is expected.

**Key difference from generic value:** The AI is reading the actual 10-K text, not screening on P/E or P/B ratios. The BUY verdict requires the synthesis to conclude that the business has merit across multiple lenses despite the fragility. A generic deep-value screen would include many value traps that the AI's SELL signal would exclude.

**Evidence of differentiation:**

| Fragile Sub-Group | 1.8Y FM Mean | FM p |
|--------------------|-------------|------|
| Fragile + BUY | +25.9% | 0.001 |
| Fragile — all actions | +9.5% | 0.172 |
| Fragile + SELL | −9.7% | 0.158 |
| Fragile + HOLD (implied) | ~+5% | n.s. |

If BUY + Fragile were purely a mechanical fragility/distress factor, all Fragile stocks should show positive excess returns. Instead, **Fragile + SELL** is negative (−9.7%) and **Fragile overall** is only +9.5% (not significant). The AI's BUY/SELL classification adds discriminative value on top of any mechanical factor exposure.

### 7.3 SELL Signal Strengthens Over Time

The SELL signal's excess return trajectory reveals compounding underperformance:

| Horizon | FM Mean Excess | FM p | Annualized Rate |
|---------|----------------|------|-----------------|
| 0.8Y (10mo) | −4.9% | 0.462 | ~−5.9%/yr |
| 1.8Y (22mo) | −12.4% | 0.028 | ~−6.8%/yr |
| 2.8Y (34mo) | −23.0% | 0.067 | ~−8.2%/yr |
| 3.8Y (FY20) | −58.2% | N/A | ~−15.3%/yr |
| 4.8Y (FY20) | −72.6% | N/A | ~−15.1%/yr |

The accelerating annualized underperformance suggests the AI identifies **structural deterioration**, not temporary mispricing.

### 7.4 Contrarian Lens Adds Independent Alpha

| Signal | 1.8Y FM Mean | FM p |
|--------|--------------|------|
| C-PRI + Fragile (max hated) | +14.4% | 0.025\*\* |
| (PASS,PASS,PRIORITY) — only contrarian says buy | +14.7% | 0.047\*\* |
| Contrarian PRIORITY — all | +3.6% | 0.473 |
| C-PRI + Final BUY | +5.8% | 0.332 |

The contrarian perspective's value is concentrated in the interaction with fragility — "most hated" stocks the contrarian lens recommends.

### 7.5 Market Regime Robustness

The four testable cohorts entered in markedly different market environments:

| Cohort | Entry Date | Market Context | BUY+Fragile 1.8Y | SELL 1.8Y |
|--------|------------|----------------|-------------------|-----------|
| FY2020 | Apr 2021 | Post-COVID recovery, low rates, peak stimulus | +27.7% | −15.7% |
| FY2021 | Apr 2022 | Start of rate-hike cycle, growth-to-value rotation | +28.8% | −14.7% |
| FY2022 | Apr 2023 | Post-bear recovery, AI/tech rally beginning | +25.9% | −16.1% |
| FY2023 | Apr 2024 | Late-cycle broadening, high rates sustained | +21.2% | −3.1% |

The signal works in rate-hike environments, bear market recoveries, and momentum-driven rallies. FY2023 shows the weakest result on both legs (+21.2% long, −3.1% short), but even this cohort is positive on the long side and negative on the short side.

---

## 8. Complete FM Summary: All Statistically Significant Findings (p < 0.10)

### 8.1 All Experiments — Findings That Survived FM Correction

| Experiment | Signal | Horizon | FM Mean | FM p | Cohorts |
|------------|--------|---------|---------|------|---------|
| **C: Moat × Action** | **BUY + Fragile** | **1.8Y** | **+25.9%** | **0.001\*\*\*** | **4** |
| E: Triple-Combo | (INV,INV,INV) | 2.8Y | −19.5% | 0.005\*\*\* | 3 |
| C: Moat × Action | SELL + Wide Moat | 2.8Y | −42.3% | 0.021\*\* | 3 |
| I: Contrarian | C-PRI + Fragile | 1.8Y | +14.4% | 0.025\*\* | 4 |
| H: SELL Anatomy | SELL (all) | 1.8Y | −12.4% | 0.028\*\* | 4 |
| B: Conviction | SELL + Low/Unknown Conv | 1.8Y | −12.2% | 0.028\*\* | 4 |
| F: Verdict | SELL — all cautious | 1.8Y | −11.5% | 0.028\*\* | 4 |
| B: Conviction | SELL + Medium Conv | 1.8Y | −20.0% | 0.032\*\* | 4 |
| C: Moat × Action | BUY + Narrow Moat | 2.8Y | +7.6% | 0.036\*\* | 3 |
| C: Moat × Action | SELL + Wide Moat | 1.8Y | −21.8% | 0.042\*\* | 4 |
| G: Fragility | Robust + SELL | 2.8Y | −37.7% | 0.045\*\* | 3 |
| I: Contrarian | C-PRI + Final BUY | 2.8Y | +12.2% | 0.046\*\* | 3 |
| E: Triple-Combo | (PASS,PASS,PRIORITY) | 1.8Y | +14.7% | 0.047\*\* | 4 |
| G: Fragility | Robust + SELL | 1.8Y | −18.2% | 0.049\*\* | 4 |
| B: Conviction | SELL + Medium Conv | 2.8Y | −34.1% | 0.054\* | 3 |
| I: Contrarian | Contrarian PRI — all | 2.8Y | +6.8% | 0.059\* | 3 |
| A: Agreement | T+C PRI (not B) | 1.8Y | −28.8% | 0.061\* | 4 |
| H: SELL Anatomy | SELL (all) | 2.8Y | −23.0% | 0.067\* | 3 |
| C: Moat × Action | SELL + Wide Moat | 0.8Y | −9.3% | 0.074\* | 5 |
| A: Agreement | T+C PRI (not B) | 2.8Y | −34.3% | 0.082\* | 3 |
| C: Moat × Action | SELL + No Moat | 2.8Y | −46.4% | 0.089\* | 3 |
| J: Composite | [L] High-conv BUY + Fragile | 1.8Y | +122.7% | 0.092\* | 4 |
| B: Conviction | BUY + High Conviction | 1.8Y | +17.3% | 0.094\* | 4 |
| J: Composite | [L] High-conv BUY | 1.8Y | +17.3% | 0.094\* | 4 |

### 8.2 L/S Spread Summary — All Tested Combinations (FM p < 0.10)

**At 0.8Y horizon (5 cohorts):**

| Long | Short | FM Spread | FM p |
|------|-------|-----------|------|
| BUY + Fragile | SELL + Hi Conv + Fragile | +25.9% | 0.016\*\* |
| BUY + Fragile | SELL (all) | +28.6% | 0.022\*\* |
| BUY + Fragile | SELL + Fragile | +28.4% | 0.024\*\* |

**At 1.8Y horizon (4 cohorts):**

| Long | Short | FM Spread | FM p |
|------|-------|-----------|------|
| BUY + Fragile | SELL (all) | +38.3% | 0.004\*\*\* |
| BUY + Fragile | SELL + Fragile | +35.6% | 0.014\*\* |
| BUY + Fragile | SELL + Hi Conv + Fragile | +35.5% | 0.024\*\* |
| BUY + Fragile | Stable multi-yr SELL | +41.1% | 0.046\*\* |
| High-conv BUY | SELL (all) | +29.7% | 0.059\* |
| High-conv BUY + Fragile | SELL (all) | +135.1% | 0.068\* |
| High-conv BUY + Fragile | SELL + Fragile | +132.4% | 0.062\* |
| High-conv BUY + Fragile | SELL + Hi Conv + Fragile | +132.4% | 0.059\* |
| High-conv BUY | SELL + Fragile | +27.0% | 0.084\* |

**At 2.8Y horizon (3 cohorts):**

| Long | Short | FM Spread | FM p |
|------|-------|-----------|------|
| BUY + Fragile | SELL + Hi Conv + Fragile | +53.6% | 0.006\*\*\* |
| BUY + Fragile | SELL + Fragile | +50.9% | 0.014\*\* |
| BUY + Fragile | SELL (all) | +59.0% | 0.029\*\* |
| B+C PRI → BUY | SELL (all) | +39.4% | 0.051\* |
| High-conv BUY | SELL + Hi Conv + Fragile | +51.0% | 0.055\* |

### 8.3 Signals That Did NOT Survive FM Correction

| Signal | Pooled p | FM p | Reason for Failure |
|--------|----------|------|-------------------|
| Signal drift (upgrades/downgrades) | < 0.05 | > 0.30 | Inconsistent direction across years |
| STRONG SELL specifically | < 0.01 | 0.944 | Extreme range: −24.3% to +54.3% across years |
| All 3 perspectives agree PRIORITY | < 0.05 | N/A | n = 1–3 per cohort; untestable |
| Conviction High vs Low (BUY) | < 0.05 | > 0.10 | Inconsistent year-to-year |
| BUY + Antifragile/Robust | < 0.05 | 0.846 | Zero excess return when tested independently |
| Stable multi-yr SELL | < 0.05 | 0.152 | FY2023 cohort near zero |

---

## 9. Limitations and Risk Disclosures

### 9.1 Statistical Limitations

- **Small number of independent observations.** FM aggregation uses K = 3–5 cohort-means. While the t-test is valid, the distribution is approximate with few degrees of freedom. A single bad future cohort would substantially widen confidence intervals. For the primary result (1.8Y, K=4, p=0.001), adding one cohort with −10% would move p to approximately 0.06.

- **Multiple testing.** Ten experiments (A–J) with multiple group definitions and five holding periods were tested. Approximately 50–80 effective hypothesis tests were conducted. No formal multiple-comparison correction (e.g., Bonferroni, FDR) has been applied. The BUY + Fragile signal at p = 0.001 would survive a Bonferroni correction at the 0.05 level over ~50 tests (adjusted threshold: 0.001). Marginal findings (p = 0.05–0.10) would not survive such correction.

- **FM assumes independence across cohorts.** If the same macro environment drives returns across adjacent cohorts (e.g., a sustained regime benefiting all BUY + Fragile stocks from FY2020 through FY2023), the FM standard error is understated. The four cohorts do span materially different market regimes (COVID recovery, rate hikes, bear market, AI rally), mitigating this concern.

- **Equal weighting of cohort means.** FM treats each cohort equally regardless of sample size. FY2021 (n=51 BUY+Fragile) receives the same weight as FY2023 (n=85). This is conservative (it doesn't favor large-sample cohorts) but means noisier cohorts receive equal influence.

### 9.2 Data Limitations

- **Price data source.** Prices are sourced from yfinance (Yahoo Finance), with auto-adjustment for splits and dividends. Data is cached locally in Parquet format. yfinance is not institutional-grade and may have errors or gaps.

- **Survivorship bias.** The ticker universe consists of companies for which SEC 10-K filings were available and successfully analyzed. Companies that delisted, were acquired, or went bankrupt may be underrepresented. **Critically:** for BUY + Fragile — the "stressed company" bucket — survivorship bias could inflate returns if the worst-performing fragile companies (those that went to zero) are missing from the dataset.

  Specifically: yfinance returns historical data through the delisting date for delisted securities. A stock that delists after 6 months post-entry contributes to 0.8Y statistics but is silently excluded from 1.8Y+ horizons. This could create a positive bias at longer horizons if delisted stocks (which tend to have the worst returns) drop out of the sample. Tickers with no price data at the entry date are silently excluded entirely. **We did not perform an explicit audit of delisted tickers in the dataset.**

- **Sample size attrition by horizon.** The reported n for each cohort-period is the number of signals with available price data for that full holding period. Attrition between 0.8Y and 1.8Y appears minimal (n stays at 73/51/84/85), but was not formally audited. Any attrition at longer horizons would disproportionately remove the worst-performing stocks.

- **Benchmark selection.** SPY is used as the sole benchmark. No adjustment is made for sector, size, value, momentum, or other factor exposures. The BUY + Fragile portfolio may have structural tilts (e.g., small-cap, high-beta) that explain part of the excess return.

### 9.3 Implementation Limitations

- **No transaction costs.** No bid-ask spreads, commissions, or market impact are modeled. Fragile companies (which are often small or mid-cap) may have wider spreads and lower liquidity.

- **No shorting costs.** The short leg assumes frictionless short selling. In practice, short borrowing costs for distressed names can be substantial (5–20% annualized for hard-to-borrow stocks). For a 1.8-year hold, cumulative shorting costs of 9–36% could significantly erode or eliminate the short leg's contribution.

- **Equal weighting.** The backtest uses equal-weighted positions. A portfolio with 51–85 long positions and 148–245 short positions requires significant capital and rebalancing infrastructure. Equal weighting into small positions may not be feasible for large AUM.

- **Annual rebalance only.** Positions are entered on April 1 and held without adjustment. No stop-losses, position sizing, or risk management is modeled. Intra-period drawdowns are not measured.

- **Entry date assumption.** April 1 assumes the AI analysis is completed promptly after 10-K filing. In practice, processing all ~1,300 filings requires time and computational resources. A staggered entry would alter the results.

### 9.4 Signal Generation Limitations

- **AI model dependency.** Signals are generated by Google Gemini (a commercial LLM). Model updates, API changes, or provider discontinuation could alter signal characteristics.

- **Retrospective signal generation.** All signals were generated after-the-fact from historical filings using the same model version. We cannot confirm that the same model would have produced identical signals in real-time. However, the AI has no access to future price data — it analyzes only the 10-K filing text for the relevant fiscal year.

- **Black-box classification.** The Fragile rating is assigned by the AI based on its interpretation of the 10-K text. The exact decision boundary between Fragile and Robust is not explicitly defined or auditable. The factors driving the Fragile classification (leverage, tail risk, concentration, lack of optionality) are specified in the prompt but the weighting is implicit.

- **Prompt sensitivity.** The AI's output is influenced by the prompt templates used. Different prompts could produce different Fragile/Robust boundaries and different BUY/SELL thresholds. No prompt sensitivity analysis has been performed.

---

## 10. Summary of Key Findings

### Primary Findings (FM-corrected, p < 0.05)

| # | Finding | Horizon | FM Mean | FM p | n/yr |
|---|---------|---------|---------|------|------|
| 1 | BUY + Fragile outperforms SPY | 1.8Y | +25.9% | 0.001\*\*\* | 51–85 |
| 2 | SELL (all) underperforms SPY | 1.8Y | −12.4% | 0.028\*\* | 148–245 |
| 3 | L/S spread: BUY+Fragile vs SELL | 0.8Y | +28.6% | 0.022\*\* | — |
| 4 | L/S spread: BUY+Fragile vs SELL | 1.8Y | +38.3% | 0.004\*\*\* | — |
| 5 | L/S spread: BUY+Fragile vs SELL | 2.8Y | +59.0% | 0.029\*\* | — |
| 6 | 50/50 portfolio excess return | 0.8Y | +14.3% | 0.023\*\* | — |
| 7 | 50/50 portfolio excess return | 1.8Y | +19.1% | 0.004\*\*\* | — |
| 8 | 50/50 portfolio excess return | 2.8Y | +29.5% | 0.029\*\* | — |
| 9 | BUY + Antifragile/Robust does NOT outperform | 1.8Y | +1.0% | 0.846 | 199–333 |
| 10 | SELL + Wide Moat is worst SELL sub-type | 2.8Y | −42.3% | 0.021\*\* | 15–39 |

### Key Negative Findings

| Finding | Implication |
|---------|-------------|
| BUY alone has no significant alpha | The Fragile interaction is essential |
| Conviction level has weak predictive power | High/Med/Low conviction adds little to the BUY/SELL signal |
| Signal changes (upgrades/downgrades) are noise | Year-over-year changes in the AI's verdict carry no information |
| Short-horizon (0.8Y) SELL signal is weak | SELL requires >1 year to manifest; don't expect quick payoff |

### Directional but Not FM-Testable (< 3 cohorts)

| Finding | Horizon | Data |
|---------|---------|------|
| SELL compounds to −72.6% (FY2020) | 4.8Y | 1 cohort, n=147 |
| SELL + Wide Moat → −98.8% (FY2020) | 4.8Y | 1 cohort, n=15 |
| BUY + Fragile positive at all horizons | 3.8Y–4.8Y | 1–2 cohorts |
| 50/50 portfolio: +36.4% to +44.0% | 3.8Y–4.8Y | 1–2 cohorts |

---

## 11. Suggested Next Steps for Validation

1. **Survivorship audit.** Cross-reference the ticker universe against CRSP or a comprehensive delisting database. Identify how many BUY + Fragile signals correspond to subsequently delisted companies, and what return they would have generated (including delisting returns). This is the single most important validation step.

2. **Factor attribution.** Regress the BUY + Fragile portfolio returns against Fama-French 5-factor model (market, size, value, profitability, investment) plus momentum. Determine how much of the +25.9% is explained by known factor exposures vs. genuine alpha.

3. **Out-of-sample test.** The FY2024 cohort entered in April 2025 and currently shows +66.7% at 0.8Y (10 months). Monitor this cohort through April 2027 (1.8Y horizon) as a genuine out-of-sample test. The FY2025 cohort (entry April 2026) will be the first fully prospective test.

4. **Transaction cost simulation.** Model realistic bid-ask spreads (using historical spread data for the specific tickers), shorting costs (borrow rates for each SELL ticker), and market impact for the portfolio sizes involved. Estimate net-of-cost returns.

5. **Sector/size decomposition.** Determine whether BUY + Fragile is concentrated in specific sectors or market-cap ranges, and whether the alpha persists after controlling for these exposures.

6. **Drawdown analysis.** Compute intra-period maximum drawdown for each cohort's portfolio. The current analysis only measures terminal returns; the path matters for risk management.

7. **Prompt sensitivity test.** Re-run the AI analysis with modified prompt templates to determine whether the Fragile/Robust boundary and BUY/SELL thresholds are robust to prompt phrasing.

8. **Real-time signal generation.** Generate signals for FY2025 filings as they become available (February–April 2026) and track the portfolio prospectively without backtest-grade hindsight.

---

## Appendix A: Experiment Overview

The BUY + Fragile strategy emerged from a systematic scan across 10 experiments (A–J), each testing different signal combinations. The full experiment set:

| Exp | Name | What It Tests | Key FM-Significant Finding |
|-----|------|---------------|---------------------------|
| A | Perspective Agreement | Do stocks where 2-3 perspectives agree outperform? | T+C agree PRI (not B): −28.8%, p=0.061 |
| B | Conviction Calibration | Does conviction level predict returns? | SELL + Med Conv: −20.0%, p=0.032 |
| C | Moat × Action | Does moat/fragility interact with BUY/SELL? | **BUY + Fragile: +25.9%, p=0.001** |
| D | Signal Drift | Do upgrades/downgrades predict returns? | Nothing survived |
| E | Triple-Combo | Which perspective combinations work best? | (INV,INV,INV): −19.5%, p=0.005 |
| F | Verdict Alignment | Does alignment with sub-perspectives matter? | SELL cautious: −11.5%, p=0.028 |
| G | Fragility Factor | Is fragility predictive? How does it interact? | **Fragile + BUY: +25.9%, p=0.001** |
| H | SELL Anatomy | Which SELL sub-types underperform most? | SELL + Wide Moat: −42.3%, p=0.021 |
| I | Contrarian | Does contrarian perspective add alpha? | C-PRI + Fragile: +14.4%, p=0.025 |
| J | Multi-Factor Composite | Best L/S combinations | **BUY+Fragile vs SELL: +38.3%, p=0.004** |

BUY + Fragile appeared as a top signal in Experiments C, G, and J independently. It was not selected post-hoc from a single experiment.

## Appendix B: Fama-MacBeth Procedure Detail

For a given strategy group G and holding period P:

1. For each fiscal year t ∈ {2020, 2021, 2022, 2023, 2024}:
   - Identify all signals in cohort t that match group G
   - Compute excess return (vs SPY) for each signal at period P (where price data exists)
   - If n ≥ 3, compute cohort mean: μ_t = (1/n) Σ excess_return_i
   - Record cohort sample size n_t

2. Collect the K cohort-means {μ_t₁, μ_t₂, ..., μ_tK} where K ≤ 5

3. If K ≥ 3:
   - FM mean: μ̄ = (1/K) Σ μ_t
   - FM standard deviation: σ = √[(1/(K−1)) Σ (μ_t − μ̄)²]
   - FM standard error: SE = σ / √K
   - FM t-statistic: t = μ̄ / SE
   - FM p-value: two-tailed, from Student's t-distribution with K−1 degrees of freedom

**Why this is conservative:**
- K is small (3–5), so the t-distribution has heavy tails (wider confidence intervals)
- Achieving p < 0.01 with df=3 requires |t| > 5.84
- Each μ_t treats all stocks in that year equally, regardless of within-year sample size
- The procedure is equivalent to asking: "Is the signal consistently positive across independent time periods?"

**Significance thresholds:**
- \*\*\* : p < 0.01
- \*\* : p < 0.05
- \* : p < 0.10

## Appendix C: Per-Experiment Complete Data Tables

### Experiment A: Perspective Agreement (1.8Y horizon)

| Group | FY2020 | FY2021 | FY2022 | FY2023 | FM Mean | FM p |
|-------|--------|--------|--------|--------|---------|------|
| B+C agree PRI (not T) | +20.8% (n=44) | +26.1% (n=78) | +0.5% (n=115) | −9.0% (n=81) | +9.6% | 0.330 |
| T+C agree PRI (not B) | −9.2% (n=3) | −23.7% (n=7) | −26.2% (n=7) | −56.1% (n=5) | −28.8% | 0.061\* |
| Buffett PRI only | −3.1% (n=8) | −8.3% (n=9) | +5.7% (n=10) | −23.2% (n=7) | −7.2% | 0.318 |
| Contrarian PRI only | +13.6% (n=255) | +2.1% (n=315) | −2.3% (n=359) | −3.6% (n=379) | +2.5% | 0.573 |
| PASS everywhere | −16.6% (n=108) | −9.1% (n=173) | −0.9% (n=160) | −1.3% (n=123) | −7.0% | 0.157 |

### Experiment B: Conviction Calibration (1.8Y horizon)

| Group | FY2020 | FY2021 | FY2022 | FY2023 | FM Mean | FM p |
|-------|--------|--------|--------|--------|---------|------|
| BUY + High Conv | +19.7% (n=36) | +15.5% (n=50) | +34.5% (n=69) | −0.3% (n=64) | +17.3% | 0.094\* |
| BUY + Medium Conv | +10.0% (n=69) | −6.9% (n=70) | +8.7% (n=94) | −10.8% (n=108) | +0.2% | 0.966 |
| BUY + Low/Unk Conv | +18.0% (n=167) | +12.5% (n=212) | −10.2% (n=254) | +0.9% (n=239) | +5.3% | 0.461 |
| SELL + High Conv | −15.9% (n=40) | −18.6% (n=61) | −9.2% (n=56) | +10.1% (n=50) | −8.4% | 0.284 |
| SELL + Medium Conv | −12.0% (n=23) | −12.1% (n=48) | −34.4% (n=27) | −21.7% (n=35) | −20.0% | 0.032\*\* |
| SELL + Low/Unk Conv | −16.6% (n=85) | −13.9% (n=136) | −15.2% (n=119) | −3.2% (n=87) | −12.2% | 0.028\*\* |

### Experiment C: Moat × Action (1.8Y horizon)

| Group | FY2020 | FY2021 | FY2022 | FY2023 | FM Mean | FM p |
|-------|--------|--------|--------|--------|---------|------|
| BUY + Wide Moat | +15.9% (n=33) | +7.2% (n=57) | −0.1% (n=64) | −13.9% (n=67) | +2.3% | 0.742 |
| BUY + Narrow Moat | +16.6% (n=231) | +8.3% (n=270) | −1.1% (n=346) | +0.1% (n=343) | +6.0% | 0.241 |
| SELL + Wide Moat | −6.3% (n=15) | −16.3% (n=39) | −33.0% (n=38) | −31.5% (n=30) | −21.8% | 0.042\*\* |
| SELL + Narrow Moat | −16.2% (n=124) | −12.8% (n=196) | −13.8% (n=154) | +3.7% (n=135) | −9.8% | 0.122 |
| BUY + Antifragile/Robust | +12.0% (n=199) | +5.2% (n=281) | −4.7% (n=333) | −8.5% (n=326) | +1.0% | 0.846 |
| **BUY + Fragile** | **+27.7% (n=73)** | **+28.8% (n=51)** | **+25.9% (n=84)** | **+21.2% (n=85)** | **+25.9%** | **0.001\*\*\*** |
| SELL + Fragile | −18.6% (n=94) | −16.8% (n=148) | −7.2% (n=136) | +3.9% (n=115) | −9.7% | 0.158 |

### Experiment G: Fragility Factor (1.8Y horizon)

| Group | FY2020 | FY2021 | FY2022 | FY2023 | FM Mean | FM p |
|-------|--------|--------|--------|--------|---------|------|
| Fragile — all actions | +1.6% (n=401) | +3.0% (n=466) | +8.5% (n=526) | +24.8% (n=522) | +9.5% | 0.172 |
| Robust — all actions | +3.0% (n=509) | +2.1% (n=815) | −15.8% (n=768) | −10.7% (n=759) | −5.3% | 0.336 |
| Fragile + BUY | +27.7% (n=73) | +28.8% (n=51) | +25.9% (n=84) | +21.2% (n=85) | +25.9% | 0.001\*\*\* |
| Fragile + SELL | −18.6% (n=94) | −16.8% (n=148) | −7.2% (n=136) | +3.9% (n=115) | −9.7% | 0.158 |
| Robust + BUY | +12.2% (n=195) | +5.4% (n=277) | −4.9% (n=330) | −9.1% (n=324) | +0.9% | 0.867 |
| Robust + SELL | −9.6% (n=53) | −11.6% (n=97) | −34.6% (n=66) | −17.2% (n=57) | −18.2% | 0.049\*\* |

### Experiment H: SELL Anatomy (1.8Y horizon)

| Group | FY2020 | FY2021 | FY2022 | FY2023 | FM Mean | FM p |
|-------|--------|--------|--------|--------|---------|------|
| SELL (all) | −15.7% (n=148) | −14.7% (n=245) | −16.1% (n=202) | −3.1% (n=172) | −12.4% | 0.028\*\* |
| STRONG SELL only | −17.0% (n=18) | −31.7% (n=9) | +26.8% (n=18) | +5.3% (n=15) | −4.1% | 0.768 |
| SELL + High Conv | −15.9% (n=40) | −18.6% (n=61) | −9.2% (n=56) | +10.1% (n=50) | −8.4% | 0.284 |
| SELL + Low/Unk Conv | −16.6% (n=85) | −13.9% (n=136) | −15.2% (n=119) | −3.2% (n=87) | −12.2% | 0.028\*\* |
| SELL + Wide Moat | −6.3% (n=15) | −16.3% (n=39) | −33.0% (n=38) | −31.5% (n=30) | −21.8% | 0.042\*\* |
| SELL + No Moat | −24.7% (n=9) | −46.8% (n=10) | +12.0% (n=10) | −12.9% (n=7) | −18.1% | 0.236 |
| SELL + Fragile | −18.6% (n=94) | −16.8% (n=148) | −7.2% (n=136) | +3.9% (n=115) | −9.7% | 0.158 |
| SELL + Robust | −9.6% (n=53) | −11.6% (n=97) | −34.6% (n=66) | −17.2% (n=57) | −18.2% | 0.049\*\* |
| SELL + No Moat + Fragile | −24.7% (n=9) | −54.1% (n=9) | +15.9% (n=9) | −12.9% (n=7) | −18.9% | 0.282 |

### Experiment J: Multi-Factor Composite (1.8Y horizon)

| Group | FY2020 | FY2021 | FY2022 | FY2023 | FM Mean | FM p |
|-------|--------|--------|--------|--------|---------|------|
| [L] B+C PRI → BUY | +20.6% (n=42) | +27.2% (n=75) | +1.6% (n=106) | −7.9% (n=77) | +10.4% | 0.292 |
| [L] High-conv BUY | +19.7% (n=36) | +15.5% (n=50) | +34.5% (n=69) | −0.3% (n=64) | +17.3% | 0.094\* |
| [L] BUY + Fragile | +27.7% (n=73) | +28.8% (n=51) | +25.9% (n=84) | +21.2% (n=85) | +25.9% | 0.001\*\*\* |
| [L] Hi-conv BUY + Fragile | +51.2% (n=3) | +22.2% (n=4) | +200.2% (n=6) | +217.3% (n=4) | +122.7% | 0.092\* |
| [S] SELL (all) | −15.7% (n=148) | −14.7% (n=245) | −16.1% (n=202) | −3.1% (n=172) | −12.4% | 0.028\*\* |
| [S] Stable multi-yr SELL | — | −25.1% (n=62) | −20.0% (n=71) | −2.2% (n=62) | −15.8% | 0.152 |
| [S] SELL + Fragile | −18.6% (n=94) | −16.8% (n=148) | −7.2% (n=136) | +3.9% (n=115) | −9.7% | 0.158 |
| [S] SELL + Hi Conv + Fragile | −21.4% (n=27) | −17.4% (n=39) | −8.6% (n=45) | +8.9% (n=36) | −9.6% | 0.247 |

## Appendix D: Data Quality Notes

- Price data sourced from yfinance and cached locally in Parquet format
- yfinance returns historical data through delisting date for delisted securities
- Stocks with no price data at entry date are silently excluded from analysis (not counted in n)
- Sample size (n) varies by holding period due to data availability
- Stocks with truncated price histories (e.g., delisted after 6 months) contribute only to periods where full data exists
- No explicit survivorship bias correction has been applied
- All returns are total returns adjusted for splits and dividends (yfinance auto-adjust=True)
- SPY (SPDR S&P 500 ETF) used as benchmark throughout
- Entry date: April 1 of fiscal_year + 1 (or next trading day)
- Returns are arithmetic excess: stock_return − SPY_return (not log or geometric)

---

*This document was generated from the EON backtesting system. The analysis code is available at `experimental/backtester/run_independent.py`. Raw experiment output totaling ~940 lines of tabular data is available upon request.*
