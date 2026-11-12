# ⚡ VeriLogIX MVP

**VeriLogIX** is a domain-specific SaaS platform built for semiconductor verification engineers. It automates the manual triage of massive SystemVerilog/UVM simulation log files (100MB+). The system streams logs to extract deterministic failure signatures, deduplicates identical errors via SHA-256 hashing, performs LLM-driven root cause classification, and presents regression insights in a unified dashboard.

## 🚀 Core Features

- **Streaming Log Parser:** Processes large simulation logs line-by-line without loading entire files into RAM.
- **Deterministic Error Extraction:** Captures `UVM_ERROR`, `UVM_FATAL`, and SystemVerilog assertion failures alongside a 15-line surrounding context window.
- **Signature Deduplication & Caching:** Computes a truncated SHA-256 hash of normalized error signatures to cache AI diagnoses and eliminate redundant LLM API calls.
- **AI-Powered Root Cause Analysis:** Integrates with DeepSeek (via OpenAI-compatible SDK) to classify defects (`RTL_BUG`, `TESTBENCH_BUG`, `TIMING_VIOLATION`, etc.) and recommend actionable fixes, with an automatic deterministic offline fallback.
- **Interactive Regression Dashboard:** Dark-mode web interface displaying regression pass/fail metrics, grouped failure buckets, source file/line pointers, and AI summaries.
- **CLI Uploader:** Lightweight Python utility for ingesting logs directly from local EDA flows or CI/CD regression runners.

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, FastAPI, Uvicorn
- **AI Engine:** DeepSeek API (OpenAI SDK compatible) + Deterministic Offline Stub
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **CLI Tool:** Python, `httpx`

## 📂 Project Structure

```text
verilogix/
├── backend/
│   ├── app.py               # FastAPI server & REST endpoints
│   ├── requirements.txt     # Backend Python dependencies
│   └── .env.example         # Environment variable template
├── cli/
│   └── verilogix.py         # CLI log ingestion tool
├── frontend/
│   └── index.html           # Single-page dark-mode dashboard
└── README.md
```

## 💻 Local Setup & Execution

### Prerequisites

- Python 3.10 or higher
- Git (optional)

### Step 1: Start the Backend

Open a terminal and set up the Python virtual environment inside the `backend` directory:

```bash
cd backend
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\activate

# Activate virtual environment (Linux / macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file from the provided template:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Edit `.env` and configure your credentials. If `DEEPSEEK_API_KEY` is left unset or invalid, the backend automatically falls back to the deterministic offline analyzer:

```env
VERILOGIX_API_KEY=dev-key-change-me
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

Start the FastAPI server:

```bash
uvicorn app:app --reload --port 8000
```

Keep this terminal running. The API is now active at `http://127.0.0.1:8000`.

### Step 3: Upload a Sample Log via CLI

Open a second terminal window and create a `sample.log` file in the project root directory:

```text
UVM_INFO @ 0: uvm_test_top [TEST] Starting test
UVM_ERROR @ 150: uvm_test_top.env.scoreboard [DATA_MISMATCH] Scoreboard mismatch on read_data: expected 0x55, got 0xAA
  file: "./rtl/memory_controller.sv", line: 88
UVM_FATAL @ 300: uvm_test_top [FATAL] Clock generator stopped unexpectedly
```

Navigate to the `cli` folder and upload the log:

```bash
cd cli
pip install httpx
python verilogix.py upload --log ../sample.log --project "My First Project"
```

*(Note: On Windows, use `py` instead of `python` if required by your PATH configuration.)*

The CLI will return a confirmation containing the generated **Regression ID** and `Errors detected: 2`.

### Step 4: Inspect Results in the Dashboard

1. Navigate to the `frontend/` directory in your file manager.
2. Open `index.html` in any modern web browser.
3. Click on the **My First Project** regression entry to expand the failure breakdown, inspect exact RTL/TB file line numbers, and review the root cause analysis and suggested fix.

## 🏗️ System Architecture

1. **Ingestion:** The CLI streams the simulation log via multipart `POST` to `/api/v1/ingest/file`.
2. **Parsing & Hashing:** `VerificationLogParser` scans the stream line-by-line, extracts UVM/assertion failures with context, and computes a 16-character SHA-256 signature hash.
3. **Deduplication & Inference:** The backend queries the signature cache. Cache misses dispatch a ~1KB context payload to DeepSeek for classification; cache hits return immediately.
4. **Storage:** Uses an in-memory data store for rapid MVP prototyping.
5. **Visualization:** The frontend polls the REST API to render regression summaries and triage details dynamically.

## 🗺️ Production Roadmap

- [ ] Replace in-memory storage with ClickHouse (time-series log analytics) and PostgreSQL (users, projects, metadata).
- [ ] Introduce Redis + BullMQ workers for asynchronous high-throughput log ingestion.
- [ ] Migrate frontend to Next.js (App Router) and Tailwind CSS.
- [ ] Add one-click Jira and GitHub Issues integration for automated bug filing.
- [ ] Expand regex parser profiles for QuestaSim, Synopsys VCS, and Cadence Xcelium native error formats.

## 📄 License

This project is licensed under the MIT License.