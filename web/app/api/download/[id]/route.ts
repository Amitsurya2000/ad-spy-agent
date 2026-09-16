import { NextRequest, NextResponse } from "next/server";
import { getPool } from "@/lib/db";

export const dynamic = "force-dynamic";

// Port of report.py's save_json/save_csv, generated on the fly from
// Postgres instead of read off disk. ?format=csv|json (default json).
const CSV_FIELDS = [
  "ad_id", "platform", "status", "start_date",
  "primary_text", "headline", "cta", "media_type",
  "angle", "funnel_stage",
  "hook", "problem", "solution", "offer", "copy_cta",
];

function csvEscape(value: unknown): string {
  const s = value === null || value === undefined ? "" : String(value);
  if (/[",\n]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const format = req.nextUrl.searchParams.get("format") === "csv" ? "csv" : "json";

  const pool = getPool();
  const [jobResult, adsResult] = await Promise.all([
    pool.query("select * from research_jobs where id = $1", [id]),
    pool.query("select * from ads where job_id = $1 order by created_at", [id]),
  ]);

  const job = jobResult.rows[0];
  if (!job) {
    return NextResponse.json({ error: "Job not found" }, { status: 404 });
  }
  const ads = adsResult.rows;

  const safeName = (job.query || "ads").toLowerCase().replace(/[^a-z0-9_-]/g, "_");

  if (format === "csv") {
    const rows = ads.map((ad) => {
      const cb = ad.copy_breakdown ?? {};
      return [
        ad.ad_id, ad.platform, ad.status, ad.start_date,
        ad.primary_text, ad.headline, ad.cta, ad.media_type,
        ad.angle, ad.funnel_stage,
        cb.hook, cb.problem, cb.solution, cb.offer, cb.cta,
      ]
        .map(csvEscape)
        .join(",");
    });
    const csv = [CSV_FIELDS.join(","), ...rows].join("\n");
    return new NextResponse(csv, {
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": `attachment; filename="${safeName}_ads.csv"`,
      },
    });
  }

  const payload = { brand: job.brand_info, ads };
  return new NextResponse(JSON.stringify(payload, null, 2), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Disposition": `attachment; filename="${safeName}_ads.json"`,
    },
  });
}
