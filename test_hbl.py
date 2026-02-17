#!/usr/bin/env python3
"""
HBL (Habib Bank Limited) — Comprehensive Agent Test
Tests all available analysis agents against the HBL.KA PSX stock.
"""

import time
import json
import os
from datetime import datetime

SYMBOL = "HBL"
SEPARATOR = "=" * 60


def section(title):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def ok(msg):
    print(f"  [OK]  {msg}")


def warn(msg):
    print(f"  [!!]  {msg}")


def info(msg):
    print(f"        {msg}")


# ---------------------------------------------------------------------------
# 1. PRICE STORE — Fetch & cache HBL price history
# ---------------------------------------------------------------------------
section("1. PSXPriceStore — Fetch price history for HBL")
price_store = None
daily_df = None

try:
    from psx_price_store import PSXPriceStore

    price_store = PSXPriceStore()
    t0 = time.time()
    price_store.bulk_update([SYMBOL], days=250)
    price_store.update_weekly_from_daily([SYMBOL])
    elapsed = time.time() - t0

    daily_df = price_store.get_prices(SYMBOL, days=250)
    weekly_df = price_store.get_weekly_prices(SYMBOL, weeks=52)

    if daily_df.empty:
        warn("Daily price data is EMPTY — HBL.KA may be unavailable on Yahoo Finance right now")
        daily_df = None
    else:
        ok(f"Daily data fetched : {len(daily_df)} rows ({elapsed:.1f}s)")
        info(f"Date range         : {daily_df.index[0].date()} → {daily_df.index[-1].date()}")
        latest = daily_df.iloc[-1]
        close_col = "Close" if "Close" in daily_df.columns else daily_df.columns[3]
        vol_col = "Volume" if "Volume" in daily_df.columns else daily_df.columns[4]
        info(f"Latest close       : Rs {latest[close_col]:.2f}  |  Volume: {int(latest[vol_col]):,}")

    if not weekly_df.empty:
        ok(f"Weekly data computed: {len(weekly_df)} rows")
    else:
        warn("Weekly data is empty")

except Exception as e:
    warn(f"PriceStore failed: {e}")
    import traceback; traceback.print_exc()
    price_store = None
    daily_df = None


# ---------------------------------------------------------------------------
# 2. TECHNICAL AGENT — RSI, MACD, Bollinger Bands, multi-timeframe
# ---------------------------------------------------------------------------
section("2. PSXTechnicalAgent — Technical indicators (daily + weekly)")
try:
    if price_store is None:
        warn("Skipped: PriceStore not available")
    else:
        from psx_technical_agent import PSXTechnicalAgent
        from psx_divergence_detector import PSXDivergenceDetector
        from psx_pattern_recognizer import PSXPatternRecognizer

        divergence_detector = PSXDivergenceDetector(
            lookback_days=30, window=5, min_prominence=0.02
        )
        pattern_recognizer = PSXPatternRecognizer(
            hs_lookback_days=60,
            hs_min_pattern_days=20,
            hs_head_prominence=0.03,
            hs_shoulder_tolerance=0.05,
            dt_lookback_days=50,
            dt_peak_tolerance=0.03,
            dt_min_trough_depth=0.05,
            dt_max_pattern_days=40,
        )

        tech_agent = PSXTechnicalAgent(price_store, divergence_detector, pattern_recognizer)

        t0 = time.time()
        mtf = tech_agent.analyze_multi_timeframe(SYMBOL)
        elapsed = time.time() - t0

        ok(f"Multi-timeframe analysis complete ({elapsed:.1f}s)")

        # Daily
        daily = mtf.daily
        info(f"Daily  bias        : {daily.overall_bias.value}  (confidence {daily.confidence*100:.0f}%)")
        rsi   = daily.indicator_values.get("RSI", float("nan"))
        macd  = daily.indicator_values.get("MACD", float("nan"))
        sma50  = daily.indicator_values.get("SMA_50", float("nan"))
        sma200 = daily.indicator_values.get("SMA_200", float("nan"))
        info(f"RSI                : {rsi:.2f}  ({'Overbought >70' if rsi >= 70 else 'Oversold <30' if rsi <= 30 else 'Neutral'})")
        info(f"MACD               : {macd:.4f}")
        info(f"SMA 50 / SMA 200   : {sma50:.2f} / {sma200:.2f}  ({'Golden Cross' if sma50 > sma200 else 'Death Cross'})")

        if daily.signals:
            info(f"Signals ({len(daily.signals)}):")
            for sig in daily.signals[:5]:
                info(f"  {sig.indicator:12s}  {sig.signal_type.value:12s}  strength={sig.strength.value}  val={sig.value:.2f}")

        if daily.divergences:
            ok(f"Divergences detected: {len(daily.divergences)}")
            for div in daily.divergences[:3]:
                info(f"  {div.divergence_type.value}  |  {div.strength}  |  {div.description[:60]}")
        else:
            info("No divergences detected")

        if daily.patterns:
            ok(f"Chart patterns detected: {len(daily.patterns)}")
            for pat in daily.patterns[:3]:
                info(f"  {pat.pattern_type.value}  [{pat.status.value}]  target={pat.target_price}")
        else:
            info("No chart patterns detected")

        # Weekly
        weekly = mtf.weekly
        info(f"Weekly bias        : {weekly.overall_bias.value}  (confidence {weekly.confidence*100:.0f}%)")
        info(f"Confirmation score : {mtf.confirmation_score*100:.0f}%")

        if mtf.aligned_signals:
            info(f"Aligned signals    : {', '.join(mtf.aligned_signals[:4])}")
        if mtf.conflicting_signals:
            info(f"Conflicting        : {', '.join(mtf.conflicting_signals[:4])}")

except Exception as e:
    warn(f"TechnicalAgent failed: {e}")
    import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# 3. FUNDAMENTAL AGENT — P/E, ROE, Dividend, Financial Health
# ---------------------------------------------------------------------------
section("3. PSXFundamentalAgent — Fundamental analysis (quick mode)")
try:
    from psx_fundamental_agent import PSXFundamentalAgent

    fund_agent = PSXFundamentalAgent(cache_ttl_hours=1)
    t0 = time.time()
    score = fund_agent.quick_analysis(SYMBOL)
    elapsed = time.time() - t0

    ok(f"Fundamental analysis complete ({elapsed:.1f}s)")
    info(f"Composite score    : {score.fundamental_score:.1f}/100")
    info(f"Recommendation     : {score.recommendation.value}  ({score.confidence.value} confidence)")
    info(f"Valuation score    : {score.valuation_score:.1f}/100")
    info(f"Health score       : {score.health_score:.1f}/100")
    info(f"Growth score       : {score.growth_score:.1f}/100")
    info(f"Momentum score     : {score.momentum_score:.1f}/100")

    # Valuation metrics
    v = score.valuation
    info(f"P/E ratio          : {v.pe_ratio:.2f}" if v.pe_ratio else "P/E ratio          : N/A")
    info(f"P/B ratio          : {v.pb_ratio:.2f}" if v.pb_ratio else "P/B ratio          : N/A")
    info(f"Dividend yield     : {v.dividend_yield:.1f}%" if v.dividend_yield else "Dividend yield     : N/A")
    info(f"EV/EBITDA          : {v.ev_ebitda:.2f}" if v.ev_ebitda else "EV/EBITDA          : N/A")

    # Health metrics
    h = score.financial_health
    info(f"ROE                : {h.roe:.1f}%" if h.roe else "ROE                : N/A")
    info(f"Debt/Equity        : {h.debt_to_equity:.1f}x" if h.debt_to_equity else "Debt/Equity        : N/A")
    info(f"Current ratio      : {h.current_ratio:.2f}" if h.current_ratio else "Current ratio      : N/A")

    if score.red_flags:
        warn(f"Red flags ({len(score.red_flags)}):")
        for rf in score.red_flags:
            info(f"  [{rf.severity}] {rf.description}")

    if score.catalysts:
        info(f"Catalysts          : {'; '.join(score.catalysts[:3])}")

    if score.upside_pct is not None:
        info(f"Estimated upside   : {score.upside_pct:+.1f}%")

except Exception as e:
    warn(f"FundamentalAgent failed: {e}")
    import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# 4. ANOMALY AGENT — Volume spikes, price gaps, volatility anomalies
# ---------------------------------------------------------------------------
section("4. PSXAnomalyAgent — Anomaly detection")
try:
    from psx_anomaly_agent import PSXAnomalyAgent, DEFAULT_Z_THRESHOLD, DEFAULT_LOOKBACK_DAYS

    anomaly_agent = PSXAnomalyAgent(
        lookback_days=DEFAULT_LOOKBACK_DAYS,
        z_threshold=DEFAULT_Z_THRESHOLD,
        price_store=price_store,
    )

    t0 = time.time()
    report = anomaly_agent.generate_report([SYMBOL])
    elapsed = time.time() - t0

    anomalies = report.get(SYMBOL, [])
    ok(f"Anomaly detection complete ({elapsed:.1f}s)")
    info(f"Anomalies found    : {len(anomalies)}")

    if anomalies:
        for a in anomalies[:6]:
            info(f"  [{a.severity.value:6s}] {a.anomaly_type.value:25s} | z={a.z_score:.2f} | {a.date}")
    else:
        info("No anomalies detected in HBL — normal trading patterns")

except Exception as e:
    warn(f"AnomalyAgent failed: {e}")
    import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# 5. NEWS AGENT — Recent HBL news & sentiment
# ---------------------------------------------------------------------------
section("5. PSXNewsAgent — Recent news & sentiment")
try:
    from psx_news_agent import PSXNewsAgent

    news_agent = PSXNewsAgent()
    t0 = time.time()
    articles = news_agent.fetch_recent_news(hours=72)
    elapsed = time.time() - t0

    ok(f"News fetch complete ({elapsed:.1f}s)")
    info(f"Total articles     : {len(articles)}")

    # Filter for HBL-relevant articles using available fields (title, full_text, summary)
    hbl_articles = [
        a for a in articles
        if "HBL" in a.title.upper() or "HABIB" in a.title.upper()
        or (getattr(a, "full_text", "") and "HBL" in a.full_text.upper())
        or (getattr(a, "summary", "") and "HBL" in a.summary.upper())
        or (getattr(a, "primary_symbol", "") == SYMBOL)
    ]
    info(f"HBL-relevant       : {len(hbl_articles)}")

    if hbl_articles:
        for art in hbl_articles[:5]:
            sentiment = getattr(art, "sentiment_label", None) or "unscored"
            info(f"  [{sentiment:8s}] {art.title[:65]}")
    else:
        info("No HBL-specific articles in last 72h (news feeds may be limited)")

    if articles:
        summary = news_agent.process_articles(articles)
        info(f"Total processed    : {summary.total_fetched} ({summary.new_articles} new, {summary.duplicates} dupes)")
        info(f"Stock / Macro news : {summary.stock_news} / {summary.macro_news}")
        if summary.symbols_mentioned:
            top_symbols = summary.symbols_mentioned[:8]
            info(f"Top symbols        : {', '.join(top_symbols)}")
        if summary.macro_categories:
            info(f"Macro categories   : {', '.join(summary.macro_categories[:5])}")

except Exception as e:
    warn(f"NewsAgent failed: {e}")
    import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# 6. SENTIMENT ANALYZER — Score HBL-related text
# ---------------------------------------------------------------------------
section("6. PSXSentimentAnalyzer — Standalone sentiment check")
try:
    from psx_sentiment_analyzer import PSXSentimentAnalyzer

    analyzer = PSXSentimentAnalyzer()

    samples = [
        "HBL reports strong quarterly profit, earnings beat expectations by 15%",
        "HBL faces regulatory fine, provisioning concerns weigh on outlook",
        "HBL maintains dividend, trading at fair value per sector peers",
    ]

    ok("Sentiment analysis on sample HBL headlines:")
    for text in samples:
        result = analyzer.analyze_text(text)
        # SentimentResult fields: score, label, confidence, scores_breakdown
        info(f"  [{result.label:8s} {result.score:+.3f}  conf={result.confidence:.2f}] {text[:55]}")

except Exception as e:
    warn(f"SentimentAnalyzer failed: {e}")
    import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# 7. DIVERGENCE DETECTOR — Standalone run on HBL data
# ---------------------------------------------------------------------------
section("7. PSXDivergenceDetector — Standalone divergence scan")
try:
    from psx_divergence_detector import PSXDivergenceDetector

    if daily_df is not None and not daily_df.empty:
        detector = PSXDivergenceDetector(lookback_days=30, window=5, min_prominence=0.02)
        t0 = time.time()
        divergences = detector.detect_all_divergences(SYMBOL, daily_df)
        elapsed = time.time() - t0

        ok(f"Divergence scan complete ({elapsed:.1f}s)")
        info(f"Divergences found  : {len(divergences)}")
        for div in divergences[:5]:
            info(f"  {div.divergence_type.value:20s}  {div.strength:6s}  |  {div.description[:55]}")
        if not divergences:
            info("No divergences detected — price and indicators moving in sync")
    else:
        warn("Skipped: no price data available for HBL")

except Exception as e:
    warn(f"DivergenceDetector failed: {e}")
    import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# 8. PATTERN RECOGNIZER — Standalone run on HBL data
# ---------------------------------------------------------------------------
section("8. PSXPatternRecognizer — Chart pattern detection")
try:
    from psx_pattern_recognizer import PSXPatternRecognizer

    if daily_df is not None and not daily_df.empty:
        recognizer = PSXPatternRecognizer(
            hs_lookback_days=60,
            hs_min_pattern_days=20,
            hs_head_prominence=0.03,
            hs_shoulder_tolerance=0.05,
            dt_lookback_days=50,
            dt_peak_tolerance=0.03,
            dt_min_trough_depth=0.05,
            dt_max_pattern_days=40,
        )
        t0 = time.time()
        patterns = recognizer.detect_all_patterns(SYMBOL, daily_df)
        elapsed = time.time() - t0

        ok(f"Pattern recognition complete ({elapsed:.1f}s)")
        info(f"Patterns found     : {len(patterns)}")
        for pat in patterns[:5]:
            target = f"  target=Rs {pat.target_price:.2f}" if pat.target_price else ""
            info(f"  {pat.pattern_type.value:22s}  [{pat.status.value:9s}]{target}")
        if not patterns:
            info("No classic chart patterns detected in current HBL data window")
    else:
        warn("Skipped: no price data available for HBL")

except Exception as e:
    warn(f"PatternRecognizer failed: {e}")
    import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# 9. LIQUIDITY SCREENER — Check HBL liquidity rank
# ---------------------------------------------------------------------------
section("9. PSXLiquidityScreener — HBL liquidity rank")
try:
    cache_file = "psx_liquidity_top100.json"
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            cached = json.load(f)
        stocks = cached.get("stocks", [])
        symbols_in_cache = [s.get("symbol", "") for s in stocks]
        if SYMBOL in symbols_in_cache:
            idx = symbols_in_cache.index(SYMBOL)
            entry = stocks[idx]
            ok(f"HBL found in top-100 liquidity cache (rank #{idx+1})")
            avg_vol = entry.get("avg_volume")
            avg_val = entry.get("avg_value")
            if isinstance(avg_vol, (int, float)):
                info(f"Avg daily volume   : {avg_vol:,.0f} shares")
            if isinstance(avg_val, (int, float)) and avg_val > 0:
                info(f"Avg daily value    : Rs {avg_val/1e6:.1f}M")
        else:
            info(f"HBL not found in top-100 cache ({len(symbols_in_cache)} symbols cached)")
    else:
        info("No cached liquidity data found; skipping network screener call")

except Exception as e:
    warn(f"LiquidityScreener failed: {e}")
    import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# 10. SYMBOL MATCHER — Verify HBL resolves correctly
# ---------------------------------------------------------------------------
section("10. PSXSymbolMatcher — Symbol resolution")
try:
    from psx_symbol_matcher import PSXSymbolMatcher

    matcher = PSXSymbolMatcher()

    # find_mentioned_symbols returns List[Tuple[symbol, confidence]]
    matches = matcher.find_mentioned_symbols("HBL stock showing strength")
    if matches:
        sym, conf = matches[0]
        ok(f"Mention 'HBL stock showing strength' → '{sym}'  (confidence {conf:.2f})")
    else:
        info("No symbols matched for 'HBL stock showing strength'")

    # resolve_company_name resolves full company names
    resolved = matcher.resolve_company_name("Habib Bank")
    info(f"resolve_company_name('Habib Bank') → '{resolved}'")

    resolved2 = matcher.resolve_company_name("Habib Bank Limited")
    info(f"resolve_company_name('Habib Bank Limited') → '{resolved2}'")

except Exception as e:
    warn(f"SymbolMatcher failed: {e}")
    import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# FINAL SUMMARY
# ---------------------------------------------------------------------------
section("SUMMARY — HBL Agent Test Results")
print(f"  Symbol : HBL (Habib Bank Limited — PSX ticker HBL.KA)")
print(f"  Date   : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"  All agents tested above — check [OK] for pass, [!!] for issues.")
print()
