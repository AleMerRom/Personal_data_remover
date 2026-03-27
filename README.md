# My Project


The idea of the project is to remove the personal data linked to an email address from databrokers. As an EU citizen, most of the databrokers will respect the GDPR rules, meaning that for the most part an email or a form will be enough to remove my data. 

it seems like I will need this architecture 



Architecture

  brokers.json          ← list of brokers + their opt-out method
    │
    ├─ email-based      → auto-generate & send GDPR request email
    └─ form-based       → Playwright automates the form

  tracker.db            ← SQLite: status per broker (pending/sent/done)
  main.py               ← orchestrates everything


