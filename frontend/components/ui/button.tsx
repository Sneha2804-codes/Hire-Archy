import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/70 disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        default: "bg-gradient-to-r from-indigo-600 via-blue-600 to-violet-600 text-white shadow-[0_8px_26px_-12px_rgba(99,102,241,.65)] hover:-translate-y-0.5 hover:shadow-[0_12px_32px_-12px_rgba(99,102,241,.7)]",
        secondary: "border border-white/10 bg-white/[0.04] text-zinc-200 hover:bg-white/[0.08]",
        ghost: "text-zinc-400 hover:bg-white/[0.06] hover:text-white",
        outline: "border border-white/15 bg-transparent text-zinc-200 hover:border-emerald-300/35 hover:bg-emerald-300/[0.05]",
        danger: "bg-rose-500/10 text-rose-300 hover:bg-rose-500/15",
      },
      size: {
        default: "h-10 px-4",
        sm: "h-8 rounded-lg px-3 text-xs",
        lg: "h-12 px-5",
        icon: "size-9",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { asChild?: boolean };

export function Button({ className, variant = "default", size, asChild, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), variant === "default" && "brand-primary", className)} {...props} />;
}
