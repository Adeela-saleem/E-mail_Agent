"""Groq LLM se mail ka reply draft likhwao (RAG context ke saath)."""
import os

from app.classifier import MailAnalysis, _get_llm
from app.rag import retrieve

DRAFT_PROMPT = """You write email replies on behalf of {name}.
Rules:
- Always write the reply in {language}, even if the incoming email is in another language or mixed (Roman Urdu / Hinglish).
- Use only the Latin alphabet. Never use Devanagari or Urdu script.
- Be polite, short and clear (3-6 lines).
- You may use the KNOWLEDGE section below, but only the parts relevant to this email.
- Do NOT invent facts, dates, prices or commitments. If the KNOWLEDGE section does not contain the needed info, politely ask for details or say {name} will get back soon.
- Do not promise anything on {name}'s behalf that is not in the email or the KNOWLEDGE section.
- End with a short sign-off using the name {name}.
- Output ONLY the email body text, no subject line, no extra commentary.

KNOWLEDGE:
{knowledge}"""


def draft_reply(mail: dict, analysis: MailAnalysis) -> str:
    name = os.getenv("USER_NAME", "Adeela")
    language = os.getenv("REPLY_LANGUAGE", "English")

    # RAG: mail ke subject + body se milti-julti info docs mein dhundo
    query = f"{mail['subject']}\n{mail['body'][:500]}"
    chunks = retrieve(query, k=3)
    knowledge = "\n---\n".join(chunks) if chunks else "(no knowledge available)"

    llm = _get_llm()
    user_msg = (
        f"From: {mail['from']}\n"
        f"Subject: {mail['subject']}\n"
        f"Category: {analysis.category}\n"
        f"Summary: {analysis.summary}\n\n"
        f"Email body:\n{mail['body'][:2000]}"
    )
    result = llm.invoke(
        [
            ("system", DRAFT_PROMPT.format(name=name, language=language, knowledge=knowledge)),
            ("human", user_msg),
        ]
    )
    return result.content.strip()