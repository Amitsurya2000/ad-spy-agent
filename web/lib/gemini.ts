// Node port of the three post-scrape, no-browser-needed methods from the
// worker's gemini_engine.py (rewrite_ad, clone_specific_ad, niche_transform).
// Same prompts, same model - these just don't need the browser, so they run
// as Vercel API routes instead of waiting on the worker's poll loop.

import { GoogleGenerativeAI } from "@google/generative-ai";

const MODEL_NAME = "gemini-3-flash-preview";

let genAI: GoogleGenerativeAI | null = null;

function getModel() {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is not set.");
  }
  if (!genAI) {
    genAI = new GoogleGenerativeAI(apiKey);
  }
  return genAI.getGenerativeModel({ model: MODEL_NAME });
}

function cleanJson(text: string): string {
  return text
    .trim()
    .replace(/^```(?:json)?\s*/, "")
    .replace(/\s*```$/, "");
}

async function generateJson<T>(prompt: string, onParseError: () => T): Promise<T> {
  const model = getModel();
  const result = await model.generateContent(prompt);
  const text = result.response.text();
  try {
    return JSON.parse(cleanJson(text)) as T;
  } catch {
    return onParseError();
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Json = Record<string, any>;

export async function rewriteAd(
  copyDna: Json,
  creativeDna: Json,
  productName: string,
  productDesc: string,
  targetAudience: string,
  numVersions = 6
): Promise<Json[]> {
  const dnaCtx = JSON.stringify(copyDna ?? {}, null, 1);
  const creativeCtx = JSON.stringify(creativeDna ?? {}, null, 1);

  const prompt = `You are an elite Direct Response Creative Strategist. Your job is to CLONE the ad DNA of a successful competitor and create READY-TO-USE ads for a new product.

COMPETITOR'S COPY DNA:
${dnaCtx}

COMPETITOR'S CREATIVE/VISUAL DNA:
${creativeCtx}

CREATE ADS FOR:
- Product: ${productName || "the client product"}
- Description: ${productDesc || "a premium product"}
- Target Audience: ${targetAudience || "general audience"}

IMPORTANT RULES:
1. Follow the EXACT same copy framework, tone, hook style, sentence structure
2. Use the SAME emotional triggers and cognitive biases
3. Match copy length, emoji usage, power words pattern
4. Do NOT copy - TRANSFORM the DNA into a new version
5. Each version = different angle but SAME DNA
6. Make it IMMEDIATELY usable - a beginner should be able to post this right now
7. Include an image brief so they know exactly what visual to create

Generate ${numVersions} ad versions. Return a JSON array:
[
  {
    "version": "V1",
    "angle": "the specific angle (emotional/logical/fear/aspiration/social-proof/offer)",
    "angle_explanation": "why this angle was chosen based on the DNA",

    "hook": "the first line that stops the scroll",
    "hook_type": "Pattern Interrupt | Curiosity | Pain Point | Offer | Social Proof",

    "primary_text": "the FULL ad copy - ready to paste into Facebook",
    "headline": "the headline",
    "description": "the link description",
    "cta": "Shop Now | Learn More | Sign Up | etc",

    "image_brief": {
      "what_to_show": "exactly what should be in the image",
      "layout": "the layout to follow",
      "colors": ["specific colors to use"],
      "text_overlay": "what text to put on image (if any)",
      "mood": "the feeling the image should convey",
      "style": "photography | graphic | UGC | etc",
      "reference_description": "describe the final image in detail like briefing a designer"
    },

    "psychology_used": {
      "emotional_triggers": ["triggers used in this version"],
      "cognitive_bias": "main bias leveraged",
      "pain_point": "specific pain point hit",
      "desire": "specific desire triggered"
    },

    "why_it_works": "explain why this version follows the DNA and should perform well",
    "dna_match_score": 1-10
  }
]

STRICT: Do NOT be generic. Every ad must feel different but carry the same DNA fingerprint.
Return ONLY valid JSON array.`;

  try {
    return await generateJson<Json[]>(prompt, () => [{ error: "Parse error" }]);
  } catch (e) {
    return [{ error: e instanceof Error ? e.message : String(e) }];
  }
}

export async function cloneSpecificAd(
  originalAd: Json,
  imageAnalysis: Json,
  productName: string,
  productDesc: string
): Promise<Json> {
  const prompt = `You are an elite Direct Response Creative Strategist. You are cloning ONE specific viral ad for a new product.

ORIGINAL AD:
- Primary Text: ${originalAd?.primary_text ?? ""}
- Headline: ${originalAd?.headline ?? ""}
- CTA: ${originalAd?.cta ?? ""}
- Angle: ${originalAd?.angle ?? ""}
- Funnel: ${originalAd?.funnel_stage ?? ""}

ORIGINAL CREATIVE ANALYSIS:
${JSON.stringify(imageAnalysis ?? {}, null, 1)}

NEW PRODUCT:
- Name: ${productName || "New Product"}
- Description: ${productDesc || "a product"}

First BREAK DOWN the original ad, then CLONE it. Return JSON:
{
  "original_breakdown": {
    "hook_type": "what type of hook the original uses",
    "psychology_triggers": ["triggers in original"],
    "copy_framework": "framework used",
    "why_original_works": "2-3 sentences on why this ad is effective"
  },

  "cloned_ad": {
    "hook": "new opening hook following same pattern",
    "primary_text": "full rewritten copy - ready to paste",
    "headline": "rewritten headline",
    "description": "rewritten link description",
    "cta": "same CTA type"
  },

  "image_brief": {
    "what_to_show": "exactly what should be in the image",
    "layout": "layout to follow",
    "colors": ["colors to use"],
    "text_overlay": "text to put on image",
    "mood": "mood to convey",
    "style": "photography | graphic | UGC",
    "full_brief": "complete description for a designer"
  },

  "niche_transformation": {
    "new_niche": "a completely different niche this could work in",
    "transformed_hook": "the hook adapted for that niche",
    "transformed_primary_text": "full ad copy for the new niche",
    "transformed_headline": "headline for new niche",
    "why_it_transfers": "why this DNA works across niches"
  },

  "dna_preserved": ["list of DNA elements that were kept identical"],
  "what_was_changed": "explain what was adapted and why"
}
Return ONLY valid JSON.`;

  try {
    return await generateJson<Json>(prompt, () => ({ error: "Parse error" }));
  } catch (e) {
    return { error: e instanceof Error ? e.message : String(e) };
  }
}

export async function nicheTransform(
  copyDna: Json,
  originalNiche: string,
  targetNiche: string,
  productName: string,
  productDesc: string
): Promise<Json[]> {
  const prompt = `You are an elite Creative Strategist. Take the winning ad DNA from one niche and transform it into a different niche while keeping the EXACT same psychological patterns.

WINNING DNA FROM ${originalNiche.toUpperCase()}:
${JSON.stringify(copyDna ?? {}, null, 1)}

TRANSFORM INTO: ${targetNiche}
PRODUCT: ${productName || targetNiche + " product"} - ${productDesc || ""}

Create 3 transformed ads. Return JSON array:
[
  {
    "version": "V1",
    "original_niche": "${originalNiche}",
    "target_niche": "${targetNiche}",
    "hook": "the scroll-stopping first line",
    "primary_text": "full ad copy ready to use",
    "headline": "headline",
    "cta": "CTA button",
    "image_brief": "what the image should look like",
    "dna_elements_preserved": ["list what DNA was kept"],
    "what_was_adapted": "what changed for the new niche",
    "why_it_transfers": "why this pattern works across niches"
  }
]
Return ONLY valid JSON array.`;

  try {
    return await generateJson<Json[]>(prompt, () => [{ error: "Parse error" }]);
  } catch (e) {
    return [{ error: e instanceof Error ? e.message : String(e) }];
  }
}
