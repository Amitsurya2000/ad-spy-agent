export type JobStatus = "pending" | "running" | "completed" | "failed";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Json = Record<string, any>;

export interface ResearchJob {
  id: string;
  query: string;
  country: string;
  max_ads: number;
  scroll_rounds: number;
  use_gemini: boolean;
  status: JobStatus;
  brand_info: Json;
  copy_dna: Json;
  creative_dna: Json;
  gemini_copy_dna: Json;
  gemini_creative_dna: Json;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface Ad {
  id: string;
  job_id: string;
  ad_id: string;
  platform: string;
  status: string;
  start_date: string;
  primary_text: string;
  headline: string;
  cta: string;
  media_type: string;
  angle: string;
  funnel_stage: string;
  copy_breakdown: Json;
  full_breakdown: Json;
  image_path: string;
  image_url: string;
  created_at: string;
}
