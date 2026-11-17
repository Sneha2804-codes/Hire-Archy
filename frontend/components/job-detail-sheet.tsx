"use client";

import { ExternalLink, MapPin, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { useApp } from "@/components/app-provider";
import type { Job } from "@/lib/api";
import { formatSalary, timeAgo } from "@/lib/utils";

export function JobDetailSheet({ job, open, onOpenChange }: { job: Job | null; open: boolean; onOpenChange: (open: boolean) => void }) {
  const { profile, setUploadOpen } = useApp();
  if (!job) return null;
  const match = job.match;
  const matchTone = (match?.total_score ?? 0) >= 80 ? "emerald" : (match?.total_score ?? 0) >= 60 ? "indigo" : "amber";
  let applyDomain = "Verified external listing";
  try { applyDomain = new URL(job.apply_url).hostname.replace(/^www\./, ""); } catch { /* Invalid URLs remain unlinked by the source pipeline. */ }
  const sourceLabel = job.source === "Greenhouse" ? "Greenhouse ATS" : job.source === "Lever" ? "Lever ATS" : job.source;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="p-0">
        <div className="border-b border-white/[0.07] bg-gradient-to-br from-emerald-300/[0.07] via-transparent to-indigo-400/[0.055] p-6 pb-7 sm:p-8">
          <div className="mb-7 flex flex-wrap items-center justify-between gap-2 pr-10">
            <div className="flex flex-wrap gap-1.5"><Badge tone="default" className="uppercase tracking-[0.12em]">{job.category}</Badge><Badge className="border-white/[0.08] bg-zinc-950/40 text-zinc-400">{sourceLabel}</Badge></div>
            {match ? <Badge tone={matchTone} className="gap-1.5"><Sparkles className="size-3" />{Math.round(match.total_score)}% match</Badge> : <Badge>CV match ready</Badge>}
          </div>
          <SheetTitle className="max-w-lg">{job.title}</SheetTitle>
          <p className="mt-2 text-sm text-zinc-300">{job.company}</p>
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-zinc-500">
            <span className="inline-flex items-center gap-1.5"><MapPin className="size-3.5" />{job.location}{job.country && job.country !== "Unknown" ? `, ${job.country}` : ""}</span>
            <Badge className="border-cyan-300/15 bg-cyan-300/[0.05] text-cyan-200">{job.region || "Global/Remote"} · {job.country && job.country !== "Unknown" ? job.location.split(",")[0] : "Remote"}</Badge>
            <span className="capitalize">{job.work_mode}</span>
            <span>{timeAgo(job.posted_at)}</span>
          </div>
          <p className="mt-5 text-sm font-medium text-zinc-200">{formatSalary(job.salary_min_usd)} – {formatSalary(job.salary_max_usd)}<span className="ml-2 text-xs font-normal text-zinc-600">USD / year{job.salary_is_estimated ? " · estimated" : ""}</span></p>
        </div>

        <div className="space-y-7 p-6 sm:p-8">
          {match ? (
            <section>
              <div className="mb-4 flex items-end justify-between">
                <div><p className="text-[10px] uppercase tracking-[0.18em] text-emerald-300/75">Match intelligence</p><h3 className="mt-1 text-sm font-semibold text-white">Score breakdown</h3></div>
                <p className="text-2xl font-semibold tracking-tight text-white">{Math.round(match.total_score)}<span className="text-sm text-zinc-600">/100</span></p>
              </div>
              <Card className="space-y-4 p-4">
                {[
                  { label: "Semantic vector", weight: "50% weight", value: match.semantic_score, color: "bg-violet-500" },
                  { label: "TF-IDF & skill overlap", weight: "35% weight", value: match.skill_score, color: "bg-cyan-500" },
                  { label: "Experience alignment", weight: "15% weight", value: match.experience_score, color: "bg-emerald-500" },
                ].map((signal, index) => (
                  <motion.div key={signal.label} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * .08 }}>
                    <div className="mb-2 flex items-center justify-between gap-3 text-xs"><span className="text-zinc-300">{signal.label}</span><span className="text-zinc-600">{signal.weight}<span className="ml-2 text-zinc-300">{Math.round(signal.value)}%</span></span></div>
                    <Progress value={signal.value} className="h-1.5" indicatorClassName={signal.color} />
                  </motion.div>
                ))}
                <p className="border-t border-white/[0.06] pt-3 text-[10px] leading-relaxed text-zinc-600">Skills signal blends TF-IDF keyword cosine (60%) and canonical skill overlap (40%).</p>
              </Card>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-emerald-300/10 bg-emerald-300/[0.035] p-3.5">
                  <p className="text-[10px] uppercase tracking-[0.12em] text-emerald-300/70">Matched skills</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">{match.matched_skills.length ? match.matched_skills.map((skill) => <Badge key={skill} tone="emerald">{skill}</Badge>) : <span className="text-xs text-zinc-600">No direct skill overlap</span>}</div>
                </div>
                <div className="rounded-xl border border-amber-300/10 bg-amber-300/[0.025] p-3.5">
                  <p className="text-[10px] uppercase tracking-[0.12em] text-amber-300/70">Skills to grow</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">{match.missing_skills.length ? match.missing_skills.map((skill) => <Badge key={skill} tone="amber">{skill}</Badge>) : <span className="text-xs text-zinc-600">No missing listed skills</span>}</div>
                </div>
              </div>
            </section>
          ) : (
            <Card className="flex items-center justify-between gap-4 border-indigo-300/10 bg-indigo-300/[0.035] p-4">
              <div><p className="text-sm font-medium text-zinc-200">See how you line up</p><p className="mt-1 text-xs leading-relaxed text-zinc-500">Add a CV to get semantic, skill, and experience scoring.</p></div>
              <Button size="sm" onClick={() => { onOpenChange(false); setUploadOpen(true); }}>Upload CV</Button>
            </Card>
          )}

          <section>
            <div className="mb-3 flex items-center justify-between"><h3 className="text-sm font-semibold text-white">About the role</h3><span className="text-[10px] text-zinc-600">via {job.source}</span></div>
            <p className="whitespace-pre-line text-sm leading-7 text-zinc-400">{job.description || "No description was provided by this source."}</p>
          </section>

          <section>
            <h3 className="mb-3 text-sm font-semibold text-white">Role signals</h3>
            <div className="mb-3 flex flex-wrap gap-1.5"><Badge tone="indigo">{job.engineering_branch || "Engineering"}</Badge>{job.domain && <Badge className="border-cyan-300/15 bg-cyan-300/[0.05] text-cyan-200">{job.domain}</Badge>}</div>
            <div className="flex flex-wrap gap-2">{job.skills.map((skill) => <Badge key={skill}>{skill}</Badge>)}</div>
            <p className="mt-3 text-xs capitalize text-zinc-600">{job.experience_level} level · {job.work_mode} · {job.category}</p>
          </section>

          <Button asChild className="h-12 w-full justify-between px-5">
            <a href={job.apply_url} target="_blank" rel="noopener noreferrer"><span>Apply Directly <span className="ml-2 text-xs font-normal text-white/65">{applyDomain}</span></span><ExternalLink className="size-4" /></a>
          </Button>
          {profile && <p className="text-center text-[10px] text-zinc-700">Scores are guidance based on the uploaded CV and listing content.</p>}
        </div>
      </SheetContent>
    </Sheet>
  );
}
