"""
Structured question generation with provider fallback.
Gemini: 1,500 req/day free, no card required.
Groq: fallback, generous free tier on Llama models.
"""
import json
import logging
import os
import re

import google.generativeai as genai
from groq import Groq

logger = logging.getLogger(__name__)

gemini_key = os.environ.get("GEMINI_API_KEY")
groq_key = os.environ.get("GROQ_API_KEY")

if gemini_key:
    genai.configure(api_key=gemini_key)
else:
    logger.warning("GEMINI_API_KEY is not set in environment variables.")

groq_client = None
if groq_key:
    groq_client = Groq(api_key=groq_key)
else:
    logger.warning("GROQ_API_KEY is not set in environment variables.")

SYSTEM_PROMPT = """You are a FAANG+ technical interviewer. Generate exactly 10 interview
questions for AI Engineer / Data Science roles, mixing:
- 2 ML fundamentals
- 2 statistics/probability
- 2 system design (ML/GenAI)
- 2 coding/algorithms applied to ML
- 2 behavioral/case-study

Use ONLY the provided recent context (real questions/discussions from the web) as
grounding signal to keep questions current and realistic.
Prioritize snippets tagged with source=reddit, source=glassdoor, and
source=leetcode_discuss when deciding themes.
Do not copy text verbatim — write original questions and answers inspired by
the themes from the grounded context.

For each item, make the model_answer practical and interview-ready.
It should include: concise answer, why it matters, and one concrete example.

Return ONLY valid JSON (no markdown fences, no preamble), as a JSON array:
[
  {
    "question": "...",
    "category": "ml_fundamentals|stats|system_design|coding|behavioral|genai",
    "difficulty": "easy|medium|hard",
        "company_style": "",
    "model_answer": "structured: definition -> intuition -> example -> edge cases/tradeoffs",
    "follow_up_questions": ["...", "..."]
  }
]
"""


def _extract_json(text: str) -> list[dict]:
    """LLMs sometimes wrap JSON in fences despite instructions — strip defensively."""
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text)
    text = re.sub(r"^```\s*|\s*```$", "", text)
    return json.loads(text)


def generate_with_gemini(context_text: str) -> list[dict]:
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )
    prompt = (
        "Recent grounded context from web search (freshness-biased):\n"
        f"{context_text}\n\n"
        "Generate the 10 questions now. Keep them tied to recurring themes in the context."
    )
    response = model.generate_content(prompt)
    return _extract_json(response.text)


def generate_with_groq(context_text: str) -> list[dict]:
    prompt = (
        "Recent grounded context from web search (freshness-biased):\n"
        f"{context_text}\n\n"
        "Generate the 10 questions now. Keep them tied to recurring themes in the context."
    )
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return _extract_json(response.choices[0].message.content)


def generate_questions(context_text: str) -> tuple[list[dict], str]:
    """
    Tries Gemini first, falls back to Groq on failure.
    Returns (questions, provider_used).
    """
    if gemini_key:
        try:
            questions = generate_with_gemini(context_text)
            return questions, "gemini"
        except Exception as e:
            logger.warning(f"Gemini generation failed, falling back to Groq: {e}")
    else:
        logger.warning("Gemini generation skipped because GEMINI_API_KEY is not set.")

    if groq_client:
        try:
            questions = generate_with_groq(context_text)
            return questions, "groq"
        except Exception as e:
            logger.error(f"Groq fallback also failed: {e}")
            raise RuntimeError("Both Gemini and Groq generation failed") from e
    else:
        raise RuntimeError("No LLM API keys configured (both GEMINI_API_KEY and GROQ_API_KEY are missing)")
