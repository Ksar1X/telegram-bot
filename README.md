# 📱 iPhone Listings Bot

Telegram bot that monitors **OLX**, **Allegro**, and **Vinted** for new iPhone listings and sends instant alerts.

Monitors: iPhone 14, 14 Pro, 15, 15 Pro, 16, 16 Pro.

---

## Setup

### 1. Clone / copy the project

```bash
cd iphone-bot
```

### 2. Install dependencies

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Your numeric chat ID (see guide) |
| `POLL_INTERVAL_SECONDS` | How often to check (default: 300) |

### 4. Run

```bash
python bot.py
```

The bot will send a startup message to your Telegram and begin monitoring.

---

## Telegram Commands

| Command | Action |
|---|---|
| `/start` | Enable alerts |
| `/stop` | Disable alerts |
| `/status` | Check if alerts are on or off |

---

## Project Structure

```
iphone-bot/
├── bot.py              # Entry point, Telegram command handler
├── scheduler.py        # Polling loop
├── notifier.py         # Telegram message formatter & sender
├── db.py               # SQLite deduplication
├── listing.py          # Shared Listing dataclass
├── config.py           # Environment config
├── http_client.py      # Shared HTTP client, UA rotation, delays
├── sources/
│   ├── olx.py          # OLX internal JSON API
│   ├── allegro.py      # Allegro HTML scraper
│   └── vinted.py       # Vinted internal catalog API
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Notes

- **Deduplication**: All seen listing IDs are stored in `seen_listings.db`. The bot will never send the same listing twice, even across restarts.
- **Rate limiting**: Random 2–8 second delays are added between each request. Do not lower `POLL_INTERVAL_SECONDS` below 120.
- **Allegro scraping**: Allegro's HTML structure may change. If Allegro stops returning results, the scraper may need updating.
- **Logs**: Written to both stdout and `bot.log`.

---

## Running as a Service (VPS)

To keep the bot running after you log out, use `systemd` or `screen`:

```bash
# With screen:
screen -S iphone-bot
python bot.py
# Ctrl+A then D to detach

# Or with nohup:
nohup python bot.py > /dev/null 2>&1 &
```
