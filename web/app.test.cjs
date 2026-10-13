const { test } = require("node:test");
const assert = require("node:assert/strict");
const { evaluateLocal } = require("./app.js");

const baseline = {
  task_id: "TASK", target_identifier: "KEY", primary_metric: 10,
  secondary_metric: 2, status_descriptor: "NOMINAL", is_critical_flag: false
};

test("no alerts with nominal values", () => {
  const res = evaluateLocal(baseline);
  assert.equal(res.overall_urgency, "ROUTINE");
  assert.equal(res.total_alerts, 0);
  assert.equal(res.audit_hash, null);
});
test("elevated threshold and anomaly rules", () => {
  const res = evaluateLocal({...baseline, primary_metric: 26, secondary_metric: 13, status_descriptor: "ANOMALY"});
  assert.equal(res.total_alerts, 3);
  assert.equal(res.overall_urgency, "ELEVATED_RISK");
});
test("critical interlock precedes other alert severity", () => {
  const res = evaluateLocal({...baseline, is_critical_flag: true});
  assert.equal(res.overall_urgency, "CRITICAL_STAT_PANIC");
});
test("rejects invalid measurements and identifiers", () => {
  assert.throws(() => evaluateLocal({...baseline, primary_metric: ""}));
  assert.throws(() => evaluateLocal({...baseline, secondary_metric: Infinity}));
  assert.throws(() => evaluateLocal({...baseline, task_id: " "}));
});
