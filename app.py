"""VeriLogIX MVP API - FastAPI backend."""
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
from datetime import datetime

from parser import VerificationLogParser
from ai_engine import analyze_error

app = FastAPI(title="VeriLogIX MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores (swap for Postgres + ClickHouse in production)
REGRESSIONS: Dict[str, Dict[str, Any]] = {}
SIGNATURE_CACHE: Dict[str, Dict[str, Any]] = {}

API_KEY = os.getenv("VERILOGIX_API_KEY", "dev-key-change-me")


def check_key(x_api_key: str | None):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


class IngestRequest(BaseModel):
    project_name: str
    git_commit: str | None = None
    branch: str | None = None
    simulator: str = "unknown"


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "verilogix", "version": "0.1.0"}


@app.post("/api/v1/ingest/text")
def ingest_text(
    payload: dict,
    x_api_key: str | None = Header(default=None),
):
    """JSON ingest: {"project_name": ..., "log_text": "..."}"""
    check_key(x_api_key)
    log_text = payload.get("log_text")
    project_name = payload.get("project_name", "default")
    if not log_text:
        raise HTTPException(400, "log_text required")

    regression_id = str(uuid.uuid4())
    parser = VerificationLogParser()
    parsed = parser.parse_log_text(log_text)

    analyzed = []
    for err in parsed["errors"]:
        sig = err["signature_hash"]
        if sig in SIGNATURE_CACHE:
            analysis = SIGNATURE_CACHE[sig]
            analysis["cached"] = True
        else:
            analysis = analyze_error(err)
            analysis["cached"] = False
            SIGNATURE_CACHE[sig] = analysis
        analyzed.append({**err, "analysis": analysis})

    record = {
        "regression_id": regression_id,
        "project_name": project_name,
        "git_commit": payload.get("git_commit"),
        "branch": payload.get("branch"),
        "simulator": payload.get("simulator", "unknown"),
        "total_lines": parsed["total_lines"],
        "error_count": parsed["error_count"],
        "fatal_detected": parsed["fatal_detected"],
        "unique_signatures": len({e["signature_hash"] for e in analyzed}),
        "errors": analyzed,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    REGRESSIONS[regression_id] = record
    return record


@app.post("/api/v1/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    project_name: str = "default",
    x_api_key: str | None = Header(default=None),
):
    check_key(x_api_key)
    raw = await file.read()
    try:
        text = raw.decode("utf-8", errors="ignore")
    except Exception:
        raise HTTPException(400, "Could not decode file")
    return ingest_text(
        {"project_name": project_name, "log_text": text}, x_api_key=x_api_key
    )


@app.get("/api/v1/regressions")
def list_regressions():
    return [
        {k: v for k, v in r.items() if k != "errors"}
        | {"sample_error": r["errors"][0] if r["errors"] else None}
        for r in sorted(
            REGRESSIONS.values(), key=lambda x: x["created_at"], reverse=True
        )
    ]


@app.get("/api/v1/regressions/{regression_id}")
def get_regression(regression_id: str):
    if regression_id not in REGRESSIONS:
        raise HTTPException(404, "Not found")
    return REGRESSIONS[regression_id]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)