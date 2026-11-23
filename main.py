import time

from app.classifier import analyze_mail
from app.drafter import draft_reply
from app.gmail_client import create_draft, fetch_unread


def main():
    mails = fetch_unread(max_results=5)
    if not mails:
        print("Koi unread mail nahi mili.")
        return

    for i, m in enumerate(mails, 1):
        print(f"\n--- Mail {i} ---")
        print("From   :", m["from"])
        print("Subject:", m["subject"])

        analysis = analyze_mail(m)
        print("Category   :", analysis.category)
        print("Summary    :", analysis.summary)
        print("Needs reply:", analysis.needs_reply)

        if analysis.needs_reply:
            reply = draft_reply(m, analysis)
            print("\nDraft reply:\n" + reply)
            draft_id = create_draft(m, reply)
            print(f"\n[Gmail Drafts mein save ho gaya, id: {draft_id}]")

        time.sleep(2)  # Groq free tier rate limit se bachne ke liye


if __name__ == "__main__":
    main()