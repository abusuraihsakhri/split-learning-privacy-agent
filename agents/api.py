"""
FastAPI REST API Server for Split Learning Privacy Agent.
"""
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Split Learning Privacy Agent API",
    description="Enterprise Distributed Component Platform (Privacy-Preserving Federated Healthcare & FHE)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "index.html")


@app.get("/app.js", include_in_schema=False)
def app_script():
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "app.js", media_type="text/javascript")


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "split-learning-privacy-agent", "domain": "Privacy-Preserving Federated Healthcare & FHE", "standard": "HIPAA Safe Harbor §164.514 / Google SecAgg Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException:
        raise HTTPException(status_code=422, detail="Identifier policy violation")
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Audit service is not configured")
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException:
        raise HTTPException(status_code=422, detail="Identifier policy violation")


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
