"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiFetch, type CandidateProfile, type EtlRun } from "@/lib/api";
import { CvUploadDialog } from "@/components/cv-upload-dialog";

type Toast = { id: number; title: string; message?: string; tone: "success" | "error" | "info" };
type AppContextValue = {
  profile: CandidateProfile | null;
  setProfile: (profile: CandidateProfile | null) => void;
  removeProfileSkill: (skill: string) => void;
  clearProfile: () => void;
  uploadOpen: boolean;
  setUploadOpen: (open: boolean) => void;
  uploadCv: (file: File) => Promise<void>;
  lastRun: EtlRun | null;
  syncing: boolean;
  syncEtl: () => Promise<void>;
  notify: (toast: Omit<Toast, "id">) => void;
};

const AppContext = createContext<AppContextValue | null>(null);

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside AppProvider");
  return context;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [profile, setProfileState] = useState<CandidateProfile | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [lastRun, setLastRun] = useState<EtlRun | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const notify = useCallback((toast: Omit<Toast, "id">) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((current) => [...current.slice(-2), { ...toast, id }]);
    window.setTimeout(() => setToasts((current) => current.filter((item) => item.id !== id)), 4200);
  }, []);

  const setProfile = useCallback((next: CandidateProfile | null) => {
    setProfileState(next);
    if (next) window.localStorage.setItem("hire-archy-profile", JSON.stringify(next));
    else window.localStorage.removeItem("hire-archy-profile");
  }, []);

  useEffect(() => {
    const stored = window.localStorage.getItem("hire-archy-profile");
    if (stored) {
      try { setProfileState(JSON.parse(stored) as CandidateProfile); }
      catch { window.localStorage.removeItem("hire-archy-profile"); }
    }
    apiFetch<EtlRun[]>("/etl/logs?limit=1").then((runs) => setLastRun(runs[0] ?? null)).catch(() => undefined);
  }, []);

  const removeProfileSkill = useCallback((skill: string) => {
    if (!profile) return;
    setProfile({ ...profile, skills: profile.skills.filter((item) => item !== skill) });
  }, [profile, setProfile]);

  const uploadCv = useCallback(async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    const extracted = await apiFetch<CandidateProfile>("/cv/upload", { method: "POST", body });
    setProfile(extracted);
    setUploadOpen(false);
    notify({ title: "CV analyzed", message: `${extracted.skills.length} skills added to your active profile.`, tone: "success" });
  }, [notify, setProfile]);

  const syncEtl = useCallback(async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      await apiFetch<{ status: string; limit: number }>("/etl/run?limit=25", { method: "POST" });
      notify({ title: "Sync started", message: "New listings are being collected in the background.", tone: "info" });
      for (let attempt = 0; attempt < 12; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1600));
        const runs = await apiFetch<EtlRun[]>("/etl/logs?limit=1");
        if (runs[0] && (!lastRun || runs[0].id !== lastRun.id)) {
          setLastRun(runs[0]);
          notify({ title: "Listings refreshed", message: `${runs[0].jobs_fetched} fetched · ${runs[0].duplicates_skipped} duplicates skipped.`, tone: "success" });
          return;
        }
      }
    } catch (error) {
      notify({ title: "Sync unavailable", message: error instanceof Error ? error.message : "Could not reach the API.", tone: "error" });
    } finally {
      setSyncing(false);
    }
  }, [lastRun, notify, syncing]);

  const value = useMemo<AppContextValue>(() => ({
    profile,
    setProfile,
    removeProfileSkill,
    clearProfile: () => setProfile(null),
    uploadOpen,
    setUploadOpen,
    uploadCv,
    lastRun,
    syncing,
    syncEtl,
    notify,
  }), [profile, setProfile, removeProfileSkill, uploadOpen, uploadCv, lastRun, syncing, syncEtl, notify]);

  return (
    <AppContext.Provider value={value}>
      {children}
      <CvUploadDialog />
      <div aria-live="polite" className="fixed bottom-5 right-5 z-[100] flex w-[min(24rem,calc(100vw-2.5rem))] flex-col gap-2">
        {toasts.map((toast) => (
          <div key={toast.id} className={`rounded-2xl border px-4 py-3 shadow-2xl backdrop-blur-xl ${toast.tone === "error" ? "border-rose-300/20 bg-zinc-950/95" : toast.tone === "success" ? "border-emerald-300/20 bg-zinc-950/95" : "border-indigo-300/20 bg-zinc-950/95"}`}>
            <p className="text-sm font-semibold text-white">{toast.title}</p>
            {toast.message && <p className="mt-1 text-xs leading-relaxed text-zinc-400">{toast.message}</p>}
          </div>
        ))}
      </div>
    </AppContext.Provider>
  );
}
