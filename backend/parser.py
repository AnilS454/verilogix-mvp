"""Verification log parser - extracts UVM errors with context."""
import re
import hashlib
from typing import Dict, Any, List


class VerificationLogParser:
    def __init__(self, context_window_lines: int = 15):
        self.context_window = context_window_lines
        self.UVM_ERROR_PATTERN = re.compile(
            r'^\s*UVM_ERROR\s+@\s*([\d\.]+\s*\w+):\s+(\S+)\s+\[(\S+)\]\s+(.*)$'
        )
        self.UVM_FATAL_PATTERN = re.compile(
            r'^\s*UVM_FATAL\s+@\s*([\d\.]+\s*\w+):\s+(\S+)\s+\[(\S+)\]\s+(.*)$'
        )
        self.FILE_LINE_PATTERN = re.compile(r'"([^"]+\.(?:sv|v|vh|sva))",\s+(\d+)')
        self.ASSERT_PATTERN = re.compile(
            r'(Assertion|ASSERT|assert)\s+.*?(failed|FAILED)', re.IGNORECASE
        )

    def parse_log_text(self, log_text: str) -> Dict[str, Any]:
        errors_found: List[Dict[str, Any]] = []
        log_buffer: List[str] = []
        total_lines = 0
        fatal_detected = False

        for line in log_text.splitlines(keepends=True):
            total_lines += 1
            log_buffer.append(line)
            if len(log_buffer) > (self.context_window * 2):
                log_buffer.pop(0)

            match = self.UVM_ERROR_PATTERN.match(line) or self.UVM_FATAL_PATTERN.match(line)
            if match:
                timestamp, scope, err_id, message = match.groups()
                context_snippet = "".join(log_buffer[-self.context_window:])
                file_match = self.FILE_LINE_PATTERN.search(context_snippet)
                source_file = file_match.group(1) if file_match else None
                line_num = int(file_match.group(2)) if file_match else None

                sig_raw = f"{err_id}:{message.strip()}"
                sig_hash = hashlib.sha256(sig_raw.encode("utf-8")).hexdigest()[:16]

                errors_found.append({
                    "timestamp": timestamp,
                    "scope": scope,
                    "error_id": err_id,
                    "message": message.strip(),
                    "source_file": source_file,
                    "line_number": line_num,
                    "signature_hash": sig_hash,
                    "context_snippet": context_snippet,
                    "is_fatal": "FATAL" in line,
                })

            if "UVM_FATAL" in line or "$fatal" in line:
                fatal_detected = True

            # Catch bare assertion failures
            if self.ASSERT_PATTERN.search(line) and not match:
                context_snippet = "".join(log_buffer[-self.context_window:])
                sig_hash = hashlib.sha256(line.strip().encode("utf-8")).hexdigest()[:16]
                errors_found.append({
                    "timestamp": "N/A",
                    "scope": "unknown",
                    "error_id": "ASSERTION",
                    "message": line.strip()[:300],
                    "source_file": None,
                    "line_number": None,
                    "signature_hash": sig_hash,
                    "context_snippet": context_snippet,
                    "is_fatal": False,
                })

        return {
            "total_lines": total_lines,
            "error_count": len(errors_found),
            "fatal_detected": fatal_detected,
            "errors": errors_found,
        }
