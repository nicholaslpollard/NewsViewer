
from django.db import models


class NewsArticle(models.Model):
    ticker = models.CharField(max_length=12, db_index=True)
    headline = models.CharField(max_length=500)
    url = models.URLField(max_length=1000)
    source = models.CharField(max_length=200)
    first_seen_at = models.DateTimeField()
    event_category = models.CharField(max_length=50, default="Other")
    sentiment = models.CharField(max_length=10, default="neutral")
    sentiment_score = models.FloatField(default=0.0)

    class Meta:
        ordering = ['-first_seen_at']
        constraints = [
            models.UniqueConstraint(
                fields=['ticker', 'url'],
                name='unique_news_article'
            )
        ]

    def __str__(self):
        return f"{self.ticker}: {self.headline}"


class DailyPrice(models.Model):
    ticker = models.CharField(max_length=12, db_index=True)
    date = models.DateField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.BigIntegerField()

    class Meta:
        ordering = ['ticker', 'date']
        constraints = [
            models.UniqueConstraint(
                fields=['ticker', 'date'],
                name='unique_daily_price'
            )
        ]

    def __str__(self):
        return f"{self.ticker} - {self.date}"
