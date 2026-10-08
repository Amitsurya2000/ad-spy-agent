"use client";

import { useEffect, useState, FormEvent } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { Ad, Json, ResearchJob } from "@/lib/types";
import { StatusBadge } from "../../status-badge";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [ads, setAds] = useState<Ad[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Single self-terminating poll: keeps refetching every 3s while the job is
  // still pending/running, and stops on its own once it reaches a terminal
  // state - based on the freshly-fetched status, not stale React state.
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;

    async function load() {
      try {
        const res = await fetch(`/api/research/${id}`);
        if (stopped) return;
        if (res.status === 404) {
          setNotFound(true);
          setLoading(false);
          return;
        }
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        const data = await res.json();
        if (stopped) return;
        setJob(data.job);
        setAds(data.ads);
        setLoadError(null);
        setLoading(false);

        if (data.job.status === "pending" || data.job.status === "running") {
          timer = setTimeout(load, 3000);
        }
      } catch (e) {
        if (stopped) return;
        // Keep any already-loaded data on screen and retry, rather than
        // leaving the page stuck on "Loading..." forever.
        setLoadError(e instanceof Error ? e.message : "Couldn't load this job.");
        setLoading(false);
        timer = setTimeout(load, 5000);
      }
    }

    load();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [id]);

  if (loading) {
    return <main className="page max-w-5xl text-sm text-neutral-600 dark:text-neutral-400">Loading...</main>;
  }
  if (notFound || !job) {
    return (
      <main className="page max-w-5xl">
        <Link href="/" className="inline-flex min-h-11 items-center text-sm text-neutral-600 hover:underline dark:text-neutral-400">
          &larr; Back
        </Link>
        <p role="alert" className="msg-error mt-2">
          {notFound ? "Job not found." : (loadError ?? "Couldn't load this job.")}
        </p>
      </main>
    );
  }

  const dnaSummary =
    job.gemini_copy_dna?.dna_summary ?? job.copy_dna?.dna_summary ?? null;

  return (
    <main className="page max-w-5xl">
      <Link href="/" className="inline-flex min-h-11 items-center text-sm text-neutral-600 hover:underline dark:text-neutral-400">
        &larr; Back
      </Link>

      {loadError && (
        <p role="alert" className="msg-error mb-2">
          Connection problem - retrying... ({loadError})
        </p>
      )}

      <div className="mt-1 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold break-words sm:text-2xl">{job.query}</h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            {job.country} - {job.brand_info?.matched_brand ?? "..."} -{" "}
            {ads.length} ads scraped
          </p>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {(job.status === "pending" || job.status === "running") && (
        <p className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-200">
          {job.status === "pending"
            ? "Queued - waiting for the worker to pick this up."
            : "Scraping in progress - this page refreshes automatically."}
        </p>
      )}

      {job.status === "failed" && (
        <p className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm break-words text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          Failed: {job.error}
        </p>
      )}

      {job.status === "completed" && (
        <>
          <div className="mt-4 flex flex-wrap gap-3">
            <a
              className="btn-secondary"
              href={`/api/download/${job.id}?format=json`}
            >
              Download JSON
            </a>
            <a
              className="btn-secondary"
              href={`/api/download/${job.id}?format=csv`}
            >
              Download CSV
            </a>
          </div>

          {dnaSummary && (
            <div className="card mt-6 p-4 text-sm">
              <h2 className="font-medium">Copy DNA summary</h2>
              <p className="mt-1 break-words text-neutral-600 dark:text-neutral-400">{dnaSummary}</p>
            </div>
          )}

          <RewritePanel jobId={job.id} />
          <NicheTransformPanel jobId={job.id} />

          <h2 className="mt-8 text-sm font-medium text-neutral-600 sm:mt-10 dark:text-neutral-400">
            Ads ({ads.length})
          </h2>
          <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
    <div className="card flex flex-col p-4 text-sm">
      {ad.image_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={ad.image_url}
          alt={ad.headline || "Ad creative"}
          loading="lazy"
          className="mb-3 max-h-64 w-full rounded bg-neutral-100 object-cover dark:bg-neutral-800"
        />
      )}
      <div className="flex flex-wrap gap-1 text-xs text-neutral-600 dark:text-neutral-400">
        {ad.platform && <span className="chip">{ad.platform}</span>}
        {ad.angle && <span className="chip">{ad.angle}</span>}
        {ad.funnel_stage && <span className="chip">{ad.funnel_stage}</span>}
      </div>
      {ad.headline && <p className="mt-2 font-medium break-words">{ad.headline}</p>}
      {ad.primary_text && (
        <p className="mt-1 whitespace-pre-line break-words text-neutral-600 dark:text-neutral-400">
          {ad.primary_text.length > 240 ? ad.primary_text.slice(0, 240) + "..." : ad.primary_text}
        </p>
      )}
      {ad.cta && <p className="mt-2 text-xs break-words text-neutral-600 dark:text-neutral-400">CTA: {ad.cta}</p>}

      <button
        type="button"
        onClick={() => setCloning((v) => !v)}
        aria-expanded={cloning}
        className="btn-secondary mt-3 self-start"
      >
        {cloning ? "Cancel" : "Clone this ad"}
      </button>

      {cloning && (
        <form onSubmit={handleClone} className="mt-3 flex flex-col gap-2">
          <input
            className="field-input"
            aria-label="Your product name"
            placeholder="Your product name"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
          />
          <input
            className="field-input"
            aria-label="Your product description"
            placeholder="Your product description"
            value={productDesc}
            onChange={(e) => setProductDesc(e.target.value)}
          />
          <button
            type="submit"
            disabled={loading}
            className="btn-primary self-start"
          >
            {loading ? "Cloning..." : "Generate clone"}
          </button>
        </form>
      )}

      {error && <p role="alert" className="msg-error mt-2">{error}</p>}

      {result?.cloned_ad && (
        <div className="mt-3 rounded border border-neutral-200 bg-neutral-50 p-3 text-xs break-words dark:border-neutral-800 dark:bg-neutral-900">
          <p className="font-medium">{result.cloned_ad.headline}</p>
          <p className="mt-1 whitespace-pre-line text-neutral-600 dark:text-neutral-400">
            {result.cloned_ad.primary_text}
          </p>
          <p className="mt-1 text-neutral-600 dark:text-neutral-400">CTA: {result.cloned_ad.cta}</p>
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
    <div className="card mt-6 p-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="min-h-11 w-full text-left text-sm font-medium pointer-fine:min-h-0"
      >
        {open ? "−" : "+"} Generate rewrites for my product
      </button>
      {open && (
        <>
          <form onSubmit={handleSubmit} className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
            <input
              className="field-input"
              aria-label="Product name"
              placeholder="Product name"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
            />
            <input
              className="field-input"
              aria-label="Product description"
              placeholder="Product description"
              value={productDesc}
              onChange={(e) => setProductDesc(e.target.value)}
            />
            <input
              className="field-input"
              aria-label="Target audience"
              placeholder="Target audience"
              value={targetAudience}
              onChange={(e) => setTargetAudience(e.target.value)}
            />
            <button
              type="submit"
              disabled={loading}
              className="btn-primary col-span-full self-start"
            >
              {loading ? "Generating..." : "Generate 6 rewrites"}
            </button>
          </form>
          {error && <p role="alert" className="msg-error mt-2">{error}</p>}
          {rewrites && (
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              {rewrites.map((r, i) => (
                <div key={i} className="min-w-0 rounded border border-neutral-200 p-3 text-xs break-words dark:border-neutral-800">
                  <p className="font-medium">{r.version} - {r.angle}</p>
                  <p className="mt-1 font-medium">{r.headline}</p>
                  <p className="mt-1 whitespace-pre-line text-neutral-600 dark:text-neutral-400">{r.primary_text}</p>
                  <p className="mt-1 text-neutral-600 dark:text-neutral-400">CTA: {r.cta}</p>
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
    <div className="card mt-4 p-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="min-h-11 w-full text-left text-sm font-medium pointer-fine:min-h-0"
      >
        {open ? "−" : "+"} Transform this DNA into a different niche
      </button>
      {open && (
        <>
          <form onSubmit={handleSubmit} className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
            <input
              className="field-input"
              aria-label="Target niche (e.g. Real Estate)"
              placeholder="Target niche (e.g. Real Estate)"
              value={targetNiche}
              onChange={(e) => setTargetNiche(e.target.value)}
            />
            <input
              className="field-input"
              aria-label="Product name"
              placeholder="Product name"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
            />
            <input
              className="field-input"
              aria-label="Product description"
              placeholder="Product description"
              value={productDesc}
              onChange={(e) => setProductDesc(e.target.value)}
            />
            <button
              type="submit"
              disabled={loading}
              className="btn-primary col-span-full self-start"
            >
              {loading ? "Transforming..." : "Generate 3 transforms"}
            </button>
          </form>
          {error && <p role="alert" className="msg-error mt-2">{error}</p>}
          {transforms && (
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              {transforms.map((t, i) => (
                <div key={i} className="min-w-0 rounded border border-neutral-200 p-3 text-xs break-words dark:border-neutral-800">
                  <p className="font-medium">{t.headline}</p>
                  <p className="mt-1 whitespace-pre-line text-neutral-600 dark:text-neutral-400">{t.primary_text}</p>
                  <p className="mt-1 text-neutral-600 dark:text-neutral-400">CTA: {t.cta}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
