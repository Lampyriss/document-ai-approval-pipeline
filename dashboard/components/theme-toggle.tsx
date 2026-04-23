"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

const CYCLE = ["light", "dark", "system"] as const;

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const next = () => {
    const idx = CYCLE.indexOf(theme as (typeof CYCLE)[number]);
    setTheme(CYCLE[(idx + 1) % CYCLE.length]);
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={next}
      aria-label={`ธีม: ${theme === "light" ? "สว่าง" : theme === "dark" ? "มืด" : "ระบบ"}`}
    >
      <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      <span className="sr-only">สลับธีม</span>
    </Button>
  );
}
