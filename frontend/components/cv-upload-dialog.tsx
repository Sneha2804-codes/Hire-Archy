"use client";

import { useRef, useState, type DragEvent } from "react";
import { FileText, LoaderCircle, UploadCloud } from "lucide-react";
import { useApp } from "@/components/app-provider";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";

const MAX_FILE_SIZE = 12 * 1024 * 1024;

export function CvUploadDialog() {
  const { uploadOpen, setUploadOpen, uploadCv, notify } = useApp();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);

  function acceptFile(candidate?: File) {
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".pdf") || candidate.type && candidate.type !== "application/pdf") {
      notify({ title: "PDF files only", message: "Choose an exported PDF resume or CV.", tone: "error" });
      return;
    }
    if (candidate.size > MAX_FILE_SIZE) {
      notify({ title: "File is too large", message: "Choose a PDF under 12 MB.", tone: "error" });
      return;
    }
    setFile(candidate);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    acceptFile(event.dataTransfer.files[0]);
  }

  async function submit() {
    if (!file) return;
    setBusy(true);
    try {
      await uploadCv(file);
      setFile(null);
    } catch (error) {
      notify({ title: "Upload failed", message: error instanceof Error ? error.message : "Try again in a moment.", tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={uploadOpen} onOpenChange={(open) => { setUploadOpen(open); if (!open) setFile(null); }}>
      <DialogContent>
        <div className="mb-5 flex size-12 items-center justify-center rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.08] text-emerald-200">
          <UploadCloud className="size-5" />
        </div>
        <DialogTitle>Bring your next role into focus</DialogTitle>
        <DialogDescription className="mt-2 max-w-md">Drop your CV to rank jobs with our 3-Factor Hybrid Scoring Engine.</DialogDescription>

        <div
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`mt-7 flex min-h-52 cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed px-6 text-center transition ${dragging ? "border-emerald-300 bg-emerald-300/[0.07]" : "border-white/15 bg-white/[0.02] hover:border-white/25 hover:bg-white/[0.04]"}`}
        >
          <input ref={inputRef} type="file" accept="application/pdf,.pdf" className="hidden" onChange={(event) => acceptFile(event.target.files?.[0])} />
          {file ? (
            <>
              <div className="mb-3 flex size-12 items-center justify-center rounded-xl bg-indigo-300/10 text-indigo-200"><FileText className="size-5" /></div>
              <p className="max-w-full truncate text-sm font-medium text-zinc-100">{file.name}</p>
              <p className="mt-1 text-xs text-zinc-500">{(file.size / 1024 / 1024).toFixed(2)} MB · ready to analyze</p>
            </>
          ) : (
            <>
              <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-white/[0.05] text-zinc-300"><UploadCloud className="size-5" /></div>
              <p className="text-sm font-medium text-zinc-200">Drop your PDF here, or <span className="text-emerald-300">browse files</span></p>
              <p className="mt-2 text-xs text-zinc-600">PDF · Up to 12 MB</p>
            </>
          )}
        </div>
        <div className="mt-6 flex items-center justify-between gap-4">
          <p className="text-[11px] leading-relaxed text-zinc-600">Your CV is used to extract skills and rank matching roles.</p>
          <Button onClick={submit} disabled={!file || busy} className="shrink-0">
            {busy ? <><LoaderCircle className="size-4 animate-spin" /> Analyzing</> : "Analyze CV"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
