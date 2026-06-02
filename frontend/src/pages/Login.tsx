import { useState } from "react";
import { api } from "../lib/api";

export function Login({ onDone }: { onDone: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [businessType, setBusinessType] = useState("c_corp");
  const [error, setError] = useState("");

  async function submit() {
    setError("");
    try {
      if (mode === "register") {
        await api.post("/auth/register", {
          email, password, company_name: companyName,
          business_type: businessType, state: "NJ",
        });
      } else {
        await api.post("/auth/login", { email, password });
      }
      onDone();
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="card w-full max-w-md">
        <h1 className="text-3xl font-bold mb-1">JDK Books</h1>
        <p className="text-slate-600 mb-6">
          {mode === "login" ? "Welcome back. Please sign in." : "Let's set up your business."}
        </p>
        <label className="label">Email</label>
        <input className="field mb-4" value={email}
               onChange={(e) => setEmail(e.target.value)} />
        <label className="label">Password</label>
        <input className="field mb-4" type="password" value={password}
               onChange={(e) => setPassword(e.target.value)} />
        {mode === "register" && (
          <>
            <label className="label">Business name</label>
            <input className="field mb-4" value={companyName}
                   onChange={(e) => setCompanyName(e.target.value)} />
            <label className="label">Business type</label>
            <select className="field mb-4" value={businessType}
                    onChange={(e) => setBusinessType(e.target.value)}>
              <option value="c_corp">C corporation</option>
              <option value="smllc">Single-member LLC</option>
              <option value="s_corp">S corporation</option>
              <option value="sole_prop">Sole proprietorship</option>
              <option value="partnership">Partnership</option>
            </select>
          </>
        )}
        {error && <p className="text-red-700 mb-3 text-lg">{error}</p>}
        <button className="btn-primary w-full mb-3" onClick={submit}>
          {mode === "login" ? "Sign in" : "Create my business"}
        </button>
        <button className="text-blue-700 underline w-full text-lg"
                onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "First time here? Set up a new business" : "I already have an account"}
        </button>
      </div>
    </div>
  );
}
