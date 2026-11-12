"""AI engine - DeepSeek API (OpenAI-compatible). Falls back to stub if no key."""
import os
import json
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

SYSTEM_PROMPT = """You are an expert SystemVerilog, UVM, and Digital Logic Verification Principal Engineer.
Analyze the simulation error log snippet and output ONLY valid JSON (no markdown fences).

RULES:
1. Identify the exact failing assertion, file line, or UVM phase objection failure.
2. Classify as: RTL_BUG, TESTBENCH_BUG, ENV_CONFIG, TIMING_VIOLATION, or UNKNOWN.
3. Provide a concise 2-sentence summary.
4. Provide a concrete fix action for the verification developer.
5. Do NOT invent module names not in the snippet.

OUTPUT SCHEMA:
{
  "failure_category": "RTL_BUG | TESTBENCH_BUG | ENV_CONFIG | TIMING_VIOLATION | UNKNOWN",
  "root_cause_file": "string or null",
  "root_cause_line": "integer or null",
  "summary": "string",
  "recommended_fix": "string",
  "confidence_score": 0.0 to 1.0
}"""


def analyze_error(error: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    # If no key is found, use the offline stub
    if not api_key or api_key == "sk-paste-your-actual-key-here":
        return _stub_analysis(error)

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        user_msg = (
            f"Error ID: {error['error_id']}\n"
            f"Scope: {error['scope']}\n"
            f"Message: {error['message']}\n"
            f"File: {error.get('source_file')}\n"
            f"Line: {error.get('line_number')}\n\n"
            f"Snippet:\n{error['context_snippet'][:4000]}"
        )
        resp = client.chat.completions.create(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        content = resp.choices[0].message.content.strip()
        
        # Clean up markdown blocks if the AI includes them
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
                
        return json.loads(content)
        
    except Exception as exc:
        # This prints the error to your terminal so we can see it
        print(f"\n🚨 DEEPSEEK API ERROR: {exc}\n") 
        result = _stub_analysis(error)
        result["summary"] = f"[AI error: {exc}] " + result["summary"]
        return result


def _stub_analysis(error: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic fallback when no API key is set."""
    msg = error["message"].lower()
    if "assert" in msg or "mismatch" in msg:
        category = "RTL_BUG"
        fix = "Inspect the RTL driving the failing signal and verify expected vs. actual values against the spec."
    elif "timeout" in msg or "watchdog" in msg:
        category = "TIMING_VIOLATION"
        fix = "Check clock/reset wiring and simulation timeout configuration."
    elif "null" in msg or "config" in msg or "unable to" in msg:
        category = "ENV_CONFIG"
        fix = "Verify UVM config_db settings and factory overrides."
    else:
        category = "UNKNOWN"
        fix = "Review the surrounding log context and reproduce the failure in isolation."

    return {
        "failure_category": category,
        "root_cause_file": error.get("source_file"),
        "root_cause_line": error.get("line_number"),
        "summary": f"{error['error_id']} in scope '{error['scope']}': {error['message'][:200]}",
        "recommended_fix": fix,
        "confidence_score": 0.5,
    }
