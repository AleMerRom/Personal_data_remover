import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import tracker

BROKERS_FILE = "brokers.json"

# --- Configuration (set these via environment variables) ---
MY_EMAIL = os.environ.get("MY_EMAIL", "your@email.com")
MY_NAME = os.environ.get("MY_NAME", "Your Name")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")


def load_brokers():
    with open(BROKERS_FILE) as f:
        return json.load(f)["brokers"]


def gdpr_email_body(broker_name: str) -> str:
    return f"""Dear Data Protection Officer,

I am writing to exercise my right to erasure under Article 17 of the General Data \
Protection Regulation (GDPR).

I request that you immediately delete all personal data you hold that is linked to \
my email address: {MY_EMAIL}

This includes, but is not limited to:
- My name
- My address(es)
- My phone number(s)
- Any other personal information associated with my email address

Please confirm in writing that the data has been erased and that it has been removed \
from any third parties to whom it may have been disclosed, as required by Article 19 GDPR.

I expect a response within 30 days as stipulated by Article 12(3) GDPR.

Kind regards,
{MY_NAME}
{MY_EMAIL}
"""


def send_email(to_address: str, broker_name: str) -> bool:
    """Send a GDPR erasure request email. Returns True on success."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"  [!] SMTP credentials not set. Skipping email to {broker_name}.")
        return False

    msg = MIMEMultipart()
    msg["From"] = MY_EMAIL
    msg["To"] = to_address
    msg["Subject"] = f"GDPR Article 17 – Right to Erasure Request ({MY_EMAIL})"
    msg.attach(MIMEText(gdpr_email_body(broker_name), "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(MY_EMAIL, to_address, msg.as_string())
        print(f"  [✓] Email sent to {broker_name} ({to_address})")
        return True
    except Exception as e:
        print(f"  [✗] Failed to send email to {broker_name}: {e}")
        return False


def handle_form_broker(broker: dict):
    """Placeholder for Playwright-based form automation."""
    print(f"  [~] Form-based broker: {broker['name']} — automation not yet implemented.")
    print(f"      Manual opt-out URL: {broker.get('opt_out_url', 'N/A')}")
    tracker.set_status(broker["name"], "pending", notes="Awaiting form automation")


def process_broker(broker: dict):
    removal_type = broker.get("removal_type", "none")

    if removal_type == "none":
        print(f"  [-] {broker['name']} — monitoring only, skipping.")
        tracker.set_status(broker["name"], "done", notes="Monitoring only, no removal needed")
        return

    if removal_type == "email":
        dpo_email = broker.get("dpo_email")
        if not dpo_email:
            print(f"  [!] {broker['name']} — no DPO email defined, skipping.")
            tracker.set_status(broker["name"], "failed", notes="No DPO email defined")
            return
        success = send_email(dpo_email, broker["name"])
        if success:
            tracker.set_status(broker["name"], "sent")
        else:
            tracker.set_status(broker["name"], "failed", notes="Email send failed")

    elif removal_type == "form":
        handle_form_broker(broker)


def main():
    print("=== Personal Data Removal Tool ===\n")

    # Init DB
    tracker.init_db()

    # Load brokers and register any new ones in the tracker
    brokers = load_brokers()
    for broker in brokers:
        tracker.upsert_broker(broker["name"], broker.get("removal_type", "unknown"))

    # Only process brokers that haven't been contacted yet
    pending_names = {r["broker_name"] for r in tracker.get_pending()}
    pending_brokers = [b for b in brokers if b["name"] in pending_names]

    if not pending_brokers:
        print("All brokers have already been contacted. Nothing to do.\n")
    else:
        print(f"Processing {len(pending_brokers)} pending broker(s)...\n")
        for broker in pending_brokers:
            print(f"[{broker['name']}]")
            process_broker(broker)

    print("\n--- Status Summary ---")
    tracker.print_summary()


if __name__ == "__main__":
    main()
