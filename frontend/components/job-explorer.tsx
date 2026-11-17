"use client";

import { useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import { ArrowDownWideNarrow, ArrowLeft, ArrowRight, BriefcaseBusiness, Check, CircleHelp, FileText, Filter, LoaderCircle, MapPin, Search, Sparkles, SlidersHorizontal, UploadCloud, Wifi } from "lucide-react";
import { motion } from "framer-motion";
import { useApp } from "@/components/app-provider";
import { JobDetailSheet } from "@/components/job-detail-sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { apiFetch, type Job, type JobPage, type LiveSearchFilters, type MarketOverview, type Taxonomy } from "@/lib/api";
import { formatCompactCurrency, formatSalary, timeAgo } from "@/lib/utils";

const CATEGORIES = ["Software Engineering", "Data Science", "AI/ML", "DevOps", "Product"];
const LEVELS = ["entry", "mid", "senior", "lead"] as const;
const QUICK_SKILLS = ["Python", "TypeScript", "React", "SQL", "AWS", "PostgreSQL", "Docker", "Machine Learning"];
const REGIONS = ["India", "APAC", "Europe", "North America", "Middle East", "Global/Remote"];
const FALLBACK_BRANCHES = ["Computer Science & IT", "Mechanical Engineering", "Civil & Structural Engineering", "Electrical & Electronics", "Chemical & Process", "Aerospace & Automotive", "Industrial & Manufacturing"];
const PAGE_SIZE = 12;
const CATEGORY_TONES: Record<string, string> = {
  "AI/ML": "border-violet-400/25 bg-violet-400/10 text-violet-200",
  "Data Science": "border-cyan-400/25 bg-cyan-400/10 text-cyan-200",
  "Software Engineering": "border-blue-400/25 bg-blue-400/10 text-blue-200",
  DevOps: "border-amber-400/25 bg-amber-400/10 text-amber-200",
  Product: "border-rose-400/25 bg-rose-400/10 text-rose-200",
};
const MODE_TONES: Record<string, string> = {
  remote: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
  hybrid: "border-sky-400/25 bg-sky-400/10 text-sky-200",
  onsite: "border-amber-400/25 bg-amber-400/10 text-amber-200",
};
const REGION_TONES: Record<string, string> = {
  India: "border-rose-300/20 bg-rose-300/[0.07] text-rose-200",
  APAC: "border-cyan-300/20 bg-cyan-300/[0.07] text-cyan-200",
  Europe: "border-violet-300/20 bg-violet-300/[0.07] text-violet-200",
  "North America": "border-blue-300/20 bg-blue-300/[0.07] text-blue-200",
  "Middle East": "border-amber-300/20 bg-amber-300/[0.07] text-amber-200",
  "Global/Remote": "border-emerald-300/20 bg-emerald-300/[0.07] text-emerald-200",
};
const SOURCE_LABELS: Record<string, string> = { Greenhouse: "Greenhouse ATS", Lever: "Lever ATS" };
const AVATAR_GRADIENTS = [
  "linear-gradient(135deg,#6366f1,#a855f7)",
  "linear-gradient(135deg,#0ea5e9,#14b8a6)",
  "linear-gradient(135deg,#f97316,#ec4899)",
  "linear-gradient(135deg,#2563eb,#06b6d4)",
  "linear-gradient(135deg,#8b5cf6,#ec4899)",
];

function companyGradient(name: string) {
  const hash = [...name].reduce((value, character) => (value * 31 + character.charCodeAt(0)) >>> 0, 7);
  return AVATAR_GRADIENTS[hash % AVATAR_GRADIENTS.length];
}

function ScoreGauge({ score, id }: { score: number; id: number }) {
  const colors = score >= 80 ? ["#10B981", "#06B6D4"] : score >= 60 ? ["#3B82F6", "#6366F1"] : ["#F59E0B", "#F43F5E"];
  const gradientId = `match-score-${id}`;
  const circumference = 2 * Math.PI * 17;
  const offset = circumference * (1 - Math.max(0, Math.min(score, 100)) / 100);
  return (
    <div className="relative size-12 shrink-0" role="img" aria-label={`${Math.round(score)} percent match`}>
      <svg viewBox="0 0 40 40" className="size-full -rotate-90 overflow-visible">
        <defs><linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1"><stop stopColor={colors[0]} /><stop offset="1" stopColor={colors[1]} /></linearGradient></defs>
        <circle cx="20" cy="20" r="17" fill="none" stroke="rgba(148,163,184,.2)" strokeWidth="3" />
        <motion.circle cx="20" cy="20" r="17" fill="none" stroke={`url(#${gradientId})`} strokeWidth="3" strokeLinecap="round" strokeDasharray={circumference} initial={{ strokeDashoffset: circumference }} animate={{ strokeDashoffset: offset }} transition={{ type: "spring", stiffness: 80, damping: 18 }} />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-mono text-[10px] font-semibold text-zinc-100">{Math.round(score)}</span>
    </div>
  );
}

function JobCard({ job, onClick, profileActive }: { job: Job; onClick: () => void; profileActive: boolean }) {
  return (
    <motion.button layout initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", stiffness: 220, damping: 24 }} onClick={onClick} className="group w-full rounded-2xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300/70">
      <Card className="relative overflow-hidden p-5 transition duration-300 hover:-translate-y-0.5 hover:border-white/[0.16] hover:bg-zinc-900/90 sm:p-6">
        <div className="absolute inset-y-0 left-0 w-px bg-gradient-to-b from-emerald-300/0 via-emerald-300/40 to-indigo-300/0 opacity-0 transition group-hover:opacity-100" />
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge className={`uppercase tracking-[0.08em] ${CATEGORY_TONES[job.category] ?? ""}`}>{job.category}</Badge>
              <Badge className={REGION_TONES[job.region ?? ""] ?? "border-white/10 bg-white/[0.04] text-zinc-300"}>{job.region || "Global/Remote"} · {job.country && job.country !== "Unknown" ? job.location.split(",")[0] : "Remote"}</Badge>
              <Badge tone="indigo" className="max-w-full truncate">{job.engineering_branch || "Engineering"}{job.domain ? ` · ${job.domain}` : ""}</Badge>
              <Badge className="border-white/[0.08] bg-zinc-950/40 text-zinc-500">{SOURCE_LABELS[job.source] ?? job.source}</Badge>
              <span className="text-[10px] text-zinc-600">{timeAgo(job.posted_at)}</span>
            </div>
            <h2 className="text-base font-semibold tracking-[-0.025em] text-zinc-100 transition group-hover:text-white sm:text-lg">{job.title}</h2>
            <div className="mt-1 flex items-center gap-2.5">
              <span style={{ backgroundImage: companyGradient(job.company) }} className="company-avatar flex size-8 items-center justify-center rounded-xl border border-white/25 text-[10px] font-bold uppercase tracking-wide text-white shadow-[0_5px_15px_-7px_rgba(79,70,229,.7)]">{job.company.split(/\s+/).slice(0, 2).map((part) => part[0]).join("")}</span>
              <p className="text-sm text-zinc-400">{job.company}</p>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-zinc-600">
              <span className="inline-flex items-center gap-1.5"><MapPin className="size-3.5" />{job.location}{job.country && job.country !== "Unknown" ? `, ${job.country}` : ""}</span>
              <Badge className={`gap-1 capitalize ${MODE_TONES[job.work_mode] ?? ""}`}><Wifi className="size-3" />{job.work_mode === "onsite" ? "On-site" : job.work_mode}</Badge>
              <span className="capitalize">{job.experience_level}</span>
            </div>
          </div>
          <div className="flex shrink-0 items-center justify-between gap-4 sm:flex-col sm:items-end">
            {job.match ? <ScoreGauge id={job.id} score={job.match.total_score} /> : profileActive ? <Badge tone="default">Scoring…</Badge> : <Badge className="gap-1"><CircleHelp className="size-3" />Add CV to score</Badge>}
            <div className="text-left sm:text-right">
              <p className="font-mono text-sm font-semibold text-zinc-100">{formatSalary(job.salary_min_usd)} – {formatSalary(job.salary_max_usd)}</p>
              <p className="mt-1 text-[10px] text-zinc-600">USD / year{job.salary_is_estimated ? " · estimated" : ""}</p>
            </div>
          </div>
        </div>
        <p className="mt-4 line-clamp-2 max-w-4xl text-xs leading-6 text-zinc-500">{job.description}</p>
        <div className="mt-4 flex flex-wrap gap-1.5">
          {(job.match?.matched_skills ?? job.skills).slice(0, 4).map((skill) => (
            <Badge key={skill} tone={job.match?.matched_skills.includes(skill) ? "emerald" : "default"}>{skill}</Badge>
          ))}
          {job.match?.missing_skills.slice(0, 2).map((skill) => <Badge key={`missing-${skill}`} tone="amber">{skill}</Badge>)}
          {job.skills.length > 4 && <span className="px-1 py-1 text-[10px] text-zinc-600">+{job.skills.length - 4}</span>}
        </div>
      </Card>
    </motion.button>
  );
}

function FilterSidebar({
  category, setCategory, workMode, setWorkMode, levels, setLevels, minSalary, setMinSalary,
  skills, setSkills, region, setRegion, branch, setBranch, domain, setDomain, taxonomy, setPage,
}: {
  category: string; setCategory: (value: string) => void;
  workMode: string; setWorkMode: (value: string) => void;
  levels: string[]; setLevels: (value: string[]) => void;
  minSalary: number; setMinSalary: (value: number) => void;
  skills: string[]; setSkills: (value: string[]) => void;
  region: string; setRegion: (value: string) => void;
  branch: string; setBranch: (value: string) => void;
  domain: string; setDomain: (value: string) => void;
  taxonomy: Taxonomy | null;
  setPage: (value: number) => void;
}) {
  const branches = taxonomy?.branches ?? {};
  const branchOptions = Object.keys(branches);
  const regionOptions = taxonomy?.regions.length ? taxonomy.regions : REGIONS;
  function toggle(list: string[], value: string, setter: (value: string[]) => void) {
    setter(list.includes(value) ? list.filter((item) => item !== value) : [...list, value]);
  }

  return (
    <aside className="space-y-6 rounded-2xl border border-white/[0.075] bg-zinc-900/60 p-5 lg:sticky lg:top-[92px]">
      <div className="flex items-center justify-between"><h2 className="text-sm font-semibold text-zinc-100">Refine roles</h2><Filter className="size-4 text-zinc-600" /></div>
      <div>
        <label className="mb-2 block text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">Category</label>
        <div className="flex flex-wrap gap-1.5">
          {["All", ...CATEGORIES].map((item) => {
            const value = item === "All" ? "" : item;
            const active = category === value;
            const tone = CATEGORY_TONES[value] ?? "border-indigo-400/25 bg-indigo-400/10 text-indigo-200";
            return <button key={item} type="button" aria-pressed={active} onClick={() => setCategory(value)} className={`rounded-lg border px-2.5 py-2 text-[10px] transition ${active ? tone : "border-white/[0.07] bg-white/[0.02] text-zinc-500 hover:text-zinc-200"}`}>{item}</button>;
          })}
        </div>
      </div>
      <div className="space-y-4">
        <label className="block">
          <span className="mb-2 block text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">Region</span>
          <select value={region} onChange={(event) => { setRegion(event.target.value); setPage(1); }} className="h-10 w-full rounded-xl border border-white/[0.07] bg-zinc-950/75 px-3 text-xs text-zinc-300 outline-none transition focus:border-indigo-300/30 focus:ring-1 focus:ring-indigo-300/15">
            <option value="">All Regions</option>{regionOptions.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="mb-2 block text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">Engineering branch</span>
          <select value={branch} onChange={(event) => { setBranch(event.target.value); setDomain(""); setPage(1); }} className="h-10 w-full rounded-xl border border-white/[0.07] bg-zinc-950/75 px-3 text-xs text-zinc-300 outline-none transition focus:border-indigo-300/30 focus:ring-1 focus:ring-indigo-300/15">
            <option value="">All Branches</option>{(branchOptions.length ? branchOptions : FALLBACK_BRANCHES).map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        {branch && <label className="block">
          <span className="mb-2 block text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">Domain</span>
          <select value={domain} onChange={(event) => { setDomain(event.target.value); setPage(1); }} className="h-10 w-full rounded-xl border border-white/[0.07] bg-zinc-950/75 px-3 text-xs text-zinc-300 outline-none transition focus:border-cyan-300/30 focus:ring-1 focus:ring-cyan-300/15">
            <option value="">All domains</option>{(branches[branch] ?? []).map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>}
      </div>
      <div>
        <label className="mb-2 block text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">Work mode</label>
        <div className="grid grid-cols-4 gap-1 rounded-xl border border-white/[0.06] bg-zinc-950 p-1">
          {[{ label: "All", value: "" }, { label: "Remote", value: "remote" }, { label: "Hybrid", value: "hybrid" }, { label: "On-site", value: "onsite" }].map(({ label, value }) => <button key={label} aria-pressed={workMode === value} onClick={() => setWorkMode(value)} className={`rounded-lg px-1 py-2 text-[9px] transition ${workMode === value ? "bg-emerald-300/10 text-emerald-200" : "text-zinc-600 hover:text-zinc-300"}`}>{label}</button>)}
        </div>
      </div>
      <div>
        <label className="mb-3 block text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">Experience level</label>
        <div className="space-y-2.5">
          {LEVELS.map((level) => <label key={level} className="group flex cursor-pointer items-center justify-between text-xs capitalize text-zinc-500 hover:text-zinc-200">
            <span>{level === "mid" ? "Mid-level" : level}</span>
            <span className={`flex size-4 items-center justify-center rounded border transition ${levels.includes(level) ? "border-emerald-300 bg-emerald-300 text-zinc-950" : "border-white/15 bg-zinc-950 group-hover:border-white/30"}`}>
              {levels.includes(level) && <Check className="size-3" />}
              <input type="checkbox" checked={levels.includes(level)} onChange={() => toggle(levels, level, setLevels)} className="sr-only" />
            </span>
          </label>)}
        </div>
      </div>
      <div>
        <div className="mb-3 flex items-center justify-between"><label htmlFor="salary-range" className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">Minimum salary</label><span className="text-xs font-medium text-zinc-300">{minSalary === 0 ? "Any" : `$${Math.round(minSalary / 1000)}k+`}</span></div>
        <input id="salary-range" type="range" min="0" max="250000" step="10000" value={minSalary} onChange={(event) => setMinSalary(Number(event.target.value))} className="h-1.5 w-full cursor-pointer accent-emerald-300" />
        <div className="mt-1 flex justify-between text-[9px] text-zinc-700"><span>$0</span><span>$250k+</span></div>
      </div>
      <div>
        <div className="mb-2 flex items-center justify-between"><label className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">Skill tags</label>{skills.length > 0 && <button onClick={() => setSkills([])} className="text-[10px] text-zinc-600 hover:text-zinc-300">Clear</button>}</div>
        <div className="flex flex-wrap gap-1.5">
          {QUICK_SKILLS.map((skill) => <button key={skill} onClick={() => toggle(skills, skill, setSkills)} className={`rounded-lg border px-2.5 py-1.5 text-[10px] transition ${skills.includes(skill) ? "border-indigo-300/30 bg-indigo-300/[0.1] text-indigo-200" : "border-white/[0.07] bg-white/[0.02] text-zinc-600 hover:border-white/15 hover:text-zinc-300"}`}>{skill}</button>)}
        </div>
      </div>
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 text-[10px] leading-relaxed text-zinc-600">Filters update the indexed role feed as you refine your search.</div>
    </aside>
  );
}

export function JobExplorer() {
  const { profile, setUploadOpen, uploadCv, notify, lastRun } = useApp();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [region, setRegion] = useState("");
  const [branch, setBranch] = useState("");
  const [domain, setDomain] = useState("");
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [workMode, setWorkMode] = useState("");
  const [levels, setLevels] = useState<string[]>([]);
  const [minSalary, setMinSalary] = useState(0);
  const [skills, setSkills] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<"recent" | "salary" | "match">("match");
  const [data, setData] = useState<JobPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Job | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [draggingCv, setDraggingCv] = useState(false);
  const [uploadingCv, setUploadingCv] = useState(false);
  const [fetchingLive, setFetchingLive] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    apiFetch<Taxonomy>("/taxonomy").then(setTaxonomy).catch(() => undefined);
  }, []);

  useEffect(() => {
    apiFetch<MarketOverview>("/analytics/overview").then(setOverview).catch(() => undefined);
  }, [lastRun?.id]);

  useEffect(() => {
    const onShortcut = (event: KeyboardEvent) => {
      if (event.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes((event.target as HTMLElement | null)?.tagName ?? "")) {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, []);

  async function onCvDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDraggingCv(false);
    const file = event.dataTransfer.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf") || (file.type && file.type !== "application/pdf")) {
      notify({ title: "PDF files only", message: "Choose an exported PDF resume or CV.", tone: "error" });
      return;
    }
    if (file.size > 12 * 1024 * 1024) {
      notify({ title: "File is too large", message: "Choose a PDF under 12 MB.", tone: "error" });
      return;
    }
    setUploadingCv(true);
    try { await uploadCv(file); }
    catch (cause) { notify({ title: "Upload failed", message: cause instanceof Error ? cause.message : "Try again in a moment.", tone: "error" }); }
    finally { setUploadingCv(false); }
  }

  const activeFilters = useMemo(() => Boolean(search || category || region || branch || domain || workMode || levels.length || minSalary || skills.length), [search, category, region, branch, domain, workMode, levels.length, minSalary, skills.length]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setLoading(true);
      setError("");
      const params = new URLSearchParams({ page: String(page), limit: String(PAGE_SIZE), sort_by: profile ? sortBy : sortBy === "match" ? "recent" : sortBy });
      if (search.trim()) params.set("q", search.trim());
      if (category) params.set("category", category);
      if (region) params.set("region", region);
      if (branch) params.set("engineering_branch", branch);
      if (domain) params.set("domain", domain);
      if (workMode) params.set("work_mode", workMode);
      if (minSalary) params.set("min_salary", String(minSalary));
      if (profile) params.set("profile_id", String(profile.id));
      levels.forEach((level) => params.append("experience_level", level));
      skills.forEach((skill) => params.append("skills", skill));
      apiFetch<JobPage>(`/jobs?${params.toString()}`)
        .then(setData)
        .catch((cause: unknown) => {
          setError(cause instanceof Error ? cause.message : "The job feed could not be loaded.");
          setData(null);
        })
        .finally(() => setLoading(false));
    }, search ? 250 : 0);
    return () => window.clearTimeout(timeout);
  }, [search, category, region, branch, domain, workMode, levels, minSalary, skills, profile?.id, sortBy, page, reloadKey, lastRun?.id]);

  async function fetchLiveJobs() {
    if (fetchingLive) return;
    setFetchingLive(true);
    try {
      const filters: LiveSearchFilters = {
        ...(search.trim() ? { q: search.trim() } : {}),
        ...(region ? { region } : {}),
        ...(branch ? { engineering_branch: branch } : {}),
        ...(domain ? { domain } : {}),
      };
      const response = await apiFetch<JobPage>("/jobs/live-search", { method: "POST", body: JSON.stringify(filters) });
      notify({
        title: response.total ? "Live roles added" : "Live search complete",
        message: response.total ? `${response.total} new verified role${response.total === 1 ? "" : "s"} added to the index.` : "No new matching roles were found across live sources.",
        tone: response.total ? "success" : "info",
      });
      setPage(1);
      setReloadKey((value) => value + 1);
    } catch (cause) {
      notify({ title: "Live search unavailable", message: cause instanceof Error ? cause.message : "Try again in a moment.", tone: "error" });
    } finally {
      setFetchingLive(false);
    }
  }

  function openJob(job: Job) {
    setSelected(job);
    setDetailOpen(true);
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="mx-auto max-w-[1500px] px-4 pb-10 pt-8 sm:px-6 sm:pt-10 lg:px-8">
      <section className="mb-9 grid items-center gap-6 lg:grid-cols-[1.06fr_.94fr] lg:gap-10">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="mb-3 inline-flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.2em] text-emerald-300/80"><span className="size-1.5 animate-pulse rounded-full bg-emerald-300" />A smarter search, built around you</div>
          <h1 className="text-3xl font-semibold tracking-[-0.055em] text-white sm:text-4xl lg:text-[48px] lg:leading-[1.04]">Your next move,<br /><span className="bg-gradient-to-r from-emerald-200 via-cyan-200 to-indigo-300 bg-clip-text text-transparent">with a clearer signal.</span></h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-zinc-400">Explore roles against your experience, understand what the market rewards, and make your next step with evidence.</p>
          <div className="mt-7 grid max-w-xl grid-cols-3 gap-2.5">
            {[
              { label: "Indexed roles", value: overview?.jobs_analyzed.toLocaleString() ?? "—", icon: BriefcaseBusiness },
              { label: "Median comp", value: formatCompactCurrency(overview?.median_salary_usd), icon: Sparkles },
              { label: "Skills tracked", value: overview?.top_skills.length ? `${overview.top_skills.length}+` : "—", icon: FileText },
            ].map(({ label, value, icon: Icon }) => <div key={label} className="rounded-xl border border-white/[0.08] bg-white/[0.035] px-3 py-3 backdrop-blur-xl"><span className="flex items-center gap-1.5 text-[9px] font-medium uppercase tracking-[.11em] text-zinc-500"><Icon className="size-3 text-emerald-300" />{label}</span><span className="mt-2 block font-mono text-[15px] font-semibold tracking-tight text-zinc-100">{value}</span></div>)}
          </div>
        </motion.div>

        {profile ? (
          <motion.div layout initial={{ opacity: 0, scale: .98 }} animate={{ opacity: 1, scale: 1 }} className="rounded-3xl border border-emerald-300/15 bg-gradient-to-br from-emerald-300/[0.1] via-white/[0.035] to-indigo-300/[0.07] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,.12)] backdrop-blur-2xl sm:p-6">
            <div className="flex items-start justify-between gap-4"><div><span className="text-[10px] font-semibold uppercase tracking-[.17em] text-emerald-200">Candidate profile active</span><h2 className="mt-2 text-xl font-semibold tracking-tight text-white">{profile.name}</h2><p className="mt-1 text-xs text-zinc-400">{profile.years_experience} years experience <span className="mx-1.5 text-zinc-700">·</span> Hybrid match scoring</p></div><span className="flex size-11 items-center justify-center rounded-2xl border border-emerald-300/20 bg-emerald-300/10 text-emerald-200"><Sparkles className="size-5" /></span></div>
            <div className="mt-5 flex flex-wrap gap-1.5">{profile.skills.slice(0, 7).map((skill) => <span key={skill} className="rounded-full border border-white/10 bg-white/[0.06] px-2.5 py-1 text-[10px] text-zinc-200">{skill}</span>)}{profile.skills.length > 7 && <span className="px-1 py-1 text-[10px] text-zinc-500">+{profile.skills.length - 7} skills</span>}</div>
            <Button variant="secondary" size="sm" className="mt-5" onClick={() => setUploadOpen(true)}><UploadCloud className="size-3.5" />Replace CV</Button>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .08 }}
            role="button" tabIndex={0} aria-label="Upload or drop a PDF CV"
            onClick={() => setUploadOpen(true)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setUploadOpen(true); }}
            onDragOver={(event) => { event.preventDefault(); setDraggingCv(true); }} onDragLeave={() => setDraggingCv(false)} onDrop={(event) => void onCvDrop(event)}
            className={`glass-dropzone group relative flex min-h-[222px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-3xl border border-dashed px-6 py-7 text-center transition duration-300 ${draggingCv ? "is-dragging" : ""}`}
          >
            <span className="pointer-events-none absolute -right-10 -top-12 size-40 rounded-full bg-cyan-300/10 blur-3xl transition group-hover:bg-cyan-300/20" />
            <span className="relative flex size-12 items-center justify-center rounded-2xl border border-white/15 bg-white/[0.08] text-emerald-200 shadow-[inset_0_1px_0_rgba(255,255,255,.18)] transition group-hover:-translate-y-1"><UploadCloud className="size-5" /></span>
            <h2 className="relative mt-4 text-sm font-semibold text-white">{uploadingCv ? "Reading your CV…" : "Drop your PDF CV to unlock your match"}</h2>
            <p className="relative mt-1.5 max-w-sm text-xs leading-5 text-zinc-400">3-Factor Hybrid Match Scoring across semantic fit, skill overlap, and experience alignment.</p>
            <span className="relative mt-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-3 py-1.5 text-[10px] font-medium text-zinc-200"><FileText className="size-3.5 text-emerald-300" /> PDF · up to 12 MB <span className="text-zinc-600">or click to browse</span></span>
          </motion.div>
        )}
      </section>

      <div className="mb-5 flex items-center gap-3 rounded-2xl border border-white/[0.07] bg-zinc-900/55 p-2.5 pl-4 shadow-inner">
        <Search className="size-4 shrink-0 text-zinc-600" />
        <input ref={searchRef} value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Search roles, companies, or skills..." className="h-9 min-w-0 flex-1 bg-transparent text-sm text-zinc-200 outline-none placeholder:text-zinc-600" />
        <kbd className="hidden rounded-md border border-white/[0.08] bg-zinc-950 px-2 py-1 font-mono text-[10px] text-zinc-700 sm:inline-block">/</kbd>
        <div className="hidden items-center gap-2 border-l border-white/[0.07] pl-3 text-[10px] text-zinc-600 md:flex"><span className="size-1.5 rounded-full bg-emerald-300" />Live index</div>
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-[250px_minmax(0,1fr)] xl:grid-cols-[270px_minmax(0,1fr)]">
        <div className="hidden lg:block"><FilterSidebar {...{ category, setCategory, workMode, setWorkMode, levels, setLevels, minSalary, setMinSalary, skills, setSkills, region, setRegion, branch, setBranch, domain, setDomain, taxonomy, setPage }} /></div>
        <div className="min-w-0">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div><h2 className="text-sm font-semibold text-zinc-100">Open opportunities</h2><p className="mt-1 text-xs text-zinc-600">{loading ? "Finding relevant roles…" : `${data?.total ?? 0} roles match your search`}{activeFilters && " · filters applied"}</p></div>
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={() => setMobileFiltersOpen((value) => !value)} className="lg:hidden"><Filter className="size-3.5" /> Filters</Button>
              <Button size="sm" onClick={() => void fetchLiveJobs()} disabled={fetchingLive} className="min-w-[126px]">
                {fetchingLive ? <LoaderCircle className="size-3.5 animate-spin" /> : <Wifi className="size-3.5" />}
                {fetchingLive ? "Searching…" : "Fetch Live Jobs"}
              </Button>
              {profile && <Badge tone="indigo" className="hidden gap-1.5 sm:inline-flex"><Sparkles className="size-3" />Ranked for {profile.name.split(" ")[0]}</Badge>}
              <label className="flex h-9 items-center gap-2 rounded-lg border border-white/[0.07] bg-zinc-900/50 px-3 text-xs text-zinc-500"><ArrowDownWideNarrow className="size-3.5" /><select value={!profile && sortBy === "match" ? "recent" : sortBy} onChange={(event) => setSortBy(event.target.value as typeof sortBy)} className="bg-transparent text-xs text-zinc-300 outline-none"><option value="match" disabled={!profile}>Best fit</option><option value="recent">Most recent</option><option value="salary">Highest salary</option></select></label>
            </div>
          </div>

          {mobileFiltersOpen && <div className="mb-4 lg:hidden"><FilterSidebar {...{ category, setCategory, workMode, setWorkMode, levels, setLevels, minSalary, setMinSalary, skills, setSkills, region, setRegion, branch, setBranch, domain, setDomain, taxonomy, setPage }} /></div>}

          {activeFilters && <div className="mb-4 flex flex-wrap gap-1.5">
            {category && <button onClick={() => { setCategory(""); setPage(1); }} className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] text-zinc-400">{category} ×</button>}
            {region && <button onClick={() => { setRegion(""); setPage(1); }} className={`rounded-full border px-2.5 py-1 text-[10px] ${REGION_TONES[region] ?? "border-white/10 bg-white/[0.04] text-zinc-400"}`}>{region} ×</button>}
            {branch && <button onClick={() => { setBranch(""); setDomain(""); setPage(1); }} className="rounded-full border border-indigo-300/15 bg-indigo-300/[0.04] px-2.5 py-1 text-[10px] text-indigo-200">{branch} ×</button>}
            {domain && <button onClick={() => { setDomain(""); setPage(1); }} className="rounded-full border border-cyan-300/15 bg-cyan-300/[0.04] px-2.5 py-1 text-[10px] text-cyan-200">{domain} ×</button>}
            {workMode && <button onClick={() => { setWorkMode(""); setPage(1); }} className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] capitalize text-zinc-400">{workMode} ×</button>}
            {skills.map((skill) => <button key={skill} onClick={() => { setSkills(skills.filter((item) => item !== skill)); setPage(1); }} className="rounded-full border border-indigo-300/15 bg-indigo-300/[0.04] px-2.5 py-1 text-[10px] text-indigo-200">{skill} ×</button>)}
            <button onClick={() => { setSearch(""); setCategory(""); setRegion(""); setBranch(""); setDomain(""); setWorkMode(""); setLevels([]); setMinSalary(0); setSkills([]); setPage(1); }} className="px-2 py-1 text-[10px] text-zinc-600 hover:text-zinc-300">Clear all</button>
          </div>}

          {error ? (
            <Card className="flex min-h-64 flex-col items-center justify-center px-6 text-center">
              <div className="mb-4 flex size-12 items-center justify-center rounded-2xl border border-amber-300/10 bg-amber-300/[0.05] text-amber-200"><CircleHelp className="size-5" /></div>
              <h3 className="text-sm font-semibold text-zinc-200">Couldn’t reach the job index</h3>
              <p className="mt-2 max-w-md text-xs leading-relaxed text-zinc-500">{error}. Start the FastAPI service and database, then refresh this view.</p>
              <Button variant="secondary" size="sm" onClick={() => setReloadKey((value) => value + 1)} className="mt-4">Retry</Button>
            </Card>
          ) : loading ? (
            <div className="space-y-3">{[0, 1, 2].map((item) => <Card key={item} className="h-64 animate-pulse bg-zinc-900/45" />)}</div>
          ) : data?.items.length ? (
            <div className="space-y-3">{data.items.map((job) => <JobCard key={job.id} job={job} onClick={() => openJob(job)} profileActive={Boolean(profile)} />)}</div>
          ) : (
            <Card className="flex min-h-64 flex-col items-center justify-center px-6 text-center">
              <div className="mb-4 flex size-12 items-center justify-center rounded-2xl border border-white/[0.07] bg-white/[0.025] text-zinc-500"><SlidersHorizontal className="size-5" /></div>
              <h3 className="text-sm font-semibold text-zinc-200">No roles match these filters</h3>
              <p className="mt-2 text-xs text-zinc-600">Clear one or more filters to widen your search.</p>
              <Button size="sm" onClick={() => void fetchLiveJobs()} disabled={fetchingLive} className="mt-4">
                {fetchingLive ? <LoaderCircle className="size-3.5 animate-spin" /> : <Wifi className="size-3.5" />}
                {fetchingLive ? "Searching live sources…" : "Fetch Live Jobs"}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => { setSearch(""); setCategory(""); setRegion(""); setBranch(""); setDomain(""); setWorkMode(""); setLevels([]); setMinSalary(0); setSkills([]); setPage(1); }}>Reset filters</Button>
            </Card>
          )}

          {data && data.total > PAGE_SIZE && <div className="mt-5 flex items-center justify-between border-t border-white/[0.06] pt-4">
            <p className="text-xs text-zinc-600">Page {page} of {totalPages}</p>
            <div className="flex gap-2"><Button variant="secondary" size="sm" disabled={page <= 1 || loading} onClick={() => setPage((value) => Math.max(1, value - 1))}><ArrowLeft className="size-3.5" /> Previous</Button><Button variant="secondary" size="sm" disabled={page >= totalPages || loading} onClick={() => setPage((value) => Math.min(totalPages, value + 1))}>Next <ArrowRight className="size-3.5" /></Button></div>
          </div>}
        </div>
      </div>
      <JobDetailSheet job={selected} open={detailOpen} onOpenChange={setDetailOpen} />
    </div>
  );
}
