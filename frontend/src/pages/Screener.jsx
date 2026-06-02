// Screener.jsx — Core drug screening interface
// SMILES input → validate → run screening → show results with RadarChart

import { useState, useCallback } from "react";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";
import { api } from "../api/client";

const TARGETS = ["ACE2", "EGFR", "CDK2", "BRAF"];

const EXAMPLE_SMILES = [
  { name: "Aspirin",    smiles: "CC(=O)Oc1ccccc1C(=O)O" },
  { name: "Ibuprofen",  smiles: "CC(C)Cc1ccc(cc1)C(C)C(=O)O" },
  { name: "Caffeine",   smiles: "Cn1cnc2c1c(=O)n(c(=O)n2C)C" },
  { name: "Paracetamol",smiles: "CC(=O)Nc1ccc(O)cc1" },
];

const VERDICT_STYLE = {
  PASS:    "border-green-500  bg-green-500/10  text-green-300",
  FAIL:    "border-red-500    bg-red-500/10    text-red-300",
  REVIEW:  "border-yellow-400 bg-yellow-400/10 text-yellow-300",
  INVALID: "border-slate-500  bg-slate-500/10  text-slate-400",
};

function ScoreRadar({ result }) {
  const data = [
    { subject: "QED",     value: Math.round((result.qed ?? 0) * 100) },
    { subject: "Safety",  value: Math.round((1 - (result.tox_overall ?? 0.5)) * 100) },
    { subject: "ADMET",   value: Math.round((result.admet_score ?? 0.5) * 100) },
    { subject: "Binding", value: Math.round(Math.min(1, -(result.binding_affinity ?? 0) / 10) * 100) },
    { subject: "Lipinski",value: result.lipinski_pass ? 100 : 0 },
  ];
  return (
    <ResponsiveContainer width="100%" height={180}>
      <RadarChart data={data}>
        <PolarGrid stroke="#334155" />
        <PolarAngleAxis dataKey="subject" tick={{ fill: "#94a3b8", fontSize: 10 }} />
        <Radar dataKey="value" stroke="#22d3ee" fill="#22d3ee" fillOpacity={0.25} />
        <Tooltip formatter={(v) => `${v}%`} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

function AIPanel({ result }) {
  const [state, setState] = useState("idle"); // idle | loading | done | error
  const [data, setData] = useState(null);

  const handleExplain = async () => {
    setState("loading");
    try {
      const res = await api.explainMolecule(result);
      setData(res);
      setState("done");
    } catch (e) {
      setData({ error: e.message });
      setState("error");
    }
  };

  if (state === "idle") {
    return (
      <button
        onClick={handleExplain}
        className="mt-3 w-full py-1.5 rounded border border-violet-500/40 bg-violet-500/10 text-violet-300 text-xs hover:bg-violet-500/20 transition-colors"
      >
        🤖 Explain with AI + Get Improvement Suggestions
      </button>
    );
  }

  if (state === "loading") {
    return (
      <div className="mt-3 text-xs text-violet-400 animate-pulse border border-violet-500/20 rounded p-2 text-center">
        Groq LLM analysing molecule…
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="mt-3 text-xs text-red-400 border border-red-500/20 rounded p-2">
        ⚠ {data?.error}
      </div>
    );
  }

  return (
    <div className="mt-3 border border-violet-500/30 bg-violet-500/5 rounded-lg p-3 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-violet-400 text-xs font-semibold">🤖 AI Analysis</span>
        <span className="text-slate-600 text-xs">· Groq LLM · research use only</span>
      </div>

      {/* Summary */}
      {data.summary && (
        <p className="text-xs text-slate-300 leading-relaxed">{data.summary}</p>
      )}

      {/* Score explanations */}
      {data.score_explanations && Object.keys(data.score_explanations).length > 0 && (
        <div className="space-y-1">
          <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide">Score Breakdown</p>
          {Object.entries(data.score_explanations).map(([k, v]) => (
            <div key={k} className="flex gap-2 text-xs">
              <span className="text-violet-400 capitalize w-16 shrink-0">{k}</span>
              <span className="text-slate-400">{v}</span>
            </div>
          ))}
        </div>
      )}

      {/* Suggestions */}
      {data.suggestions?.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide">Improvement Suggestions</p>
          {data.suggestions.map((s, i) => (
            <div key={i} className="flex gap-2 text-xs text-slate-300">
              <span className="text-cyan-500 shrink-0">{i + 1}.</span>
              <span>{s}</span>
            </div>
          ))}
        </div>
      )}

      {/* Candidate SMILES */}
      {data.candidate_smiles?.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide">Candidate Modifications</p>
          {data.candidate_smiles.map((s, i) => (
            <div key={i} className="font-mono text-xs text-cyan-300 bg-slate-900 rounded px-2 py-1 break-all">
              {s}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ResultCard({ result, index }) {
  const [expanded, setExpanded] = useState(false);
  const verdict = result.verdict ?? "INVALID";
  return (
    <div className={`rounded-lg border p-4 transition-all ${VERDICT_STYLE[verdict] ?? VERDICT_STYLE.INVALID}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-slate-400">#{index + 1}</span>
            <span className={`text-xs font-bold px-2 py-0.5 rounded border ${VERDICT_STYLE[verdict]}`}>
              {verdict}
            </span>
            {result.overall_score != null && (
              <span className="text-xs text-slate-300">
                Score: {(result.overall_score * 100).toFixed(1)}%
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 font-mono truncate">{result.smiles}</p>
          {result.error && (
            <p className="text-xs text-red-400 mt-1">⚠ {result.error}</p>
          )}
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-cyan-400 hover:text-cyan-300 shrink-0"
        >
          {expanded ? "▲ less" : "▼ more"}
        </button>
      </div>

      {expanded && !result.error && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-4">
            {/* Properties table */}
            <div>
              <table className="w-full text-xs">
                <tbody>
                  {[
                    ["MW (Da)", result.mol_weight],
                    ["LogP", result.logp],
                    ["HBD / HBA", `${result.hbd} / ${result.hba}`],
                    ["TPSA", result.tpsa],
                    ["QED", result.qed],
                    ["Binding (kcal/mol)", result.binding_affinity],
                    ["Tox overall", result.tox_overall?.toFixed(3)],
                  ].map(([k, v]) => (
                    <tr key={k} className="border-b border-slate-700/50">
                      <td className="py-1 text-slate-400 pr-3">{k}</td>
                      <td className="py-1 text-slate-200 text-right">{v ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {result.lipinski_violations?.length > 0 && (
                <div className="mt-2 text-xs text-yellow-300">
                  ⚠ Violations: {result.lipinski_violations.join(", ")}
                </div>
              )}
            </div>
            {/* Radar chart */}
            <ScoreRadar result={result} />
          </div>
          <AIPanel result={result} />
        </>
      )}
    </div>
  );
}

export default function Screener() {
  const [smiles, setSmiles] = useState("");
  const [target, setTarget] = useState("ACE2");
  const [mode, setMode] = useState("single");   // single | batch
  const [results, setResults] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | validating | running | done | error
  const [error, setError] = useState(null);
  const [runId, setRunId] = useState(null);

  const handleValidate = useCallback(async () => {
    if (!smiles.trim()) return;
    setStatus("validating");
    setError(null);
    try {
      const data = await api.validateMolecule(smiles.trim());
      setResults([data]);
      setStatus("done");
    } catch (e) {
      setError(e.message);
      setStatus("error");
    }
  }, [smiles]);

  const handleScreen = useCallback(async () => {
    const lines = smiles.split("\n").map((s) => s.trim()).filter(Boolean);
    if (!lines.length) return;
    setStatus("running");
    setError(null);
    try {
      const run = await api.startScreening(lines, target);
      setRunId(run.run_id);
      // Poll for completion
      const poll = setInterval(async () => {
        const statusData = await api.getRunStatus(run.run_id);
        if (statusData.status === "completed") {
          clearInterval(poll);
          setResults(statusData.results ?? []);
          setStatus("done");
        } else if (statusData.status === "failed") {
          clearInterval(poll);
          setError(statusData.error ?? "Run failed");
          setStatus("error");
        }
      }, 2000);
    } catch (e) {
      setError(e.message);
      setStatus("error");
    }
  }, [smiles, target]);

  const handleExport = useCallback(async () => {
    try {
      await api.downloadReport(results, runId);
    } catch (e) {
      alert("Report generation failed: " + e.message);
    }
  }, [results, runId]);

  return (
    <div className="space-y-6">
      {/* ── Mode toggle ── */}
      <div className="flex gap-2">
        {["single", "batch"].map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-4 py-1.5 rounded text-sm border transition-colors ${
              mode === m
                ? "border-cyan-500 bg-cyan-500/20 text-cyan-300"
                : "border-slate-700 text-slate-400 hover:border-slate-500"
            }`}
          >
            {m === "single" ? "Single molecule" : "Batch (SMILES list)"}
          </button>
        ))}
      </div>

      {/* ── Input panel ── */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <label className="text-sm text-slate-300 font-semibold">
            {mode === "single" ? "SMILES string" : "SMILES list (one per line)"}
          </label>
          <div className="flex gap-2">
            {EXAMPLE_SMILES.map((ex) => (
              <button
                key={ex.name}
                onClick={() => setSmiles(ex.smiles)}
                className="text-xs text-cyan-500 hover:text-cyan-300 underline underline-offset-2"
              >
                {ex.name}
              </button>
            ))}
          </div>
        </div>
        <textarea
          value={smiles}
          onChange={(e) => setSmiles(e.target.value)}
          rows={mode === "batch" ? 6 : 2}
          placeholder={
            mode === "single"
              ? "e.g. CC(=O)Oc1ccccc1C(=O)O"
              : "CC(=O)Oc1ccccc1C(=O)O\nCC(C)Cc1ccc(cc1)C(C)C(=O)O\n..."
          }
          className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-cyan-500 resize-none"
        />

        {/* Target selector */}
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-400">Target protein:</label>
          <div className="flex gap-2">
            {TARGETS.map((t) => (
              <button
                key={t}
                onClick={() => setTarget(t)}
                className={`px-3 py-1 rounded text-xs border transition-colors ${
                  target === t
                    ? "border-violet-500 bg-violet-500/20 text-violet-300"
                    : "border-slate-700 text-slate-400 hover:border-slate-500"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            onClick={handleValidate}
            disabled={!smiles.trim() || status === "running"}
            className="px-5 py-2 rounded-lg text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-600 disabled:opacity-40 transition-colors"
          >
            Validate &amp; Properties
          </button>
          <button
            onClick={handleScreen}
            disabled={!smiles.trim() || status === "running"}
            className="px-5 py-2 rounded-lg text-sm bg-cyan-600 hover:bg-cyan-500 text-white border border-cyan-500 disabled:opacity-40 transition-colors font-semibold"
          >
            {status === "running" ? "⏳ Screening…" : "▶ Run Full Screening"}
          </button>
          {results.length > 0 && (
            <button
              onClick={handleExport}
              className="ml-auto px-4 py-2 rounded-lg text-sm border border-slate-600 text-slate-300 hover:border-slate-400 transition-colors"
            >
              ⬇ Export PDF Report
            </button>
          )}
        </div>

        {error && (
          <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/30 rounded p-2">
            ⚠ {error}
          </p>
        )}
        {status === "running" && (
          <p className="text-xs text-cyan-400 animate-pulse">
            Pipeline running: RDKit → Tox21 → ADMET → AutoDock Vina…
          </p>
        )}
      </div>

      {/* ── Results ── */}
      {results.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300">
              Results ({results.length} molecule{results.length !== 1 ? "s" : ""})
            </h2>
            <div className="flex gap-3 text-xs">
              <span className="text-green-400">
                ✓ {results.filter((r) => r.verdict === "PASS").length} PASS
              </span>
              <span className="text-red-400">
                ✗ {results.filter((r) => r.verdict === "FAIL").length} FAIL
              </span>
              <span className="text-yellow-400">
                ~ {results.filter((r) => r.verdict === "REVIEW").length} REVIEW
              </span>
            </div>
          </div>
          <div className="space-y-3">
            {results.map((r, i) => (
              <ResultCard key={i} result={r} index={i} />
            ))}
          </div>
          <p className="text-xs text-slate-600 text-center pt-2">
            All outputs are computational predictions for research purposes only — not clinical advice.
          </p>
        </div>
      )}
    </div>
  );
}