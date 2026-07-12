# Notice Scraper & WhatsApp Alert System

An automated Python scraper and GitHub Actions workflow that checks [CUExam.net](https://cuexam.net/exam-notice.php) and [Scottish Church College](https://www.scottishchurch.ac.in/notice-board.php) every 24 hours for new notices. When new notices appear, it formats a clean alert message and delivers it directly to your phone via the **Official WhatsApp Cloud API**.

Seen notice IDs are persisted in a lightweight JSON file (`seen_notices.json`) that is automatically committed back to the repository by GitHub Actions.

---

## ✨ Features

- **Automated Daily Monitoring**: Runs every 24 hours (`0 4 * * *` UTC) via GitHub Actions or on-demand via `workflow_dispatch`.
- **Multi-Source Scraping**:
  - **CUExam.net** (`https://cuexam.net/exam-notice.php`)
  - **Scottish Church College** (`https://www.scottishchurch.ac.in/notice-board.php`)
- **Official WhatsApp Cloud API**: Uses Meta's Graph API (`v21.0`) to send secure, reliable WhatsApp messages without third-party scrapers or headless browsers.
- **Robust Networking**:
  - **Retries & Exponential Backoff**: Uses `urllib3.util.retry.Retry` for automatic retries on HTTP `429`, `500`, `502`, `503`, and `504` errors.
  - **Explicit Timeouts**: Custom HTTP adapter enforces a `15-second` timeout on all requests to prevent hanging.
- **Idempotent Persistence**: Tracks unique notice hashes in `seen_notices.json` to prevent duplicate alerts.
- **Spam Prevention**: On its very first run (when `seen_notices.json` is empty), the scraper seeds existing notices silently without blasting historical alerts.

---

## 🔐 Setup Instructions for Secrets (WhatsApp Cloud API)

To keep your credentials secure, **no secrets are hardcoded in the codebase**. All sensitive values must be passed as environment variables.

### 1. Get Official WhatsApp Cloud API Credentials

1. Go to the [Meta for Developers Portal](https://developers.facebook.com/) and log in.
2. Click **My Apps** → **Create App** → select **Other** → **Business** application type.
3. In your new App Dashboard, scroll to **WhatsApp** and click **Set up**.
4. Navigate to **WhatsApp > API Setup** in the left menu.
5. Note the following values:
   - **Phone Number ID**: Your WhatsApp test or production Phone Number ID.
   - **Access Token**: Either a temporary token (for quick testing) or a permanent System User Token generated via Business Settings.
6. **Recipient Phone Number**: Ensure the recipient number is registered/verified in your WhatsApp API dashboard and formatted in standard **E.164 format without the `+` sign** (e.g., `919876543210`).

---

### 2. Configure GitHub Repository Secrets

To enable GitHub Actions to send WhatsApp alerts:

1. Open your GitHub repository on GitHub.com.
2. Navigate to **Settings** → **Secrets and variables** → **Actions**.
3. Click **New repository secret** and add each of the following:

| Secret Name | Description | Example Value |
| :--- | :--- | :--- |
| `WHATSAPP_TOKEN` | Meta API Access Token (Bearer Token) | `EAAG...` |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Phone Number ID | `104829103948...` |
| `WHATSAPP_RECIPIENT_PHONE_NUMBER` | Recipient phone number with country code | `919876543210` |

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

#### Option A: Dry Run (No WhatsApp alerts or file updates)
Great for testing scraping logic safely:
```bash
python scraper.py --dry-run
```

#### Option B: Full Run with WhatsApp Notification
Set your environment variables and execute:
```bash
export WHATSAPP_TOKEN="your_access_token"
export WHATSAPP_PHONE_NUMBER_ID="your_phone_number_id"
export WHATSAPP_RECIPIENT_PHONE_NUMBER="919876543210"

python scraper.py
```

#### Option C: Force Alerting All Notices on Initial Seed
By default, the first run seeds `seen_notices.json` silently. To send WhatsApp alerts for all discovered notices even on initial setup:
```bash
python scraper.py --notify-all
```

---

## 📂 Project Structure

```text
notice_scrapper/
├── .github/
│   └── workflows/
│       └── scrape_notices.yml   # Daily 24h cron workflow + auto-commit
├── scraper.py                   # Core scraper with retries, timeouts & WhatsApp API
├── seen_notices.json            # Lightweight JSON persistence state
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```
