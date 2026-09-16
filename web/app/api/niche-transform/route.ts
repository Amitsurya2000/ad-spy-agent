import { NextRequest, NextResponse } from "next/server";
import { getPool } from "@/lib/db";
import { nicheTransform } from "@/lib/gemini";
import type { Json } from "@/lib/types";

export const dynamic = "force-dynamic";

function pickDna(primary: Json, fallback: Json): Json {
  return primary && Object.keys(primary).length ? primary : fallback;
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const jobId = body.job_id;
  const targetNiche = (body.target_niche ?? "").trim();
  if (!jobId || !targetNiche) {
    return NextResponse.json(
      { error: "job_id and target_niche are required" },
      { status: 400 }
    );
  }

  const { rows } = await getPool().query(
    "select query, copy_dna, gemini_copy_dna from research_jobs where id = $1",
    [jobId]
  );
  const job = rows[0];
  if (!job) {
    return NextResponse.json({ error: "Research not found" }, { status: 404 });
  }

  const copyDna = pickDna(job.gemini_copy_dna, job.copy_dna);
  const originalNiche = job.query || "unknown";

  const transforms = await nicheTransform(
    copyDna,
    originalNiche,
    targetNiche,
    body.product_name ?? "",
    body.product_desc ?? ""
  );

  return NextResponse.json({
    transforms,
    original_niche: originalNiche,
    target_niche: targetNiche,
  });
}
