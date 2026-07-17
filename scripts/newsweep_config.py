"""
News Sweep Config — Source of truth for queries, sources, keywords, entities, watch lists.
Pattern: mirrors market-data/config.py
Updated: 2026-04-03

Schedule: M-F via GH Actions cron 15:00 UTC (~11:00 ET; queue delay lands runs ~12:10-12:20 ET in practice) + workflow_dispatch on-demand
"""

# ---------------------------------------------------------------------------
# Google News RSS search feeds — thesis-tagged
# ---------------------------------------------------------------------------

GOOGLE_NEWS_QUERIES = [
    # BROCK domain — private credit / BDC / insurance
    {
        "query": '"private credit" OR "BDC" OR "CLO default" OR "direct lending"',
        "agents": ["BROCK"],
        "priority": "high",
        "label": "private-credit",
    },
    {
        "query": '"Blue Owl" OR "OBDC" OR "Owl Rock" OR "ARES Capital" OR "ARCC"',
        "agents": ["BROCK"],
        "priority": "high",
        "label": "bdc-names",
    },
    {
        "query": '"Apollo credit" OR "Athene" OR "insurance insolvency" OR "PE insurance"',
        "agents": ["BROCK"],
        "priority": "medium",
        "label": "pe-insurance",
    },

    # HENRY domain — energy / oil / geopolitics
    {
        "query": '"Brent crude" OR "oil price" OR "Hormuz" OR "Iran oil"',
        "agents": ["HENRY", "BRENT"],
        "priority": "high",
        "label": "oil-energy",
    },
    {
        "query": '"gasoline prices" OR "refinery" OR "SPR release" OR "OPEC"',
        "agents": ["HENRY", "BRENT"],
        "priority": "medium",
        "label": "gas-supply",
    },

    # SAM domain — Japan / yen / carry
    {
        "query": '"BOJ" OR "Bank of Japan" OR "yen" OR "carry trade" OR "JGB"',
        "agents": ["SAM"],
        "priority": "high",
        "label": "japan-boj",
    },

    # LABOR domain — employment
    {
        "query": '"layoffs" OR "unemployment claims" OR "hiring freeze" OR "mass layoff"',
        "agents": ["LABOR"],
        "priority": "high",
        "label": "labor-layoffs",
    },
    {
        "query": '"nonfarm payrolls" OR "NFP" OR "jobs report" OR "BLS employment"',
        "agents": ["LABOR"],
        "priority": "high",
        "label": "labor-nfp",
    },

    # LIQUID domain — credit / funding / rates
    {
        "query": '"high yield spread" OR "credit stress" OR "HY OAS" OR "junk bonds"',
        "agents": ["LIQUID"],
        "priority": "high",
        "label": "credit-spreads",
    },
    {
        "query": '"repo market" OR "SOFR" OR "Fed lending" OR "reserve scarcity"',
        "agents": ["LIQUID"],
        "priority": "medium",
        "label": "funding-stress",
    },

    # REGINALD domain — CRE / banks
    {
        "query": '"commercial real estate" OR "CRE default" OR "office vacancy"',
        "agents": ["REGINALD"],
        "priority": "high",
        "label": "cre-stress",
    },
    {
        "query": '"bank failure" OR "FDIC seizure" OR "deposit flight" OR "regional bank stress"',
        "agents": ["REGINALD", "LIQUID"],
        "priority": "high",
        "label": "bank-stress",
    },

    # CARL domain — consumer
    {
        "query": '"subprime auto" OR "credit card delinquency" OR "consumer default"',
        "agents": ["CARL"],
        "priority": "high",
        "label": "consumer-stress",
    },

    # Position-specific
    {
        "query": '"KRE" OR "OZK" OR "WAL" OR "Western Alliance"',
        "agents": ["REGINALD"],
        "priority": "medium",
        "label": "position-banks",
    },
    {
        "query": '"APO" OR "Apollo Global" OR "ARES Management"',
        "agents": ["BROCK"],
        "priority": "medium",
        "label": "position-pe",
    },
    # VULCAN domain — AI capex / semis / memory (added 2026-07-16, WALTER
    # coverage-gap note: zero AI/semis/memory queries existed; TrendForce = the
    # canonical memory contract-price source, 0 hits in 764 archive rows)
    {
        "query": '"TrendForce" OR "DRAM contract price" OR "NAND pricing" OR "memory shortage" OR "HBM"',
        "agents": ["VULCAN"],
        "priority": "high",
        "label": "memory-cycle",
    },
    {
        "query": '"hyperscaler capex" OR "AI capex" OR "data center capex" OR "capex guidance"',
        "agents": ["VULCAN", "HENRY"],
        "priority": "high",
        "label": "ai-capex",
    },

    # Fleet coverage sweep (2026-07-16, Will-approved; WALTER-drafted from
    # REGISTRY domain strings, PROME-landed; owners ratify/amend at next boot —
    # owner wins). Purpose: autonomous collection for domains whose discovery
    # previously depended on Will's drops or the agent's own in-session pulls
    # ("coverage that doesn't route through Will").
    # NEXUS deliberately has NO query (synthesis-class; convergence is derived).
    # First-run flood watch (PROME+WALTER reconciled 7/16 eve): "foreclosure",
    # "copper price", "mortgage rates" — tune narrow if they flood the gate.
    #
    # vol-regime (v2, WALTER-corrected 7/16 eve): bare "VIX" dropped (worst
    # flood risk of the nine) and the wording kept DIRECTION-NEUTRAL — a
    # spike-only query would blind the lane to registered LOW-vol triggers
    # (RED-FT-06 = VIX <16 sustain-5, live). JUSTIFICATION CORRECTION: VIOLET
    # was never uncovered — the cftc_cot feed is its lane (VIX futures
    # positioning, weekly). This query is COMPLEMENTARY, not gap-filling →
    # strongest CUT candidate of the nine at the ~7/30 redundancy review.
    {
        "query": '"VIX spike" OR "VIX collapse" OR "volatility regime" OR "vol compression" OR "VVIX" OR "SKEW index"',
        "agents": ["VIOLET"],
        "priority": "high",
        "label": "vol-regime",
    },
    {
        "query": '"grid emergency" OR "PJM" OR "ERCOT" OR "capacity auction" OR "power prices" OR "interconnection queue"',
        "agents": ["WATT", "VULCAN"],
        "priority": "high",
        "label": "power-grid",
    },
    {
        "query": '"central bank gold" OR "gold-silver ratio" OR "LME inventories" OR "copper price" OR "COMEX"',
        "agents": ["MIDAS"],
        "priority": "medium",
        "label": "metals",
    },
    {
        "query": '"El Nino" OR "La Nina" OR "heat dome" OR "hurricane forecast" OR "reinsurance pricing" OR "crop conditions"',
        "agents": ["AEOLUS"],
        "priority": "medium",
        "label": "climate-macro",
    },
    {
        "query": '"existing home sales" OR "housing inventory" OR "foreclosure" OR "homebuilder" OR "mortgage rates"',
        "agents": ["HOMER", "CARL"],
        "priority": "high",
        "label": "housing",
    },
    {
        "query": '"Russia refinery" OR "Ukraine drone strike" OR "Russian oil exports" OR "Novorossiysk" OR "Druzhba"',
        "agents": ["OSPREY", "BRENT"],
        "priority": "high",
        "label": "russia-ukraine-energy",
    },
    {
        "query": '"Strait of Hormuz" OR "Bab al-Mandab" OR "tanker attack" OR "IRGC" OR "Gulf strike" OR "naval blockade"',
        "agents": ["FALCON", "BRENT"],
        "priority": "high",
        "label": "gulf-theater",
    },
    {
        "query": '"Florida condo" OR "Florida insurance" OR "Citizens Property Insurance" OR "Florida housing"',
        "agents": ["CORAL", "HOMER"],
        "priority": "medium",
        "label": "florida",
    },
    {
        "query": '"HIBOR" OR "LGFV" OR "China property" OR "Hong Kong peg" OR "PBOC"',
        "agents": ["ZHAO"],
        "priority": "medium",
        "label": "china-asia",
    },
]

# ---------------------------------------------------------------------------
# RSS feeds — direct (non-Google)
# ---------------------------------------------------------------------------

RSS_FEEDS = [
    {
        "url": "https://www.ft.com/rss/home",
        "name": "FT",
        "agents": ["ALL"],
        "priority": "high",
    },
    {
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "name": "BBC Business",
        "agents": ["ALL"],
        "priority": "high",
    },
    {
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "name": "BBC World",
        "agents": ["ALL"],
        "priority": "medium",
    },
]

# ---------------------------------------------------------------------------
# Web scrape targets — headline extraction via fetch
# ---------------------------------------------------------------------------

WEB_SCRAPE = [
    {
        "url": "https://www.zerohedge.com/",
        "name": "ZeroHedge",
        "agents": ["ALL"],
        "priority": "high",
    },
    # Reuters returns 401 via fetch — use Google News instead
]

# ---------------------------------------------------------------------------
# Source quality weighting (Pattern 2 — EDR)
# Higher weight = more authoritative for factual claims
# Used in scoring: priority = keyword_score × source_weight
# ---------------------------------------------------------------------------

SOURCE_WEIGHT = {
    # Tier 1: Wire services / primary
    "Reuters": 3, "Bloomberg": 3, "Bloomberg.com": 3,
    "WSJ": 3, "Wall Street Journal": 3,
    "FT": 3, "Financial Times": 3,
    "Federal Reserve": 3, "FDIC": 3, "BLS": 3,
    # Tier 2: Major outlets
    "CNBC": 2, "BBC": 2, "BBC Business": 2, "BBC World": 2,
    "NYT": 2, "The New York Times": 2,
    "WaPo": 2, "The Washington Post": 2,
    "AP": 2, "Associated Press": 2,
    "Barron's": 2, "Investopedia": 2,
    "Fortune": 2, "Business Insider": 2,
    # Tier 3: Specialist — domain-valuable
    "Auto Finance News": 2, "Banking Dive": 2,
    "Bond Buyer": 2, "CoStar": 2, "S&P Global": 2,
    "Insurance Business": 2, "Neuberger Berman": 2,
    "Indeed Hiring Lab": 2, "Seeking Alpha": 1,
    # Tier 4: Aggregator / opinion — signal but verify
    "ZeroHedge": 1, "MSN": 1, "Yahoo Finance": 1,
    "PYMNTS.com": 1, "simplywall.st": 1,
    # Default
    "_default": 1,
}

# ---------------------------------------------------------------------------
# Noise filters — title patterns to auto-skip
# ---------------------------------------------------------------------------

NOISE_TITLE_PATTERNS = [
    # CRE local deal noise
    r"(?i)\bcommercial real estate (awards|deals|listings|roundup|honorees)\b",
    r"(?i)\b(announces|snags|closes) .*(building|property|plaza)\b",
    r"(?i)\b\d+ biggest .* deals\b",
    # FDIC non-crisis
    r"(?i)\bFDIC.*(stablecoin|preview|international|conference)\b",
    r"(?i)\bfire engineering\b",
    r"(?i)\bFDIC International\b",
    # Generic filler
    r"(?i)\bhow (to|the) .*(affect|impact) you\b",
    r"(?i)\byour .* stories\b",
    r"(?i)\b(subscription|cancel|refund)\b",
    r"(?i)\bminimum wage\b",
    r"(?i)\b(academic study|german women)\b",
    r"(?i)\bnational flags?\b",
]

# ---------------------------------------------------------------------------
# Entity Index (Pattern 1 — Trilogy)
# Manually curated. Maps known entities to owning agents + aliases.
# Used for: routing, KNOWN/DEVELOPMENT classification
# Rebuild after major STATUS changes.
# Last updated: 2026-04-03
# ---------------------------------------------------------------------------

ENTITY_INDEX = {
    # BROCK domain
    "Blue Owl":     {"agents": ["BROCK", "LIQUID"], "aliases": ["OWL", "OBDC", "Owl Rock", "Blue Owl Capital"]},
    "ARES":         {"agents": ["BROCK"], "aliases": ["ARCC", "ARES Capital", "ARES Management", "Ares Capital", "Ares Management"]},
    "IHAM":         {"agents": ["BROCK"], "aliases": ["Ivy Hill"]},
    "Apollo":       {"agents": ["BROCK"], "aliases": ["APO", "Apollo Global", "Athene"]},
    "Blackstone":   {"agents": ["BROCK", "LIQUID"], "aliases": ["BX", "Evermore"]},
    "KKR":          {"agents": ["BROCK"], "aliases": ["Global Atlantic"]},
    "BCRED":        {"agents": ["BROCK"], "aliases": ["Blackstone Credit"]},
    "BIZD":         {"agents": ["BROCK"], "aliases": []},

    # REGINALD domain
    "OZK":          {"agents": ["REGINALD"], "aliases": ["Bank OZK"]},
    "WAL":          {"agents": ["REGINALD"], "aliases": ["Western Alliance", "Western Alliance Bank"]},
    "KRE":          {"agents": ["REGINALD", "LIQUID"], "aliases": []},

    # HENRY domain
    "Hormuz":       {"agents": ["HENRY", "SAM"], "aliases": ["Strait of Hormuz", "Hormuz Strait"]},
    "ADCOP":        {"agents": ["HENRY"], "aliases": ["Abu Dhabi pipeline"]},
    "Brent":        {"agents": ["HENRY"], "aliases": ["Brent crude"]},
    "OPEC":         {"agents": ["HENRY"], "aliases": ["OPEC+"]},

    # SAM domain
    "BOJ":          {"agents": ["SAM"], "aliases": ["Bank of Japan", "Ueda", "Kuroda"]},
    "JGB":          {"agents": ["SAM"], "aliases": ["Japanese government bond"]},
    "GPIF":         {"agents": ["SAM"], "aliases": []},
    "FXY":          {"agents": ["SAM"], "aliases": []},

    # LABOR domain
    "Oracle":       {"agents": ["LABOR"], "aliases": ["Oracle layoffs"]},
    "DOGE":         {"agents": ["LABOR", "MARCO"], "aliases": ["Department of Government Efficiency"]},

    # CARL domain
    "Tricolor":     {"agents": ["CARL", "OTTO"], "aliases": ["Tricolor Auto"]},

    # OTTO domain
    "CVNA":         {"agents": ["OTTO"], "aliases": ["Carvana"]},

    # MARCO domain
    "DHS":          {"agents": ["MARCO"], "aliases": ["DHS shutdown", "Homeland Security"]},
    "ICE":          {"agents": ["MARCO"], "aliases": ["immigration enforcement"]},
    "TSA":          {"agents": ["MARCO"], "aliases": []},

    # LIQUID domain
    "SOFR":         {"agents": ["LIQUID"], "aliases": []},
    "TLT":          {"agents": ["LIQUID"], "aliases": []},
    "HYG":          {"agents": ["LIQUID"], "aliases": []},
}

# ---------------------------------------------------------------------------
# Escalation qualifiers
# Known entity + qualifier = DEVELOPMENT (not just KNOWN)
# ---------------------------------------------------------------------------

ESCALATION_QUALIFIERS = [
    "SEC", "probe", "investigation", "subpoena", "indictment",
    "bankruptcy", "chapter 7", "chapter 11", "seized", "insolvent",
    "emergency", "unprecedented", "record", "all-time",
    "fraud", "criminal", "charged", "arrested",
    "downgrade", "default", "collapsed", "halted", "suspended",
    "intervention", "bailout", "backstop",
    "contagion", "systemic", "spillover",
    "doubled", "tripled", "surged", "plunged", "crashed",
]

# ---------------------------------------------------------------------------
# WATCH_FOR lists (Pattern 2 — EDR gap identification)
# Forward-looking: what does each agent WANT to learn?
# Maintained by Prome after reading agent COMPLETION_SPECs.
# Last updated: 2026-04-03
# ---------------------------------------------------------------------------

WATCH_FOR = {
    "BROCK": [
        "second BDC gating",           # Blue Owl was first — who's next?
        "insurance regulator action",   # State-level on PE-controlled insurers
        "IHAM SEC filing",             # Any new ARES/IHAM disclosure
        "CLO OC test failure",         # Overcollateralization breach
        "BDC NAV cut >5%",            # Honest marks starting
        "private credit fund closure",  # Beyond gating — actual wind-down
        "Athene policyholder action",   # Insurance transmission
    ],
    "HENRY": [
        "Hormuz reopening",            # Ceasefire / passage restored
        "ceasefire deal",              # Iran-US deal terms
        "SPR release >50M bbl",        # Emergency supply response
        "Iran nuclear",                # Escalation beyond conventional
        "refinery attack",             # Supply infrastructure damage
        "gas above $4.50",            # Next behavioral breakpoint
    ],
    "SAM": [
        "BOJ rate hike announcement",  # Actual hike (not just signal)
        "yen intervention confirmed",  # MOF/BOJ action
        "GPIF allocation shift",       # Rebalancing away from UST
        "Japan life insurer UST sale", # Repatriation acceleration
        "USD/JPY above 162",          # Next stress level
        "carry trade unwind confirmed", # Not just risk — actual unwind
    ],
    "LABOR": [
        "claims above 250K",              # CARL cross-agent trigger
        "Florida unemployment claims",     # FL Wave 1 — needs both Florida + claims
        "Fortune 500 hiring freeze",       # Major corporate transmission
        "healthcare sector layoffs",       # Last sector standing — needs "sector" qualifier
        "payrolls revision downward",      # Feb/Mar revisions
        "WARN filing surge",              # Leading indicator of next month's claims
    ],
    "LIQUID": [
        "HY OAS above 350",           # Issuance freeze territory
        "repo rate spike",             # Funding stress
        "SRF usage",                   # Fed facility tapped
        "money market fund break",     # 2008-type stress
        "Treasury auction failure",    # Demand hole manifesting
        "bank reserve crunch",         # Below comfortable level
    ],
    "REGINALD": [
        "OZK CRE loss announcement",  # Position-specific
        "WAL earnings miss",          # Position-specific
        "CMBS delinquency spike",     # Broad CRE stress
        "FDIC seizes bank",           # New FDIC seizure — tighter than "regional bank failure"
        "office loan default",         # Major single-asset default
        "CRE maturity refinancing",   # Refinancing crunch
    ],
    "CARL": [
        "subprime auto delinquency rate",  # Threshold — needs actual rate data
        "credit card charge-off record",   # Consumer breaking — needs "record" or hard number
        "consumer confidence collapse",    # Sentiment shift
        "retail bankruptcy filing",        # Downstream — needs actual filing
        "mortgage delinquency surge",      # Housing + consumer convergence
    ],
    "MARCO": [
        "DHS shutdown resolved",       # Status change
        "ICE agricultural raid",       # Labor supply shock
        "H-2A program change",         # Policy shift
        "self-deportation data",       # Quantifying the exodus
        "remittance collapse",         # Mexico flow data
    ],
    "OTTO": [
        "CVNA earnings",              # Position-specific
        "Hindenburg report",          # Short thesis catalyst
        "subprime ABS downgrade",     # Securitization stress
        "auto dealer bankruptcy",      # Downstream
    ],
}

# ---------------------------------------------------------------------------
# Alert keywords — instant flag (🔴)
# ---------------------------------------------------------------------------

ALERT_KEYWORDS = [
    # Credit/liquidity crisis
    "gating", "redemption suspension", "redemption halt",
    "NAV write-down", "NAV writedown", "fire sale", "forced selling",
    "margin call", "liquidity crisis",
    # Banking
    "bank run", "deposit flight", "FDIC seizure", "bank failure",
    # Geopolitical
    "Hormuz closed", "strait closed", "nuclear strike", "nuclear weapon",
    # Central bank emergency
    "Fed emergency", "emergency lending", "BOJ emergency",
    "yen intervention", "currency intervention",
    # Market structure
    "circuit breaker", "trading halt", "flash crash",
]

# ---------------------------------------------------------------------------
# Watch keywords — flag but don't alert (🟡)
# ---------------------------------------------------------------------------

WATCH_KEYWORDS = [
    # Credit
    "covenant breach", "PIK toggle", "PIK rate",
    "CLO downgrade", "CLO tranche", "insurance impairment",
    "BDC loss", "BDC NAV", "direct lending default",
    "high yield issuance", "junk bond",
    # Labor
    "hiring freeze", "WARN notice", "mass layoff",
    "unemployment spike", "claims surge",
    # Real estate
    "CRE maturity", "office default", "CMBS delinquency",
    "multifamily stress",
    # Japan/carry
    "carry trade unwind", "JGB sell", "life insurer",
    "yen repatriation",
    # Funding
    "repo stress", "SRF usage", "T-bill shortage",
    "money market", "reserve scarcity",
    # Energy
    "refinery outage", "pipeline attack", "Iran oil embargo",
    "gasoline shortage", "SPR release",
    # Consumer
    "subprime", "delinquency rate", "charge-off",
    "credit card default",
]

# ---------------------------------------------------------------------------
# Dedup window and cache settings
# ---------------------------------------------------------------------------

DEDUP_HOURS = 24          # Ignore headlines seen within this window
CACHE_DIR = ".cache"       # Relative to tool directory
MAX_ARTICLES_PER_SOURCE = 15
REQUEST_TIMEOUT = 10       # seconds
GOOGLE_NEWS_DELAY = 1.0    # seconds between Google News RSS requests (rate limit)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

import os
WORKSPACE = "/home/moltbot/.openclaw/workspace"
AGENTS_DIR = os.path.join(WORKSPACE, "AGENTS")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def google_news_rss_url(query):
    """Build Google News RSS URL from search query."""
    from urllib.parse import quote
    return f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"


def get_source_weight(source_name):
    """Look up source weight, with fuzzy matching."""
    if not source_name:
        return SOURCE_WEIGHT.get("_default", 1)
    # Exact match
    if source_name in SOURCE_WEIGHT:
        return SOURCE_WEIGHT[source_name]
    # Partial match
    source_lower = source_name.lower()
    for key, weight in SOURCE_WEIGHT.items():
        if key.lower() in source_lower or source_lower in key.lower():
            return weight
    return SOURCE_WEIGHT.get("_default", 1)


def score_headline(title):
    """
    Score a headline against keyword lists.
    Returns: ("alert", keyword) | ("watch", keyword) | ("normal", None)
    """
    title_lower = title.lower()
    for kw in ALERT_KEYWORDS:
        if kw.lower() in title_lower:
            return ("alert", kw)
    for kw in WATCH_KEYWORDS:
        if kw.lower() in title_lower:
            return ("watch", kw)
    return ("normal", None)


def match_entity(title):
    """
    Match a headline against the entity index.
    Returns: (entity_name, entity_info) or (None, None)
    """
    title_lower = title.lower()
    for entity, info in ENTITY_INDEX.items():
        if entity.lower() in title_lower:
            return (entity, info)
        for alias in info.get("aliases", []):
            if alias and alias.lower() in title_lower:
                return (entity, info)
    return (None, None)


def has_escalation_qualifier(title):
    """Check if title contains an escalation qualifier (word-boundary match)."""
    import re
    title_lower = title.lower()
    for q in ESCALATION_QUALIFIERS:
        # Word boundary match to prevent "SEC" matching "second"
        pattern = r'\b' + re.escape(q.lower()) + r'\b'
        if re.search(pattern, title_lower):
            return q
    return None


def match_watch_for(title):
    """
    Check if headline matches any WATCH_FOR item.
    STRICT matching: requires ALL significant words (>3 chars) to appear.
    Returns: list of (agent, watch_item) tuples
    """
    title_lower = title.lower()
    matches = []
    for agent, items in WATCH_FOR.items():
        for item in items:
            # Extract significant words (>3 chars, skip articles/prepositions)
            skip = {"above", "below", "from", "with", "that", "this", "than", "into"}
            words = [w.lower() for w in item.split() if len(w) > 3 and w.lower() not in skip]
            if not words:
                continue
            # ALL significant words must appear (strict)
            if all(w in title_lower for w in words):
                matches.append((agent, item))
    return matches


def is_noise(title):
    """Check if title matches noise filter patterns."""
    import re
    for pattern in NOISE_TITLE_PATTERNS:
        if re.search(pattern, title):
            return True
    return False


def classify_article(title, description=""):
    """
    Full classification pipeline for a single article.
    Returns dict with: level, keyword, entity, entity_info, escalation,
                       watch_hits, classification, suppressed
    
    Classifications:
      NEW_WATCH_HIT  — matches a WATCH_FOR item (highest priority)
      NEW_ALERT      — unknown entity + alert keyword
      NEW_WATCH      — unknown entity + watch keyword  
      NEW            — no entity match, no keyword
      DEVELOPMENT    — known entity + escalation qualifier
      KNOWN          — known entity, no escalation
      NOISE          — matched noise filter
    """
    result = {
        "level": "normal",
        "keyword": None,
        "entity": None,
        "entity_info": None,
        "escalation": None,
        "watch_hits": [],
        "classification": "NEW",
        "suppressed": False,
    }

    # Step 0: Noise filter
    if is_noise(title):
        result["classification"] = "NOISE"
        result["suppressed"] = True
        return result

    # Step 1: Keyword scoring
    level, keyword = score_headline(title)
    if level == "normal" and description:
        level, keyword = score_headline(description)
    result["level"] = level
    result["keyword"] = keyword

    # Step 2: Entity matching
    entity, entity_info = match_entity(title)
    result["entity"] = entity
    result["entity_info"] = entity_info

    # Step 3: WATCH_FOR matching (highest priority)
    watch_hits = match_watch_for(title)
    if not watch_hits and description:
        watch_hits = match_watch_for(description)
    result["watch_hits"] = watch_hits

    # Step 4: Classification
    if watch_hits:
        result["classification"] = "NEW_WATCH_HIT"
        result["suppressed"] = False
    elif entity:
        escalation = has_escalation_qualifier(title)
        result["escalation"] = escalation
        if escalation:
            result["classification"] = "DEVELOPMENT"
            result["suppressed"] = False
        else:
            result["classification"] = "KNOWN"
            result["suppressed"] = True
    elif level == "alert":
        result["classification"] = "NEW_ALERT"
        result["suppressed"] = False
    elif level == "watch":
        result["classification"] = "NEW_WATCH"
        result["suppressed"] = False
    else:
        result["classification"] = "NEW"
        result["suppressed"] = False

    return result
