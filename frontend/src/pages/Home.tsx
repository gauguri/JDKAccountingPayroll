import { View } from "../App";

const TILES: { view: View; label: string; sub: string; emoji: string }[] = [
  { view: "income", label: "Record money coming in", sub: "A sale or payment", emoji: "💵" },
  { view: "expense", label: "Record money going out", sub: "A bill or purchase", emoji: "🧾" },
  { view: "payroll", label: "Run payroll", sub: "Pay employees, print stubs", emoji: "👥" },
  { view: "reports", label: "See how I'm doing", sub: "Profit, balances, taxes", emoji: "📊" },
  { view: "accounts", label: "My categories", sub: "Chart of accounts", emoji: "🗂️" },
];

export function Home({ companyName, go }: { companyName: string; go: (v: View) => void }) {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">What do you want to do today?</h1>
      <p className="text-slate-600 mb-8 text-lg">Working on: {companyName}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        {TILES.map((t) => (
          <button key={t.view} onClick={() => go(t.view)}
                  className="card text-left hover:border-blue-500 hover:shadow-lg transition">
            <div className="text-5xl mb-3">{t.emoji}</div>
            <div className="text-2xl font-semibold">{t.label}</div>
            <div className="text-slate-600 text-lg">{t.sub}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
