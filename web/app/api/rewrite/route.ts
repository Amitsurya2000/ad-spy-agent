import { NextRequest, NextResponse } from "next/server";
import { getPool } from "@/lib/db";
import { rewriteAd } from "@/lib/gemini";
import type { Json } from "@/lib/types";

export const dynamic = "force-dynamic";

function pickDna(primary: Json, fallback: Json): Json {
  return primary && Object.keys(primary).length ? primary : fallback;
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const jobId = body.job_id;
  if (!jobId) {
    return NextResponse.json({ error: "job_id is required" }, { status: 400 });
  }

  const { rows } = await getPool().query(
    `select status, copy_dna, creative_dna, gemini_copy_dna, gemini_creative_dna
     from research_jobs where id = $1`,
    [jobId]
  );
  const job = rows[0];

  if (!job || job.status !== "completed") {
    return NextResponse.json(
      { error: "Research not found or not completed" },
      { status: 404 }
    );
  }

  const copyDna = pickDna(job.gemini_copy_dna, job.copy_dna);
  const creativeDna = pickDna(job.gemini_creative_dna, job.creative_dna);

  const rewrites = await rewriteAd(
    copyDna,
    creativeDna,
    body.product_name ?? "",
    body.product_desc ?? "",
    body.target_audience ?? "",
    6
  );

  return NextResponse.json({ rewrites, copy_dna: copyDna, creative_dna: creativeDna });
}
