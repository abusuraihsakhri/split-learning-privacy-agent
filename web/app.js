"use strict";

// This is a local demonstration of the thresholds in agents/workers.py.
// It is not a split-neural-network implementation or a privacy certification.
function evaluateLocal(payload) {
  const id = String(payload.task_id || "").trim();
  const target = String(payload.target_identifier || "").trim();
  const primary = Number(payload.primary_metric);
  const secondary = Number(payload.secondary_metric);
  if (!id || !target || id.length > 128 || target.length > 128) {
    throw new Error("A task ID and target key (up to 128 characters each) are required.");
  }
  if (payload.primary_metric === "" || !Number.isFinite(primary) || !Number.isFinite(secondary)) {
    throw new Error("Primary and secondary measurements must be finite numbers.");
  }
  const desc = String(payload.status_descriptor || "NOMINAL").slice(0, 256);
  const critical = payload.is_critical_flag === true;
  const alerts = [];
  function add(worker, urgency, summary, details) {
    alerts.push({ origin_worker: worker, urgency, summary, technical_details: details });
  }
  if (primary > 25) {
    add("InvariantQCWorker", "ELEVATED_RISK", "Primary Metric Threshold Exceeded",
      "Primary metric " + primary + " exceeds the demonstration threshold 25.");
  }
  if (critical || secondary > 12) {
    add("SafetyEscalationWorker", critical ? "CRITICAL_STAT_PANIC" : "ELEVATED_RISK",
      "Safety Interlock Triggered",
      "Critical flag: " + critical + "; secondary metric: " + secondary + " (threshold 12).");
  }
  if (["DISCORDANT", "ANOMALY", "MUTANT", "VIOLATION", "FAIL", "REJECT"].some(word => desc.toUpperCase().includes(word))) {
    add("ProtocolConformanceWorker", "ELEVATED_RISK", "Descriptor anomaly", "Status descriptor triggers a rule-based alert.");
  }
  const highest = alerts.some(x => x.urgency === "CRITICAL_STAT_PANIC")
    ? "CRITICAL_STAT_PANIC" : alerts.length ? "ELEVATED_RISK" : "ROUTINE";
  return {
    mode: "LOCAL_DEMO_NO_SERVER",
    task_id: id,
    target_identifier: target,
    overall_urgency: highest,
    integrity_status: highest === "CRITICAL_STAT_PANIC"
      ? "RECALIBRATION_REQUIRED" : alerts.length ? "DISCORDANT_ANOMALY" : "VALIDATED_OPTIMAL",
    total_alerts: alerts.length,
    alerts,
    audit_hash: null,
    note: "Rule-based browser demo only. No audit block signed; no clinical or privacy certification."
  };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { evaluateLocal };
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("audit-form");
    const mode = document.getElementById("execution-mode");
    const output = document.getElementById("output");
    const message = document.getElementById("message");
    const run = document.getElementById("run");
    const download = document.getElementById("download");
    const count = document.getElementById("task-count");
    const signed = document.getElementById("signed-count");
    const modeNote = document.getElementById("mode-note");
    const browserHost = location.hostname.endsWith(".github.io") || location.protocol === "file:";
    mode.value = browserHost ? "local" : "api";
    let tasks = 0;
    let signedBlocks = 0;
    let lastResult = null;
    function explainMode() {
      modeNote.textContent = mode.value === "local"
        ? "Runs entirely in this browser. No network request, persistent storage, or cryptographic audit."
        : "Sends this input to the server at this site's /api/audit endpoint. Requires a configured Python backend.";
    }
    mode.addEventListener("change", explainMode);
    explainMode();

    form.addEventListener("submit", async event => {
      event.preventDefault();
      message.textContent = "";
      lastResult = null;
      download.disabled = true;
      run.disabled = true;
      output.textContent = "Running evaluation…";
      const primaryText = document.getElementById("primary").value;
      const secondaryText = document.getElementById("secondary").value;
      const payload = {
        task_id: document.getElementById("task").value.trim(),
        target_identifier: document.getElementById("target").value.trim(),
        primary_metric: primaryText === "" ? "" : Number(primaryText),
        secondary_metric: secondaryText === "" ? 0 : Number(secondaryText),
        status_descriptor: document.getElementById("descriptor").value,
        is_critical_flag: document.getElementById("critical").checked
      };
      try {
        let result;
        if (mode.value === "local") {
          result = evaluateLocal(payload);
        } else {
          if (payload.primary_metric === "" || !Number.isFinite(payload.primary_metric) ||
              !Number.isFinite(payload.secondary_metric)) {
            throw new Error("Both metrics must be finite numbers.");
          }
          const response = await fetch("./api/audit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          if (!response.ok) {
            throw new Error("API request failed (HTTP " + response.status + "). Check the server configuration and inputs.");
          }
          result = await response.json();
        }
        lastResult = result;
        output.textContent = JSON.stringify(result, null, 2);
        tasks += 1;
        if (typeof result.audit_hash === "string" && result.audit_hash.length === 64) signedBlocks += 1;
        count.textContent = String(tasks);
        signed.textContent = String(signedBlocks);
        download.disabled = false;
        message.textContent = mode.value === "local" ? "Local demonstration complete." : "Server response received.";
      } catch (error) {
        output.textContent = "No evaluation was recorded.";
        message.textContent = error instanceof Error ? error.message : "Unexpected error.";
      } finally {
        run.disabled = false;
      }
    });

    download.addEventListener("click", () => {
      if (!lastResult) return;
      const blob = new Blob([JSON.stringify(lastResult, null, 2) + "\n"], { type: "application/json" });
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = "audit-result.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
    });
  });
}
