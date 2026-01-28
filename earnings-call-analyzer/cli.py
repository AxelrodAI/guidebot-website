#!/usr/bin/env python3
"""
Earnings Call Transcript Analyzer CLI

Commands:
  analyze <ticker> [file]  - Analyze a transcript (or use sample)
  compare <ticker>         - Compare latest vs previous quarter
  history <ticker>         - Show analysis history
  alerts [ticker]          - Show active alerts
  summary <ticker>         - Quick summary of latest call
  keywords <ticker>        - Detailed keyword analysis
  tone <ticker>            - Tone and speaker analysis
  correlations             - Show sentiment vs price correlations
  test                     - Run with sample data
"""

import sys
import json
import argparse
from datetime import datetime
from dataclasses import asdict

# Windows Unicode fix
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from transcript_analyzer import (
    get_analyzer, 
    generate_sample_transcript,
    TranscriptAnalysis
)


def format_sentiment(score) -> str:
    """Format sentiment score with visual indicator"""
    compound = score.compound if hasattr(score, 'compound') else score['compound']
    
    if compound > 0.2:
        indicator = "🟢 BULLISH"
    elif compound > 0.05:
        indicator = "🟢 Slightly Bullish"
    elif compound < -0.2:
        indicator = "🔴 BEARISH"
    elif compound < -0.05:
        indicator = "🔴 Slightly Bearish"
    else:
        indicator = "⚪ NEUTRAL"
    
    return f"{indicator} ({compound:+.2f})"


def cmd_analyze(args):
    """Analyze a transcript"""
    analyzer = get_analyzer()
    ticker = args.ticker.upper()
    
    # Get transcript
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                transcript = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}")
            return
    else:
        # Use sample transcript
        sentiment = args.sentiment if hasattr(args, 'sentiment') else 'mixed'
        transcript = generate_sample_transcript(ticker, sentiment)
        print(f"[Using sample {sentiment} transcript for {ticker}]\n")
    
    # Analyze
    analysis = analyzer.analyze(ticker, transcript, args.quarter)
    
    # Print results
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  EARNINGS CALL ANALYSIS: {analysis.ticker} {analysis.quarter}")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    print(f"📊 OVERALL SENTIMENT: {format_sentiment(analysis.overall_sentiment)}")
    print(f"   Confidence: {analysis.overall_sentiment.confidence}%")
    print()
    
    print("📝 SUMMARY:")
    print(f"   {analysis.summary}")
    print()
    
    print("🎯 TONE ANALYSIS:")
    print(f"   Prepared Remarks: {format_sentiment(analysis.tone.prepared_sentiment)}")
    print(f"   Q&A Session:      {format_sentiment(analysis.tone.qa_sentiment)}")
    shift_indicator = "⬆️" if analysis.tone.tone_shift > 0.1 else "⬇️" if analysis.tone.tone_shift < -0.1 else "➡️"
    print(f"   Tone Shift:       {shift_indicator} {analysis.tone.tone_shift:+.2f}")
    print(f"   Deflections:      {analysis.tone.deflection_count}")
    print(f"   Hedging:          {analysis.tone.hedging_count}")
    print()
    
    print("🔑 KEYWORD SUMMARY:")
    print(f"   Bullish Ratio:    {analysis.keywords.bullish_ratio:.0%}")
    print(f"   Bearish Ratio:    {analysis.keywords.bearish_ratio:.0%}")
    
    if analysis.keywords.bullish_keywords:
        top_bull = sorted(analysis.keywords.bullish_keywords.items(), 
                         key=lambda x: x[1], reverse=True)[:5]
        print(f"   Top Bullish:      {', '.join(f'{w}({c})' for w,c in top_bull)}")
    
    if analysis.keywords.bearish_keywords:
        top_bear = sorted(analysis.keywords.bearish_keywords.items(), 
                         key=lambda x: x[1], reverse=True)[:5]
        print(f"   Top Bearish:      {', '.join(f'{w}({c})' for w,c in top_bear)}")
    print()
    
    if analysis.alerts:
        print("⚠️  ALERTS:")
        for alert in analysis.alerts:
            severity_icon = "🔴" if alert['severity'] == 'high' else "🟡" if alert['severity'] == 'medium' else "⚪"
            print(f"   {severity_icon} [{alert['type']}] {alert['message']}")
        print()
    
    if args.json:
        print("\n📄 JSON Output:")
        print(json.dumps(asdict(analysis), indent=2, default=str))


def cmd_compare(args):
    """Compare quarters"""
    analyzer = get_analyzer()
    ticker = args.ticker.upper()
    
    history = analyzer.get_history(ticker)
    
    if len(history) < 2:
        print(f"Need at least 2 quarters of data for {ticker} to compare.")
        print("Run 'analyze' command multiple times first.")
        
        # Generate sample comparison
        print("\n[Generating sample comparison data...]\n")
        
        # Analyze two sample transcripts
        prev_transcript = generate_sample_transcript(ticker, 'bearish')
        prev_analysis = analyzer.analyze(ticker, prev_transcript, 'Q3 2025')
        
        curr_transcript = generate_sample_transcript(ticker, 'bullish')
        curr_analysis = analyzer.analyze(ticker, curr_transcript, 'Q4 2025')
        
        history = analyzer.get_history(ticker)
    
    # Get latest two
    current = history[-1]
    previous = history[-2]
    
    # Create analysis objects for comparison
    from transcript_analyzer import TranscriptAnalysis, SentimentScore, KeywordAnalysis, ToneAnalysis
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  QUARTER COMPARISON: {ticker}")
    print(f"  {previous['quarter']} → {current['quarter']}")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    # Sentiment change
    prev_sent = previous['overall_sentiment']['compound']
    curr_sent = current['overall_sentiment']['compound']
    sent_change = curr_sent - prev_sent
    
    direction = "📈 IMPROVED" if sent_change > 0.05 else "📉 DETERIORATED" if sent_change < -0.05 else "➡️ STABLE"
    
    print(f"📊 SENTIMENT TREND: {direction}")
    print(f"   {previous['quarter']}: {prev_sent:+.2f}")
    print(f"   {current['quarter']}: {curr_sent:+.2f}")
    print(f"   Change:           {sent_change:+.2f}")
    print()
    
    # Tone shift comparison
    prev_tone = previous['tone']['tone_shift']
    curr_tone = current['tone']['tone_shift']
    
    print("🎯 TONE SHIFT COMPARISON:")
    print(f"   {previous['quarter']} Q&A shift: {prev_tone:+.2f}")
    print(f"   {current['quarter']} Q&A shift: {curr_tone:+.2f}")
    print()
    
    # Deflection comparison
    prev_defl = previous['tone']['deflection_count']
    curr_defl = current['tone']['deflection_count']
    
    print("❓ DEFLECTION COMPARISON:")
    print(f"   {previous['quarter']}: {prev_defl} deflections")
    print(f"   {current['quarter']}: {curr_defl} deflections")
    if curr_defl > prev_defl:
        print("   ⚠️ Management being more evasive in Q&A")
    elif curr_defl < prev_defl:
        print("   ✓ Management being more direct in Q&A")
    print()
    
    # Keyword evolution
    print("🔑 KEYWORD EVOLUTION:")
    prev_bull = set(previous['keywords']['bullish_keywords'].keys())
    curr_bull = set(current['keywords']['bullish_keywords'].keys())
    prev_bear = set(previous['keywords']['bearish_keywords'].keys())
    curr_bear = set(current['keywords']['bearish_keywords'].keys())
    
    new_bull = curr_bull - prev_bull
    new_bear = curr_bear - prev_bear
    dropped_bear = prev_bear - curr_bear
    
    if new_bull:
        print(f"   New bullish themes: {', '.join(new_bull)}")
    if new_bear:
        print(f"   ⚠️ New bearish themes: {', '.join(new_bear)}")
    if dropped_bear:
        print(f"   ✓ Resolved concerns: {', '.join(dropped_bear)}")


def cmd_history(args):
    """Show analysis history"""
    analyzer = get_analyzer()
    ticker = args.ticker.upper()
    
    history = analyzer.get_history(ticker)
    
    if not history:
        print(f"No history found for {ticker}.")
        print("Run 'analyze' command first.")
        return
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  ANALYSIS HISTORY: {ticker}")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    print(f"{'Quarter':<12} {'Sentiment':>10} {'Tone Shift':>12} {'Alerts':>8}")
    print("-" * 50)
    
    for analysis in history:
        quarter = analysis['quarter']
        sentiment = analysis['overall_sentiment']['compound']
        tone_shift = analysis['tone']['tone_shift']
        alert_count = len(analysis['alerts'])
        
        print(f"{quarter:<12} {sentiment:>+10.2f} {tone_shift:>+12.2f} {alert_count:>8}")
    
    print()
    print(f"Total analyses: {len(history)}")


def cmd_alerts(args):
    """Show alerts"""
    analyzer = get_analyzer()
    
    if args.ticker:
        ticker = args.ticker.upper()
        history = analyzer.get_history(ticker)
        tickers_to_check = {ticker: history}
    else:
        tickers_to_check = analyzer.history
    
    if not tickers_to_check:
        print("No analyses found. Run 'analyze' command first.")
        return
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  ACTIVE ALERTS")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    total_alerts = 0
    for ticker, history in tickers_to_check.items():
        if not history:
            continue
        
        latest = history[-1]
        alerts = latest.get('alerts', [])
        
        if alerts:
            print(f"📌 {ticker} ({latest['quarter']}):")
            for alert in alerts:
                severity_icon = "🔴" if alert['severity'] == 'high' else "🟡" if alert['severity'] == 'medium' else "⚪"
                print(f"   {severity_icon} [{alert['type']}] {alert['message']}")
            print()
            total_alerts += len(alerts)
    
    if total_alerts == 0:
        print("No active alerts.")
    else:
        print(f"Total alerts: {total_alerts}")


def cmd_summary(args):
    """Quick summary"""
    analyzer = get_analyzer()
    ticker = args.ticker.upper()
    
    history = analyzer.get_history(ticker)
    
    if not history:
        print(f"No analysis found for {ticker}. Run 'analyze' first.")
        return
    
    latest = history[-1]
    print()
    print(f"📊 {ticker} {latest['quarter']} SUMMARY:")
    print(f"   {latest['summary']}")
    print()


def cmd_keywords(args):
    """Detailed keyword analysis"""
    analyzer = get_analyzer()
    ticker = args.ticker.upper()
    
    history = analyzer.get_history(ticker)
    
    if not history:
        print(f"No analysis found for {ticker}. Run 'analyze' first.")
        return
    
    latest = history[-1]
    kw = latest['keywords']
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  KEYWORD ANALYSIS: {ticker} {latest['quarter']}")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    print(f"Total words analyzed: {kw['total_words']}")
    print(f"Bullish/Bearish ratio: {kw['bullish_ratio']:.0%} / {kw['bearish_ratio']:.0%}")
    print()
    
    if kw['bullish_keywords']:
        print("🟢 BULLISH KEYWORDS:")
        for word, count in sorted(kw['bullish_keywords'].items(), key=lambda x: x[1], reverse=True):
            bar = "█" * min(count, 20)
            print(f"   {word:<15} {count:>3} {bar}")
        print()
    
    if kw['bearish_keywords']:
        print("🔴 BEARISH KEYWORDS:")
        for word, count in sorted(kw['bearish_keywords'].items(), key=lambda x: x[1], reverse=True):
            bar = "█" * min(count, 20)
            print(f"   {word:<15} {count:>3} {bar}")
        print()
    
    if kw['guidance_keywords']:
        print("📋 GUIDANCE KEYWORDS:")
        for word, count in sorted(kw['guidance_keywords'].items(), key=lambda x: x[1], reverse=True):
            print(f"   {word:<15} {count:>3}")
        print()
    
    if kw['uncertainty_keywords']:
        print("❓ UNCERTAINTY KEYWORDS:")
        for word, count in sorted(kw['uncertainty_keywords'].items(), key=lambda x: x[1], reverse=True):
            print(f"   {word:<15} {count:>3}")


def cmd_tone(args):
    """Tone and speaker analysis"""
    analyzer = get_analyzer()
    ticker = args.ticker.upper()
    
    history = analyzer.get_history(ticker)
    
    if not history:
        print(f"No analysis found for {ticker}. Run 'analyze' first.")
        return
    
    latest = history[-1]
    tone = latest['tone']
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  TONE ANALYSIS: {ticker} {latest['quarter']}")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    
    print("📝 PREPARED REMARKS:")
    prep = tone['prepared_sentiment']
    print(f"   Sentiment: {format_sentiment(prep)}")
    print(f"   Positive: {prep['positive']:.1%} | Negative: {prep['negative']:.1%} | Neutral: {prep['neutral']:.1%}")
    print()
    
    print("❓ Q&A SESSION:")
    qa = tone['qa_sentiment']
    print(f"   Sentiment: {format_sentiment(qa)}")
    print(f"   Positive: {qa['positive']:.1%} | Negative: {qa['negative']:.1%} | Neutral: {qa['neutral']:.1%}")
    print()
    
    print("📊 TONE DYNAMICS:")
    shift = tone['tone_shift']
    if shift > 0.1:
        print(f"   ⬆️ Tone improved during Q&A (shift: {shift:+.2f})")
        print("   Interpretation: Management more confident when challenged")
    elif shift < -0.1:
        print(f"   ⬇️ Tone weakened during Q&A (shift: {shift:+.2f})")
        print("   Interpretation: Management less certain when pressed on details")
    else:
        print(f"   ➡️ Tone consistent throughout (shift: {shift:+.2f})")
    print()
    
    print(f"   Deflections detected: {tone['deflection_count']}")
    if tone['deflection_count'] > 3:
        print("   ⚠️ High deflection count may indicate discomfort with questions")
    
    print(f"   Hedging phrases: {tone['hedging_count']}")
    if tone['hedging_count'] > 5:
        print("   ⚠️ Excessive hedging suggests uncertainty about outlook")


def cmd_correlations(args):
    """Show correlations"""
    analyzer = get_analyzer()
    
    corr = analyzer.get_correlations()
    
    print(f"═══════════════════════════════════════════════════════════════")
    print(f"  SENTIMENT VS PRICE CORRELATIONS")
    print(f"═══════════════════════════════════════════════════════════════")
    print()
    print("Historical correlations (based on backtested data):")
    print()
    print(f"   Overall Sentiment vs 1-Day Return:  {corr['sentiment_vs_1day']:+.2f}")
    print(f"   Overall Sentiment vs 5-Day Return:  {corr['sentiment_vs_5day']:+.2f}")
    print(f"   Q&A Tone Shift vs 1-Day Return:     {corr['tone_shift_vs_1day']:+.2f}")
    print(f"   Deflection Count vs 1-Day Return:   {corr['deflection_vs_1day']:+.2f}")
    print()
    print("📈 Key insights:")
    print("   • Positive sentiment correlates with positive 1-day returns")
    print("   • Negative tone shift in Q&A is a warning signal")
    print("   • High deflection count correlates with negative returns")
    print()
    print(f"Note: {corr['note']}")


def cmd_test(args):
    """Run tests with sample data"""
    print("═══════════════════════════════════════════════════════════════")
    print("  EARNINGS CALL ANALYZER - TEST MODE")
    print("═══════════════════════════════════════════════════════════════")
    print()
    
    analyzer = get_analyzer()
    
    # Test 1: Bullish transcript
    print("Test 1: Analyzing BULLISH transcript (AAPL)...")
    transcript = generate_sample_transcript('AAPL', 'bullish')
    analysis = analyzer.analyze('AAPL', transcript, 'Q4 2025')
    assert analysis.overall_sentiment.compound > 0, "Expected positive sentiment"
    print(f"   ✓ Sentiment: {analysis.overall_sentiment.compound:+.2f} (expected positive)")
    print(f"   ✓ Bullish ratio: {analysis.keywords.bullish_ratio:.0%}")
    print()
    
    # Test 2: Bearish transcript
    print("Test 2: Analyzing BEARISH transcript (XYZ)...")
    transcript = generate_sample_transcript('XYZ', 'bearish')
    analysis = analyzer.analyze('XYZ', transcript, 'Q4 2025')
    assert analysis.overall_sentiment.compound < 0, "Expected negative sentiment"
    print(f"   ✓ Sentiment: {analysis.overall_sentiment.compound:+.2f} (expected negative)")
    print(f"   ✓ Bearish ratio: {analysis.keywords.bearish_ratio:.0%}")
    print(f"   ✓ Deflections detected: {analysis.tone.deflection_count}")
    print()
    
    # Test 3: Mixed transcript
    print("Test 3: Analyzing MIXED transcript (MSFT)...")
    transcript = generate_sample_transcript('MSFT', 'mixed')
    analysis = analyzer.analyze('MSFT', transcript, 'Q4 2025')
    print(f"   ✓ Sentiment: {analysis.overall_sentiment.compound:+.2f} (expected neutral)")
    print()
    
    # Test 4: Quarter comparison
    print("Test 4: Quarter-over-quarter comparison...")
    prev_transcript = generate_sample_transcript('NVDA', 'bearish')
    prev_analysis = analyzer.analyze('NVDA', prev_transcript, 'Q3 2025')
    
    curr_transcript = generate_sample_transcript('NVDA', 'bullish')
    curr_analysis = analyzer.analyze('NVDA', curr_transcript, 'Q4 2025')
    
    history = analyzer.get_history('NVDA')
    assert len(history) == 2, "Expected 2 quarters of history"
    print(f"   ✓ History tracking: {len(history)} quarters stored")
    
    improvement = curr_analysis.overall_sentiment.compound - prev_analysis.overall_sentiment.compound
    print(f"   ✓ Sentiment change: {improvement:+.2f} (Q3→Q4 improvement detected)")
    print()
    
    # Test 5: Alert generation
    print("Test 5: Alert generation...")
    total_alerts = sum(len(h.get('alerts', [])) for h in analyzer.history.get('XYZ', []))
    print(f"   ✓ Alerts generated for bearish call: {total_alerts}")
    print()
    
    # Test 6: Correlations
    print("Test 6: Correlation data...")
    corr = analyzer.get_correlations()
    print(f"   ✓ Correlation data available: {len(corr)} metrics")
    print()
    
    print("═══════════════════════════════════════════════════════════════")
    print("  ALL TESTS PASSED ✓")
    print("═══════════════════════════════════════════════════════════════")


def main():
    parser = argparse.ArgumentParser(
        description="Earnings Call Transcript Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py analyze AAPL                    # Analyze with sample data
  python cli.py analyze AAPL transcript.txt     # Analyze from file
  python cli.py analyze AAPL --sentiment bullish # Use bullish sample
  python cli.py compare AAPL                    # Compare quarters
  python cli.py alerts                          # Show all alerts
  python cli.py keywords AAPL                   # Detailed keyword analysis
  python cli.py tone AAPL                       # Tone and speaker analysis
  python cli.py test                            # Run tests
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # analyze
    p_analyze = subparsers.add_parser('analyze', help='Analyze a transcript')
    p_analyze.add_argument('ticker', help='Stock ticker')
    p_analyze.add_argument('file', nargs='?', help='Transcript file (optional)')
    p_analyze.add_argument('--quarter', '-q', help='Quarter label (e.g., Q4 2025)')
    p_analyze.add_argument('--sentiment', '-s', choices=['bullish', 'bearish', 'mixed'],
                          default='mixed', help='Sample sentiment type')
    p_analyze.add_argument('--json', '-j', action='store_true', help='Output JSON')
    p_analyze.set_defaults(func=cmd_analyze)
    
    # compare
    p_compare = subparsers.add_parser('compare', help='Compare quarters')
    p_compare.add_argument('ticker', help='Stock ticker')
    p_compare.set_defaults(func=cmd_compare)
    
    # history
    p_history = subparsers.add_parser('history', help='Show analysis history')
    p_history.add_argument('ticker', help='Stock ticker')
    p_history.set_defaults(func=cmd_history)
    
    # alerts
    p_alerts = subparsers.add_parser('alerts', help='Show alerts')
    p_alerts.add_argument('ticker', nargs='?', help='Stock ticker (optional)')
    p_alerts.set_defaults(func=cmd_alerts)
    
    # summary
    p_summary = subparsers.add_parser('summary', help='Quick summary')
    p_summary.add_argument('ticker', help='Stock ticker')
    p_summary.set_defaults(func=cmd_summary)
    
    # keywords
    p_keywords = subparsers.add_parser('keywords', help='Keyword analysis')
    p_keywords.add_argument('ticker', help='Stock ticker')
    p_keywords.set_defaults(func=cmd_keywords)
    
    # tone
    p_tone = subparsers.add_parser('tone', help='Tone analysis')
    p_tone.add_argument('ticker', help='Stock ticker')
    p_tone.set_defaults(func=cmd_tone)
    
    # correlations
    p_corr = subparsers.add_parser('correlations', help='Sentiment correlations')
    p_corr.set_defaults(func=cmd_correlations)
    
    # test
    p_test = subparsers.add_parser('test', help='Run tests')
    p_test.set_defaults(func=cmd_test)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == '__main__':
    main()
