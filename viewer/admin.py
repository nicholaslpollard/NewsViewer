
from django.contrib import admin
from .models import NewsArticle, DailyPrice


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = (
        "ticker", "headline", "event_category",
        "sentiment", "sentiment_score", "first_seen_at"
    )
    list_filter = ("ticker", "event_category", "sentiment")
    search_fields = ("ticker", "headline")


@admin.register(DailyPrice)
class DailyPriceAdmin(admin.ModelAdmin):
    list_display = ("ticker", "date", "open", "high", "low", "close", "volume")
    list_filter = ("ticker",)
    search_fields = ("ticker",)
