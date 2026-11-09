
from datetime import datetime, timezone
from math import isfinite

import requests
import yfinance as yf
from django.core.management.base import BaseCommand, CommandError

from viewer.models import DailyPrice, NewsArticle
from viewer.news_analysis import analyze_headline


class Command(BaseCommand):
    help = "Import financial news and daily stock prices"

    def add_arguments(self, parser):
        parser.add_argument("--ticker", required=True)
        parser.add_argument("--company", required=True)
        parser.add_argument("--days", type=int, default=60)
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        ticker = options["ticker"].strip().upper()
        company = options["company"].strip()
        days = options["days"]
        limit = options["limit"]

        if not ticker or not company:
            raise CommandError("Ticker and company cannot be empty.")

        if not 1 <= days <= 90:
            raise CommandError("Days must be between 1 and 90.")

        if not 1 <= limit <= 250:
            raise CommandError("Limit must be between 1 and 250.")

        # Download daily stock prices
        self.stdout.write(f"Downloading {ticker} stock prices...")

        try:
            prices = yf.Ticker(ticker).history(
                period="6mo",
                interval="1d",
                auto_adjust=True
            )
        except Exception as error:
            raise CommandError(f"Stock download failed: {error}") from error

        if prices.empty:
            raise CommandError("No stock prices were returned.")

        price_count = 0

        for date, row in prices.iterrows():
            try:
                values = {
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                }
                volume = int(row["Volume"])
            except (TypeError, ValueError, OverflowError):
                continue

            if not all(isfinite(value) for value in values.values()):
                continue

            DailyPrice.objects.update_or_create(
                ticker=ticker,
                date=date.date(),
                defaults={
                    **values,
                    "volume": volume,
                }
            )
            price_count += 1

        self.stdout.write(f"Saved {price_count} daily prices.")

        # Search for company-related financial news
        self.stdout.write(f"Downloading {company} news...")

        query = (
            f'"{company}" '
            '(earnings OR revenue OR shares OR stock OR lawsuit OR production) '
            'sourcelang:english'
        )

        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "timespan": f"{days}d",
            "maxrecords": limit,
            "sort": "DateAsc",
        }

        try:
            response = requests.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            articles = response.json().get("articles", [])
        except (requests.RequestException, ValueError) as error:
            self.stdout.write(
                self.style.WARNING(f"News download failed: {error}")
            )
            return

        news_count = 0

        for article in articles:
            headline = article.get("title", "").strip()
            url = article.get("url", "")
            seen_date = article.get("seendate")

            if not headline or not url or not seen_date:
                continue

            if not url.startswith(("http://", "https://")):
                continue

            try:
                first_seen = datetime.strptime(
                    seen_date, "%Y%m%dT%H%M%SZ"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            category, sentiment, score = analyze_headline(headline)

            NewsArticle.objects.update_or_create(
                ticker=ticker,
                url=url,
                defaults={
                    "headline": headline[:500],
                    "source": article.get("domain", "Unknown")[:200],
                    "first_seen_at": first_seen,
                    "event_category": category,
                    "sentiment": sentiment,
                    "sentiment_score": score,
                }
            )
            news_count += 1

        self.stdout.write(f"Saved {news_count} news articles.")
        self.stdout.write(self.style.SUCCESS("Import complete."))
