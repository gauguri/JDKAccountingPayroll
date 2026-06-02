import { useEffect, useRef, useState } from "react";

// A large, senior-friendly date picker. Replaces <input type="date">, whose
// native calendar popup can't be resized with CSS.

const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
  "August", "September", "October", "November", "December"];
const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function parse(value: string): { y: number; m: number; d: number } | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
  return m ? { y: +m[1], m: +m[2] - 1, d: +m[3] } : null;  // m is zero-based
}
function fmt(y: number, m: number, d: number): string {
  return `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export function DateField({ value, onChange, className = "" }: {
  value: string;
  onChange: (v: string) => void;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const parsed = parse(value);
  const today = new Date();
  const [view, setView] = useState(() => {
    const p = parse(value);
    return p ? { y: p.y, m: p.m } : { y: today.getFullYear(), m: today.getMonth() };
  });

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const firstDow = new Date(view.y, view.m, 1).getDay();
  const daysInMonth = new Date(view.y, view.m + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const display = parsed ? `${MONTHS[parsed.m]} ${parsed.d}, ${parsed.y}` : "Pick a date";

  const prevMonth = () => setView(v => (v.m === 0 ? { y: v.y - 1, m: 11 } : { y: v.y, m: v.m - 1 }));
  const nextMonth = () => setView(v => (v.m === 11 ? { y: v.y + 1, m: 0 } : { y: v.y, m: v.m + 1 }));
  const pick = (d: number) => { onChange(fmt(view.y, view.m, d)); setOpen(false); };

  const isSelected = (d: number) =>
    parsed && parsed.y === view.y && parsed.m === view.m && parsed.d === d;

  return (
    <div className={`relative ${className}`} ref={ref}>
      <button type="button" onClick={() => setOpen(o => !o)}
              className="field text-left flex justify-between items-center">
        <span>{display}</span>
        <span className="text-2xl leading-none">📅</span>
      </button>

      {open && (
        <div className="absolute z-50 mt-2 bg-white border-2 border-slate-300 rounded-2xl shadow-xl p-4"
             style={{ minWidth: "24rem" }}>
          <div className="flex items-center justify-between mb-3">
            <button type="button" onClick={prevMonth}
                    className="px-4 py-2 text-3xl leading-none rounded-lg hover:bg-slate-100">‹</button>
            <div className="text-2xl font-semibold">{MONTHS[view.m]} {view.y}</div>
            <button type="button" onClick={nextMonth}
                    className="px-4 py-2 text-3xl leading-none rounded-lg hover:bg-slate-100">›</button>
          </div>
          <div className="grid grid-cols-7 gap-1 text-center">
            {DOW.map(d => (
              <div key={d} className="text-lg font-semibold text-slate-500 py-1">{d}</div>
            ))}
            {cells.map((d, i) => d === null ? (
              <div key={i} />
            ) : (
              <button type="button" key={i} onClick={() => pick(d)}
                      className={`text-2xl py-2 rounded-lg hover:bg-blue-100 ${
                        isSelected(d) ? "bg-blue-700 text-white hover:bg-blue-700" : ""}`}>
                {d}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
