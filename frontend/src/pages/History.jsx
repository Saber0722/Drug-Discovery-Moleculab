// History.jsx — Browse past screening runs from the DB

import { useState, useEffect } from "react";
import { api } from "../api/client";

export default function History() {
  return (
    <div className="text-slate-400 text-sm space-y-4">
      <h2 className="text-slate-200 font-semibold text-base">Screening History</h2>
      <p className="text-slate-500">
        Past screening runs will appear here once the backend DB is running.
        Each run links to its full result set and PDF report.
      </p>
      <div className="border border-slate-700 rounded-lg p-6 text-center text-slate-600">
        No runs yet — start a screening from the Screener tab.
      </div>
    </div>
  );
}
