import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & { tone?: "default" | "emerald" | "indigo" | "amber" | "rose" };

const tones = {
  default: "border-white/10 bg-white/[0.04] text-zinc-300",
  emerald: "border-emerald-300/20 bg-emerald-300/[0.09] text-emerald-200",
  indigo: "border-indigo-300/20 bg-indigo-300/[0.09] text-indigo-200",
  amber: "border-amber-300/20 bg-amber-300/[0.09] text-amber-200",
  rose: "border-rose-300/20 bg-rose-300/[0.09] text-rose-200",
};

export function Badge({ className, tone = "default", ...props }: BadgeProps) {
  return <span className={cn("inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium leading-none", tones[tone], className)} {...props} />;
}
