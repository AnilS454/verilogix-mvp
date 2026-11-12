#!/usr/bin/env python3
"""verilogix-cli — upload simulation logs to VeriLogIX."""
import argparse
import os
import sys
import httpx
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(prog="verilogix-cli")
    ap.add_argument("upload", help="subcommand: upload")
    ap.add_argument("--log", required=True, help="Path to simulation log file")
    ap.add_argument("--project", default="default", help="Project name")
    ap.add_argument("--commit", default=None, help="Git commit hash")
    ap.add_argument("--branch", default=None, help="Git branch")
    ap.add_argument("--simulator", default="unknown",
                    choices=["questasim", "vcs", "xcelium", "icarus", "unknown"])
    ap.add_argument("--server", default=os.getenv("VERILOGIX_URL", "http://localhost:8000"))
    ap.add_argument("--key", default=os.getenv("VERILOGIX_API_KEY", "dev-key-change-me"))
    args = ap.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        print(f"❌ Log file not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    size_mb = log_path.stat().st_size / (1024 * 1024)
    print(f"📤 Uploading {log_path.name} ({size_mb:.2f} MB) → {args.server}")

    with log_path.open("rb") as fh:
        files = {"file": (log_path.name, fh, "text/plain")}
        params = {"project_name": args.project}
        headers = {"x-api-key": args.key}

        try:
            resp = httpx.post(
                f"{args.server}/api/v1/ingest/file",
                files=files, params=params, headers=headers,
                timeout=300.0,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"❌ Upload failed: {exc}", file=sys.stderr)
            sys.exit(1)

    print(f"\n✅ Regression ID: {data['regression_id']}")
    print(f"   Lines parsed:       {data['total_lines']:,}")
    print(f"   Errors detected:    {data['error_count']}")
    print(f"   Fatal detected:     {data['fatal_detected']}")
    print(f"   Unique signatures:  {data['unique_signatures']}")
    print(f"\n🔎 View details: {args.server}/api/v1/regressions/{data['regression_id']}")
    print(f"   Dashboard:    open frontend/index.html (or your deployed URL)")


if __name__ == "__main__":
    main()