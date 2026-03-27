# Personal Data Remover

A tool that automatically sends GDPR Article 17 erasure requests to data brokers on your behalf, then monitors your inbox for replies and updates the status of each request automatically using a local LLM.

Designed for EU citizens — data brokers are legally required to comply with GDPR erasure requests within 30 days.

> **Note:** The data brokers currently included in `brokers.json` are primarily EU-based or well-known global brokers that operate in Europe. US-only brokers are not the focus of this tool since they are not bound by GDPR.

---

## How it works

1. Sends a GDPR erasure email to each data broker linked to your email address
2. On subsequent runs, checks your inbox for replies from brokers
3. Uses a local LLM (Ollama) to classify each reply as `done`, `needs_action`, `failed`, or `needs_review`
4. Tracks the status of every request in a local SQLite database

---

## Architecture

```
brokers.json          ← list of brokers + their opt-out method
  │
  ├─ email-based      → sends GDPR Article 17 erasure request automatically
  ├─ manual           → prints the URL, requires manual submission (Google, Bing)
  └─ none             → skipped (HaveIBeenPwned, monitoring only)

tracker.db            ← SQLite database tracking status per broker
main.py               ← orchestrates everything (reply check + send emails)
check_replies.py      ← connects to Gmail API, classifies replies with Ollama
tracker.py            ← DB helpers + manual status update CLI
```

---

## Requirements

- Python 3.10+
- A Gmail account
- [Ollama](https://ollama.com) installed on your machine
- `make` (pre-installed on Mac/Linux)

---

## Setup

### Step 1 — Clone the repo and install dependencies

```bash
git clone <repo-url>
cd Personal_data_remover
make install
```

This creates a virtual environment and installs all dependencies automatically.

---

### Step 2 — Gmail API setup

The tool needs read access to your inbox to detect broker replies. Your data never leaves your machine.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in with the Gmail account you will use
2. Click the project dropdown (top left) → **New Project** → give it any name → **Create**
3. In the search bar type **Gmail API** → click it → click **Enable**
4. Go to **APIs & Services → OAuth consent screen**
   - Click **Get started** (or **Create**)
   - Fill in **App name** (anything, e.g. `Data Remover`) and your email address
   - Save and continue through all steps
   - On the **Test users** step, click **+ Add users** → add your Gmail address → Save
5. Go to **APIs & Services → Credentials**
   - Click **+ Create Credentials → OAuth client ID**
   - Choose **Desktop app** → give it any name → **Create**
   - Click **Download JSON** in the popup
6. Rename the downloaded file to `credentials.json` and place it in the project folder

> The first time you run the tool, a browser window will open asking you to authorise access. Click **Allow**. After that, a `token.json` file is saved locally and the browser will never open again.

---

### Step 3 — Ollama setup

The tool uses a local LLM to classify broker reply emails. No data is sent to any external service.

1. Download and install Ollama from [ollama.com](https://ollama.com)
2. Pull a model (we recommend `mistral`):
```bash
ollama pull mistral
```
3. Ollama runs as a background service on your machine — you do not need to start it manually each time

> To use a different model, set `OLLAMA_MODEL` in your `.env` file (see next step).

---

### Step 4 — Create your `.env` file

Create a file called `.env` in the project folder with the following content:

```
MY_EMAIL=you@gmail.com
MY_NAME=Your Full Name
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your_app_password
OLLAMA_MODEL=mistral
```

**How to get your App Password (required for Gmail):**
1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Go to **Security → 2-Step Verification** (must be enabled)
3. Scroll down to **App Passwords**
4. Create a new one named `data-remover` → copy the 16-character password
5. Paste it as the value for `SMTP_PASSWORD` in your `.env` file

> Your normal Gmail password will not work — you must use an App Password.

---

## How to run

### First run — sends all erasure emails

```bash
make run
```

On the first run it will:
- Create `tracker.db` automatically
- Send GDPR Article 17 erasure emails to all data brokers
- Print the opt-out URLs for Google and Bing (requires manual submission)
- Print a full status summary

### Subsequent runs — check replies + send any pending emails

```bash
make run
```

On each subsequent run it will:
- Check your inbox for replies from brokers received after the request was sent
- Classify each reply using Ollama and update the tracker automatically
- Skip brokers that have already been contacted
- Print a status summary

### Check replies only (without sending emails)

```bash
make check
```

### View the current status of all brokers

```bash
make summary
```

---

## Updating statuses manually

Statuses are updated automatically when the reply checker runs. You can also update them manually if needed:

```bash
# Mark a broker as done
python3 tracker.py --mark-done "Spokeo"

# Mark a broker as needing action (e.g. they asked for more info)
python3 tracker.py --mark-action "Spokeo" "Requested identity verification"

# Mark a broker as failed (e.g. no reply after 30 days)
python3 tracker.py --mark-failed "Spokeo" "No reply after 30 days"

# View full status summary
python3 tracker.py --summary
```

---

## Broker statuses

| Status | Meaning | Set by |
|--------|---------|--------|
| `pending` | Not yet contacted | Automatic |
| `sent` | Erasure email sent successfully | Automatic |
| `done` | Broker confirmed deletion | Automatic (Ollama) / Manual |
| `needs_action` | Broker replied asking for more information | Automatic (Ollama) / Manual |
| `needs_review` | Reply is unclear — check your inbox manually | Automatic (Ollama) |
| `failed` | Broker refused, or email failed to send | Automatic (Ollama) / Manual |

---

## Future work

### Automatic form submission for brokers that don't accept emails

Some brokers (e.g. TruePeopleSearch, Google, Bing) do not accept GDPR erasure requests by email and require you to submit a web form manually. The goal is to automate this using [Playwright](https://playwright.dev/python/), a browser automation library.

Each broker would have its own handler that:
1. Opens the opt-out page in a headless browser
2. Fills in the required fields automatically
3. Submits the form
4. Updates the tracker

This would eliminate the remaining manual steps and make the tool fully autonomous.

---

## Important notes

- `credentials.json`, `token.json`, `tracker.db`, and `.env` are all listed in `.gitignore` and will never be pushed to Git
- Each user must create their own Gmail API project — your credentials are never shared
- GDPR requires brokers to respond within 30 days — run `make check` periodically to monitor replies
- Some brokers (Google, Bing) require manual form submission — links are printed when you run the tool
