
# NewsViewer

Historical Analysis of Market Reactions to Financial News

## About the Project

NewsViewer is a Python Django application that helps users compare financial news with similar historical articles and see how stock prices reacted afterward.

The goal is to make historical financial news easier to research and understand. NewsViewer is intended for educational use and does not provide stock predictions or trading recommendations.

## Demo 1 Features

The current application allows users to:

- Search for saved financial news by stock ticker.
- Select a news article for historical comparison.
- View automatically classified news sentiment.
- Compare articles using sentiment and headline keywords of these methods.
- Display historical stock-price changes after 1, 3, 5, and 10 trading days.
- View summary statistics, including median returns and the percentage of positive outcomes.

Sentiment is the default comparison method.

## Technologies

- Python
- Django
- SQLite
- yfinance for historical stock prices
- Google News RSS for financial news
- VADER for headline sentiment analysis

The application stores financial news and daily OHLCV data locally.

## Installation

Python and pip are required.

1. Download or clone the repository.
2. Open a terminal in the NewsViewer project folder.
3. Create a virtual environment:

   python -m venv .venv

4. Activate the virtual environment.

   Windows PowerShell:

   .\.venv\Scripts\Activate.ps1

5. Install dependencies:

   python -m pip install -r requirements.txt

6. Create a file named `.env` in the project root and add:

   DJANGO_SECRET_KEY=your-own-random-secret-key

   Generate a secure Django secret key using Python's
   `django.core.management.utils.get_random_secret_key`
   function.

7. Initialize the database:

   python manage.py migrate

8. Load the included demonstration data:

   python -X utf8 manage.py loaddata viewer/fixtures/demo_data.json

9. Start the server:

   python manage.py runserver

10. Open http://127.0.0.1:8000/ in a browser.

## Using NewsViewer

Enter a stock ticker that has been imported into the database, such as TSLA.

Select an article and click Analyze.

Choose a comparison method and historical return period, then click Apply.

NewsViewer displays earlier matching articles and the stock's historical price changes following those events.

## Importing Additional Data

To import news and historical stock prices for another company, run:

python manage.py import_demo_data --ticker AAPL --company "Apple Inc" --lookback 180

This requires an internet connection. The news source may have limitations or return incomplete results.

The included demonstration data can be used without making new data requests.

## Testing

Run:

python -X utf8 manage.py test viewer

## Demo 1 Limitations

This is an initial proof of concept, not the completed semester project.

News sentiment is currently calculated from article headlines. News-feed timestamps may not always match original publisher timestamps.

Historical matches are ranked using basic similarity methods. Articles about the same event may still appear separately.

Price comparisons use daily historical closing prices. They are intended to provide historical context rather than predict future returns.

Additional improvements to classification, comparison methods, and the interface are planned for the completed project.
