"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowUpRight, BarChart3, BriefcaseBusiness, CircleHelp, Radio, Sparkles, Target, TrendingUp, UploadCloud, Users } from "lucide-react";
import { motion } from "framer-motion";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { useApp } from "@/components/app-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch, type MarketOverview } from "@/lib/api";
import { formatCompactCurrency, formatSalary } from "@/lib/utils";

const COLORS = { remote: "#10b981", hybrid: "#0ea5e9", onsite: "#f59e0b" };
const MODES = ["remote", "hybrid", "onsite"] as const;
const TOOLTIP_STYLE = { backgroundColor: "var(--chart-tooltip-bg)", border: "1px solid var(--hairline)", borderRadius: 12, color: "var(--chart-tooltip-fg)", fontSize: 11, boxShadow: "0 14px 40px rgba(0,0,0,.18)", backdropFilter: "blur(20px)" };

function StatCard({ label, value, detail, icon: Icon, accent = "emerald", trend, index }: {
  label: string; value: string; detail: string; icon: React.ElementType; accent?: "emerald" | "indigo" | "amber" | "cyan" | "violet"; trend?: string; index: number;
}) {
  const color = accent === "indigo" ? "text-indigo-200 bg-indigo-300/[0.08] border-indigo-300/10" : accent === "amber" ? "text-amber-200 bg-amber-300/[0.07] border-amber-300/10" : accent === "cyan" ? "text-cyan-200 bg-cyan-300/[0.08] border-cyan-300/10" : accent === "violet" ? "text-violet-200 bg-violet-300/[0.08] border-violet-300/10" : "text-emerald-200 bg-emerald-300/[0.07] border-emerald-300/10";
  const strip = accent === "indigo" ? "from-indigo-500 to-blue-500" : accent === "amber" ? "from-amber-400 to-rose-500" : accent === "cyan" ? "from-cyan-400 to-sky-500" : accent === "violet" ? "from-violet-500 to-fuchsia-500" : "from-emerald-400 to-teal-500";
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", stiffness: 220, damping: 24, delay: index * .06 }}>
    <Card className="relative overflow-hidden p-5">
      <div className={`absolute inset-x-5 top-0 h-0.5 rounded-full bg-gradient-to-r ${strip}`} />
      <div className="absolute -right-8 -top-8 size-24 rounded-full bg-white/[0.015] blur-2xl" />
      <div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600">{label}</p><p className="mt-3 font-mono text-2xl font-semibold tracking-[-0.04em] text-white">{value}</p></div><span className={`flex size-9 items-center justify-center rounded-xl border ${color}`}><Icon className="size-4" /></span></div>
      <div className="mt-3 flex items-center gap-1.5 text-[10px] text-zinc-600">{trend && <ArrowUpRight className="size-3 text-emerald-300" />}{detail}</div>
    </Card>
    </motion.div>
  );
}

function EmptyChart({ label }: { label: string }) {
  return <div className="flex h-full min-h-64 flex-col items-center justify-center text-center"><div className="mb-3 flex size-10 items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.025] text-zinc-600"><BarChart3 className="size-4" /></div><p className="text-xs text-zinc-500">{label}</p><p className="mt-1 text-[10px] text-zinc-700">Run a sync or seed the dataset to populate this view.</p></div>;
}

export function AnalyticsDashboard() {
  const { profile, setUploadOpen, lastRun } = useApp();
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    const query = profile ? `?profile_id=${profile.id}` : "";
    apiFetch<MarketOverview>(`/analytics/overview${query}`)
      .then(setOverview)
      .catch((cause: unknown) => { setOverview(null); setError(cause instanceof Error ? cause.message : "Could not load analytics."); })
      .finally(() => setLoading(false));
  }, [profile?.id, lastRun?.id]);

  const skills = overview?.top_skills ?? [];
  const salaryRows = useMemo(() => (overview?.salary_distribution ?? []).map((row) => ({
    ...row,
    label: `${row.experience_level.slice(0, 1).toUpperCase()}${row.experience_level.slice(1)} · ${row.work_mode}`,
  })), [overview?.salary_distribution]);
  const categoryRows = useMemo(() => {
    const grouped = new Map<string, { category: string; remote: number; hybrid: number; onsite: number }>();
    for (const row of overview?.job_volume ?? []) {
      const current = grouped.get(row.category) ?? { category: row.category, remote: 0, hybrid: 0, onsite: 0 };
      current[row.work_mode as keyof Omit<typeof current, "category">] = row.job_count;
      grouped.set(row.category, current);
    }
    return [...grouped.values()];
  }, [overview?.job_volume]);
  const modeRows = useMemo(() => MODES.map((mode) => ({
    name: mode[0].toUpperCase() + mode.slice(1),
    value: (overview?.job_volume ?? []).filter((row) => row.work_mode === mode).reduce((sum, row) => sum + row.job_count, 0),
    color: COLORS[mode],
  })).filter((row) => row.value > 0), [overview?.job_volume]);

  const busiestSkill = skills[0];
  const highestPayingSkill = [...skills].filter((skill) => skill.mean_salary_usd != null).sort((left, right) => (right.mean_salary_usd ?? 0) - (left.mean_salary_usd ?? 0))[0];
  const jobsIndexed = overview?.jobs_analyzed ?? 0;
  const remoteShare = overview?.remote_role_share ?? 0;

  return (
    <div className="mx-auto max-w-[1500px] px-4 pb-10 pt-8 sm:px-6 sm:pt-10 lg:px-8">
      <section className="mb-8 flex flex-col justify-between gap-5 lg:mb-9 lg:flex-row lg:items-end">
        <div className="max-w-2xl">
          <div className="mb-3 inline-flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.2em] text-indigo-200/75"><span className="size-1.5 rounded-full bg-indigo-300" />Labor market signals</div>
          <h1 className="text-3xl font-semibold tracking-[-0.055em] text-white sm:text-4xl lg:text-[46px] lg:leading-[1.08]">Read the market <span className="bg-gradient-to-r from-indigo-200 via-indigo-300 to-emerald-200 bg-clip-text text-transparent">behind the roles.</span></h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-zinc-500">Explore demand, compensation, and the skill signals moving across the indexed technology market.</p>
        </div>
        <Badge tone="indigo" className="w-fit gap-2 px-3 py-2"><Activity className="size-3.5" />{loading ? "Updating market view" : "Market index"}<span className="ml-1 size-1.5 rounded-full bg-emerald-300" /></Badge>
      </section>

      {error && <div className="mb-5 rounded-xl border border-amber-300/10 bg-amber-300/[0.035] px-4 py-3 text-xs text-amber-100/80">Analytics API unavailable: {error}. Start FastAPI and refresh to load live market data.</div>}

      <section className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard index={0} label="Indexed opportunities" value={loading ? "—" : jobsIndexed.toLocaleString()} detail="Across live sources" icon={BriefcaseBusiness} trend={jobsIndexed > 0 ? "Source listings" : undefined} />
        <StatCard index={1} label="Median salary · USD" value={formatCompactCurrency(overview?.median_salary_usd)} detail="Annualized range midpoint" icon={TrendingUp} accent="emerald" />
        <StatCard index={2} label="Remote role share" value={`${Math.round(remoteShare * 100)}%`} detail="Of indexed opportunities" icon={Radio} accent="cyan" />
        <StatCard index={3} label="Highest-paying skill" value={highestPayingSkill?.skill ?? busiestSkill?.skill ?? "—"} detail={highestPayingSkill ? `${formatCompactCurrency(highestPayingSkill.mean_salary_usd)} mean salary` : "Awaiting indexed roles"} icon={Sparkles} accent="violet" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_.8fr]">
        <Card className="min-w-0">
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div><CardTitle>Skill demand & compensation</CardTitle><CardDescription className="mt-1">Most requested capabilities across the current job index.</CardDescription></div>
            <Badge tone="emerald">Top 15</Badge>
          </CardHeader>
          <CardContent className="pt-0">
            {loading ? <div className="h-[380px] animate-pulse rounded-xl bg-white/[0.025]" /> : skills.length === 0 ? <EmptyChart label="No skill demand to display" /> : (
              <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_115px]">
                <div className="h-[390px] min-w-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={skills} layout="vertical" margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
                      <defs><linearGradient id="skillGradient" x1="0" y1="1" x2="1" y2="0"><stop offset="0%" stopColor="#4f46e5" /><stop offset="100%" stopColor="#06b6d4" /></linearGradient></defs>
                      <CartesianGrid horizontal={false} stroke="rgba(255,255,255,.055)" />
                      <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: "#71717a", fontSize: 10 }} />
                      <YAxis type="category" dataKey="skill" width={104} tickLine={false} axisLine={false} tick={{ fill: "#a1a1aa", fontSize: 10 }} />
                      <Tooltip cursor={{ fill: "rgba(255,255,255,.03)" }} contentStyle={TOOLTIP_STYLE} formatter={(value) => [`${value ?? 0} listings`, "Demand"]} />
                      <Bar dataKey="frequency" name="Demand" fill="url(#skillGradient)" radius={[0, 5, 5, 0]} barSize={13} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="hidden border-l border-white/[0.055] py-2 pl-3 md:block">
                  <p className="mb-3 text-[9px] uppercase tracking-[0.12em] text-zinc-700">Mean salary</p>
                  <div className="space-y-[13px]">
                    {skills.map((row) => <div key={row.skill} title={`${row.skill}: ${formatSalary(row.mean_salary_usd)}`} className="flex h-[13px] items-center text-[10px] font-medium tabular-nums text-zinc-400">{formatCompactCurrency(row.mean_salary_usd)}</div>)}
                  </div>
                </div>
                <div className="grid gap-1.5 md:hidden">
                  {skills.slice(0, 6).map((row) => <div key={row.skill} className="flex items-center justify-between border-t border-white/[0.04] pt-2 text-[10px]"><span className="text-zinc-400">{row.skill}</span><span className="text-zinc-600">{row.frequency} roles <span className="mx-1 text-zinc-800">·</span>{formatCompactCurrency(row.mean_salary_usd)}</span></div>)}
                </div>
              </div>
            )}
            <div className="mt-2 flex items-center gap-2 text-[10px] text-zinc-700"><span className="size-2 rounded-sm bg-emerald-300" />Jobs requiring the skill <span className="ml-auto">Salary values use range midpoint</span></div>
          </CardContent>
        </Card>

        <Card className="min-w-0">
          <CardHeader className="flex flex-row items-start justify-between gap-3"><div><CardTitle>Salary quartiles</CardTitle><CardDescription className="mt-1">USD range by experience and work mode.</CardDescription></div><Badge>Annual</Badge></CardHeader>
          <CardContent className="pt-0">
            {loading ? <div className="h-[390px] animate-pulse rounded-xl bg-white/[0.025]" /> : salaryRows.length === 0 ? <EmptyChart label="No salary data to display" /> : (
              <div className="h-[390px] min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={salaryRows} margin={{ top: 8, right: 6, left: 0, bottom: 45 }}>
                    <CartesianGrid vertical={false} stroke="rgba(255,255,255,.055)" />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} interval={0} angle={-28} textAnchor="end" height={60} tick={{ fill: "#71717a", fontSize: 9 }} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fill: "#71717a", fontSize: 10 }} tickFormatter={(value: number) => `$${Math.round(value / 1000)}k`} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value, name) => [formatSalary(Number(value)), name]} />
                    <Legend wrapperStyle={{ fontSize: 10, color: "#71717a" }} />
                    <Bar dataKey="p25" name="P25" fill="#38bdf8" radius={[4, 4, 0, 0]} barSize={10} />
                    <Bar dataKey="median" name="Median" fill="#6366f1" radius={[4, 4, 0, 0]} barSize={10} />
                    <Bar dataKey="p75" name="P75" fill="#10b981" radius={[4, 4, 0, 0]} barSize={10} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-zinc-600"><span>Min {formatCompactCurrency(Math.min(...salaryRows.map((row) => row.minimum), Infinity))}</span><span>Max {formatCompactCurrency(Math.max(...salaryRows.map((row) => row.maximum), 0))}</span><span className="ml-auto">Grouped by experience · mode</span></div>
          </CardContent>
        </Card>
      </section>

      <section className="mt-4 grid gap-4 xl:grid-cols-[1.2fr_.8fr]">
        <Card className="min-w-0">
          <CardHeader className="flex flex-row items-start justify-between gap-3"><div><CardTitle>Where roles are growing</CardTitle><CardDescription className="mt-1">Job volume across categories and work modes.</CardDescription></div><Badge tone="indigo">{categoryRows.length} categories</Badge></CardHeader>
          <CardContent className="pt-0">
            {loading ? <div className="h-[330px] animate-pulse rounded-xl bg-white/[0.025]" /> : categoryRows.length === 0 ? <EmptyChart label="No job volume to display" /> : (
              <div className="h-[330px] min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={categoryRows} margin={{ top: 10, right: 10, left: 0, bottom: 28 }}>
                    <CartesianGrid vertical={false} stroke="rgba(255,255,255,.055)" />
                    <XAxis dataKey="category" tickLine={false} axisLine={false} interval={0} angle={-16} textAnchor="end" height={60} tick={{ fill: "#71717a", fontSize: 9 }} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fill: "#71717a", fontSize: 10 }} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Legend wrapperStyle={{ fontSize: 10, color: "#71717a" }} />
                    <Bar dataKey="remote" name="Remote" stackId="modes" fill={COLORS.remote} />
                    <Bar dataKey="hybrid" name="Hybrid" stackId="modes" fill={COLORS.hybrid} />
                    <Bar dataKey="onsite" name="On-site" stackId="modes" fill={COLORS.onsite} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="min-w-0">
          <CardHeader><CardTitle>Work mode mix</CardTitle><CardDescription className="mt-1">How the indexed roles meet people where they work.</CardDescription></CardHeader>
          <CardContent className="pt-0">
            {loading ? <div className="h-[330px] animate-pulse rounded-xl bg-white/[0.025]" /> : modeRows.length === 0 ? <EmptyChart label="No work mode data to display" /> : (
              <div className="grid items-center gap-4 sm:grid-cols-[1fr_150px]">
                <div className="h-[280px] min-w-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={modeRows} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="88%" paddingAngle={4} stroke="none">
                        {modeRows.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
                      </Pie>
                      <Tooltip contentStyle={TOOLTIP_STYLE} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-3">
                  {modeRows.map((row) => <div key={row.name} className="flex items-center justify-between gap-3 text-xs"><span className="flex items-center gap-2 text-zinc-500"><span className="size-2 rounded-full" style={{ backgroundColor: row.color }} />{row.name}</span><span className="font-medium tabular-nums text-zinc-200">{row.value}</span></div>)}
                  <div className="border-t border-white/[0.06] pt-3"><p className="text-[10px] uppercase tracking-[0.12em] text-zinc-700">Remote index</p><p className="mt-1 text-xl font-semibold text-white">{Math.round(remoteShare * 100)}<span className="text-sm text-zinc-600">%</span></p></div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="mt-4">
        <Card className="overflow-hidden border-indigo-300/[0.11] bg-gradient-to-br from-indigo-400/[0.055] via-zinc-900/80 to-emerald-300/[0.025]">
          <div className="grid gap-0 lg:grid-cols-[.8fr_1.2fr]">
            <div className="border-b border-white/[0.06] p-5 sm:p-6 lg:border-b-0 lg:border-r">
              <div className="mb-4 flex size-10 items-center justify-center rounded-xl border border-indigo-300/15 bg-indigo-300/[0.08] text-indigo-200"><Target className="size-4" /></div>
              <p className="text-[10px] uppercase tracking-[0.18em] text-indigo-200/70">Personal skill-gap ROI</p>
              <h2 className="mt-2 text-lg font-semibold tracking-[-0.03em] text-white">Your next skill, in context.</h2>
              <p className="mt-2 max-w-md text-xs leading-6 text-zinc-500">Skills below appear most often in high-scoring roles for your profile, showing where focused learning could open more doors.</p>
              {!profile && <Button size="sm" onClick={() => setUploadOpen(true)} className="mt-5"><UploadCloud className="size-3.5" />Upload a CV to personalize</Button>}
            </div>
            <div className="p-5 sm:p-6">
              {loading ? <div className="h-36 animate-pulse rounded-xl bg-white/[0.025]" /> : profile ? overview?.personal_skill_gap_roi.length ? (
                <div className="space-y-2">
                  {overview.personal_skill_gap_roi.map((item, index) => <div key={item.skill} className="flex items-center gap-3 rounded-xl border border-white/[0.045] bg-black/[0.12] px-3.5 py-3">
                    <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-white/[0.045] text-[10px] font-semibold text-zinc-400">0{index + 1}</span>
                    <span className="min-w-0 flex-1"><span className="block text-xs font-medium text-zinc-200">{item.skill}</span><span className="mt-1 block text-[10px] text-zinc-600">Appears in {item.high_scoring_jobs} high-fit roles</span></span>
                    <span className="text-right"><span className="block text-xs font-medium text-emerald-200">{item.high_scoring_jobs} roles</span><span className="mt-1 block text-[9px] text-zinc-600">{Math.round(item.mean_match_score)} avg fit</span></span>
                  </div>)}
                </div>
              ) : <div className="flex min-h-36 items-center justify-center rounded-xl border border-white/[0.05] bg-black/[0.1] text-center"><div><CircleHelp className="mx-auto size-5 text-zinc-600" /><p className="mt-2 text-xs text-zinc-500">No high-fit skill gaps surfaced yet.</p><p className="mt-1 text-[10px] text-zinc-700">Your current profile may already cover these roles.</p></div></div>
                : <div className="flex min-h-36 items-center justify-center rounded-xl border border-dashed border-white/[0.08] bg-black/[0.1] text-center"><div><Users className="mx-auto size-5 text-zinc-700" /><p className="mt-2 text-xs text-zinc-500">Upload a CV to reveal your personal opportunity map.</p></div></div>}
            </div>
          </div>
        </Card>
      </section>
    </div>
  );
}
