import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Emp = { id: string; first_name: string; last_name: string; pay_type: string;
  pay_rate: string; filing_status: string; ssn_masked?: string; is_active: boolean };

type Tab = "employees" | "run" | "reports";

export function Payroll({ companyId, onBack }: { companyId: string; onBack: () => void }) {
  const [tab, setTab] = useState<Tab>("run");
  return (
    <div>
      <button className="text-blue-700 underline text-lg mb-4" onClick={onBack}>← Back</button>
      <h1 className="text-3xl font-bold mb-2">Payroll</h1>
      <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 mb-6 text-lg">
        ⚠️ Payroll uses <strong>sample tax tables that are still in draft</strong>. Have your
        CPA review and approve the rates before paying anyone for real.
      </div>
      <div className="flex gap-2 mb-6">
        {(["run", "employees", "reports"] as Tab[]).map((t) => (
          <button key={t}
            className={`px-5 py-3 rounded-xl text-lg font-semibold ${tab === t
              ? "bg-blue-700 text-white" : "bg-white border-2 border-blue-700 text-blue-800"}`}
            onClick={() => setTab(t)}>
            {t === "run" ? "Run payroll" : t === "employees" ? "Employees" : "Reports"}
          </button>
        ))}
      </div>
      {tab === "employees" && <Employees companyId={companyId} />}
      {tab === "run" && <RunPayroll companyId={companyId} />}
      {tab === "reports" && <PayrollReports companyId={companyId} />}
    </div>
  );
}

function Employees({ companyId }: { companyId: string }) {
  const [emps, setEmps] = useState<Emp[]>([]);
  const [form, setForm] = useState({ first_name: "", last_name: "", ssn: "",
    pay_type: "hourly", pay_rate: "", filing_status: "single" });
  function load() { api.get(`/companies/${companyId}/payroll/employees`).then(setEmps); }
  useEffect(() => { load(); }, [companyId]);

  async function add() {
    if (!form.first_name || !form.pay_rate) return;
    await api.post(`/companies/${companyId}/payroll/employees`, form);
    setForm({ ...form, first_name: "", last_name: "", ssn: "", pay_rate: "" });
    load();
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="card">
        <h2 className="text-2xl font-semibold mb-3">Your people</h2>
        {emps.length === 0 && <p className="text-slate-600">No employees yet.</p>}
        <ul className="divide-y">
          {emps.map((e) => (
            <li key={e.id} className="py-3 text-lg">
              <span className="font-medium">{e.first_name} {e.last_name}</span>
              <span className="text-slate-600"> · {e.pay_type === "hourly"
                ? `$${e.pay_rate}/hr` : `$${e.pay_rate}/yr`} · SSN {e.ssn_masked || "—"}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="card">
        <h2 className="text-2xl font-semibold mb-3">Add an employee</h2>
        <div className="space-y-3">
          <input className="field" placeholder="First name" value={form.first_name}
                 onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
          <input className="field" placeholder="Last name" value={form.last_name}
                 onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
          <input className="field" placeholder="Social Security Number" value={form.ssn}
                 onChange={(e) => setForm({ ...form, ssn: e.target.value })} />
          <select className="field" value={form.pay_type}
                  onChange={(e) => setForm({ ...form, pay_type: e.target.value })}>
            <option value="hourly">Hourly</option>
            <option value="salary">Salary (per year)</option>
          </select>
          <input className="field" inputMode="decimal"
                 placeholder={form.pay_type === "hourly" ? "Rate per hour" : "Yearly salary"}
                 value={form.pay_rate}
                 onChange={(e) => setForm({ ...form, pay_rate: e.target.value })} />
          <select className="field" value={form.filing_status}
                  onChange={(e) => setForm({ ...form, filing_status: e.target.value })}>
            <option value="single">Single</option>
            <option value="married_joint">Married (filing jointly)</option>
            <option value="head_of_household">Head of household</option>
          </select>
          <button className="btn-primary w-full" onClick={add}>Add employee</button>
        </div>
      </div>
    </div>
  );
}

function RunPayroll({ companyId }: { companyId: string }) {
  const [emps, setEmps] = useState<Emp[]>([]);
  const [hours, setHours] = useState<Record<string, string>>({});
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [payDate, setPayDate] = useState(new Date().toISOString().slice(0, 10));
  const [run, setRun] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(`/companies/${companyId}/payroll/employees`).then((e) =>
      setEmps(e.filter((x: Emp) => x.is_active)));
  }, [companyId]);

  async function calculate() {
    setError("");
    try {
      const r = await api.post(`/companies/${companyId}/payroll/runs`, {
        pay_period_start: start, pay_period_end: end, pay_date: payDate,
        hours: emps.map((e) => ({ employee_id: e.id, hours: hours[e.id] || "0" })),
      });
      setRun(r);
    } catch (e: any) { setError(e.message); }
  }

  async function post() {
    await api.post(`/companies/${companyId}/payroll/runs/${run.id}/post`);
    const refreshed = await api.get(`/companies/${companyId}/payroll/runs/${run.id}`);
    setRun(refreshed);
  }

  if (run) {
    const t = run.totals;
    return (
      <div className="card">
        <h2 className="text-2xl font-semibold mb-2">
          {run.status === "posted" ? "✅ Payroll posted" : "Review this payroll"}
        </h2>
        <p className="text-lg bg-amber-50 rounded-xl p-3 mb-4">{run.disclaimer}</p>
        <div className="overflow-x-auto">
          <table className="w-full text-lg mb-4">
            <thead><tr className="text-left border-b-2">
              <th>Employee</th><th className="text-right">Gross</th>
              <th className="text-right">Taxes</th><th className="text-right">Net</th>
              <th></th></tr></thead>
            <tbody>
              {run.items.map((it: any) => {
                const taxes = (Number(it.fed_wh) + Number(it.state_wh) +
                  Number(it.ss_employee) + Number(it.medicare_employee)).toFixed(2);
                return (
                  <tr key={it.id} className="border-b">
                    <td className="py-2">{it.employee}</td>
                    <td className="text-right">${it.gross_pay}</td>
                    <td className="text-right">${taxes}</td>
                    <td className="text-right font-semibold">${it.net_pay}</td>
                    <td className="text-right">
                      {run.status === "posted" && (
                        <button className="text-blue-700 underline"
                          onClick={() => window.open(api.fileUrl(
                            `/companies/${companyId}/payroll/runs/${run.id}/stubs/${it.id}`), "_blank")}>
                          Pay stub
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot><tr className="font-bold border-t-2">
              <td className="py-2">Totals</td>
              <td className="text-right">${t.gross_pay}</td>
              <td className="text-right"></td>
              <td className="text-right">${t.net_pay}</td><td></td>
            </tr></tfoot>
          </table>
        </div>
        {run.status !== "posted" ? (
          <div className="flex gap-3">
            <button className="btn-secondary" onClick={() => setRun(null)}>← Start over</button>
            <button className="btn-primary" onClick={post}>Approve &amp; record this payroll</button>
          </div>
        ) : (
          <button className="btn-primary" onClick={() => setRun(null)}>Run another payroll</button>
        )}
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="text-2xl font-semibold mb-4">Run a payroll</h2>
      {error && <p className="text-red-700 mb-3 text-lg">{error}</p>}
      <div className="grid sm:grid-cols-3 gap-4 mb-5">
        <div><label className="label">Period start</label>
          <input type="date" className="field" value={start} onChange={(e) => setStart(e.target.value)} /></div>
        <div><label className="label">Period end</label>
          <input type="date" className="field" value={end} onChange={(e) => setEnd(e.target.value)} /></div>
        <div><label className="label">Pay date</label>
          <input type="date" className="field" value={payDate} onChange={(e) => setPayDate(e.target.value)} /></div>
      </div>
      <h3 className="text-xl font-semibold mb-2">Hours this period</h3>
      {emps.length === 0 && <p className="text-slate-600 mb-3">Add an employee first.</p>}
      {emps.map((e) => (
        <div key={e.id} className="flex items-center justify-between py-2 text-lg">
          <span>{e.first_name} {e.last_name} {e.pay_type === "salary" && "(salary)"}</span>
          {e.pay_type === "hourly" ? (
            <input className="field w-32" inputMode="decimal" placeholder="hours"
                   value={hours[e.id] || ""}
                   onChange={(ev) => setHours({ ...hours, [e.id]: ev.target.value })} />
          ) : <span className="text-slate-500">auto</span>}
        </div>
      ))}
      <button className="btn-primary w-full mt-4" disabled={!start || !end || !emps.length}
              onClick={calculate}>Calculate payroll →</button>
    </div>
  );
}

function PayrollReports({ companyId }: { companyId: string }) {
  const [liab, setLiab] = useState<any>(null);
  useEffect(() => {
    api.get(`/companies/${companyId}/payroll/reports/tax_liability`).then(setLiab).catch(() => {});
  }, [companyId]);
  return (
    <div className="card">
      <h2 className="text-2xl font-semibold mb-3">Payroll tax liability (this year)</h2>
      {!liab ? <p>Loading…</p> : (
        <ul className="text-lg space-y-2">
          <li>Federal payroll taxes (Form 941): <strong>${liab.federal_941_liability}</strong></li>
          <li>Federal unemployment (Form 940 / FUTA): <strong>${liab.federal_unemployment_940_futa}</strong></li>
          <li>NJ state withholding: <strong>${liab.state_withholding}</strong></li>
          <li>NJ unemployment (SUTA): <strong>${liab.state_unemployment_suta}</strong></li>
        </ul>
      )}
      <p className="text-slate-600 mt-4">{liab?.disclaimer}</p>
    </div>
  );
}
