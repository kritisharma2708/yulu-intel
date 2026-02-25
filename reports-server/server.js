require("dotenv").config({ path: require("path").resolve(__dirname, "../.env") });
const express = require("express");
const path = require("path");
const fs = require("fs");
const { createClient } = require("@supabase/supabase-js");

const app = express();
const PORT = process.env.PORT || 3000;
const REPORTS_DIR = path.resolve(__dirname, "../reports");

// Supabase client (optional — graceful if not configured)
let supabase = null;
if (process.env.SUPABASE_URL && process.env.SUPABASE_KEY) {
  supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);
}

// --- Root redirect ---
app.get("/", (_req, res) => res.redirect("/reports"));

// --- Health check ---
app.get("/health", (_req, res) => {
  res.json({ status: "ok", supabase: !!supabase, reportsDir: REPORTS_DIR });
});

// --- Redirect to latest report ---
app.get("/report/latest", async (_req, res) => {
  // Try local files first
  try {
    const files = fs
      .readdirSync(REPORTS_DIR)
      .filter((f) => f.endsWith(".html"))
      .sort()
      .reverse();
    if (files.length > 0) {
      const dateStr = files[0].replace(".html", "");
      return res.redirect(`/report/${dateStr}`);
    }
  } catch {
    // directory may not exist
  }

  // Fallback: Supabase
  if (supabase) {
    try {
      const { data } = await supabase
        .from("analysis_runs")
        .select("run_date")
        .not("report_html", "is", null)
        .order("run_date", { ascending: false })
        .limit(1);
      if (data && data.length > 0) {
        return res.redirect(`/report/${data[0].run_date}`);
      }
    } catch {
      // ignore
    }
  }

  res.status(404).send("No reports found.");
});

// --- Serve a specific report by date ---
app.get("/report/:date", async (req, res) => {
  const dateStr = req.params.date;

  // Validate date format (YYYY-MM-DD)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    return res.status(400).send("Invalid date format. Use YYYY-MM-DD.");
  }

  const localPath = path.join(REPORTS_DIR, `${dateStr}.html`);

  // Try local file
  if (fs.existsSync(localPath)) {
    return res.sendFile(localPath);
  }

  // Supabase fallback — fetch and cache locally
  if (supabase) {
    try {
      const { data } = await supabase
        .from("analysis_runs")
        .select("report_html")
        .eq("run_date", dateStr)
        .limit(1)
        .single();

      if (data && data.report_html) {
        // Cache locally
        fs.mkdirSync(REPORTS_DIR, { recursive: true });
        fs.writeFileSync(localPath, data.report_html, "utf-8");
        return res.type("html").send(data.report_html);
      }
    } catch {
      // ignore
    }
  }

  res.status(404).send(`No report found for ${dateStr}.`);
});

// --- Index page: list all reports ---
app.get("/reports", async (_req, res) => {
  const reports = [];

  // Collect from local files
  try {
    const files = fs
      .readdirSync(REPORTS_DIR)
      .filter((f) => f.endsWith(".html"))
      .sort()
      .reverse();
    for (const f of files) {
      reports.push({ date: f.replace(".html", ""), source: "local" });
    }
  } catch {
    // directory may not exist
  }

  // Collect from Supabase (merge, avoiding duplicates)
  if (supabase) {
    try {
      const { data } = await supabase
        .from("analysis_runs")
        .select("run_date")
        .not("report_html", "is", null)
        .order("run_date", { ascending: false });
      if (data) {
        const existing = new Set(reports.map((r) => r.date));
        for (const row of data) {
          if (!existing.has(row.run_date)) {
            reports.push({ date: row.run_date, source: "supabase" });
          }
        }
      }
    } catch {
      // ignore
    }
  }

  // Sort descending
  reports.sort((a, b) => b.date.localeCompare(a.date));

  const cards = reports
    .map(
      (r, i) => `
      <a href="/report/${r.date}" class="report-card">
        <span class="report-date">${r.date}</span>
        ${i === 0 ? '<span class="badge">Latest</span>' : ""}
        <span class="view-link">View Report &rarr;</span>
      </a>`
    )
    .join("\n");

  res.type("html").send(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CompeteIQ Reports</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',system-ui,sans-serif;background:#f8fafc;color:#1e293b;padding:40px 20px}
.container{max-width:700px;margin:0 auto}
h1{font-size:1.8rem;font-weight:700;margin-bottom:8px}
p.sub{color:#64748b;margin-bottom:32px}
.report-card{display:flex;align-items:center;gap:12px;background:#fff;border-radius:12px;padding:18px 24px;margin-bottom:12px;text-decoration:none;color:#1e293b;box-shadow:0 1px 3px rgba(0,0,0,.08);transition:transform .1s,box-shadow .15s}
.report-card:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.12)}
.report-date{font-weight:600;font-size:1.05rem}
.badge{background:#4f46e5;color:#fff;font-size:.7rem;font-weight:600;padding:2px 10px;border-radius:99px;text-transform:uppercase}
.view-link{margin-left:auto;color:#4f46e5;font-weight:500;font-size:.9rem}
.empty{text-align:center;color:#94a3b8;margin-top:60px;font-size:1.1rem}
</style>
</head>
<body>
<div class="container">
<h1>CompeteIQ Reports</h1>
<p class="sub">Competitive intelligence reports for Yulu</p>
${reports.length === 0 ? '<p class="empty">No reports yet. Run the agent to generate your first report.</p>' : cards}
</div>
</body>
</html>`);
});

app.listen(PORT, () => {
  console.log(`CompeteIQ reports server running on http://localhost:${PORT}`);
  console.log(`  Reports index:  http://localhost:${PORT}/reports`);
  console.log(`  Latest report:  http://localhost:${PORT}/report/latest`);
  console.log(`  Health check:   http://localhost:${PORT}/health`);
});
