"""Version 1 broad taxonomies; confidence from rules is uncalibrated."""

TOPICS = {
    "business.earnings": ("earnings", "quarterly results", "profit"),
    "business.mergers": ("acquisition", "acquire", "merger"),
    "markets.equities": ("stocks", "equities", "stock market"),
    "technology.ai": ("artificial intelligence", "machine learning", "ai"),
    "politics.policy": ("legislation", "policy", "parliament", "government"),
    "regional": ("municipal", "regional", "local council"),
    "company": ("company", "executive", "product launch"),
    "commodities": ("oil", "copper", "commodity", "wheat"),
    "economy": ("inflation", "interest rate", "gdp", "unemployment"),
    "business": ("business", "revenue", "trade"),
    "markets": ("bond", "currency", "market"),
    "technology": ("software", "technology", "cyber"),
    "politics/public-policy": ("election", "public policy"),
    "general": (),
}

EVENTS = {
    "company.earnings": ("earnings", "quarterly results"),
    "company.acquisition": ("acquisition", "acquire", "merger"),
    "company.executive_change": ("appointed", "resigned", "new ceo"),
    "company.product_launch": ("launched", "product launch", "unveiled"),
    "regulatory.action": ("regulator", "antitrust", "fined", "enforcement"),
    "policy.change": ("legislation", "policy change", "new law"),
    "economy.rate_change": ("rate cut", "rate hike", "interest rate"),
    "commodity.supply_disruption": ("supply disruption", "pipeline outage", "mine closure"),
    "security.cyber_incident": ("cyberattack", "ransomware", "data breach"),
    "general": (),
}

POSITIVE = ("growth", "strong", "gain", "gains", "improved", "success", "profit")
NEGATIVE = ("loss", "losses", "decline", "weak", "failed", "failure", "disruption")
