
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from math import isfinite
import xml.etree.ElementTree as ET

import requests
import yfinance as yf
from django.core.management.base import BaseCommand, CommandError

from viewer.models import DailyPrice, NewsArticle
from viewer.news_analysis import analyze_headline


class Command(BaseCommand):
    help = "Import daily prices and financial news without an API key"

    def add_arguments(self, parser):
        parser.add_argument("--ticker", required=True)
        parser.add_argument("--company", required=True)
        parser.add_argument("--lookback", type=int, default=180)

    def handle(self, *args, **options):
        ticker = options["ticker"].strip().upper()
        company = options["company"].strip()
        lookback = options["lookback"]
        if not ticker or not company or not 30 <= lookback <= 360:
            raise CommandError("Provide a ticker, company, and lookback of 30–360 days.")

        # Import a year of adjusted daily prices for the comparison windows.
        self.stdout.write(f"Downloading {ticker} prices...")
        try:
            history = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=True)
            if history.empty:
                self.stdout.write(self.style.WARNING("No stock prices were returned."))
            else:
                saved = 0
                for day, row in history.iterrows():
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
                        date=day.date(),
                        defaults={**values, "volume": volume},
                    )
                    saved += 1
                self.stdout.write(f"Saved {saved} daily prices.")
        except Exception as error:
            self.stdout.write(self.style.WARNING(f"Price download failed: {error}"))

        # Query Google News RSS in smaller date windows for older articles.
        today = datetime.now(timezone.utc).date()
        saved_news = 0
        for days_back in range(0, lookback, 60):
            end = today + timedelta(days=1 - days_back)
            start = max(end - timedelta(days=60), today - timedelta(days=lookback))
            query = (
                f'"{company}" (stock OR earnings OR revenue OR shares OR lawsuit) '
                f'after:{start.isoformat()} before:{end.isoformat()}'
            )
            self.stdout.write(f"Searching news from {start} to {end}...")
            try:
                response = requests.get(
                    "https://news.google.com/rss/search",
                    params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                    headers={"User-Agent": "Mozilla/5.0 (compatible; NewsViewer/1.0)"},
                    timeout=25,
                )
                response.raise_for_status()
                root = ET.fromstring(response.content)
            except (requests.RequestException, ET.ParseError) as error:
                self.stdout.write(self.style.WARNING(f"News search unavailable: {error}"))
                continue

            for item in root.findall("./channel/item")[:50]:
                headline = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                published = (item.findtext("pubDate") or "").strip()
                publisher = (item.findtext("source") or "Google News").strip()
                if not headline or not link or not published:
                    continue
                if not link.startswith(("https://", "http://")):
                    continue
                if headline.endswith(" - " + publisher):
                    headline = headline[:-(len(publisher) + 3)]
                try:
                    published_at = parsedate_to_datetime(published)
                    if published_at.tzinfo is None:
                        published_at = published_at.replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue

                category, sentiment, score = analyze_headline(headline)
                _, created = NewsArticle.objects.update_or_create(
                    ticker=ticker,
                    url=link,
                    defaults={
                        "headline": headline[:500],
                        "source": publisher[:200],
                        "first_seen_at": published_at,
                        "event_category": category,
                        "sentiment": sentiment,
                        "sentiment_score": score,
                    },
                )
                if created:
                    saved_news += 1

        total_news = NewsArticle.objects.filter(ticker=ticker).count()
        total_prices = DailyPrice.objects.filter(ticker=ticker).count()
        self.stdout.write(f"Added {saved_news} news articles. Database now contains:")
        self.stdout.write(f"{ticker}: {total_news} news articles, {total_prices} daily prices.")
        if total_news == 0:
            self.stdout.write(self.style.WARNING("No news available; try again later or another ticker."))
