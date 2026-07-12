"""LLM Judge for the AI Football Scout.

Checks whether an answer's reasoning follows from the source data:
unsupported claims, data denial, logical leaps. Numbers are NOT
checked here — that is the deterministic judge's job.

Unlike the deterministic judge, verdicts are not guaranteed to be
reproducible: the same input may yield different judgements.
"""

import json

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv(override=True)

client = genai.Client()

MODEL = "gemini-2.5-flash"

JUDGE_PROMPT = """You are a verification judge for a football scouting system.

You will receive:
1. DATA: the exact database records that were given to a scouting agent
2. ANSWER: the agent's answer, which must be based ONLY on that data

Numbers are checked by a separate system — do NOT check numbers.
Your job is to check the REASONING:

- Does the answer make claims that the data does not support?
- Does the answer dismiss, deny, or reinterpret any part of the data
  (e.g. calling a record an error) without evidence?
- Does the answer draw conclusions that do not follow from the data?

Respond in JSON:
{"verdict": "pass" or "fail",
 "reasoning": "one short paragraph explaining your judgement",
 "violations": ["each unsupported claim, quoted", ...]}

If the answer only states what the data shows, verdict is "pass"
and violations is an empty list."""


def verify_reasoning(answer_text, source_record):
    """LLM Judge: does the answer's reasoning follow from the source data?

    Same contract as verify_numbers: (answer, source) in, verdict dict out.
    Checks interpretation, not numbers — numbers belong to the
    deterministic judge.
    """
    payload = (f"DATA:\n{json.dumps(source_record, indent=2)}\n\n"
               f"ANSWER:\n{answer_text}")

    resp = client.models.generate_content(
        model=MODEL,
        contents=payload,
        config=types.GenerateContentConfig(
            system_instruction=JUDGE_PROMPT,
            response_mime_type="application/json",
        ),
    )
    return json.loads(resp.text)