# Financial Market Insights

A Flask web app for US and ASX equities: interactive candlestick charts, technical indicators, Finnhub news, and earnings/macro events.

**For research only — not investment advice.**

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
copy .env.example .env          # add Finnhub key for news/events (optional)
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `FINNHUB_API_KEY` | For news & events | [Finnhub](https://finnhub.io/register) free tier |

Charts and quotes work with **yfinance only**; Finnhub unlocks the news and events panels.

## Project layout

```
Financial-Market-Analysis/
├── app.py                 # Entry point
├── requirements.txt
├── .env.example
├── fmi/
│   ├── config.py
│   ├── quotes.py          # yfinance quotes & OHLC
│   ├── web/               # Flask routes
│   ├── analysis/          # Indicators & insight cards
│   ├── data/              # Macro calendar
│   ├── integrations/finnhub/
│   └── services/events.py
├── templates/
└── static/css/  static/js/
```

## Main URLs

| Path | Description |
|------|-------------|
| `/` | Home — ticker lookup & watchlist compare |
| `/ticker/<symbol>?market=us\|asx` | Chart dashboard |
| `/api/ohlc` | Candlestick data + indicators |
| `/api/quote` | Quote + history |
| `/api/news` | Finnhub headlines |
| `/api/events` | Earnings & macro calendar |

## Default watchlist

NDQ, VAS, VGS (ASX) · NVTS, ETHA (US)
