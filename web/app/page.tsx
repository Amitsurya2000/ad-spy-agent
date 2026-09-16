"use client";

import { useEffect, useState, FormEvent } from "react";
import Link from "next/link";

interface JobRow {
  id: string;
  query: string;
  country: string;
  status: "pending" | "running" | "completed" | "failed";
  error: string | null;
  created_at: string;
}

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  running: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export default function DashboardPage() {
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [country, setCountry] = useState("ALL");
  const [maxAds, setMaxAds] = useState(30);
  const [scrollRounds, setScrollRounds] = useState(5);

  async function loadJobs() {
    try {
      const res = await fetch("/api/research");
      if (res.ok) setJobs(await res.json());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 4000);
    return () => clearInterval(interval);
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!query.trim()) {
      setFormError("Enter a brand or keyword to research.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          country,
          max_ads: maxAds,
          scroll_rounds: scrollRounds,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setFormError(data.error || "Failed to start research.");
        return;
      }
      setQuery("");
      await loadJobs();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-2xl font-semibold">Ad Spy Agent</h1>
      <p className="mt-1 text-sm text-neutral-500">
        Facebook Ad Library research + Gemini ad cloning.
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-8 grid grid-cols-1 gap-3 rounded-lg border border-neutral-200 p-4 sm:grid-cols-[1fr_auto_auto_auto_auto] sm:items-end dark:border-neutral-800"
      >
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-neutral-500">Brand / keyword</label>
          <input
            className="rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            placeholder="e.g. Nike"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-neutral-500">Country</label>
          <input
            className="w-24 rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            value={country}
            onChange={(e) => setCountry(e.target.value.toUpperCase())}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-neutral-500">Max ads</label>
          <input
            type="number"
            min={1}
            max={50}
            className="w-20 rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            value={maxAds}
            onChange={(e) => setMaxAds(Number(e.target.value))}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-neutral-500">Scroll rounds</label>
          <input
            type="number"
            min={1}
            max={10}
            className="w-24 rounded border border-neutral-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            value={scrollRounds}
            onChange={(e) => setScrollRounds(Number(e.target.value))}
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="rounded bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
        >
          {submitting ? "Starting..." : "Research"}
        </button>
      </form>
      {formError && <p className="mt-2 text-sm text-red-600">{formError}</p>}
      <p className="mt-2 text-xs text-neutral-500">
        Jobs are queued here and picked up by your worker (see RUN.md) - keep
        it running for these to complete.
      </p>

      <h2 className="mt-10 text-sm font-medium text-neutral-500">History</h2>
      <div className="mt-3 divide-y divide-neutral-200 rounded-lg border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
        {loading && <p className="p-4 text-sm text-neutral-500">Loading...</p>}
        {!loading && jobs.length === 0 && (
          <p className="p-4 text-sm text-neutral-500">No research jobs yet.</p>
        )}
        {jobs.map((job) => (
          <Link
            key={job.id}
            href={`/jobs/${job.id}`}
            className="flex items-center justify-between gap-4 p-4 text-sm hover:bg-neutral-50 dark:hover:bg-neutral-900"
          >
            <div>
              <div className="font-medium">{job.query}</div>
              <div className="text-xs text-neutral-500">
                {job.country} - {new Date(job.created_at).toLocaleString()}
              </div>
              {job.status === "failed" && job.error && (
                <div className="mt-1 text-xs text-red-600">{job.error}</div>
              )}
            </div>
            <span
              className={`rounded-full px-2 py-1 text-xs font-medium ${STATUS_STYLES[job.status] ?? ""}`}
            >
              {job.status}
            </span>
          </Link>
        ))}
      </div>
    </main>
  );
}
