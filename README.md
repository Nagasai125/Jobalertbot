# Job Alert Notification System

A real-time job monitoring system that scrapes company career pages, filters jobs by keywords, and sends notifications via Telegram and Email.

## Features

- 🔍 **Multi-company scraping** - Monitor multiple company career pages
- 🎯 **Smart keyword matching** - Tokenized, exact, and fuzzy matching modes
- 📧 **Multi-channel notifications** - Telegram and Email support
- 🗄️ **Deduplication** - SQLite storage prevents duplicate alerts
- ⏰ **Scheduled polling** - Configurable check intervals
- 🐳 **Docker support** - Easy deployment with Docker Compose

## Quick Start

### 1. Clone and Install

```bash
cd /path/to/MCP
pip install -r requirements.txt
```

### 2. Configure

Edit `config/config.yaml` to set:
- Target companies and their career page URLs
- Keywords to match (job titles, locations)
- Notification preferences

### 3. Set Up Notifications

#### Telegram
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow prompts to create a bot
3. Copy the bot token
4. Message [@userinfobot](https://t.me/userinfobot) to get your chat ID
5. Set environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_token"
   export TELEGRAM_CHAT_ID="your_chat_id"
   ```

#### Email (Gmail)
1. Enable 2-Factor Authentication in your Google Account
2. Go to Security → App Passwords → Generate new password
3. Set environment variables:
   ```bash
   export EMAIL_SENDER="your_email@gmail.com"
   export EMAIL_PASSWORD="your_app_password"
   export EMAIL_RECIPIENT="recipient@example.com"
   ```

### 4. Run

```bash
# Test scraping (no notifications)
python -m job_alerts.main --test-scrape

# Test notifications
python -m job_alerts.main --test-notify

# Run once
python -m job_alerts.main --once

# Run with scheduling (default: every 10 minutes)
python -m job_alerts.main
```

## Docker Deployment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env

# Build and run
docker-compose up -d

# View logs
docker-compose logs -f
```

## Configuration

### config/config.yaml

```yaml
polling:
  interval_minutes: 10

companies:
  - name: "GitHub"
    url: "https://github.com/about/careers"
    scraper: "github"
  - name: "Stripe"
    url: "https://stripe.com/jobs/search"
    scraper: "stripe"
  - name: "Custom Company"
    url: "https://example.com/careers"
    scraper: "generic"

keywords:
  include:
    - "Software Engineer"
    - "Data Scientist"
    - "Machine Learning"
  exclude: []  # Optional: exclude terms like "intern"
  locations:
    - "Remote"
    - "San Francisco"

matching:
  mode: "tokenized"  # exact | tokenized | fuzzy
  fuzzy_threshold: 0.85
```

### Matching Modes

| Mode | Description | Example |
|------|-------------|---------|
| `exact` | Case-insensitive substring | "engineer" matches "Software Engineer" |
| `tokenized` | Matches base keywords, ignores modifiers | "Software Engineer" matches "Software Engineer II" |
| `fuzzy` | Similarity-based (85% default) | "Data Scientist" matches "Data Science Engineer" |

## Adding New Companies

1. For most sites, use the `generic` scraper:
   ```yaml
   companies:
     - name: "New Company"
       url: "https://newcompany.com/careers"
       scraper: "generic"
   ```

2. For complex sites, create a custom scraper in `job_alerts/scrapers/`:
   ```python
   from .base import BaseScraper
   
   class NewCompanyScraper(BaseScraper):
       def scrape(self):
           # Custom scraping logic
           pass
   ```

## Project Structure

```
MCP/
├── job_alerts/
│   ├── main.py           # Entry point
│   ├── config.py         # Configuration loader
│   ├── database.py       # SQLite storage
│   ├── scheduler.py      # APScheduler setup
│   ├── scrapers/         # Company scrapers
│   ├── matchers/         # Keyword matching
│   └── notifiers/        # Notification channels
├── config/
│   └── config.yaml       # Configuration
├── data/                 # SQLite database
├── logs/                 # Log files
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Troubleshooting

### No jobs found
- Check the career page URL is correct
- Run with `--test-scrape` to see raw output
- Try the `generic` scraper if custom one fails

### Telegram not working
- Verify bot token with `curl https://api.telegram.org/bot<TOKEN>/getMe`
- Ensure you've started a chat with your bot first
- Check chat_id is correct (should be a number)

### Email not sending
- For Gmail, use App Passwords (not your regular password)
- Check SMTP settings if using custom server
- Look for errors in `logs/job_alerts.log`

## License

MIT
