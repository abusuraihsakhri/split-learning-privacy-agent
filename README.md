# Split Learning Privacy Agent

A research-oriented Python toolkit with a rule-based supervisory audit service, mathematical split-learning utilities, a CLI, and an optional browser demonstration.

## Features

- **Supervisory audit:** three deterministic rules (primary metric >25; secondary metric >12 or critical flag; anomaly-related descriptors), producing alerts and overall status.
- **Audit ledger:** in-memory HMAC-SHA256 chaining and signature verification using `AUDIT_SECRET_KEY`. The ledger is **not durable across restarts**.
- **Split-learning examples:** a separate coordinator and evaluation engine; finite-field Shamir sharing, share aggregation, budget monitoring, and gradient anomaly utilities (NumPy optional).
- **Interfaces:** CLI, FastAPI REST endpoints, and an interactive static HTML/JavaScript demo with JSON download.

**Scope and limitations:** This project does not implement end-to-end split neural-network training, quantify mutual information leakage, prove differential privacy for arbitrary models, provide a production secure aggregation protocol, or establish HIPAA compliance. The budget monitor assumes a pure-DP Laplace mechanism with a supplied clipping sensitivity and noise scale; its RDP option currently uses conservative basic composition rather than an RDP accountant. Cut-layer values must be **integer-quantized** before Shamir sharing. Commitments and malicious-share verification are not implemented.

## Browser demonstration

The `web/` directory contains a self-contained browser application. Open `web/index.html` locally, or access it from the Python API homepage. The local mode evaluates the same three rules without an API request, persistent storage, or cryptographic signing. The Python API mode communicates with a running backend. GitHub Pages publication is configured through `.github/workflows/pages.yml`; availability depends on the repository's Pages settings and a successful deployment.

## Install and run

Requires Python 3.10 or newer.

```bash
git clone https://github.com/abusuraihsakhri/split-learning-privacy-agent.git
cd split-learning-privacy-agent
python -m pip install -e ".[api,test,numpy]"
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python cli.py audit --task-id DEMO-001 --target KEY-001 --primary 26 --secondary 13
python cli.py batch -i sample.csv -o results.csv
python cli.py verify-audit
python cli.py serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` for the UI, `/docs` for FastAPI documentation, `/health` for health, and `/metrics` for JSON counters. `POST /api/audit` accepts a JSON `SystemTaskPayload`. The second, independent CLI is `python -m split_learning.cli --help`; the installed `split-learning-privacy-engine` command invokes it.

For Docker, populate `.env` from `.env.example` with a **new secret key**, then run `docker compose up --build`. The container runs as an unprivileged user.

## Data handling and security

Local browser mode stores results in memory for the current page session, makes no evaluation network request, and exports JSON only when requested. Python API mode sends inputs to the server and keeps the audit trail in server memory. **Do not use protected health information or real patient identifiers.** The regex-based PHI guard is not comprehensive de-identification. The API does not implement authentication, rate limiting, secure transport termination, or persistent logging and is not suitable for direct public exposure. Prefer binding it to loopback or protecting it behind an appropriately configured gateway.

## Development and verification

```bash
python -m pytest -q
python -m compileall -q agents split_learning cli.py enrichment.py simulator.py
node --test web/app.test.cjs
```

GitHub Actions runs Python 3.10–3.12 tests, browser-rule unit tests, and a keyed HMAC check. The web demo works in current Chromium, Firefox, and Safari releases supporting modern JavaScript; the API requires a running Python server.

## License

MIT — see [LICENSE](LICENSE).
