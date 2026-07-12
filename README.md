# Notice Scraper & Multi-Channel Alert System

An automated Python scraper and GitHub Actions workflow that checks [CUExam.net](https://cuexam.net/exam-notice.php) and [Scottish Church College](https://www.scottishchurch.ac.in/notice-board.php) every 24 hours for new notices. When new notices appear, it formats a clean alert message and delivers it instantly via your preferred messaging channels: **Telegram Bot**, **Discord Webhook**, and/or **Official WhatsApp Cloud API**.

Seen notice IDs are persisted in a lightweight JSON file (`seen_notices.json`) that is automatically committed back to the repository by GitHub Actions.

---

## ✨ Features

- **Automated Daily Monitoring**: Runs every 24 hours (`0 4 * * *` UTC) via GitHub Actions or on-demand via `workflow_dispatch`.
- **Multi-Source Scraping**:
  - **CUExam.net** (`https://cuexam.net/exam-notice.php`)
  - **Scottish Church College** (`https://www.scottishchurch.ac.in/notice-board.php`)
- **Multi-Channel Notifications**:
  - **Telegram Bot API**: Instant messages with zero SMS/business verification needed.
  - **Discord Webhooks**: Instant alerts to any Discord server channel.
  - **Official WhatsApp Cloud API**: Direct WhatsApp alerts via Meta's Graph API (`v21.0`).
- **Robust Networking**:
  - **Retries & Exponential Backoff**: Uses `urllib3.util.retry.Retry` for automatic retries on HTTP `429`, `500`, `502`, `503`, and `504` errors.
  - **Explicit Timeouts**: Custom HTTP adapter enforces a `15-second` timeout on all requests to prevent hanging.
- **Idempotent Persistence**: Tracks unique notice hashes in `seen_notices.json` to prevent duplicate alerts.
- **Daily Active Status Heartbeat**: Sends a daily confirmation message (`🤖 Notice Scraper Bot Active`) when no new notices are found, so you always know the bot ran successfully.
- **Spam Prevention**: On its very first run (when `seen_notices.json` is empty), the scraper seeds existing notices silently without blasting historical alerts.

---

## 🔐 Setup Instructions for Secrets (Multi-Channel Alerts)

To keep your credentials secure, **no secrets are hardcoded in the codebase**. You can configure any combination of **WhatsApp Cloud API**, **Telegram Bot**, or **Discord Webhook** by setting environment variables or GitHub Repository Secrets.

### Option A: Telegram Bot Setup (Instant — No SMS Verification Required!)
1. Open Telegram and message **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot`, name your bot, and save the **HTTP API Token** (`TELEGRAM_BOT_TOKEN`).
3. Message **[@userinfobot](https://t.me/userinfobot)** on Telegram to get your numeric **Chat ID** (`TELEGRAM_CHAT_ID`).

### Option B: Discord Webhook Setup (Instant — Under 60 Seconds!)
1. Open your Discord server → go to **Channel Settings** → **Integrations** → **Webhooks**.
2. Click **New Webhook** → **Copy Webhook URL** (`DISCORD_WEBHOOK_URL`).

### Option C: Official WhatsApp Cloud API Setup
1. Go to the [Meta for Developers Portal](https://developers.facebook.com/) and log in.
2. Click **My Apps** → **Create App** → select **Other** → **Business** application type.
3. In your new App Dashboard, scroll to **WhatsApp** and click **Set up**.
4. Navigate to **WhatsApp > API Setup** in the left menu.
5. Note your **Phone Number ID** (`WHATSAPP_PHONE_NUMBER_ID`) and **Access Token** (`WHATSAPP_TOKEN`).
6. Note your recipient phone number (`WHATSAPP_RECIPIENT_PHONE_NUMBER`) in standard E.164 format without `+` (e.g., `919876543210`).

---

### Configure GitHub Repository Secrets

Open your repository on GitHub.com → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**. Add whichever notification channel(s) you wish to use:

| Secret Name | Description | Required For |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API HTTP Token from BotFather | Telegram Alerts |
| `TELEGRAM_CHAT_ID` | Your numeric Telegram Chat ID | Telegram Alerts |
| `DISCORD_WEBHOOK_URL` | Full Discord Channel Webhook URL | Discord Alerts |
| `WHATSAPP_TOKEN` | Meta API Access Token | WhatsApp Alerts |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business Phone Number ID | WhatsApp Alerts |
| `WHATSAPP_RECIPIENT_PHONE_NUMBER` | Recipient phone number (country code + number) | WhatsApp Alerts |

---

### 3. Enable GitHub Actions Write Permissions

The workflow automatically commits new notice IDs back to `seen_notices.json` so state is preserved between runs.

1. In your GitHub repository, go to **Settings** → **Actions** → **General**.
2. Scroll down to **Workflow permissions**.
3. Select **Read and write permissions**.
4. Click **Save**.

---

## 🚀 Running Locally

### 1. Installation

Requires Python 3.10+.

```bash
# Clone repository
git clone <your-repo-url>
cd notice_scrapper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Scraper Locally

#### Option A: Dry Run (No alerts or file updates)
Great for testing scraping logic safely without sending notifications or modifying state:
```bash
python scraper.py --dry-run
```

#### Option B: Full Run with Notifications
Configure any combination of Telegram, Discord, or WhatsApp environment variables and execute:
```bash
# Example 1: Telegram Alerts
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# Example 2: Discord Alerts
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# Example 3: WhatsApp Alerts
export WHATSAPP_TOKEN="your_access_token"
export WHATSAPP_PHONE_NUMBER_ID="your_phone_number_id"
export WHATSAPP_RECIPIENT_PHONE_NUMBER="919876543210"

python scraper.py
```

#### Option C: Force Alerting All Notices on Initial Seed
By default, the first run seeds `seen_notices.json` silently. To send alerts for all discovered notices even on initial setup:
```bash
python scraper.py --notify-all
```

#### Option D: Suppress Daily Active Status Heartbeat
By default, when no new notices are found, the bot sends an active status confirmation message so you know it ran. To disable this message:
```bash
python scraper.py --no-heartbeat
```

---

## 📂 Project Structure

```text
notice_scrapper/
├── .github/
│   └── workflows/
│       └── scrape_notices.yml   # Daily 24h cron workflow + auto-commit
├── scraper.py                   # Core scraper with multi-channel alerts (Telegram, Discord, WhatsApp)
├── seen_notices.json            # Lightweight JSON persistence state
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```
