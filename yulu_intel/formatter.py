from datetime import date
from typing import Dict, List

from yulu_intel.models import CompetitiveAnalysis


def _section(text: str) -> Dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _header(text: str) -> Dict:
    return {"type": "header", "text": {"type": "plain_text", "text": text}}


def _divider() -> Dict:
    return {"type": "divider"}


def _truncate(text: str, limit: int = 2900) -> str:
    """Slack blocks have a 3000 char limit per text field."""
    return text[:limit] + "..." if len(text) > limit else text


def format_messages(
    analysis: CompetitiveAnalysis,
    new_competitors: List[str],
    returning_competitors: List[str],
    is_first_run: bool,
) -> List[Dict]:
    """Build 4 Slack Block Kit payloads."""
    new_set = set(new_competitors)
    today = date.today().strftime("%B %d, %Y")

    # === MESSAGE 1: Header + Overview + New Competitor Alert ===
    msg1_blocks = [
        _header(f"Competitive Intel Report - {analysis.product_name}"),
        _section(f"*Date:* {today}  |  *Competitors tracked:* {len(analysis.competitors)}"),
        _divider(),
        _section(f"*Market Overview*\n{_truncate(analysis.market_overview)}"),
        _divider(),
    ]

    if is_first_run:
        msg1_blocks.append(
            _section(":information_source: *First Run* — All competitors are newly tracked. Future reports will highlight only new entrants.")
        )
    elif new_competitors:
        alert_lines = [":rotating_light: *New Competitor Alert!*\n"]
        for comp in analysis.competitors:
            if comp.name in new_set:
                strengths = ", ".join(comp.strengths[:3]) if comp.strengths else "N/A"
                weaknesses = ", ".join(comp.weaknesses[:3]) if comp.weaknesses else "N/A"
                alert_lines.append(f":new: *{comp.name}*")
                alert_lines.append(f"  _Strengths:_ {strengths}")
                alert_lines.append(f"  _Weaknesses:_ {weaknesses}\n")
        msg1_blocks.append(_section(_truncate("\n".join(alert_lines))))
    else:
        msg1_blocks.append(
            _section(":white_check_mark: *No new competitors detected.* All {0} competitors are returning.".format(len(returning_competitors)))
        )

    # === MESSAGE 2: Competitor Profiles ===
    msg2_blocks = [_header("Competitor Profiles")]

    for comp in analysis.competitors:
        badge = " :new:" if comp.name in new_set and not is_first_run else ""
        strengths = "\n".join(f"  :white_check_mark: {s}" for s in comp.strengths[:4])
        weaknesses = "\n".join(f"  :x: {w}" for w in comp.weaknesses[:4])
        sentiment_str = ""
        if comp.sentiment:
            sentiment_str = f"\n_Sentiment:_ {comp.sentiment.net_sentiment}"

        profile = (
            f"*{comp.name}*{badge}\n"
            f"_{comp.market_position}_\n\n"
            f"{comp.description[:300]}\n\n"
            f"*Strengths:*\n{strengths}\n\n"
            f"*Weaknesses:*\n{weaknesses}\n\n"
            f"*Pricing:* {comp.pricing_model}\n"
            f"*Differentiator:* {comp.key_differentiator}"
            f"{sentiment_str}"
        )
        msg2_blocks.append(_divider())
        msg2_blocks.append(_section(_truncate(profile)))

    # === MESSAGE 3: News Digest + SWOT ===
    msg3_blocks = [_header("News Digest & SWOT Analysis")]

    linked_news = [item for item in (analysis.news_digest or []) if item.url]
    if linked_news:
        news_lines = ["*:newspaper: Recent News*\n"]
        for item in linked_news[:8]:
            news_lines.append(f":small_blue_diamond: <{item.url}|{item.headline}> — {item.summary} ({item.date})")
        msg3_blocks.append(_section(_truncate("\n".join(news_lines))))

    msg3_blocks.append(_divider())
    swot = analysis.swot
    swot_text = (
        f"*SWOT Analysis for {analysis.product_name}*\n\n"
        f"*:muscle: Strengths*\n" + "\n".join(f"  • {s}" for s in swot.strengths) + "\n\n"
        f"*:warning: Weaknesses*\n" + "\n".join(f"  • {w}" for w in swot.weaknesses) + "\n\n"
        f"*:bulb: Opportunities*\n" + "\n".join(f"  • {o}" for o in swot.opportunities) + "\n\n"
        f"*:exclamation: Threats*\n" + "\n".join(f"  • {t}" for t in swot.threats)
    )
    msg3_blocks.append(_section(_truncate(swot_text)))

    # === MESSAGE 4: Strategies + Threats/Gaps/Opportunities + 90-Day Plan + Key Insights ===
    msg4_blocks = [_header("Strategy & Action Plan")]

    # Strategies
    strat_lines = ["*:dart: Strategic Recommendations*\n"]
    for s in analysis.strategies:
        priority_emoji = {
            "high": ":red_circle:",
            "medium": ":large_orange_circle:",
            "low": ":white_circle:",
        }.get(s.priority.lower(), ":black_circle:")
        strat_lines.append(f"{priority_emoji} *{s.title}* [{s.category}]")
        strat_lines.append(f"  {s.description}\n")
    msg4_blocks.append(_section(_truncate("\n".join(strat_lines))))
    msg4_blocks.append(_divider())

    # Threats / Gaps / Opportunities
    tgo_lines = []
    if analysis.biggest_threats:
        tgo_lines.append("*:rotating_light: Biggest Threats*")
        tgo_lines.extend(f"  • {t}" for t in analysis.biggest_threats)
        tgo_lines.append("")
    if analysis.market_gaps:
        tgo_lines.append("*:mag: Market Gaps*")
        tgo_lines.extend(f"  • {g}" for g in analysis.market_gaps)
        tgo_lines.append("")
    if analysis.urgent_opportunities:
        tgo_lines.append("*:rocket: Urgent Opportunities*")
        tgo_lines.extend(f"  • {o}" for o in analysis.urgent_opportunities)
    if tgo_lines:
        msg4_blocks.append(_section(_truncate("\n".join(tgo_lines))))
        msg4_blocks.append(_divider())

    # 90-Day Plan
    if analysis.action_plan_90day:
        plan_lines = ["*:calendar: 90-Day Action Plan*\n"]
        for m in analysis.action_plan_90day:
            plan_lines.append(f"*{m.month}: {m.title}*")
            plan_lines.append(f"_{m.description}_")
            plan_lines.extend(f"  {i+1}. {a}" for i, a in enumerate(m.actions))
            plan_lines.append("")
        msg4_blocks.append(_section(_truncate("\n".join(plan_lines))))
        msg4_blocks.append(_divider())

    # Key Insights
    insight_lines = ["*:brain: Key Insights*\n"]
    for idx, ins in enumerate(analysis.key_insights, 1):
        insight_lines.append(f"  {idx}. {ins}")
    msg4_blocks.append(_section(_truncate("\n".join(insight_lines))))

    return [
        {"blocks": msg1_blocks},
        {"blocks": msg2_blocks},
        {"blocks": msg3_blocks},
        {"blocks": msg4_blocks},
    ]
