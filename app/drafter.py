"""Groq LLM se mail ka reply draft likhwao."""
import os

from app.classifier import MailAnalysis, _get_llm

DRAFT_PROMPT = """You write email replies on behalf of {name}.
Rules:
- Reply in the same language as the incoming email.
- Be polite, short and clear (3-6 lines).
- Do NOT invent facts, dates, prices or commitments. If info is missing, politely ask for it.
- Do not promise anything on {name}'s behalf that is not in the email.
- End with a short sign-off using the name {name}.
- Output ONLY the email body text, no subject line, no extra commentary."""


def draft_reply(mail: dict, analysis: MailAnalysis) -> str:
    name = os.getenv("USER_NAME", "Adeela")
    llm = _get_llm()
    user_msg = (
        f"From: {mail['from']}\n"
        f"Subject: {mail['subject']}\n"
        f"Category: {analysis.category}\n"
        f"Summary: {analysis.summary}\n\n"
        f"Email body:\n{mail['body'][:2000]}"
    )
    result = llm.invoke(
        [("system", DRAFT_PROMPT.format(name=name)), ("human", user_msg)]
    )
    return result.content.strip()
