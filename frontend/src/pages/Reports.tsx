import { useEffect, useState } from "react";
import { api } from "../lib/api";

const YEAR = new Date().getFullYear();

export function Reports({ companyId, onBack }: { companyId: string; onBack: () => void }) {
  const [pnl, setPnl] = useState<any>(null);
  const [bs, setBs] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    const from = `${YEAR}-01-01`, to = `${YEAR}-12-31`;
    setPnl(await api.get(`/companies/${companyId}/reports/pnl?from=${from}&to=${to}`));
    setBs(await api.get(`/companies/${companyId}/reports/balance_sheet`));
  }
  useEffect(() => { load(); }, [companyId]);

  function dl(path: string) {
    window.open(api.fileUrl(path), "_blank");
  }

  async function cpaPackage() {
    setBusy(true);
    try {
      const res: Response = await fetch(api.fileUrl(`/companies/${companyId}/cpa-export`), {
        method: "POST", credentials: "include",
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "cpa_package.zip"; a.click();
      URL.revokeObjectURL(url);
    } finally { setBusy(false); }
  }

  return (
    <div>
      <button className="text-blue-700 underline text-lg mb-4" onClick={onBack}>← Back</button>
      <h1 className="text-3xl font-bold mb-6">See how I'm doing</h1>

      {pnl && (
        <div className="card mb-6">
          <h2 className="text-2xl font-semibold mb-2">Profit &amp; Loss ({YEAR})</h2>
          <p className="text-lg bg-green-50 rounded-xl p-4 mb-4">{pnl.explanation}</p>
          <div className="text-xl font-semibold">
            Net {Number(pnl.net_income) >= 0 ? "profit" : "loss"}: ${pnl.net_income}
          </div>
          <div className="mt-3 flex gap-3">
            <button className="btn-secondary" onClick={() => dl(`/companies/${companyId}/reports/pnl?format=pdf`)}>Download PDF</button>
            <button className="btn-secondary" onClick={() => dl(`/companies/${companyId}/reports/pnl?format=csv`)}>Download CSV</button>
          </div>
        </div>
      )}

      {bs && (
        <div className="card mb-6">
          <h2 className="text-2xl font-semibold mb-2">Balance Sheet</h2>
          <p className="text-lg bg-blue-50 rounded-xl p-4 mb-2">{bs.explanation}</p>
          <p className="text-slate-600">
            {bs.balances ? "✅ Your books balance." : "⚠️ Your books don't balance — tell your CPA."}
          </p>
          <div className="mt-3 flex gap-3">
            <button className="btn-secondary" onClick={() => dl(`/companies/${companyId}/reports/balance_sheet?format=pdf`)}>Download PDF</button>
            <button className="btn-secondary" onClick={() => dl(`/companies/${companyId}/reports/trial_balance?format=pdf`)}>Trial balance</button>
          </div>
        </div>
      )}

      <div className="card bg-blue-50 border-blue-200">
        <h2 className="text-2xl font-semibold mb-2">Send everything to my CPA</h2>
        <p className="text-lg mb-4">
          Builds one ZIP file with all your reports and notes — ready to email your accountant.
        </p>
        <button className="btn-primary" disabled={busy} onClick={cpaPackage}>
          {busy ? "Building…" : "Download CPA package"}
        </button>
      </div>
    </div>
  );
}
