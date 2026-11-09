
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


analyzer = SentimentIntensityAnalyzer()

# Keywords used to identify different financial news events
EVENT_KEYWORDS = {
    "Earnings": ["earnings", "quarterly", "revenue", "profit", "guidance"],
    "Acquisition": ["acquisition", "merger", "acquire", "takeover"],
    "Legal": ["lawsuit", "sued", "litigation", "settlement"],
    "Executive": ["ceo", "cfo", "executive", "resigns", "appointed"],
    "Product": ["product", "launch", "unveils", "release"],
    "Dividend": ["dividend"],
    "Regulatory": ["regulator", "antitrust", "fda", "investigation"],
    "Financing": ["financing", "stock offering", "debt offering"],
}


def analyze_headline(headline):
    text = headline.lower()

    category = "Other"

    for event, keywords in EVENT_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            category = event
            break

    score = analyzer.polarity_scores(headline)["compound"]

    if score >= 0.05:
        sentiment = "positive"
    elif score <= -0.05:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return category, sentiment, round(score, 4)
