"use client";

import { useEffect, useState, FormEvent } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { Ad, Json, ResearchJob } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  running: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [ads, setAds] = useState<Ad[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // Single self-terminating poll: keeps refetching every 3s while the job is
  // still pending/running, and stops on its own once it reaches a terminal
  // state - based on the freshly-fetched status, not stale React state.
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;

    async function load() {
      const res = await fetch(`/api/research/${id}`);
      if (stopped) return;
      if (res.status === 404) {
        setNotFound(true);
        setLoading(false);
        return;
      }
      const data = await res.json();
      setJob(data.job);
      setAds(data.ads);
      setLoading(false);

      if (data.job.status === "pending" || data.job.status === "running") {
        timer = setTimeout(load, 3000);
      }
    }

    load();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [id]);

  if (loading) {
    return <main className="mx-auto max-w-5xl px-4 py-10 text-sm text-neutral-500">Loading...</main>;
  }
  if (notFound || !job) {
    return <main className="mx-auto max-w-5xl px-4 py-10 text-sm text-red-600">Job not found.</main>;
  }

  const dnaSummary =
    job.gemini_copy_dna?.dna_summary ?? job.copy_dna?.dna_summary ?? null;

  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <Link href="/" className="text-sm text-neutral-500 hover:underline">
        &larr; Back
      </Link>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{job.query}</h1>
          <p className="text-sm text-neutral-500">
            {job.country} - {job.brand_info?.matched_brand ?? "..."} -{" "}
            {ads.length} ads scraped
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_STYLES[job.status]}`}>
          {job.status}
        </span>
      </div>

      {(job.status === "pending" || job.status === "running") && (
        <p className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-200">
          {job.status === "pending"
            ? "Queued - waiting for the worker to pick this up."
            : "Scraping in progress - this page refreshes automatically."}
        </p>
      )}

      {job.status === "failed" && (
        <p className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          Failed: {job.error}
        </p>
      )}

      {job.status === "completed" && (
        <>
          <div className="mt-4 flex gap-3 text-sm">
            <a
              className="rounded border border-neutral-300 px-3 py-1.5 hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-900"
              href={`/api/download/${job.id}?format=json`}
            >
              Download JSON
            </a>
            <a
              className="rounded border border-neutral-300 px-3 py-1.5 hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-900"
              href={`/api/download/${job.id}?format=csv`}
            >
              Download CSV
            </a>
          </div>

          {dnaSummary && (
            <div className="mt-6 rounded-lg border border-neutral-200 p-4 text-sm dark:border-neutral-800">
              <h2 className="font-medium">Copy DNA summary</h2>
              <p className="mt-1 text-neutral-600 dark:text-neutral-400">{dnaSummary}</p>
            </div>
          )}

          <RewritePanel jobId={job.id} />
          <NicheTransformPanel jobId={job.id} />

          <h2 className="mt-10 text-sm font-medium text-neutral-500">
            Ads ({ads.length})
          </h2>
          <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {ads.map((ad) => (
              <AdCard key={ad.id} ad={ad} />
            ))}
          </div>
        </>
      )}
    </main>
  );
}

function AdCard({ ad }: { ad: Ad }) {
  const [cloning, setCloning] = useState(false);
  const [productName, setProductName] = useState("");
  const [productDesc, setProductDesc] = useState("");
  const [result, setResult] = useState<Json | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClone(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/clone", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ad_id: ad.id, product_name: productName, product_desc: productDesc }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Clone failed.");
        return;
      }
      setResult(data.clone);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-neutral-200 p-4 text-sm dark:border-neutral-800">
      {ad.image_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={ad.image_url}
          alt={ad.headline || "Ad creative"}
          className="mb-3 max-h-64 w-full rounded object-cover"
        />
      )}
      <div className="flex flex-wrap gap-1 text-xs text-neutral-500">
        {ad.platform && <span className="rounded bg-neutral-100 px-2 py-0.5 dark:bg-neutral-800">{ad.platform}</span>}
        {ad.angle && <span className="rounded bg-neutral-100 px-2 py-0.5 dark:bg-neutral-800">{ad.angle}</span>}
        {ad.funnel_stage && <span className="rounded bg-neutral-100 px-2 py-0.5 dark:bg-neutral-800">{ad.funnel_stage}</span>}
      </div>
      {ad.headline && <p className="mt-2 font-medium">{ad.headline}</p>}
      {ad.primary_text && (
        <p className="mt-1 whitespace-pre-line text-neutral-600 dark:text-neutral-400">
          {ad.primary_text.length > 240 ? ad.primary_text.slice(0, 240) + "..." : ad.primary_text}
        </p>
      )}
      {ad.cta && <p className="mt-2 text-xs text-neutral-500">CTA: {ad.cta}</p>}

      <button
        onClick={() => setCloning((v) => !v)}
        className="mt-3 rounded border border-neutral-300 px-3 py-1.5 text-xs hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-900"
      >
        {cloning ? "Cancel" : "Clone this ad"}
      </button>

      {cloning && (
        <form onSubmit={handleClone} className="mt-3 flex flex-col gap-2">
          <input
            className="rounded border border-neutral-300 px-2 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-900"
            placeholder="Your product name"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
          />
          <input
            className="rounded border border-neutral-300 px-2 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-900"
            placeholder="Your product description"
            value={productDesc}
            onChange={(e) => setProductDesc(e.target.value)}
          />
          <button
            type="submit"
            disabled={loading}
            className="self-start rounded bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
          >
            {loading ? "Cloning..." : "Generate clone"}
          </button>
        </form>
      )}

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

      {result?.cloned_ad && (
        <div className="mt-3 rounded border border-neutral-200 bg-neutral-50 p-3 text-xs dark:border-neutral-800 dark:bg-neutral-900">
          <p className="font-medium">{result.cloned_ad.headline}</p>
          <p className="mt-1 whitespace-pre-line text-neutral-600 dark:text-neutral-400">
            {result.cloned_ad.primary_text}
          </p>
          <p className="mt-1 text-neutral-500">CTA: {result.cloned_ad.cta}</p>
        </div>
      )}
    </div>
  );
}

function RewritePanel({ jobId }: { jobId: string }) {
  const [open, setOpen] = useState(false);
  const [productName, setProductName] = useState("");
  const [productDesc, setProductDesc] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [rewrites, setRewrites] = useState<Json[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/rewrite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: jobId,
          product_name: productName,
          product_desc: productDesc,
          target_audience: targetAudience,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Rewrite failed.");
        return;
      }
      setRewrites(data.rewrites);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-6 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-sm font-medium"
      >
        {open ? "−" : "+"} Generate rewrites for my product
      </button>
      {open && (
        <>
          <form onSubmit={handleSubmit} className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-3">
            <input
              className="rounded border border-neutral-300 px-2 py-1.5 dark:border-neutral-700 dark:bg-neutral-900"
              placeholder="Product name"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
            />
            <input
              className="rounded border border-neutral-300 px-2 py-1.5 dark:border-neutral-700 dark:bg-neutral-900"
              placeholder="Product description"
              value={productDesc}
              onChange={(e) => setProductDesc(e.target.value)}
            />
            <input
              className="rounded border border-neutral-300 px-2 py-1.5 dark:border-neutral-700 dark:bg-neutral-900"
              placeholder="Target audience"
              value={targetAudience}
              onChange={(e) => setTargetAudience(e.target.value)}
            />
            <button
              type="submit"
              disabled={loading}
              className="col-span-full self-start rounded bg-neutral-900 px-4 py-1.5 text-xs font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
            >
              {loading ? "Generating..." : "Generate 6 rewrites"}
            </button>
          </form>
          {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
          {rewrites && (
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {rewrites.map((r, i) => (
                <div key={i} className="rounded border border-neutral-200 p-3 text-xs dark:border-neutral-800">
                  <p className="font-medium">{r.version} - {r.angle}</p>
                  <p className="mt-1 font-medium">{r.headline}</p>
                  <p className="mt-1 whitespace-pre-line text-neutral-600 dark:text-neutral-400">{r.primary_text}</p>
                  <p className="mt-1 text-neutral-500">CTA: {r.cta}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function NicheTransformPanel({ jobId }: { jobId: string }) {
  const [open, setOpen] = useState(false);
  const [targetNiche, setTargetNiche] = useState("");
  const [productName, setProductName] = useState("");
  const [productDesc, setProductDesc] = useState("");
  const [transforms, setTransforms] = useState<Json[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/niche-transform", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: jobId,
          target_niche: targetNiche,
          product_name: productName,
          product_desc: productDesc,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Niche transform failed.");
        return;
      }
      setTransforms(data.transforms);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-4 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
      <button onClick={() => setOpen((v) => !v)} className="text-sm font-medium">
        {open ? "−" : "+"} Transform this DNA into a different niche
      </button>
      {open && (
        <>
          <form onSubmit={handleSubmit} className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-3">
            <input
              className="rounded border border-neutral-300 px-2 py-1.5 dark:border-neutral-700 dark:bg-neutral-900"
              placeholder="Target niche (e.g. Real Estate)"
              value={targetNiche}
              onChange={(e) => setTargetNiche(e.target.value)}
            />
            <input
              className="rounded border border-neutral-300 px-2 py-1.5 dark:border-neutral-700 dark:bg-neutral-900"
              placeholder="Product name"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
            />
            <input
              className="rounded border border-neutral-300 px-2 py-1.5 dark:border-neutral-700 dark:bg-neutral-900"
              placeholder="Product description"
              value={productDesc}
              onChange={(e) => setProductDesc(e.target.value)}
            />
            <button
              type="submit"
              disabled={loading}
              className="col-span-full self-start rounded bg-neutral-900 px-4 py-1.5 text-xs font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
            >
              {loading ? "Transforming..." : "Generate 3 transforms"}
            </button>
          </form>
          {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
          {transforms && (
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {transforms.map((t, i) => (
                <div key={i} className="rounded border border-neutral-200 p-3 text-xs dark:border-neutral-800">
                  <p className="font-medium">{t.headline}</p>
                  <p className="mt-1 whitespace-pre-line text-neutral-600 dark:text-neutral-400">{t.primary_text}</p>
                  <p className="mt-1 text-neutral-500">CTA: {t.cta}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
