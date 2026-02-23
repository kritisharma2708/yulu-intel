from typing import List, Optional

from pydantic import BaseModel


class CompetitorInsights(BaseModel):
    top_features: List[str]
    growth_signals: List[str]
    winning_segments: List[str]
    marketing_angles: List[str]


class RecentDevelopment(BaseModel):
    headline: str
    summary: str
    type: str
    recency: str


class CustomerSentiment(BaseModel):
    what_users_love: List[str]
    common_complaints: List[str]
    net_sentiment: str


class Competitor(BaseModel):
    name: str
    description: str
    strengths: List[str]
    weaknesses: List[str]
    market_position: str
    pricing_model: str
    key_differentiator: str
    insights: Optional[CompetitorInsights] = None
    recent_developments: Optional[List[RecentDevelopment]] = None
    sentiment: Optional[CustomerSentiment] = None


class SWOTAnalysis(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]


class StrategyRecommendation(BaseModel):
    title: str
    description: str
    priority: str
    category: str


class MonthlyAction(BaseModel):
    month: str
    title: str
    description: str
    actions: List[str]


class NewsDigestItem(BaseModel):
    headline: str
    competitor_name: str
    summary: str
    url: Optional[str] = None
    date: str
    type: str


class NewsExtractionResponse(BaseModel):
    items: List[NewsDigestItem]


class GigWorkerPulseItem(BaseModel):
    quote: str
    source_platform: str


class CompetitiveAnalysis(BaseModel):
    product_name: str
    market_overview: str
    competitors: List[Competitor]
    swot: SWOTAnalysis
    strategies: List[StrategyRecommendation]
    key_insights: List[str]
    news_digest: Optional[List[NewsDigestItem]] = None
    biggest_threats: Optional[List[str]] = None
    market_gaps: Optional[List[str]] = None
    urgent_opportunities: Optional[List[str]] = None
    action_plan_90day: Optional[List[MonthlyAction]] = None
    gig_worker_pulse: Optional[List[GigWorkerPulseItem]] = None
