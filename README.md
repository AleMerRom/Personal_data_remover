# Personal Data Remover

The idea of the project is to remove the personal data linked to an email address from databrokers. As an EU citizen, most of the databrokers will respect the GDPR rules, meaning that for the most part an email or a form will be enough to remove my data.

## Architecture

```
brokers.json          ← list of brokers + their opt-out method
  │
  ├─ email-based      → auto-generate & send GDPR Article 17 erasure request email
  └─ form-based       → Playwright automates the opt-out form

tracker.db            ← SQLite: status per broker (pending/sent/done/failed)
main.py               ← orchestrates everything
tracker.py            ← DB helpers
```

## How to run

### 1. Set your credentials

```bash
export MY_EMAIL="you@example.com"
export MY_NAME="Your Name"
export SMTP_USER="you@gmail.com"
export SMTP_PASSWORD="your_app_password"
```

> If you use Gmail, you cannot use your normal password. Generate an **App Password**:
> Google Account → Security → 2-Step Verification → App Passwords.

### 2. Run

```bash
python3 main.py
```

### What happens on first run

- Creates `tracker.db` automatically
- Registers all brokers as `pending`
- Sends GDPR Article 17 erasure emails to all email-based brokers
- Prints opt-out URLs for form-based brokers (Playwright automation coming later)
- Prints a full status summary at the end

### What happens on re-runs

- Already-contacted brokers are skipped — safe to re-run at any time
- Prints the current status table

### Dry run (no emails sent)

Leave `SMTP_USER` and `SMTP_PASSWORD` unset — the tool will skip sending and just print what it would do.

## Broker statuses

| Status | Meaning |
|--------|---------|
| `pending` | Not yet contacted |
| `sent` | Email sent or form submitted |
| `done` | Confirmed removed |
| `failed` | Something went wrong |


