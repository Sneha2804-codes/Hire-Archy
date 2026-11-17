"use client";

import { useEffect, useState } from "react";
import { Blend, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";

const THEMES = [
  { id: "urban", label: "Blended Urban", icon: Blend },
  { id: "light", label: "Light", icon: Sun },
  { id: "midnight", label: "Midnight", icon: Moon },
] as const;

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  return (
    <div className="theme-switcher" role="group" aria-label="Choose color theme">
      {THEMES.map(({ id, label, icon: Icon }) => {
        const active = mounted && theme === id;
        return (
          <button
            key={id}
            type="button"
            aria-label={`${label} theme`}
            aria-pressed={active}
            title={label}
            onClick={() => setTheme(id)}
            className={cn("theme-switcher-button", active && "is-active")}
          >
            <Icon className="size-3.5" />
            <span className="hidden xl:inline">{label === "Blended Urban" ? "Urban" : label}</span>
          </button>
        );
      })}
    </div>
  );
}
