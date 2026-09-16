import { NextRequest, NextResponse } from "next/server";
import { getPool } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  try {
    const pool = getPool();
    const [jobResult, adsResult] = await Promise.all([
      pool.query("select * from research_jobs where id = $1", [id]),
      pool.query("select * from ads where job_id = $1 order by created_at", [id]),
    ]);

    if (jobResult.rows.length === 0) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    return NextResponse.json({ job: jobResult.rows[0], ads: adsResult.rows });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : String(e) },
      { status: 500 }
    );
  }
}
