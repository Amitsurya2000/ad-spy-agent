"""
Gemini AI Engine - Powers the Viral Ad Cloner
==============================================
Elite Direct Response Creative Strategist & Ad Intelligence Analyst.
Every ad becomes: See -> Understand -> Replicate -> Launch
"""

import base64
import json
import os
import re
import google.generativeai as genai


def _clean_json(text):
    """Strip markdown fences and extract JSON from Gemini response."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text


class GeminiEngine:

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-3-flash-preview")
        self.vision_model = genai.GenerativeModel("gemini-3-flash-preview")

    # ------------------------------------------------------------------
    # 1. FULL CREATIVE DNA BREAKDOWN per ad (image + copy)
    # ------------------------------------------------------------------

    def full_ad_breakdown(self, ad: dict, image_path: str = None) -> dict:
        """Complete Creative DNA Breakdown for a single ad - the core analysis."""

        image_part = None
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_part = {"mime_type": "image/jpeg", "data": f.read()}

        prompt = f"""You are an elite Direct Response Creative Strategist and Ad Intelligence Analyst.

Your job is to perform a COMPLETE "Creative DNA Breakdown" on this ad. Your output must be simple, structured, and highly actionable for someone with ZERO marketing knowledge.

AD DATA:
- Primary Text: {ad.get('primary_text', 'N/A')}
- Headline: {ad.get('headline', 'N/A')}
- CTA: {ad.get('cta', 'N/A')}
- Platform: {ad.get('platform', 'Facebook')}
- Status: {ad.get('status', 'Unknown')}
- Media Type: {ad.get('media_type', 'Image')}
{"- [Image attached for visual analysis]" if image_part else "- No image available"}

Perform the COMPLETE breakdown and return a JSON object:
{{
  "basic_info": {{
    "ad_type": "Video | Image | Carousel",
    "platform": "Facebook | Instagram",
    "cta_used": "the CTA button text",
    "funnel_stage": "Cold | Warm | Retargeting",
    "funnel_reasoning": "why you think this funnel stage"
  }},

  "hook_analysis": {{
    "first_3_seconds": "what grabs attention immediately",
    "hook_type": "Pattern Interrupt | Curiosity | Pain Point | Offer | Social Proof | Shock",
    "why_it_works": "psychology behind why this hook stops the scroll"
  }},

  "psychology_triggers": {{
    "pain_points_targeted": ["list each pain point"],
    "desire_triggered": ["what desires does this tap into"],
    "emotional_drivers": ["Fear | Greed | Status | Convenience | Belonging | etc"],
    "cognitive_biases": ["FOMO | Authority | Scarcity | Social Proof | Anchoring | etc"],
    "persuasion_explanation": "explain HOW these triggers work together in simple terms"
  }},

  "creative_dna": {{
    "hook_formula": "the reusable hook template/pattern",
    "body_structure": "how the story/body is structured step by step",
    "offer_structure": "how the offer is presented",
    "cta_strategy": "how they drive action",
    "replicable_pattern": "explain the full pattern so a beginner can copy it"
  }},

  "copy_breakdown": {{
    "primary_text_style": "short | long | story | salesy | educational",
    "headline_strategy": "what the headline does and why",
    "tone": "aggressive | emotional | educational | conversational | urgent | inspirational",
    "power_words": ["list the power/action words used"],
    "copy_score": 1-10
  }},

  "visual_breakdown": {{
    "what_is_shown": "describe exactly what the viewer sees",
    "layout_type": "product shot | lifestyle | UGC | text-heavy | before-after | testimonial",
    "color_palette": ["main colors"],
    "has_text_overlay": true/false,
    "text_overlay_content": "what text is on the image",
    "has_person": true/false,
    "person_description": "who is in the image and their expression",
    "product_focus": "how the product is displayed",
    "editing_style": "raw | polished | UGC | fast cuts | minimal",
    "why_visuals_convert": "explain WHY these visuals help drive action"
  }},

  "why_this_ad_works": [
    "reason 1 - be specific",
    "reason 2 - be specific",
    "reason 3 - be specific",
    "reason 4 - be specific",
    "reason 5 - be specific"
  ],

  "overall_score": 1-10,
  "one_line_verdict": "one sentence summary of this ad's strength"
}}

STRICT RULES:
- Do NOT give generic answers. Be SPECIFIC to THIS ad.
- Do NOT just describe - always explain WHY.
- Keep language SIMPLE. No jargon.
- Make it feel like a lesson, not a report.

Return ONLY valid JSON."""

        try:
            parts = [prompt]
            if image_part:
                parts.append(image_part)
            response = self.vision_model.generate_content(parts)
            return json.loads(_clean_json(response.text))
        except json.JSONDecodeError:
            return {"raw_analysis": response.text if response else ""}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # 2. COPY DNA across ALL ads
    # ------------------------------------------------------------------

    def analyze_copy_dna(self, ads: list) -> dict:
        copies = []
        for ad in ads:
            if ad.get("primary_text"):
                copies.append({
                    "text": ad["primary_text"],
                    "headline": ad.get("headline", ""),
                    "cta": ad.get("cta", ""),
                    "status": ad.get("status", ""),
                })
        if not copies:
            return {"error": "No ad copies to analyze"}

        prompt = f"""You are an elite Direct Response Creative Strategist. Analyze these {len(copies)} Facebook/Instagram ads from the same brand and extract the COPY DNA - the hidden patterns that make their ads work.

Your audience has ZERO marketing knowledge. Make everything simple and actionable.

ADS DATA:
{json.dumps(copies[:20], ensure_ascii=False, indent=1)}

Return a JSON object:
{{
  "dna_summary": "3-4 sentence summary a complete beginner could use to write ads in this brand's style. Be specific, not generic.",

  "copy_framework": "PAS | AIDA | BAB | FAB | Direct Offer | Storytelling | Question-based",
  "copy_framework_explanation": "explain HOW they use this framework in simple terms with examples from their ads",

  "hook_strategy": {{
    "pattern": "describe the hook pattern they repeat",
    "hook_type": "Pain Point | Curiosity | Offer | Social Proof | Pattern Interrupt",
    "hook_examples": ["top 3 actual hooks from their ads"],
    "hook_formula": "the fill-in-the-blank formula a beginner can use"
  }},

  "tone": {{
    "primary": "conversational | professional | urgent | playful | inspirational | authoritative",
    "secondary": "secondary tone if any",
    "description": "describe their voice like you are explaining to a friend"
  }},

  "psychology_playbook": {{
    "emotional_triggers": ["list each emotional trigger they use"],
    "cognitive_biases": ["FOMO | Scarcity | Authority | Social Proof | etc"],
    "pain_points_targeted": ["specific pain points across all ads"],
    "desires_targeted": ["specific desires they tap into"],
    "persuasion_technique": "the main persuasion approach"
  }},

  "copy_patterns": {{
    "sentence_structure": "short punchy | long descriptive | mixed | fragmented",
    "avg_copy_length": "short (1-2 lines) | medium (3-5 lines) | long (5+ lines)",
    "uses_emoji": true/false,
    "emoji_style": "how they use emoji",
    "uses_numbers": true/false,
    "uses_questions": true/false,
    "power_words": ["top power/action words they repeat"],
    "unique_phrases": ["recurring phrases or taglines"],
    "language_style": "formal | informal | slang | technical | simple"
  }},

  "cta_strategy": {{
    "primary_cta": "most used CTA",
    "cta_pattern": "how they drive action",
    "urgency_tactics": "how they create urgency"
  }},

  "target_audience_inferred": "who these ads are targeting - be specific",
  "what_makes_it_viral": "the SECRET SAUCE - why these ads work. Be specific, not generic.",
  "brand_voice": "describe the brand voice like explaining to a friend"
}}
Return ONLY valid JSON."""

        try:
            response = self.model.generate_content(prompt)
            return json.loads(_clean_json(response.text))
        except json.JSONDecodeError:
            return {"raw_analysis": response.text if response else ""}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # 3. CREATIVE DNA across all images
    # ------------------------------------------------------------------

    def analyze_creative_dna(self, image_analyses: list) -> dict:
        if not image_analyses:
            return {}

        prompt = f"""You are an elite Creative Director analyzing {len(image_analyses)} ad creatives from the same brand. Extract the VISUAL DNA - the design patterns that make their creatives convert.

Make everything simple for someone with zero design knowledge.

INDIVIDUAL ANALYSES:
{json.dumps(image_analyses[:15], ensure_ascii=False, indent=1)}

Return a JSON object:
{{
  "creative_dna_summary": "3-4 sentence summary a designer or beginner could use to replicate this brand's visual style",
  "visual_identity": "describe the brand's visual identity simply",
  "dominant_layout": "most common layout",
  "color_strategy": {{
    "primary_colors": ["top 3 colors"],
    "color_mood": "warm | cool | vibrant | muted | dark | bright",
    "why_these_colors": "explain why these colors work for their audience"
  }},
  "typography_style": "bold | minimal | decorative | clean",
  "image_style": "photography | illustration | graphic | UGC | mixed",
  "product_showcase": "how they display their product",
  "human_element": "how they use people in ads",
  "text_overlay_strategy": "how they use text on images",
  "mood_consistency": "the consistent mood/feeling",
  "design_patterns": ["recurring design elements"],
  "visual_hook_strategy": "what visual element grabs attention first",
  "what_makes_creatives_work": "the visual secret sauce - be specific",
  "replication_guide": "step by step instructions for a beginner to recreate this visual style"
}}
Return ONLY valid JSON."""

        try:
            response = self.model.generate_content(prompt)
            return json.loads(_clean_json(response.text))
        except json.JSONDecodeError:
            return {"raw_analysis": response.text if response else ""}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # 4. REWRITE ENGINE - Clone DNA into new ads
    # ------------------------------------------------------------------

    def rewrite_ad(self, copy_dna: dict, creative_dna: dict,
                   product_name: str, product_desc: str,
                   target_audience: str, num_versions: int = 6) -> list:

        dna_ctx = json.dumps(copy_dna, ensure_ascii=False, indent=1)
        creative_ctx = json.dumps(creative_dna, ensure_ascii=False, indent=1) if creative_dna else "{}"

        prompt = f"""You are an elite Direct Response Creative Strategist. Your job is to CLONE the ad DNA of a successful competitor and create READY-TO-USE ads for a new product.

COMPETITOR'S COPY DNA:
{dna_ctx}

COMPETITOR'S CREATIVE/VISUAL DNA:
{creative_ctx}

CREATE ADS FOR:
- Product: {product_name or 'the client product'}
- Description: {product_desc or 'a premium product'}
- Target Audience: {target_audience or 'general audience'}

IMPORTANT RULES:
1. Follow the EXACT same copy framework, tone, hook style, sentence structure
2. Use the SAME emotional triggers and cognitive biases
3. Match copy length, emoji usage, power words pattern
4. Do NOT copy - TRANSFORM the DNA into a new version
5. Each version = different angle but SAME DNA
6. Make it IMMEDIATELY usable - a beginner should be able to post this right now
7. Include an image brief so they know exactly what visual to create

Generate {num_versions} ad versions. Return a JSON array:
[
  {{
    "version": "V1",
    "angle": "the specific angle (emotional/logical/fear/aspiration/social-proof/offer)",
    "angle_explanation": "why this angle was chosen based on the DNA",

    "hook": "the first line that stops the scroll",
    "hook_type": "Pattern Interrupt | Curiosity | Pain Point | Offer | Social Proof",

    "primary_text": "the FULL ad copy - ready to paste into Facebook",
    "headline": "the headline",
    "description": "the link description",
    "cta": "Shop Now | Learn More | Sign Up | etc",

    "image_brief": {{
      "what_to_show": "exactly what should be in the image",
      "layout": "the layout to follow",
      "colors": ["specific colors to use"],
      "text_overlay": "what text to put on image (if any)",
      "mood": "the feeling the image should convey",
      "style": "photography | graphic | UGC | etc",
      "reference_description": "describe the final image in detail like briefing a designer"
    }},

    "psychology_used": {{
      "emotional_triggers": ["triggers used in this version"],
      "cognitive_bias": "main bias leveraged",
      "pain_point": "specific pain point hit",
      "desire": "specific desire triggered"
    }},

    "why_it_works": "explain why this version follows the DNA and should perform well",
    "dna_match_score": 1-10
  }}
]

STRICT: Do NOT be generic. Every ad must feel different but carry the same DNA fingerprint.
Return ONLY valid JSON array."""

        try:
            response = self.model.generate_content(prompt)
            return json.loads(_clean_json(response.text))
        except json.JSONDecodeError:
            return [{"error": "Parse error", "raw": response.text if response else ""}]
        except Exception as e:
            return [{"error": str(e)}]

    # ------------------------------------------------------------------
    # 5. CLONE SPECIFIC AD - Full breakdown + rewrite
    # ------------------------------------------------------------------

    def clone_specific_ad(self, original_ad: dict, image_analysis: dict,
                          product_name: str, product_desc: str) -> dict:

        prompt = f"""You are an elite Direct Response Creative Strategist. You are cloning ONE specific viral ad for a new product.

ORIGINAL AD:
- Primary Text: {original_ad.get('primary_text', '')}
- Headline: {original_ad.get('headline', '')}
- CTA: {original_ad.get('cta', '')}
- Angle: {original_ad.get('angle', '')}
- Funnel: {original_ad.get('funnel_stage', '')}

ORIGINAL CREATIVE ANALYSIS:
{json.dumps(image_analysis, ensure_ascii=False, indent=1)}

NEW PRODUCT:
- Name: {product_name or 'New Product'}
- Description: {product_desc or 'a product'}

First BREAK DOWN the original ad, then CLONE it. Return JSON:
{{
  "original_breakdown": {{
    "hook_type": "what type of hook the original uses",
    "psychology_triggers": ["triggers in original"],
    "copy_framework": "framework used",
    "why_original_works": "2-3 sentences on why this ad is effective"
  }},

  "cloned_ad": {{
    "hook": "new opening hook following same pattern",
    "primary_text": "full rewritten copy - ready to paste",
    "headline": "rewritten headline",
    "description": "rewritten link description",
    "cta": "same CTA type"
  }},

  "image_brief": {{
    "what_to_show": "exactly what should be in the image",
    "layout": "layout to follow",
    "colors": ["colors to use"],
    "text_overlay": "text to put on image",
    "mood": "mood to convey",
    "style": "photography | graphic | UGC",
    "full_brief": "complete description for a designer"
  }},

  "niche_transformation": {{
    "new_niche": "a completely different niche this could work in",
    "transformed_hook": "the hook adapted for that niche",
    "transformed_primary_text": "full ad copy for the new niche",
    "transformed_headline": "headline for new niche",
    "why_it_transfers": "why this DNA works across niches"
  }},

  "dna_preserved": ["list of DNA elements that were kept identical"],
  "what_was_changed": "explain what was adapted and why"
}}
Return ONLY valid JSON."""

        try:
            response = self.model.generate_content(prompt)
            return json.loads(_clean_json(response.text))
        except json.JSONDecodeError:
            return {"raw": response.text if response else ""}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # 6. NICHE TRANSFORMATION - Same DNA, different industry
    # ------------------------------------------------------------------

    def niche_transform(self, copy_dna: dict, original_niche: str,
                        target_niche: str, product_name: str,
                        product_desc: str) -> list:
        """Transform winning ad DNA from one niche to a completely different one."""

        prompt = f"""You are an elite Creative Strategist. Take the winning ad DNA from one niche and transform it into a different niche while keeping the EXACT same psychological patterns.

WINNING DNA FROM {original_niche.upper()}:
{json.dumps(copy_dna, ensure_ascii=False, indent=1)}

TRANSFORM INTO: {target_niche}
PRODUCT: {product_name or target_niche + ' product'} - {product_desc or ''}

Create 3 transformed ads. Return JSON array:
[
  {{
    "version": "V1",
    "original_niche": "{original_niche}",
    "target_niche": "{target_niche}",
    "hook": "the scroll-stopping first line",
    "primary_text": "full ad copy ready to use",
    "headline": "headline",
    "cta": "CTA button",
    "image_brief": "what the image should look like",
    "dna_elements_preserved": ["list what DNA was kept"],
    "what_was_adapted": "what changed for the new niche",
    "why_it_transfers": "why this pattern works across niches"
  }}
]
Return ONLY valid JSON array."""

        try:
            response = self.model.generate_content(prompt)
            return json.loads(_clean_json(response.text))
        except json.JSONDecodeError:
            return [{"raw": response.text if response else ""}]
        except Exception as e:
            return [{"error": str(e)}]
