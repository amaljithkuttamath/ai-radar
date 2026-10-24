const canonical = "https://amaljithkuttamath.github.io/radar/";

export function destination(hash = "") {
  const [view, date] = hash.replace(/^#/, "").split("/");
  if (view === "archive" || view === "evidence") return `${canonical}#${view}`;
  if (view === "briefing" && /^\d{4}-\d{2}-\d{2}$/.test(date || "")) {
    const parsed = new Date(`${date}T00:00:00Z`);
    if (Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === date)
      return `${canonical}#briefing/${date}`;
  }
  return `${canonical}#briefing`;
}

if (typeof window !== "undefined") window.location.replace(destination(window.location.hash));
