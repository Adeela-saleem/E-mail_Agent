import time

from app.classifier import analyze_mail
from app.gmail_client import fetch_unread


def main():
    mails = fetch_unread(max_results=5)
    if not mails:
        print("Koi unread mail nahi mili.")
        return

    for i, m in enumerate(mails, 1):
        print(f"\n--- Mail {i} ---")
        print("From   :", m["from"])
        print("Subject:", m["subject"])

        result = analyze_mail(m)
        print("Category   :", result.category)
        print("Summary    :", result.summary)
        print("Needs reply:", result.needs_reply)
        print("Reason     :", result.reason)

        time.sleep(2)  # Groq free tier rate limit se bachne ke liye


if __name__ == "__main__":
    main()
