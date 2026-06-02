// MolecuLab Frontend — main App.jsx
// Stack: React + Vite + Tailwind + Recharts + Ketcher embed

import { useState } from "react";
import Screener from "./pages/Screener";
import History from "./pages/History";
import About from "./pages/About";

const NAV_ITEMS = [
  { id: "screener", label: "Screener" },
  { id: "history",  label: "History" },
  { id: "about",    label: "About" },
];

export default function App() {
  const [page, setPage] = useState("screener");

  return (
    <div className="min-h-screen bg-[#0d0d1a] text-slate-100 font-mono">
      {/* ── Top nav ── */}
      <header className="border-b border-slate-700 px-6 py-3 flex items-center gap-8">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 text-lg font-bold tracking-tight">
            🧪 MolecuLab
          </span>
          <span className="text-slate-500 text-xs">open in-silico workbench</span>
        </div>
        <nav className="flex gap-1 ml-auto">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`px-4 py-1.5 rounded text-sm transition-colors ${
                page === item.id
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      {/* ── Page content ── */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {page === "screener" && <Screener />}
        {page === "history"  && <History />}
        {page === "about"    && <About />}
      </main>

      <footer className="text-center text-slate-600 text-xs py-6 border-t border-slate-800">
        All outputs are computational predictions for research purposes only — not clinical advice.
      </footer>
    </div>
  );
}
