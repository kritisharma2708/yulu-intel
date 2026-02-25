"""Self-contained HTML report generator for CompeteIQ."""

import html
import json
from datetime import date
from typing import List

from yulu_intel.models import CompetitiveAnalysis


def _e(text: str) -> str:
    """HTML-escape user-facing text."""
    return html.escape(str(text))


def generate_html_report(
    analysis: CompetitiveAnalysis,
    new_competitors: List[str],
    returning_competitors: List[str],
    is_first_run: bool,
) -> str:
    """Return a self-contained HTML string with tabs, charts, and inline CSS."""
    today = date.today().strftime("%B %d, %Y")
    new_set = set(new_competitors)

    # --- Chart data ---
    comp_names = json.dumps([c.name for c in analysis.competitors])
    # Threat score: rough heuristic — more weaknesses Yulu has that they exploit = higher threat
    threat_scores = json.dumps([
        min(10, len(c.strengths) * 2 + (1 if c.sentiment and c.sentiment.net_sentiment == "positive" else 0))
        for c in analysis.competitors
    ])

    swot = analysis.swot
    radar_labels = json.dumps(["Strengths", "Weaknesses", "Opportunities", "Threats"])
    radar_data = json.dumps([
        len(swot.strengths),
        len(swot.weaknesses),
        len(swot.opportunities),
        len(swot.threats),
    ])

    # --- News items ---
    news_items = analysis.news_digest or []
    type_colors = {
        "launch": "#6366f1",
        "funding": "#22c55e",
        "partnership": "#3b82f6",
        "controversy": "#ef4444",
        "growth": "#f59e0b",
    }

    news_html_parts = []
    news_types_seen = set()
    for item in news_items:
        news_types_seen.add(item.type)
        color = type_colors.get(item.type, "#6b7280")
        url_attr = f' href="{_e(item.url)}" target="_blank"' if item.url else ""
        news_html_parts.append(f"""
        <div class="card news-card" data-type="{_e(item.type)}" style="border-left:4px solid {color}">
            <div class="news-meta">
                <span class="badge" style="background:{color}">{_e(item.type)}</span>
                <span class="date-label">{_e(item.date)}</span>
                <span class="comp-label">{_e(item.competitor_name)}</span>
            </div>
            <h3><a{url_attr}>{_e(item.headline)}</a></h3>
            <p>{_e(item.summary)}</p>
        </div>""")
    news_html = "\n".join(news_html_parts) if news_html_parts else '<p class="muted">No recent news items.</p>'

    # News filter buttons
    filter_buttons = ['<button class="filter-btn active" data-filter="all">All</button>']
    for t in sorted(news_types_seen):
        color = type_colors.get(t, "#6b7280")
        filter_buttons.append(f'<button class="filter-btn" data-filter="{_e(t)}" style="--btn-color:{color}">{_e(t.title())}</button>')
    filter_html = "\n".join(filter_buttons)

    # --- Competitor cards ---
    comp_html_parts = []
    for comp in analysis.competitors:
        badge = '<span class="badge new-badge">NEW</span>' if comp.name in new_set and not is_first_run else ""
        strengths = "".join(f"<li>{_e(s)}</li>" for s in comp.strengths)
        weaknesses = "".join(f"<li>{_e(w)}</li>" for w in comp.weaknesses)
        sentiment_html = ""
        if comp.sentiment:
            sent_color = {"positive": "#22c55e", "negative": "#ef4444"}.get(comp.sentiment.net_sentiment, "#f59e0b")
            sentiment_html = f'<span class="badge" style="background:{sent_color}">Sentiment: {_e(comp.sentiment.net_sentiment)}</span>'

        insights_html = ""
        expand_btn = ""
        if comp.insights:
            features = ", ".join(_e(f) for f in comp.insights.top_features[:3])
            growth = ", ".join(_e(g) for g in comp.insights.growth_signals[:3])
            insights_html = (
                '<div class="insights-detail" style="display:none">'
                f"<p><strong>Top Features:</strong> {features}</p>"
                f"<p><strong>Growth Signals:</strong> {growth}</p>"
                "</div>"
            )
            expand_btn = (
                "<button class='expand-btn' onclick='"
                'this.previousElementSibling.style.display="block";'
                'this.style.display="none"'
                "'>Show More</button>"
            )

        comp_html_parts.append(f"""
        <div class="card competitor-card">
            <div class="comp-header">
                <h3>{_e(comp.name)} {badge}</h3>
                {sentiment_html}
            </div>
            <p class="market-pos">{_e(comp.market_position)}</p>
            <p>{_e(comp.description[:300])}</p>
            <div class="two-col">
                <div class="strength-list">
                    <h4>Strengths</h4>
                    <ul class="green-list">{strengths}</ul>
                </div>
                <div class="weakness-list">
                    <h4>Weaknesses</h4>
                    <ul class="red-list">{weaknesses}</ul>
                </div>
            </div>
            <p><strong>Pricing:</strong> {_e(comp.pricing_model)}</p>
            <p><strong>Differentiator:</strong> {_e(comp.key_differentiator)}</p>
            {insights_html}
            {expand_btn}
        </div>""")
    comp_html = "\n".join(comp_html_parts)

    # --- SWOT grid ---
    swot_strengths = "".join(f"<li>{_e(s)}</li>" for s in swot.strengths)
    swot_weaknesses = "".join(f"<li>{_e(w)}</li>" for w in swot.weaknesses)
    swot_opportunities = "".join(f"<li>{_e(o)}</li>" for o in swot.opportunities)
    swot_threats = "".join(f"<li>{_e(t)}</li>" for t in swot.threats)

    pulse_html = ""
    if analysis.gig_worker_pulse:
        quotes = "".join(
            f'<blockquote>"{_e(p.quote)}" <cite>— {_e(p.source_platform)}</cite></blockquote>'
            for p in analysis.gig_worker_pulse[:4]
        )
        pulse_html = f'<h3>Gig Worker Pulse</h3>{quotes}'

    # --- Strategy cards ---
    priority_colors = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}
    strat_html_parts = []
    for s in analysis.strategies:
        p_color = priority_colors.get(s.priority.lower(), "#6b7280")
        strat_html_parts.append(f"""
        <div class="card strat-card" style="border-left:4px solid {p_color}">
            <div class="strat-header">
                <h3>{_e(s.title)}</h3>
                <span class="badge" style="background:{p_color}">{_e(s.priority.upper())}</span>
                <span class="badge cat-badge">{_e(s.category)}</span>
            </div>
            <p>{_e(s.description)}</p>
        </div>""")
    strat_html = "\n".join(strat_html_parts)

    # --- 90-day timeline ---
    timeline_cols = []
    for m in (analysis.action_plan_90day or []):
        actions_li = "".join(f"<li>{_e(a)}</li>" for a in m.actions)
        timeline_cols.append(f"""
        <div class="timeline-col">
            <h3>{_e(m.month)}</h3>
            <h4>{_e(m.title)}</h4>
            <p class="muted">{_e(m.description)}</p>
            <ul>{actions_li}</ul>
        </div>""")
    timeline_html = "\n".join(timeline_cols) if timeline_cols else '<p class="muted">No 90-day plan available.</p>'

    # --- Threats / Gaps / Opportunities for Strategy tab ---
    tgo_html_parts = []
    if analysis.biggest_threats:
        items = "".join(f"<li>{_e(t)}</li>" for t in analysis.biggest_threats)
        tgo_html_parts.append(f'<div class="tgo-section threat-section"><h3>Biggest Threats</h3><ul>{items}</ul></div>')
    if analysis.market_gaps:
        items = "".join(f"<li>{_e(g)}</li>" for g in analysis.market_gaps)
        tgo_html_parts.append(f'<div class="tgo-section gap-section"><h3>Market Gaps</h3><ul>{items}</ul></div>')
    if analysis.urgent_opportunities:
        items = "".join(f"<li>{_e(o)}</li>" for o in analysis.urgent_opportunities)
        tgo_html_parts.append(f'<div class="tgo-section opp-section"><h3>Urgent Opportunities</h3><ul>{items}</ul></div>')
    tgo_html = "\n".join(tgo_html_parts)

    # --- Key insights ---
    insights_list = "".join(f"<li>{_e(i)}</li>" for i in analysis.key_insights)

    # --- KPI numbers ---
    n_competitors = len(analysis.competitors)
    n_threats = len(analysis.biggest_threats or [])
    n_opportunities = len(analysis.urgent_opportunities or [])
    n_news = len(news_items)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CompeteIQ Report — {_e(analysis.product_name)} — {_e(today)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',system-ui,sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6}}
.container{{max-width:1100px;margin:0 auto;padding:20px}}
header{{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;padding:32px 0;text-align:center}}
header h1{{font-size:1.8rem;font-weight:700}}
header p{{opacity:.85;margin-top:4px}}
.tabs{{display:flex;gap:0;background:#fff;border-bottom:2px solid #e2e8f0;position:sticky;top:0;z-index:10;overflow-x:auto}}
.tab-btn{{padding:12px 24px;border:none;background:none;font-family:inherit;font-size:.95rem;font-weight:500;color:#64748b;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;transition:all .15s}}
.tab-btn:hover{{color:#4f46e5}}
.tab-btn.active{{color:#4f46e5;border-bottom-color:#4f46e5}}
.tab-content{{display:none;padding:24px 0;animation:fadeIn .2s}}
.tab-content.active{{display:block}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
.kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:24px}}
.kpi-card{{background:#fff;border-radius:12px;padding:20px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.kpi-card .num{{font-size:2rem;font-weight:700;color:#4f46e5}}
.kpi-card .label{{font-size:.85rem;color:#64748b;margin-top:4px}}
.card{{background:#fff;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.badge{{display:inline-block;padding:2px 10px;border-radius:99px;color:#fff;font-size:.75rem;font-weight:600;text-transform:uppercase}}
.new-badge{{background:#ef4444}}
.cat-badge{{background:#6366f1}}
.chart-container{{background:#fff;border-radius:12px;padding:20px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.08);max-width:600px}}
h2{{font-size:1.3rem;font-weight:700;margin-bottom:16px;color:#1e293b}}
h3{{font-size:1.1rem;font-weight:600;margin-bottom:8px}}
h4{{font-size:.95rem;font-weight:600;margin-bottom:4px;color:#475569}}
a{{color:#4f46e5;text-decoration:none}}
a:hover{{text-decoration:underline}}
.muted{{color:#94a3b8;font-size:.9rem}}
/* News */
.filter-bar{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}}
.filter-btn{{padding:6px 16px;border-radius:99px;border:1px solid #e2e8f0;background:#fff;font-family:inherit;font-size:.85rem;cursor:pointer;transition:all .15s}}
.filter-btn:hover,.filter-btn.active{{background:var(--btn-color,#4f46e5);color:#fff;border-color:var(--btn-color,#4f46e5)}}
.news-card{{transition:all .15s}}
.news-card.hidden{{display:none}}
.news-meta{{display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-wrap:wrap}}
.date-label,.comp-label{{font-size:.8rem;color:#64748b}}
/* Competitors */
.comp-header{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px}}
.market-pos{{color:#6366f1;font-weight:500;margin-bottom:8px}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:12px 0}}
.green-list li{{color:#16a34a;margin-left:20px}}
.red-list li{{color:#dc2626;margin-left:20px}}
.green-list li::marker{{color:#16a34a}}
.red-list li::marker{{color:#dc2626}}
.expand-btn{{padding:6px 16px;border-radius:8px;border:1px solid #e2e8f0;background:#fff;font-family:inherit;cursor:pointer;font-size:.85rem;margin-top:8px}}
.expand-btn:hover{{background:#f1f5f9}}
/* SWOT */
.swot-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}}
.swot-box{{border-radius:12px;padding:20px}}
.swot-box ul{{margin-left:20px}}
.swot-box.s{{background:#f0fdf4;border:1px solid #bbf7d0}}
.swot-box.w{{background:#fef2f2;border:1px solid #fecaca}}
.swot-box.o{{background:#f0f9ff;border:1px solid #bae6fd}}
.swot-box.t{{background:#fefce8;border:1px solid #fef08a}}
.swot-box.s h3{{color:#16a34a}}
.swot-box.w h3{{color:#dc2626}}
.swot-box.o h3{{color:#0284c7}}
.swot-box.t h3{{color:#ca8a04}}
blockquote{{border-left:3px solid #6366f1;padding:8px 16px;margin:12px 0;background:#f8fafc;border-radius:0 8px 8px 0;font-style:italic}}
blockquote cite{{display:block;font-style:normal;font-size:.85rem;color:#64748b;margin-top:4px}}
/* Strategy */
.strat-header{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}}
.tgo-section{{margin-bottom:16px;padding:16px;border-radius:12px}}
.tgo-section ul{{margin-left:20px}}
.threat-section{{background:#fef2f2;border:1px solid #fecaca}}
.gap-section{{background:#f0f9ff;border:1px solid #bae6fd}}
.opp-section{{background:#f0fdf4;border:1px solid #bbf7d0}}
.timeline{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin:24px 0}}
.timeline-col{{background:#fff;border-radius:12px;padding:20px;border-top:4px solid #6366f1;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.timeline-col ul{{margin-left:20px;margin-top:8px}}
footer{{text-align:center;padding:32px 0;color:#94a3b8;font-size:.85rem;border-top:1px solid #e2e8f0;margin-top:40px}}
@media(max-width:640px){{
  .two-col,.swot-grid{{grid-template-columns:1fr}}
  .tab-btn{{padding:10px 14px;font-size:.85rem}}
  .kpi-row{{grid-template-columns:1fr 1fr}}
}}
</style>
</head>
<body>
<header>
    <div class="container">
        <h1>CompeteIQ — {_e(analysis.product_name)}</h1>
        <p>{_e(today)} | Micromobility &amp; Gig Worker Segment</p>
    </div>
</header>

<div class="container">
<nav class="tabs">
    <button class="tab-btn active" data-tab="overview">Overview</button>
    <button class="tab-btn" data-tab="news">News</button>
    <button class="tab-btn" data-tab="competitors">Competitors</button>
    <button class="tab-btn" data-tab="swot">SWOT</button>
    <button class="tab-btn" data-tab="strategy">Strategy</button>
</nav>

<!-- ===== OVERVIEW ===== -->
<div class="tab-content active" id="overview">
    <h2>Market Overview</h2>
    <div class="card"><p>{_e(analysis.market_overview)}</p></div>

    <div class="kpi-row">
        <div class="kpi-card"><div class="num">{n_competitors}</div><div class="label">Competitors Tracked</div></div>
        <div class="kpi-card"><div class="num" style="color:#ef4444">{n_threats}</div><div class="label">Threats Identified</div></div>
        <div class="kpi-card"><div class="num" style="color:#22c55e">{n_opportunities}</div><div class="label">Opportunities</div></div>
        <div class="kpi-card"><div class="num" style="color:#f59e0b">{n_news}</div><div class="label">News Items</div></div>
    </div>

    <div class="chart-container">
        <h3>Competitor Threat Scores</h3>
        <canvas id="threatChart"></canvas>
    </div>

    <h2>Key Insights</h2>
    <div class="card"><ol>{insights_list}</ol></div>
</div>

<!-- ===== NEWS ===== -->
<div class="tab-content" id="news">
    <h2>News Digest</h2>
    <div class="filter-bar">{filter_html}</div>
    {news_html}
</div>

<!-- ===== COMPETITORS ===== -->
<div class="tab-content" id="competitors">
    <h2>Competitor Profiles</h2>
    {comp_html}
</div>

<!-- ===== SWOT ===== -->
<div class="tab-content" id="swot">
    <h2>SWOT Analysis — {_e(analysis.product_name)}</h2>
    <div class="swot-grid">
        <div class="swot-box s"><h3>Strengths</h3><ul>{swot_strengths}</ul></div>
        <div class="swot-box w"><h3>Weaknesses</h3><ul>{swot_weaknesses}</ul></div>
        <div class="swot-box o"><h3>Opportunities</h3><ul>{swot_opportunities}</ul></div>
        <div class="swot-box t"><h3>Threats</h3><ul>{swot_threats}</ul></div>
    </div>

    <div class="chart-container">
        <h3>SWOT Dimensions</h3>
        <canvas id="radarChart"></canvas>
    </div>

    {pulse_html}
</div>

<!-- ===== STRATEGY ===== -->
<div class="tab-content" id="strategy">
    <h2>Strategic Recommendations</h2>
    {strat_html}

    {tgo_html}

    <h2>90-Day Action Plan</h2>
    <div class="timeline">{timeline_html}</div>
</div>
</div>

<footer>
    <p>Generated by <strong>CompeteIQ Agent</strong> &mdash; {_e(today)}</p>
</footer>

<script>
// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
    }});
}});

// News filter
document.querySelectorAll('.filter-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const filter = btn.dataset.filter;
        document.querySelectorAll('.news-card').forEach(card => {{
            card.classList.toggle('hidden', filter !== 'all' && card.dataset.type !== filter);
        }});
    }});
}});

// Charts
const threatCtx = document.getElementById('threatChart');
if (threatCtx) {{
    new Chart(threatCtx, {{
        type: 'bar',
        data: {{
            labels: {comp_names},
            datasets: [{{
                label: 'Threat Score',
                data: {threat_scores},
                backgroundColor: ['#6366f1','#8b5cf6','#a78bfa','#c4b5fd','#ddd6fe','#ede9fe'],
                borderRadius: 8,
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{ y: {{ beginAtZero: true, max: 10 }} }}
        }}
    }});
}}

const radarCtx = document.getElementById('radarChart');
if (radarCtx) {{
    new Chart(radarCtx, {{
        type: 'radar',
        data: {{
            labels: {radar_labels},
            datasets: [{{
                label: '{_e(analysis.product_name)}',
                data: {radar_data},
                backgroundColor: 'rgba(99,102,241,.2)',
                borderColor: '#6366f1',
                pointBackgroundColor: '#6366f1',
            }}]
        }},
        options: {{
            responsive: true,
            scales: {{ r: {{ beginAtZero: true }} }}
        }}
    }});
}}
</script>
</body>
</html>"""
