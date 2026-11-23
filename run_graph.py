import time

from app.gmail_client import fetch_unread
from app.graph import build_graph


def main():
    graph = build_graph()
    mails = fetch_unread(max_results=5)
    if not mails:
        print("Koi unread mail nahi mili.")
        return

    for i, m in enumerate(mails, 1):
        print(f"\n=== Mail {i}: {m['subject']} ({m['from']}) ===")
        graph.invoke({"mail": m})
        time.sleep(2)  # Groq free tier rate limit


if __name__ == "__main__":
    main()
