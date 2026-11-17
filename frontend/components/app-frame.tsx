"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, ArrowUpRight, BriefcaseBusiness, ChartNoAxesCombined, ChevronDown, ChevronUp, FileUp, LoaderCircle, RefreshCw, Sparkles, X } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";
import { useApp } from "@/components/app-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, timeAgo } from "@/lib/utils";
import { ThemeSwitcher } from "@/components/theme-switcher";

export function AppFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { profile, removeProfileSkill, clearProfile, setUploadOpen, lastRun, syncing, syncEtl } = useApp();
  const [profileExpanded, setProfileExpanded] = useState(true);

  return (
    <div className="app-shell relative min-h-screen">
      <div className="ambient-field" />
      <div className="surface-grid pointer-events-none fixed inset-x-0 top-0 z-0 h-[480px] opacity-50" />
      <header className="sticky top-3 z-40 mx-auto w-[calc(100%-1.5rem)] max-w-[1420px]">
        <div className="glass-nav rounded-2xl border">
        <div className="mx-auto flex h-[64px] max-w-[1500px] items-center justify-between gap-3 px-3 sm:gap-4 sm:px-5 lg:px-7">
          <Link href="/" className="group flex min-w-0 items-center gap-3" aria-label="Hire-Archy home">
            <span className="relative flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-indigo-300/30 bg-gradient-to-br from-indigo-600 via-blue-600 to-violet-600 text-white shadow-[0_4px_20px_-7px_rgba(99,102,241,.8)]">
              <span className="text-[11px] font-black tracking-[-.1em]">H<span className="text-cyan-200">A</span></span>
              <span className="absolute -bottom-2 -right-2 size-5 rounded-full bg-emerald-300/20 blur-md" />
            </span>
            <span className="truncate text-[15px] font-semibold tracking-[-0.04em] text-white">Hire-Archy<span className="ml-1.5 align-top text-[9px] font-medium uppercase tracking-[0.18em] text-zinc-600">Labs</span></span>
          </Link>

          <nav className="hidden items-center gap-1 rounded-xl border border-white/[0.08] bg-white/[0.035] p-1 md:flex" aria-label="Primary navigation">
            <Link href="/" className={cn("relative flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-medium transition", pathname === "/" ? "nav-active text-white" : "text-zinc-500 hover:text-zinc-200")}>
              {pathname === "/" && <motion.span layoutId="active-nav" className="nav-active-pill absolute inset-0 rounded-lg shadow-sm" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
              <span className="relative z-10 inline-flex items-center gap-2">
              <BriefcaseBusiness className="size-3.5" /> Job Explorer
              </span>
            </Link>
            <Link href="/analytics" className={cn("relative flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-medium transition", pathname.startsWith("/analytics") ? "nav-active text-white" : "text-zinc-500 hover:text-zinc-200")}>
              {pathname.startsWith("/analytics") && <motion.span layoutId="active-nav" className="nav-active-pill absolute inset-0 rounded-lg shadow-sm" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
              <span className="relative z-10 inline-flex items-center gap-2">
              <ChartNoAxesCombined className="size-3.5" /> Market Analytics
              </span>
            </Link>
          </nav>

          <div className="flex shrink-0 items-center gap-2">
            <div className="hidden items-center gap-2 pr-1 lg:flex">
              <span className={cn("size-1.5 rounded-full", lastRun ? "animate-pulse bg-emerald-300 shadow-[0_0_10px_rgba(52,211,153,.65)]" : "bg-zinc-600")} />
              <span className="max-w-28 truncate text-[10px] text-zinc-500">{lastRun ? `Synced ${timeAgo(lastRun.run_at)}` : "Awaiting first sync"}</span>
            </div>
            <Button variant="secondary" size="sm" onClick={() => void syncEtl()} disabled={syncing} className="hidden h-9 rounded-xl sm:inline-flex">
              {syncing ? <LoaderCircle className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
              <span className="hidden lg:inline">ETL Sync</span>
            </Button>
            <ThemeSwitcher />
            <Button size="sm" onClick={() => setUploadOpen(true)} className="h-9 px-3 sm:px-3.5">
              <FileUp className="size-3.5" /><span className="hidden sm:inline">Upload CV</span><span className="sm:hidden">CV</span>
            </Button>
          </div>
        </div>
        <div className="flex items-center justify-center gap-2 border-t border-white/[0.07] py-2 md:hidden">
          <Link href="/" className={cn("rounded-md px-3 py-1.5 text-[11px]", pathname === "/" ? "text-emerald-200" : "text-zinc-500")}>Job Explorer</Link>
          <Link href="/analytics" className={cn("rounded-md px-3 py-1.5 text-[11px]", pathname.startsWith("/analytics") ? "text-emerald-200" : "text-zinc-500")}>Market Analytics</Link>
          <button onClick={() => void syncEtl()} disabled={syncing} className="ml-1 inline-flex items-center gap-1.5 px-2 py-1 text-[11px] text-zinc-500"><Activity className="size-3" />{syncing ? "Syncing" : "Sync"}</button>
        </div>
        </div>
      </header>

      {profile && (
        <section className="relative z-10 border-b border-emerald-300/[0.11] bg-emerald-300/[0.025]">
          <div className="mx-auto max-w-[1500px] px-4 py-3 sm:px-6 lg:px-8">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <button onClick={() => setProfileExpanded((current) => !current)} className="flex min-w-0 items-center gap-3 text-left">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-xl border border-indigo-300/20 bg-indigo-300/[0.09] text-indigo-200"><Sparkles className="size-4" /></span>
                <span className="min-w-0">
                  <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium text-zinc-100">
                    {profile.name}<span className="text-xs font-normal text-zinc-500">{profile.years_experience} yrs experience</span>
                  </span>
                  <span className="mt-0.5 block text-[10px] uppercase tracking-[0.13em] text-emerald-300/70">Active candidate profile · hybrid match scoring</span>
                </span>
                {profileExpanded ? <ChevronUp className="ml-1 size-4 text-zinc-600" /> : <ChevronDown className="ml-1 size-4 text-zinc-600" />}
              </button>
              <div className="flex items-center gap-1">
                <Button variant="secondary" size="sm" onClick={() => setUploadOpen(true)} className="h-8 text-xs"><FileUp className="size-3.5" /> Replace CV</Button>
                <Button variant="ghost" size="sm" onClick={clearProfile} className="h-8 text-xs text-zinc-500"><X className="size-3.5" /> Clear CV</Button>
              </div>
            </div>
            {profileExpanded && (
              <div className="mt-3 flex flex-wrap items-center gap-1.5 pl-11">
                <span className="mr-1 text-[10px] uppercase tracking-[0.12em] text-zinc-600">Detected skills</span>
                {profile.skills.map((skill) => (
                  <Badge key={skill} tone="indigo" className="group gap-1.5 py-1 pl-2.5 pr-1.5">
                    {skill}
                    <button onClick={(event) => { event.stopPropagation(); removeProfileSkill(skill); }} aria-label={`Remove ${skill} from profile`} className="rounded-full p-0.5 text-indigo-200/50 transition hover:bg-indigo-200/10 hover:text-white"><X className="size-3" /></button>
                  </Badge>
                ))}
                {profile.skills.length === 0 && <span className="text-xs text-zinc-500">No skills detected</span>}
              </div>
            )}
          </div>
        </section>
      )}

      <main className="relative z-10">{children}</main>
      <footer className="relative z-10 mt-16 border-t border-white/[0.06]">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-2 px-4 py-7 text-[11px] text-zinc-600 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <span>Hire-Archy <span className="text-zinc-700">·</span> Intelligence for the next move.</span>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 hover:text-zinc-400">API documentation <ArrowUpRight className="size-3" /></a>
        </div>
      </footer>
    </div>
  );
}
