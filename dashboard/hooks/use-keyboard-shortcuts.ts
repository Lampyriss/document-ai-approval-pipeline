"use client";

import { useEffect } from "react";
import { useTheme } from "next-themes";
import { useDashboardStore, type DataMode } from "@/store/dashboard-store";
import { showToast } from "@/hooks/use-toast";

const DATA_MODES: DataMode[] = ["auto", "mock", "live"];
const DATA_MODE_LABELS: Record<DataMode, string> = {
  auto: "อัตโนมัติ",
  mock: "ข้อมูลตัวอย่าง",
  live: "API จริง",
};

export function useKeyboardShortcuts() {
  const { setTheme, theme } = useTheme();
  const { viewMode, setViewMode, clearFilters, searchQuery } =
    useDashboardStore();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;

      // Esc — clear filters or blur input
      if (e.key === "Escape") {
        if (isInput) {
          (target as HTMLInputElement).blur();
          return;
        }
        if (searchQuery !== "") {
          clearFilters();
        }
        return;
      }

      // Skip shortcuts when typing in inputs
      if (isInput) return;

      // / — focus search
      if (e.key === "/") {
        e.preventDefault();
        const searchInput = document.querySelector<HTMLInputElement>(
          'input[placeholder*="ค้นหา"]'
        );
        searchInput?.focus();
        return;
      }

      // k — toggle view
      if (e.key === "k") {
        const next = viewMode === "table" ? "kanban" : "table";
        setViewMode(next);
        showToast(`สลับเป็นมุมมอง ${next === "table" ? "ตาราง" : "Kanban"}`, "info");
        return;
      }

      // t — cycle theme (light → dark → system)
      if (e.key === "t") {
        const THEMES = ["light", "dark", "system"] as const;
        const idx = THEMES.indexOf(theme as (typeof THEMES)[number]);
        setTheme(THEMES[(idx + 1) % THEMES.length]);
        return;
      }

      // d — cycle data mode (read from store on-demand to avoid dep array size change)
      if (e.key === "d") {
        const { dataMode, setDataMode } = useDashboardStore.getState();
        const next = DATA_MODES[(DATA_MODES.indexOf(dataMode) + 1) % DATA_MODES.length];
        setDataMode(next);
        showToast(`โหมดข้อมูล: ${DATA_MODE_LABELS[next]}`, "info");
        return;
      }

      // s — toggle settings page
      if (e.key === "s") {
        const { currentPage, setCurrentPage } = useDashboardStore.getState();
        setCurrentPage(currentPage === "settings" ? "dashboard" : "settings");
        return;
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [viewMode, setViewMode, setTheme, theme, clearFilters, searchQuery]);
}
