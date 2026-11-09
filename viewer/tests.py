
from django.test import TestCase

from .models import DailyPrice, NewsArticle


class DemoDataTests(TestCase):
    fixtures = ["demo_data.json"]

    def test_demo_data_loads(self):
        self.assertTrue(
            NewsArticle.objects.filter(ticker="TSLA").exists()
        )
        self.assertTrue(
            DailyPrice.objects.filter(ticker="TSLA").exists()
        )

    def test_homepage(self):
        response = self.client.get("/", {"ticker": "TSLA"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Available News Articles")

    def test_sentiment_comparison(self):
        article = NewsArticle.objects.filter(
            ticker="TSLA"
        ).order_by("-first_seen_at").first()

        response = self.client.get("/", {
            "ticker": "TSLA",
            "article": article.id,
            "match": "sentiment",
            "period": "all",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Similar Historical News")

        for match in response.context["matches"]:
            self.assertEqual(
                match["article"].sentiment,
                article.sentiment
            )
