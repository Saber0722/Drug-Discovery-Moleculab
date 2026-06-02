// About.jsx — tech stack and disclaimer

const STACK = [
  { layer: "Molecule input",    tech: "RDKit + Ketcher embed", tag: "RDKit" },
  { layer: "Property predict",  tech: "Lipinski RO5, QED, TPSA — local", tag: "RDKit" },
  { layer: "Toxicity + ADMET",  tech: "DeepChem AttentiveFP (Tox21, ClinTox, SIDER)", tag: "DeepChem" },
  { layer: "Binding affinity",  tech: "AutoDock Vina 4.2 — target PDB docking", tag: "AutoDock Vina" },
  { layer: "Protein structure", tech: "ESMFold API (free) / pre-dl PDB fallback", tag: "ESMFold" },
  { layer: "AI optimizer",      tech: "Groq LLM (scaffold hopping, bioisostere swaps)", tag: "Groq + RDKit" },
  { layer: "Molecule gen",      tech: "REINVENT4 / SMILES perturbation for analogues", tag: "REINVENT4" },
  { layer: "Backend API",       tech: "FastAPI + Celery + Redis + SQLite", tag: "FastAPI" },
  { layer: "Frontend",          tech: "React + Vite + Recharts + Ketcher", tag: "React" },
  { layer: "Report export",     tech: "ReportLab — structured PDF with scores", tag: "ReportLab" },
];

const TAG_COLORS = {
  "RDKit": "bg-blue-900/50 text-blue-300 border-blue-700",
  "DeepChem": "bg-purple-900/50 text-purple-300 border-purple-700",
  "AutoDock Vina": "bg-orange-900/50 text-orange-300 border-orange-700",
  "ESMFold": "bg-teal-900/50 text-teal-300 border-teal-700",
  "Groq + RDKit": "bg-pink-900/50 text-pink-300 border-pink-700",
  "REINVENT4": "bg-yellow-900/50 text-yellow-300 border-yellow-700",
  "FastAPI": "bg-green-900/50 text-green-300 border-green-700",
  "React": "bg-cyan-900/50 text-cyan-300 border-cyan-700",
  "ReportLab": "bg-slate-700/50 text-slate-300 border-slate-600",
};

export default function About() {
  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h2 className="text-slate-100 font-bold text-xl mb-2">🧪 MolecuLab</h2>
        <p className="text-slate-400 text-sm leading-relaxed">
          An open-source in-silico drug screening workbench. Screen candidate molecules through a
          multi-layer computational pipeline — Lipinski RO5 → ADMET → toxicity → binding affinity
          — and get structured pass/fail reports. Replacing $50k/yr enterprise tools with open-source
          ML for academic and early biotech teams.
        </p>
      </div>

      <div>
        <h3 className="text-slate-200 font-semibold mb-3">Full Tech Stack</h3>
        <div className="space-y-2">
          {STACK.map((item) => (
            <div
              key={item.layer}
              className="flex items-center gap-4 bg-slate-800/40 border border-slate-700 rounded-lg px-4 py-2.5"
            >
              <span className="text-slate-400 text-sm w-40 shrink-0">{item.layer}</span>
              <span className="text-slate-200 text-sm flex-1">{item.tech}</span>
              <span className={`text-xs px-2 py-0.5 rounded border ${TAG_COLORS[item.tag] ?? "bg-slate-700 text-slate-300 border-slate-600"}`}>
                {item.tag}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="border border-yellow-500/30 bg-yellow-500/5 rounded-lg p-4 text-sm text-yellow-300/80">
        ⚠️ <strong>Important framing note:</strong> All outputs are computational predictions for
        research purposes only — not clinical advice. This is standard practice in all cheminformatics
        tools and is included in all reports and the UI.
      </div>
    </div>
  );
}
