import { useState } from "react";
import { api, Company } from "../lib/api";

export function CompanyBar({
  companies, companyId, onPick, onLogout, onReload,
}: {
  companies: Company[];
  companyId: string;
  onPick: (id: string) => void;
  onLogout: () => void;
  onReload: () => void;
}) {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("smllc");

  async function add() {
    if (!name.trim()) return;
    await api.post("/companies", { name, business_type: type, state: "NJ" });
    setName(""); setAdding(false); onReload();
  }

  return (
    <header className="bg-blue-800 text-white">
      <div className="max-w-6xl mx-auto px-6 py-4 flex flex-wrap items-center gap-3">
        <span className="text-2xl font-bold mr-2">JDK Books</span>
        <select
          className="text-slate-900 rounded-lg px-3 py-2 text-lg"
          value={companyId}
          onChange={(e) => onPick(e.target.value)}
        >
          {companies.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <button className="underline text-lg" onClick={() => setAdding((v) => !v)}>
          + Add business
        </button>
        <div className="ml-auto">
          <button className="underline text-lg" onClick={onLogout}>Sign out</button>
        </div>
      </div>
      {adding && (
        <div className="max-w-6xl mx-auto px-6 pb-4 flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-sm">Business name</label>
            <input className="text-slate-900 rounded-lg px-3 py-2"
                   value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm">Type</label>
            <select className="text-slate-900 rounded-lg px-3 py-2"
                    value={type} onChange={(e) => setType(e.target.value)}>
              <option value="smllc">Single-member LLC</option>
              <option value="c_corp">C corporation</option>
              <option value="s_corp">S corporation</option>
              <option value="sole_prop">Sole proprietorship</option>
              <option value="partnership">Partnership</option>
            </select>
          </div>
          <button className="bg-white text-blue-800 rounded-lg px-4 py-2 font-semibold"
                  onClick={add}>Create</button>
        </div>
      )}
    </header>
  );
}
