// api/client.js — typed API client for MolecuLab backend

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  /** Validate single SMILES + compute RDKit properties only (fast) */
  validateMolecule: (smiles, name) =>
    request("/api/molecules/validate", {
      method: "POST",
      body: JSON.stringify({ smiles, name }),
    }),

  /** Full synchronous single-molecule pipeline: RDKit + Tox21 + Vina (slow, ~60s) */
  screenMolecule: (smiles, target = "ACE2", name) =>
    request("/api/molecules/screen", {
      method: "POST",
      body: JSON.stringify({ smiles, target, name }),
    }),

  /** Launch async batch screening run */
  startScreening: (smiles_list, target = "ACE2") =>
    request("/api/screening/run", {
      method: "POST",
      body: JSON.stringify({ smiles_list, target }),
    }),

  /** Poll screening run status */
  getRunStatus: (runId) => request(`/api/screening/status/${runId}`),

  /** Predict ADMET for single molecule */
  predictAdmet: (smiles) =>
    request("/api/admet/predict", {
      method: "POST",
      body: JSON.stringify({ smiles }),
    }),

  /** Run docking (returns task_id if async) */
  runDocking: (smiles, target = "ACE2", asyncRun = true) =>
    request("/api/docking/run", {
      method: "POST",
      body: JSON.stringify({ smiles, target, async_run: asyncRun }),
    }),

  /** Poll docking result */
  getDockingResult: (taskId) => request(`/api/docking/result/${taskId}`),

  /** Generate and download PDF report */
  downloadReport: async (molecules, runId) => {
    const res = await fetch(`${BASE}/api/report/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ molecules, run_id: runId, title: "MolecuLab Screening Report" }),
    });
    if (!res.ok) throw new Error("Report generation failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `moleculab_report_${runId ?? "export"}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },
  /** Get Groq AI explanation for a screening result */
  explainMolecule: (mol_result) =>
    request("/api/ai/explain", {
      method: "POST",
      body: JSON.stringify({ mol_result }),
    }),
};