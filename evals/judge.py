"""LLM-as-judge for groundedness. Claim-level, not a single vibe score:
a judge that lists each claim is easier to audit and spot-check by hand."""
import json

from pydantic import BaseModel

from app.config import get_settings
from app.llm.client import load_prompt, structured


class Claim(BaseModel):
    claim: str
    supported: bool
    evidence_id: str = ""


class Judgement(BaseModel):
    claims: list[Claim] = []


def judge(reply: str, evidence: list[dict]) -> Judgement:
    ev = "\n".join(f"[{e['id']}] {e['text']}" for e in evidence)
    return structured(
        [{"role": "system", "content": load_prompt("judge")},
         {"role": "user", "content": f"EVIDENCE:\n{ev}\n\nREPLY:\n{reply}"}],
        Judgement, model=get_settings().judge_model, purpose="judge",
    )


def evidence_from_state(state: dict) -> list[dict]:
    ev = [{"id": d.source_id, "text": d.snippet} for d in state.get("docs", []) if d.source_type == "kb"]
    agent = state.get("agent")
    if agent:
        for c in agent.trace:
            if c.result is not None:
                ev.append({"id": c.tool, "text": json.dumps(c.result, default=str)[:1500]})
    return ev
