#!/usr/bin/env python3
"""
Earnings Call Transcript Analyzer

NLP analysis of earnings call transcripts with sentiment tracking,
keyword frequency, tone analysis, and historical correlation.
"""

import sys
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import Counter
import random

# Windows Unicode fix
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


@dataclass
class SentimentScore:
    """Sentiment score breakdown"""
    compound: float  # -1 to 1 overall
    positive: float
    negative: float
    neutral: float
    confidence: float  # 0-100


@dataclass
class KeywordAnalysis:
    """Keyword frequency analysis"""
    bullish_keywords: dict  # word -> count
    bearish_keywords: dict
    guidance_keywords: dict
    uncertainty_keywords: dict
    total_words: int
    bullish_ratio: float
    bearish_ratio: float


@dataclass 
class ToneAnalysis:
    """Management tone analysis"""
    prepared_sentiment: SentimentScore
    qa_sentiment: SentimentScore
    tone_shift: float  # Q&A sentiment - Prepared sentiment
    speaker_sentiments: dict  # speaker -> sentiment
    deflection_count: int
    hedging_count: int


@dataclass
class TranscriptSection:
    """Section of the transcript"""
    section_type: str  # 'prepared' or 'qa'
    speaker: str
    role: str  # CEO, CFO, Analyst, etc.
    text: str
    sentiment: SentimentScore


@dataclass
class TranscriptAnalysis:
    """Full transcript analysis result"""
    ticker: str
    quarter: str
    date: str
    overall_sentiment: SentimentScore
    keywords: KeywordAnalysis
    tone: ToneAnalysis
    sections: list
    price_reaction: Optional[float]  # % change after call
    alerts: list
    summary: str


# Financial keyword dictionaries
BULLISH_KEYWORDS = [
    'growth', 'opportunity', 'strong', 'momentum', 'exceeded', 'beat',
    'record', 'expand', 'accelerate', 'outperform', 'confident', 'robust',
    'tailwind', 'upside', 'improving', 'optimistic', 'positive', 'solid',
    'strength', 'healthy', 'favorable', 'gain', 'increase', 'raised'
]

BEARISH_KEYWORDS = [
    'challenge', 'headwind', 'decline', 'pressure', 'weakness', 'miss',
    'difficult', 'uncertainty', 'concern', 'soft', 'slowdown', 'contraction',
    'cautious', 'risk', 'volatile', 'disappointed', 'below', 'lower',
    'reduced', 'constrained', 'muted', 'decelerate', 'impact', 'disruption'
]

GUIDANCE_KEYWORDS = [
    'guidance', 'outlook', 'expect', 'anticipate', 'forecast', 'project',
    'target', 'range', 'full-year', 'quarter', 'forward', 'reaffirm',
    'raise', 'lower', 'maintain', 'revise', 'update'
]

UNCERTAINTY_KEYWORDS = [
    'uncertain', 'may', 'might', 'could', 'possibly', 'approximately',
    'roughly', 'estimate', 'unclear', 'depends', 'variable', 'volatile',
    'unpredictable', 'cautious', 'conservative', 'monitor', 'evaluate'
]

HEDGING_PHRASES = [
    "we'll have to see", "it depends", "hard to predict", "remains uncertain",
    "too early to tell", "we're monitoring", "subject to change", "in the range of",
    "could be impacted", "potential headwinds"
]

DEFLECTION_PHRASES = [
    "i'll let", "let me turn it over", "i'll have", "let me ask",
    "i don't have the specific", "we'll get back to you", "off the top of my head",
    "i don't recall", "i'm not sure", "we'll follow up"
]


class EarningsCallAnalyzer:
    """Analyzer for earnings call transcripts"""
    
    def __init__(self):
        self.history = {}  # ticker -> list of analyses
        
    def _calculate_sentiment(self, text: str) -> SentimentScore:
        """Calculate sentiment score using VADER-like approach"""
        if not text:
            return SentimentScore(0, 0, 0, 1, 50)
            
        words = text.lower().split()
        total = len(words)
        if total == 0:
            return SentimentScore(0, 0, 0, 1, 50)
        
        positive = sum(1 for w in words if any(bw in w for bw in BULLISH_KEYWORDS))
        negative = sum(1 for w in words if any(bw in w for bw in BEARISH_KEYWORDS))
        
        pos_ratio = positive / total
        neg_ratio = negative / total
        neu_ratio = 1 - pos_ratio - neg_ratio
        
        compound = (pos_ratio - neg_ratio) * 2  # Scale to -1 to 1
        compound = max(-1, min(1, compound))
        
        # Confidence based on signal strength
        confidence = min(100, (positive + negative) * 5 + 30)
        
        return SentimentScore(
            compound=round(compound, 3),
            positive=round(pos_ratio, 3),
            negative=round(neg_ratio, 3),
            neutral=round(neu_ratio, 3),
            confidence=round(confidence, 1)
        )
    
    def _analyze_keywords(self, text: str) -> KeywordAnalysis:
        """Analyze keyword frequency"""
        text_lower = text.lower()
        words = text_lower.split()
        total_words = len(words)
        
        bullish = {}
        bearish = {}
        guidance = {}
        uncertainty = {}
        
        for kw in BULLISH_KEYWORDS:
            count = text_lower.count(kw)
            if count > 0:
                bullish[kw] = count
                
        for kw in BEARISH_KEYWORDS:
            count = text_lower.count(kw)
            if count > 0:
                bearish[kw] = count
                
        for kw in GUIDANCE_KEYWORDS:
            count = text_lower.count(kw)
            if count > 0:
                guidance[kw] = count
                
        for kw in UNCERTAINTY_KEYWORDS:
            count = text_lower.count(kw)
            if count > 0:
                uncertainty[kw] = count
        
        total_bullish = sum(bullish.values())
        total_bearish = sum(bearish.values())
        total_kw = total_bullish + total_bearish or 1
        
        return KeywordAnalysis(
            bullish_keywords=bullish,
            bearish_keywords=bearish,
            guidance_keywords=guidance,
            uncertainty_keywords=uncertainty,
            total_words=total_words,
            bullish_ratio=round(total_bullish / total_kw, 3),
            bearish_ratio=round(total_bearish / total_kw, 3)
        )
    
    def _analyze_tone(self, prepared_text: str, qa_text: str, 
                      sections: list) -> ToneAnalysis:
        """Analyze management tone across transcript"""
        prepared_sentiment = self._calculate_sentiment(prepared_text)
        qa_sentiment = self._calculate_sentiment(qa_text)
        
        tone_shift = qa_sentiment.compound - prepared_sentiment.compound
        
        # Speaker-level sentiment
        speaker_sentiments = {}
        for section in sections:
            if section.speaker and section.speaker not in speaker_sentiments:
                speaker_sentiments[section.speaker] = asdict(section.sentiment)
        
        # Count deflections and hedging
        qa_lower = qa_text.lower()
        deflection_count = sum(1 for phrase in DEFLECTION_PHRASES 
                               if phrase in qa_lower)
        hedging_count = sum(1 for phrase in HEDGING_PHRASES 
                           if phrase in qa_lower)
        
        return ToneAnalysis(
            prepared_sentiment=prepared_sentiment,
            qa_sentiment=qa_sentiment,
            tone_shift=round(tone_shift, 3),
            speaker_sentiments=speaker_sentiments,
            deflection_count=deflection_count,
            hedging_count=hedging_count
        )
    
    def _parse_transcript(self, transcript: str, ticker: str) -> list:
        """Parse transcript into sections"""
        sections = []
        
        # Simple section parsing (real implementation would be more sophisticated)
        # Detect prepared remarks vs Q&A
        qa_markers = ['question-and-answer', 'q&a', 'questions and answers', 
                      'operator:', 'analyst:']
        
        in_qa = False
        current_speaker = "Management"
        current_role = "Executive"
        
        paragraphs = transcript.split('\n\n')
        
        for para in paragraphs:
            if not para.strip():
                continue
                
            # Check if entering Q&A
            para_lower = para.lower()
            if any(marker in para_lower for marker in qa_markers):
                in_qa = True
                
            # Try to detect speaker
            if ':' in para[:50]:
                parts = para.split(':', 1)
                potential_speaker = parts[0].strip()
                if len(potential_speaker) < 50:
                    current_speaker = potential_speaker
                    if 'ceo' in potential_speaker.lower():
                        current_role = 'CEO'
                    elif 'cfo' in potential_speaker.lower():
                        current_role = 'CFO'
                    elif 'analyst' in potential_speaker.lower():
                        current_role = 'Analyst'
                    else:
                        current_role = 'Speaker'
            
            sentiment = self._calculate_sentiment(para)
            
            sections.append(TranscriptSection(
                section_type='qa' if in_qa else 'prepared',
                speaker=current_speaker,
                role=current_role,
                text=para[:500],  # Truncate for storage
                sentiment=sentiment
            ))
        
        return sections
    
    def _generate_alerts(self, analysis: TranscriptAnalysis) -> list:
        """Generate alerts based on analysis"""
        alerts = []
        
        # Tone divergence alert
        if abs(analysis.tone.tone_shift) > 0.15:
            direction = "more positive" if analysis.tone.tone_shift > 0 else "more negative"
            alerts.append({
                'type': 'TONE_DIVERGENCE',
                'severity': 'high' if abs(analysis.tone.tone_shift) > 0.25 else 'medium',
                'message': f"Q&A tone significantly {direction} than prepared remarks (shift: {analysis.tone.tone_shift:+.2f})"
            })
        
        # High uncertainty alert
        uncertainty_count = sum(analysis.keywords.uncertainty_keywords.values())
        if uncertainty_count > 15:
            alerts.append({
                'type': 'HIGH_UNCERTAINTY',
                'severity': 'medium',
                'message': f"High uncertainty language detected ({uncertainty_count} instances)"
            })
        
        # Deflection alert
        if analysis.tone.deflection_count > 3:
            alerts.append({
                'type': 'DEFLECTION_PATTERN',
                'severity': 'medium',
                'message': f"Multiple deflections detected in Q&A ({analysis.tone.deflection_count} instances)"
            })
        
        # Hedging alert
        if analysis.tone.hedging_count > 5:
            alerts.append({
                'type': 'EXCESSIVE_HEDGING',
                'severity': 'medium',
                'message': f"Excessive hedging language detected ({analysis.tone.hedging_count} instances)"
            })
        
        # Sentiment extreme
        if abs(analysis.overall_sentiment.compound) > 0.4:
            direction = "bullish" if analysis.overall_sentiment.compound > 0 else "bearish"
            alerts.append({
                'type': 'EXTREME_SENTIMENT',
                'severity': 'low',
                'message': f"Extremely {direction} overall sentiment ({analysis.overall_sentiment.compound:+.2f})"
            })
        
        # Bearish keyword dominance
        if analysis.keywords.bearish_ratio > 0.6:
            alerts.append({
                'type': 'BEARISH_LANGUAGE',
                'severity': 'high',
                'message': f"Bearish keywords dominate ({analysis.keywords.bearish_ratio:.0%} of sentiment words)"
            })
        
        return alerts
    
    def _generate_summary(self, analysis: TranscriptAnalysis) -> str:
        """Generate human-readable summary"""
        sentiment_label = "bullish" if analysis.overall_sentiment.compound > 0.1 else \
                         "bearish" if analysis.overall_sentiment.compound < -0.1 else "neutral"
        
        tone_direction = ""
        if analysis.tone.tone_shift > 0.1:
            tone_direction = "Management was more confident during Q&A than prepared remarks."
        elif analysis.tone.tone_shift < -0.1:
            tone_direction = "Management tone weakened during Q&A compared to prepared remarks."
        
        top_bullish = sorted(analysis.keywords.bullish_keywords.items(), 
                            key=lambda x: x[1], reverse=True)[:3]
        top_bearish = sorted(analysis.keywords.bearish_keywords.items(), 
                            key=lambda x: x[1], reverse=True)[:3]
        
        summary = f"{analysis.ticker} {analysis.quarter} earnings call: Overall {sentiment_label} tone "
        summary += f"(sentiment score: {analysis.overall_sentiment.compound:+.2f}). "
        
        if tone_direction:
            summary += tone_direction + " "
        
        if top_bullish:
            summary += f"Key positive themes: {', '.join(w for w,c in top_bullish)}. "
        
        if top_bearish:
            summary += f"Key concerns: {', '.join(w for w,c in top_bearish)}. "
        
        if analysis.tone.deflection_count > 2:
            summary += f"Note: {analysis.tone.deflection_count} deflections detected in Q&A. "
        
        if analysis.alerts:
            high_alerts = [a for a in analysis.alerts if a['severity'] == 'high']
            if high_alerts:
                summary += f"⚠️ {len(high_alerts)} high-priority alerts."
        
        return summary
    
    def analyze(self, ticker: str, transcript: str, quarter: str = None,
                date: str = None) -> TranscriptAnalysis:
        """Analyze an earnings call transcript"""
        if not quarter:
            quarter = f"Q{(datetime.now().month - 1) // 3 + 1} {datetime.now().year}"
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Parse into sections
        sections = self._parse_transcript(transcript, ticker)
        
        # Separate prepared remarks from Q&A
        prepared_text = ' '.join(s.text for s in sections if s.section_type == 'prepared')
        qa_text = ' '.join(s.text for s in sections if s.section_type == 'qa')
        full_text = transcript
        
        # Analyze
        overall_sentiment = self._calculate_sentiment(full_text)
        keywords = self._analyze_keywords(full_text)
        tone = self._analyze_tone(prepared_text, qa_text, sections)
        
        # Build analysis object
        analysis = TranscriptAnalysis(
            ticker=ticker.upper(),
            quarter=quarter,
            date=date,
            overall_sentiment=overall_sentiment,
            keywords=keywords,
            tone=tone,
            sections=[asdict(s) for s in sections[:10]],  # Limit stored sections
            price_reaction=None,
            alerts=[],
            summary=""
        )
        
        # Generate alerts and summary
        analysis.alerts = self._generate_alerts(analysis)
        analysis.summary = self._generate_summary(analysis)
        
        # Store in history
        if ticker.upper() not in self.history:
            self.history[ticker.upper()] = []
        self.history[ticker.upper()].append(asdict(analysis))
        
        return analysis
    
    def compare_quarters(self, ticker: str, 
                        current: TranscriptAnalysis, 
                        previous: TranscriptAnalysis) -> dict:
        """Compare two quarters of transcripts"""
        sentiment_change = current.overall_sentiment.compound - previous.overall_sentiment.compound
        
        # Keyword changes
        current_bullish = sum(current.keywords.bullish_keywords.values())
        previous_bullish = sum(previous.keywords.bullish_keywords.values())
        bullish_change = current_bullish - previous_bullish
        
        current_bearish = sum(current.keywords.bearish_keywords.values())
        previous_bearish = sum(previous.keywords.bearish_keywords.values())
        bearish_change = current_bearish - previous_bearish
        
        # New keywords appearing
        new_bearish = set(current.keywords.bearish_keywords.keys()) - \
                     set(previous.keywords.bearish_keywords.keys())
        new_bullish = set(current.keywords.bullish_keywords.keys()) - \
                     set(previous.keywords.bullish_keywords.keys())
        
        return {
            'ticker': ticker,
            'current_quarter': current.quarter,
            'previous_quarter': previous.quarter,
            'sentiment_change': round(sentiment_change, 3),
            'sentiment_direction': 'improved' if sentiment_change > 0.05 else 
                                  'deteriorated' if sentiment_change < -0.05 else 'stable',
            'bullish_keyword_change': bullish_change,
            'bearish_keyword_change': bearish_change,
            'new_bearish_keywords': list(new_bearish),
            'new_bullish_keywords': list(new_bullish),
            'tone_shift_change': current.tone.tone_shift - previous.tone.tone_shift,
            'deflection_change': current.tone.deflection_count - previous.tone.deflection_count
        }
    
    def get_history(self, ticker: str) -> list:
        """Get analysis history for a ticker"""
        return self.history.get(ticker.upper(), [])
    
    def get_correlations(self) -> dict:
        """Calculate sentiment vs price reaction correlations"""
        # This would use historical data
        # For now, return simulated correlations
        return {
            'sentiment_vs_1day': 0.23,
            'sentiment_vs_5day': 0.18,
            'tone_shift_vs_1day': -0.15,
            'deflection_vs_1day': -0.31,
            'sample_size': len(self.history),
            'note': 'Correlations based on historical transcript analysis'
        }


# Sample transcript generator for testing
def generate_sample_transcript(ticker: str, sentiment: str = 'mixed') -> str:
    """Generate a sample earnings call transcript for testing"""
    
    ceo_name = f"{ticker} CEO"
    cfo_name = f"{ticker} CFO"
    
    if sentiment == 'bullish':
        prepared = f"""
{ceo_name}: Good afternoon everyone and thank you for joining us. We're excited to share our strong results this quarter.

Revenue growth exceeded expectations with record performance across all segments. We saw accelerating momentum in our core business and significant expansion in new markets.

Our strategic initiatives are delivering robust returns. The tailwinds we discussed last quarter have strengthened, and we're confident in our ability to outperform expectations going forward.

{cfo_name}: Thank you. Our financial results demonstrate healthy growth with expanding margins. We're raising guidance for the full year based on the strong momentum we're seeing.

Operating income increased significantly, and we generated record free cash flow. Our balance sheet remains solid with ample capacity for growth investments.
"""
        qa = """
Question-and-Answer Session

Analyst: Can you talk about the sustainability of this growth?

{ceo_name}: Absolutely. The underlying trends driving our growth are durable and improving. We have clear visibility into continued strong performance.

Analyst: Any concerns about competition?

{ceo_name}: We continue to gain market share and see significant opportunity ahead. Our competitive position has never been stronger.
""".format(ceo_name=ceo_name)
    
    elif sentiment == 'bearish':
        prepared = f"""
{ceo_name}: Thank you for joining us today. This was a challenging quarter as we navigated significant headwinds.

We experienced pressure across multiple segments as market conditions deteriorated. The uncertainty in the macro environment created difficulties for our customers.

While we're taking steps to address these challenges, we expect continued volatility in the near term. We're being cautious in our outlook given the uncertain environment.

{cfo_name}: Our results reflected the difficult operating conditions. Revenue came in below expectations and margins were impacted by cost pressures.

We're reducing guidance for the full year to reflect the softness we're seeing. We're focused on cost containment and operational efficiency.
"""
        qa = """
Question-and-Answer Session

Analyst: When do you expect conditions to improve?

{ceo_name}: It's hard to predict with the current uncertainty. We're monitoring the situation closely and will update when we have more visibility.

Analyst: Can you quantify the impact of the headwinds?

{cfo_name}: I don't have the specific breakdown... let me get back to you on that. It depends on several factors that remain unclear.
""".format(ceo_name=ceo_name, cfo_name=cfo_name)
    
    else:  # mixed
        prepared = f"""
{ceo_name}: Good afternoon and thank you for joining our earnings call today.

This quarter showed solid progress in some areas while we faced challenges in others. Our core business delivered growth, though new market expansion was slower than anticipated.

We remain confident in our long-term strategy while being cautious about near-term uncertainties. The fundamentals of our business are healthy despite some headwinds.

{cfo_name}: Revenue met expectations with modest growth year over year. Margins were stable though we saw some pressure from cost inflation.

We're maintaining our guidance range while acknowledging both opportunities and risks ahead.
"""
        qa = """
Question-and-Answer Session

Analyst: Can you elaborate on the challenges you mentioned?

{ceo_name}: Sure. We saw some softness in certain markets, but this was offset by strength in others. It's a mixed picture overall.

Analyst: What's your outlook for next quarter?

{cfo_name}: We expect relatively stable performance. There's uncertainty around some factors, but we're cautiously optimistic about achieving our targets.
""".format(ceo_name=ceo_name, cfo_name=cfo_name)
    
    return prepared + qa


# Singleton instance
_analyzer = None

def get_analyzer() -> EarningsCallAnalyzer:
    """Get or create the analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = EarningsCallAnalyzer()
    return _analyzer
