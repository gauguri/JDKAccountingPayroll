import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { loadAccounts } from "../App";
import { DateField } from "../components/DateField";

type Kind = "income" | "expense";
type Acct = { id: string; name: string; type: string };
type Preview = { explanation: string; lines: { account_name: string; debit: string; credit: string }[] };

const PAYMENT_METHODS = ["cash", "check", "credit_card", "ach", "zelle", "venmo"];
const LABEL: Record<string, string> = {
  cash: "Cash", check: "Check", credit_card: "Credit card",
  ach: "Bank transfer (ACH)", zelle: "Zelle", venmo: "Venmo",
};

export function EntryWizard({ kind, companyId, onBack }: {
  kind: Kind; companyId: string; onBack: () => void;
}) {
  const [accounts, setAccounts] = useState<Acct[]>([]);
  const [step, setStep] = useState(1);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState("");
  const [done, setDone] = useState<string | null>(null);

  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [amount, setAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("check");
  const [accountId, setAccountId] = useState("");
  const [party, setParty] = useState("");
  const [salesTax, setSalesTax] = useState("0");
  const [cpaReview, setCpaReview] = useState(false);
  const [notes, setNotes] = useState("");

  const isIncome = kind === "income";
  // API resource path: income endpoints are /income, expense endpoints are /expenses.
  const resource = isIncome ? "income" : "expenses";
  const categoryAccounts = accounts.filter((a) => a.type === (isIncome ? "income" : "expense"));

  useEffect(() => {
    loadAccounts(companyId).then((a) => {
      setAccounts(a);
      const first = a.find((x) => x.type === (isIncome ? "income" : "expense"));
      if (first) setAccountId(first.id);
    });
  }, [companyId, kind]);

  function body() {
    return isIncome
      ? { date, amount, payment_method: paymentMethod, income_account_id: accountId,
          customer_name: party || null, sales_tax_collected: salesTax || "0", notes }
      : { date, amount, payment_method: paymentMethod, expense_account_id: accountId,
          vendor_name: party || null, cpa_review: cpaReview, notes };
  }

  async function doPreview() {
    setError("");
    try {
      const p = await api.post(`/companies/${companyId}/${resource}/preview`, body());
      setPreview(p); setStep(2);
    } catch (e: any) { setError(e.message); }
  }

  async function confirm() {
    setError("");
    try {
      const r = await api.post(`/companies/${companyId}/${resource}`, body());
      setDone(r.explanation); setStep(3);
    } catch (e: any) { setError(e.message); }
  }

  if (step === 3)
    return (
      <div className="card max-w-2xl">
        <div className="text-5xl mb-3">✅</div>
        <h2 className="text-2xl font-bold mb-2">Saved to your books</h2>
        <p className="text-lg text-slate-700 mb-6">{done}</p>
        <button className="btn-primary" onClick={onBack}>Back to home</button>
      </div>
    );

  return (
    <div className="max-w-2xl">
      <button className="text-blue-700 underline text-lg mb-4" onClick={onBack}>← Back</button>
      <h1 className="text-3xl font-bold mb-1">
        {isIncome ? "Record money coming in" : "Record money going out"}
      </h1>
      <p className="text-slate-600 mb-6 text-lg">Step {step} of 2</p>

      {error && <p className="text-red-700 mb-4 text-lg">{error}</p>}

      {step === 1 && (
        <div className="card space-y-4">
          <div>
            <label className="label">Date</label>
            <DateField value={date} onChange={setDate} />
          </div>
          <div>
            <label className="label">Amount ($)</label>
            <input className="field" inputMode="decimal" value={amount}
                   placeholder="0.00" onChange={(e) => setAmount(e.target.value)} />
          </div>
          <div>
            <label className="label">{isIncome ? "Customer (optional)" : "Who did you pay?"}</label>
            <input className="field" value={party}
                   onChange={(e) => setParty(e.target.value)} />
          </div>
          <div>
            <label className="label">{isIncome ? "What was it for?" : "Category"}</label>
            <select className="field" value={accountId}
                    onChange={(e) => setAccountId(e.target.value)}>
              {categoryAccounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Payment method</label>
            <select className="field" value={paymentMethod}
                    onChange={(e) => setPaymentMethod(e.target.value)}>
              {PAYMENT_METHODS.map((m) => <option key={m} value={m}>{LABEL[m]}</option>)}
            </select>
          </div>
          {isIncome && (
            <div>
              <label className="label">Sales tax collected ($)</label>
              <input className="field" inputMode="decimal" value={salesTax}
                     onChange={(e) => setSalesTax(e.target.value)} />
            </div>
          )}
          {!isIncome && (
            <label className="flex items-center gap-3 text-lg">
              <input type="checkbox" className="w-6 h-6" checked={cpaReview}
                     onChange={(e) => setCpaReview(e.target.checked)} />
              Flag this for my CPA to review
            </label>
          )}
          <button className="btn-primary w-full" onClick={doPreview}>
            See what this will do →
          </button>
        </div>
      )}

      {step === 2 && preview && (
        <div className="card">
          <h2 className="text-2xl font-semibold mb-3">Here's what will happen</h2>
          <p className="text-lg bg-blue-50 rounded-xl p-4 mb-5">{preview.explanation}</p>
          <table className="w-full text-lg mb-6">
            <thead>
              <tr className="text-left border-b-2"><th>Account</th>
                <th className="text-right">In</th><th className="text-right">Out</th></tr>
            </thead>
            <tbody>
              {preview.lines.map((l, i) => (
                <tr key={i} className="border-b">
                  <td className="py-2">{l.account_name}</td>
                  <td className="text-right">{Number(l.debit) ? `$${l.debit}` : ""}</td>
                  <td className="text-right">{Number(l.credit) ? `$${l.credit}` : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex gap-3">
            <button className="btn-secondary" onClick={() => setStep(1)}>← Change something</button>
            <button className="btn-primary" onClick={confirm}>Yes, save it</button>
          </div>
        </div>
      )}
    </div>
  );
}
