

import re
from statistics import median
from zoneinfo import ZoneInfo

from django.shortcuts import render

from .models import DailyPrice, NewsArticle


COMMON_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "after", "before",
    "about", "into", "more", "than", "amid", "says", "said", "will", "its",
    "stock", "stocks", "shares", "company", "companies", "today", "new",
}

PERIODS = (1, 3, 5, 10)
MATCH_METHODS = ("sentiment", "headline", "category", "combined")
EASTERN = ZoneInfo("America/New_York")

def headline_words(headline, ticker):
    words = set(re.findall(r"[a-z0-9]+", headline.lower()))
    return words - COMMON_WORDS - {ticker.lower()}

def headline_similarity(first, second, ticker):
    first_words = headline_words(first.headline, ticker)
    second_words = headline_words(second.headline, ticker)

    all_words = first_words | second_words

    if not all_words:
        return 0.0

    return len(first_words & second_words) / len(all_words)


def match_score(selected, other, ticker, method):
    keyword_score = headline_similarity(selected, other, ticker)

    same_category = (
        selected.event_category == other.event_category
        and selected.event_category != "Other"
    )

    same_sentiment = selected.sentiment == other.sentiment

    # Only compare articles with matching sentiment.
    if method == "sentiment":
        if not same_sentiment:
            return None

        secondary_score = 0.7 * keyword_score + 0.3 * same_category
        return 1.0, secondary_score

    # Compare articles based on headline keywords.
    if method == "headline":
        if keyword_score < 0.10:
            return None

        secondary_score = 0.7 * same_category + 0.3 * same_sentiment
        return keyword_score, secondary_score

    # Compare articles belonging to the same event category.
    if method == "category":
        if not same_category:
            return None

        secondary_score = 0.7 * keyword_score + 0.3 * same_sentiment
        return 1.0, secondary_score

    # Combine all three methods.
    if not keyword_score and not same_category:
        return None

    combined_score = (
        0.50 * keyword_score
        + 0.35 * same_category
        + 0.15 * same_sentiment
    )

    if combined_score < 0.10:
        return None

    return combined_score, keyword_score


def price_reactions(article, prices):
    published = article.first_seen_at.astimezone(EASTERN)
    baseline_index = None

    for index, price in enumerate(prices):
        # Use the latest completed closing price before the article.
        if price.date < published.date() or (
            price.date == published.date() and published.hour >= 16
        ):
            baseline_index = index
        else:
            break

    results = {period: None for period in PERIODS}

    if baseline_index is None:
        return None, results

    baseline = prices[baseline_index].close

    if baseline <= 0:
        return None, results

    for period in PERIODS:
        target_index = baseline_index + period

        if target_index < len(prices):
            ending_price = prices[target_index].close
            results[period] = (ending_price / baseline - 1) * 100

    return baseline, results


def format_return(value):
    return f"{value:+.2f}%" if value is not None else "N/A"


def home(request):
    ticker = request.GET.get("ticker", "TSLA").strip().upper()

    if not re.fullmatch(r"[A-Z0-9.\-]{1,12}", ticker):
        ticker = "TSLA"

    period = request.GET.get("period", "all")

    if period not in ("all", "1", "3", "5", "10"):
        period = "all"

    # Sentiment is the default comparison method.
    match_method = request.GET.get("match", "sentiment")

    if match_method not in MATCH_METHODS:
        match_method = "sentiment"

    articles = list(
        NewsArticle.objects.filter(ticker=ticker)
        .order_by("-first_seen_at")[:10]
    )

    prices = list(
        DailyPrice.objects.filter(ticker=ticker).order_by("date")
    )

    selected_id = request.GET.get("article", "")
    selected = None

    if selected_id.isdigit():
        selected = NewsArticle.objects.filter(
            ticker=ticker,
            pk=int(selected_id)
        ).first()

    matches = []
    summary = {}

    if selected:
        selected_date = selected.first_seen_at.astimezone(EASTERN).date()

        candidates = NewsArticle.objects.filter(
            ticker=ticker,
            first_seen_at__lt=selected.first_seen_at
        ).exclude(pk=selected.pk)

        for other in candidates:
            # Only use events from dates before the selected article.
            other_date = other.first_seen_at.astimezone(EASTERN).date()

            if other_date >= selected_date:
                continue

            scores = match_score(
                selected, other, ticker, match_method
            )

            if scores is None:
                continue

            score, secondary_score = scores
            baseline, reactions = price_reactions(other, prices)

            if match_method == "sentiment":
                match_label = "Same sentiment"
            elif match_method == "category":
                match_label = "Same category"
            else:
                match_label = f"{score * 100:.0f}%"

            matches.append({
                "article": other,
                "score": score,
                "secondary_score": secondary_score,
                "match_label": match_label,
                "baseline": baseline,
                "returns": reactions,
                "d1": format_return(reactions[1]),
                "d3": format_return(reactions[3]),
                "d5": format_return(reactions[5]),
                "d10": format_return(reactions[10]),
            })

        matches.sort(
            key=lambda row: (
                row["score"],
                row["secondary_score"],
                row["article"].first_seen_at
            ),
            reverse=True
        )

        # Keep one representative article per date and category.
        distinct_matches = []
        seen_events = set()

        for row in matches:
            article = row["article"]

            event_key = (
                article.first_seen_at.astimezone(EASTERN).date(),
                article.event_category
            )

            if event_key in seen_events:
                continue

            seen_events.add(event_key)
            distinct_matches.append(row)

            if len(distinct_matches) == 10:
                break

        matches = distinct_matches

        # Calculate the historical summary for each period.
        for day in PERIODS:
            valid = [
                row["returns"][day]
                for row in matches
                if row["returns"][day] is not None
            ]

            summary[str(day)] = {
                "count": len(valid),
                "median": format_return(median(valid)) if valid else "N/A",
                "positive": (
                    round(100 * sum(value > 0 for value in valid) / len(valid))
                    if valid else None
                ),
            }

    return render(request, "viewer/home.html", {
        "ticker": ticker,
        "articles": articles,
        "selected": selected,
        "matches": matches,
        "summary": summary,
        "period": period,
        "match_method": match_method,
        "price_count": len(prices),
    })
