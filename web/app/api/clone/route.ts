import { NextRequest, NextResponse } from "next/server";
import { getPool } from "@/lib/db";
import { cloneSpecificAd } from "@/lib/gemini";

export const dynamic = "force-dynamic";

// Clones one specific scraped ad (identified by its Postgres row id).
export async function POST(req: NextRequest) {
  const body = await req.json();
  const adId = body.ad_id;
  if (!adId) {
    return NextResponse.json({ error: "ad_id is required" }, { status: 400 });
  }

  const { rows } = await getPool().query("select * from ads where id = $1", [adId]);
  const ad = rows[0];
  if (!ad) {
    return NextResponse.json({ error: "Ad not found" }, { status: 404 });
  }

  const imageAnalysis = ad.full_breakdown?.visual_breakdown ?? {};
  const clone = await cloneSpecificAd(
    ad,
    imageAnalysis,
    body.product_name ?? "",
    body.product_desc ?? ""
  );

  return NextResponse.json({ clone, original: ad });
}
