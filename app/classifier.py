"""Groq LLM se mail ko classify + summarize karo (structured output)."""
import os
from typing import Literal

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

load_dotenv()


class MailAnalysis(BaseModel):
    category: Literal["urgent", "query", "meeting", "newsletter", "spam", "other"] = Field(
        description="Mail ki category"
    )
    summary: str = Field(description="Mail ka 1-2 line ka summary")
    needs_reply: bool = Field(description="Kya is mail ka jawab dena zaroori hai?")
    reason: str = Field(description="Is category/decision ki chhoti si wajah")


SYSTEM_PROMPT = """You are an email triage assistant.
Analyze the email and return:
- category: urgent / query / meeting / newsletter / spam / other
- summary: 1-2 short lines
- needs_reply: true only if a real person expects a response
- reason: one short line

Rules: newsletters, promotions, automated notifications and spam never need a reply."""


def _get_llm():
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(model=model, temperature=0)


def analyze_mail(mail: dict) -> MailAnalysis:
    llm = _get_llm().with_structured_output(MailAnalysis)
    body = mail["body"][:2000]  # lambi mails chhoti kar do (token/rate limit bachane ke liye)
    user_msg = (
        f"From: {mail['from']}\n"
        f"Subject: {mail['subject']}\n"
        f"Date: {mail['date']}\n\n"
        f"{body}"
    )
    return llm.invoke([("system", SYSTEM_PROMPT), ("human", user_msg)])
