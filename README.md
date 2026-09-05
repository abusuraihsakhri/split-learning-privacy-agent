# Split Learning Privacy Agent

> **Domain:** Privacy-Preserving Healthcare & Federated Computing
> **Reference Guidelines & Standards:** `HIPAA Safe Harbor §164.514 & Differential Privacy RDP`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**Split Learning Privacy Agent** is an advanced analytical and computational platform implementing Cut-layer neural network split learning & mutual information privacy leakage auditor.

---

## ⚙️ Key Capabilities & Algorithmic Modules

- **Deterministic Calculation Engine**: Strict compliance with standard reference formulations and thresholds.
- **Risk & Urgency Classification**: Multi-tier categorization with automated clinical/operational action recommendations.
- **Validation & Guardrails**: Rigorous input bounds checking and anomaly detection.

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/split-learning-privacy-agent.git
cd split-learning-privacy-agent

# Install core dependencies
pip install fastapi uvicorn pydantic pytest

# Optional: Install numpy for advanced split-learning modules
pip install numpy

# Copy environment template and configure
cp .env.example .env
# Edit .env and set a secure AUDIT_SECRET_KEY
```

### Environment Setup

The application requires an `AUDIT_SECRET_KEY` environment variable for cryptographic audit trail integrity. Generate a secure key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set it in your `.env` file or export it directly:

```bash
export AUDIT_SECRET_KEY="your-generated-key"
```

---

## 💻 CLI Quickstart & Usage

The CLI uses subcommands for different operations:

### 1. Audit (Single Task Evaluation)
```bash
python cli.py audit --task-id TASK-001 --target KEY-01 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
```

### 2. Chat (Supervisory Query)
```bash
python cli.py chat "What is the system status?"
```

### 3. Batch (CSV Processing)
```bash
python cli.py batch -i sample.csv -o results.csv
```

### 4. Verify Audit Trail Integrity
```bash
python cli.py verify-audit
```

### 5. Serve (FastAPI REST Server)
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Parameter Reference
- `--task-id`: Unique task/case identifier
- `--target`: Target entity or specimen key
- `--primary`: Primary measurement value (float)
- `--secondary`: Secondary measurement value (float)
- `--critical`: Flag for critical/emergency escalation
- `--status`: Status descriptor (NOMINAL, DISCORDANT, etc.)

### Input Data Schema (Batch CSV)

| Field | Description | Requirement |
|:------|:------------|:------------|
| `task_id` | Parameter / observation metric | Required |
| `target_identifier` | Parameter / observation metric | Required |
| `primary_metric` | Primary measurement value | Required |
| `secondary_metric` | Secondary measurement value | Optional |
| `is_critical_flag` | Emergency escalation flag | Optional |
| `status_descriptor` | Status code or phenotype | Optional |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 1000
```

---

## 🐳 Container Deployment

```bash
docker build -t split-learning-privacy-agent .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY="your-key" split-learning-privacy-agent
```

Or using Docker Compose:

```bash
# Create .env file first
cp .env.example .env
# Edit .env with your secure key
docker-compose up -d
```

---

## 📁 Project Structure

```
split-learning-privacy-agent/
├── agents/                  # Core agent modules (supervisor, workers, API)
│   ├── api.py              # FastAPI REST endpoints
│   ├── base.py             # PHI Guard, HMAC Audit Trail
│   ├── models.py           # Pydantic data models
│   ├── supervisor.py       # Master orchestrator
│   └── workers.py          # Specialized evaluation workers
├── split_learning/          # Split learning engine modules
│   ├── agents.py           # Cut-layer agents
│   ├── engine.py           # Core evaluation engine
│   ├── byzantine_detector.py  # Byzantine resilience (requires numpy)
│   ├── privacy_budget.py   # Differential privacy budget tracking
│   └── secure_aggregation.py  # Shamir secret sharing (requires numpy)
├── tests/                   # Test suite
├── cli.py                   # Main CLI entry point
├── simulator.py             # High-throughput simulation
├── enrichment.py            # Feature enrichment suite
└── web/                     # Web operations console
```

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.
