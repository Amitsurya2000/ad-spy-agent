"use client";

import { useEffect, useState, FormEvent } from "react";
import Link from "next/link";
import { StatusBadge } from "./status-badge";

interface JobRow {
  id: string;
  query: string;
  country: string;
  status: "pending" | "running" | "completed" | "failed";
  error: string | null;
  created_at: string;
}

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
    <main className="page max-w-4xl">
      <h1 className="text-xl font-semibold sm:text-2xl">Ad Spy Agent</h1>
      <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
        Facebook Ad Library research + Gemini ad cloning.
      </p>

      <form
        onSubmit={handleSubmit}
        className="card mt-6 grid grid-cols-1 gap-3 p-4 sm:mt-8 min-[30rem]:grid-cols-3 lg:grid-cols-[1fr_6rem_5.5rem_6.5rem_auto] lg:items-end"
      >
        <div className="flex min-w-0 flex-col gap-1 min-[30rem]:col-span-3 lg:col-span-1">
          <label htmlFor="query" className="field-label">Brand / keyword</label>
          <input
            id="query"
            className="field-input"
            placeholder="e.g. Nike"
            autoComplete="off"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="flex min-w-0 flex-col gap-1">
          <label htmlFor="country" className="field-label">Country</label>
          <input
            id="country"
            className="field-input"
            autoCapitalize="characters"
            autoComplete="off"
            value={country}
            onChange={(e) => setCountry(e.target.value.toUpperCase())}
          />
        </div>
        <div className="flex min-w-0 flex-col gap-1">
          <label htmlFor="max-ads" className="field-label">Max ads</label>
          <input
            id="max-ads"
            type="number"
            inputMode="numeric"
            min={1}
            max={50}
            className="field-input"
            value={maxAds}
            onChange={(e) => setMaxAds(Number(e.target.value))}
          />
        </div>
        <div className="flex min-w-0 flex-col gap-1">
          <label htmlFor="scroll-rounds" className="field-label">Scroll rounds</label>
          <input
            id="scroll-rounds"
            type="number"
            inputMode="numeric"
            min={1}
            max={10}
            className="field-input"
            value={scrollRounds}
            onChange={(e) => setScrollRounds(Number(e.target.value))}
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="btn-primary min-[30rem]:col-span-3 lg:col-span-1"
        >
          {submitting ? "Starting..." : "Research"}
        </button>
      </form>
      {formError && <p role="alert" className="msg-error mt-2">{formError}</p>}
      <p className="mt-2 text-xs text-neutral-600 dark:text-neutral-400">
        Jobs are queued here and picked up by your worker (see RUN.md) - keep
        it running for these to complete.
      </p>

      <h2 className="mt-8 text-sm font-medium text-neutral-600 sm:mt-10 dark:text-neutral-400">History</h2>
      <div className="card mt-3 divide-y divide-neutral-200 dark:divide-neutral-800">
        {loading && <p className="p-4 text-sm text-neutral-600 dark:text-neutral-400">Loading...</p>}
        {!loading && jobs.length === 0 && (
          <p className="p-4 text-sm text-neutral-600 dark:text-neutral-400">No research jobs yet.</p>
        )}
        {jobs.map((job) => (
          <Link
            key={job.id}
            href={`/jobs/${job.id}`}
            className="flex min-h-14 items-start justify-between gap-3 p-4 text-sm hover:bg-neutral-50 dark:hover:bg-neutral-900"
          >
            <div className="min-w-0 flex-1">
              <div className="font-medium break-words">{job.query}</div>
              <div className="text-xs text-neutral-600 dark:text-neutral-400">
                {job.country} - {new Date(job.created_at).toLocaleString()}
              </div>
              {job.status === "failed" && job.error && (
                <div className="mt-1 text-xs break-words text-red-600 dark:text-red-400">{job.error}</div>
              )}
            </div>
            <StatusBadge status={job.status} />
          </Link>
        ))}
      </div>
    </main>
  );
}
