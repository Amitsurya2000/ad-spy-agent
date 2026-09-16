import { NextRequest, NextResponse } from "next/server";
import { getPool } from "@/lib/db";

export const dynamic = "force-dynamic";

// Inserts a pending job row - the external worker (worker.py) polls for
// these and does the actual scraping. See RUN.md.
export async function POST(req: NextRequest) {
  const body = await req.json();
  const query = (body.query ?? "").trim();
  if (!query) {
    return NextResponse.json({ error: "Query is required" }, { status: 400 });
  }

  const country = body.country || "ALL";
  const maxAds = Math.min(Number(body.max_ads) || 30, 50);
  const scrollRounds = Math.min(Number(body.scroll_rounds) || 5, 10);
  const useGemini = body.use_gemini !== false;

  try {
    const { rows } = await getPool().query(
      `insert into research_jobs (query, country, max_ads, scroll_rounds, use_gemini, status)
       values ($1, $2, $3, $4, $5, 'pending')
       returning *`,
      [query, country, maxAds, scrollRounds, useGemini]
    );
    return NextResponse.json(rows[0], { status: 201 });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : String(e) },
      { status: 500 }
    );
  }
}

export async function GET() {
  try {
    const { rows } = await getPool().query(
      `select id, query, country, status, error, created_at, updated_at
       from research_jobs
       order by created_at desc
       limit 100`
    );
    return NextResponse.json(rows);
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : String(e) },
      { status: 500 }
    );
  }
}
