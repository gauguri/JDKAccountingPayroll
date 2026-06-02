import { useEffect, useState } from "react";
import { api, Account, Company } from "./lib/api";
import { Login } from "./pages/Login";
import { Home } from "./pages/Home";
import { EntryWizard } from "./pages/EntryWizard";
import { Reports } from "./pages/Reports";
import { Accounts } from "./pages/Accounts";
import { Payroll } from "./pages/Payroll";
import { CompanyBar } from "./components/CompanyBar";

export type View = "home" | "income" | "expense" | "reports" | "accounts" | "payroll";

export default function App() {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyId, setCompanyId] = useState<string>("");
  const [view, setView] = useState<View>("home");

  async function loadSession() {
    try {
      await api.get("/auth/me");
      const cos = await api.get("/companies");
      setCompanies(cos);
      setCompanyId((prev) => prev || (cos[0]?.id ?? ""));
      setAuthed(true);
    } catch {
      setAuthed(false);
    }
  }
  useEffect(() => {
    loadSession();
  }, []);

  if (authed === null)
    return <div className="p-10 text-xl">Loading…</div>;
  if (!authed) return <Login onDone={loadSession} />;

  const company = companies.find((c) => c.id === companyId);

  return (
    <div className="min-h-screen">
      <CompanyBar
        companies={companies}
        companyId={companyId}
        onPick={(id) => { setCompanyId(id); setView("home"); }}
        onLogout={async () => { await api.post("/auth/logout"); setAuthed(false); }}
        onReload={loadSession}
      />
      <main className="max-w-4xl mx-auto px-4 py-8">
        {!companyId ? (
          <p className="text-xl">Add a business to get started.</p>
        ) : view === "home" ? (
          <Home companyName={company?.name || ""} go={setView} />
        ) : view === "income" ? (
          <EntryWizard kind="income" companyId={companyId} onBack={() => setView("home")} />
        ) : view === "expense" ? (
          <EntryWizard kind="expense" companyId={companyId} onBack={() => setView("home")} />
        ) : view === "reports" ? (
          <Reports companyId={companyId} onBack={() => setView("home")} />
        ) : view === "payroll" ? (
          <Payroll companyId={companyId} onBack={() => setView("home")} />
        ) : (
          <Accounts companyId={companyId} onBack={() => setView("home")} />
        )}
      </main>
    </div>
  );
}

// Re-export a shared account loader for pages.
export async function loadAccounts(companyId: string): Promise<Account[]> {
  return api.get(`/companies/${companyId}/accounts`);
}
