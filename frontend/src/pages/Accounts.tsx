import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Acct = { id: string; code?: string; name: string; type: string; description_plain?: string };

const TYPE_LABEL: Record<string, string> = {
  income: "Money coming in", expense: "Money going out",
  asset: "What you own", liability: "What you owe", equity: "Owner's value",
};
const ORDER = ["income", "expense", "asset", "liability", "equity"];

export function Accounts({ companyId, onBack }: { companyId: string; onBack: () => void }) {
  const [accounts, setAccounts] = useState<Acct[]>([]);
  function load() { api.get(`/companies/${companyId}/accounts`).then(setAccounts); }
  useEffect(() => { load(); }, [companyId]);

  return (
    <div>
      <button className="text-blue-700 underline text-lg mb-4" onClick={onBack}>← Back</button>
      <h1 className="text-3xl font-bold mb-2">My categories</h1>
      <p className="text-slate-600 mb-6 text-lg">
        These are the buckets your money is sorted into. They're set up for an apparel and signs shop.
      </p>
      {ORDER.map((type) => {
        const items = accounts.filter((a) => a.type === type);
        if (!items.length) return null;
        return (
          <div key={type} className="card mb-5">
            <h2 className="text-2xl font-semibold mb-3">{TYPE_LABEL[type]}</h2>
            <ul className="divide-y">
              {items.map((a) => (
                <li key={a.id} className="py-3">
                  <div className="text-xl font-medium">{a.name}</div>
                  {a.description_plain && (
                    <div className="text-slate-600">{a.description_plain}</div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
