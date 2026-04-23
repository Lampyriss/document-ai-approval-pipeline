"use client";

import { WelcomeSection } from "./header";
import { StatsCards } from "./stats-cards";
import { LeadsChart } from "./leads-chart";
import { TopPerformers } from "./top-performers";
import { LeadsTable } from "./leads-table";
import { KanbanBoard } from "./kanban-board";
import { ActivityTimeline } from "./activity-timeline";
import { SettingsPage } from "./settings-page";
import { useDashboardStore } from "@/store/dashboard-store";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";
import { TableProperties, Columns3 } from "lucide-react";
import { cn } from "@/lib/utils";

function ViewSwitcher() {
  const { viewMode, setViewMode } = useDashboardStore();

  const tabs = [
    { id: "table" as const, label: "ตาราง", icon: TableProperties },
    { id: "kanban" as const, label: "Kanban", icon: Columns3 },
  ];

  return (
    <div className="flex items-center gap-1 p-1 rounded-lg bg-muted/50 border border-border/50 w-fit">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => setViewMode(tab.id)}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all",
            viewMode === tab.id
              ? "bg-card text-foreground shadow-sm border border-border/50"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <tab.icon className="size-3.5" />
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
}

export function DashboardContent() {
  const { viewMode, currentPage } = useDashboardStore();
  useKeyboardShortcuts();

  if (currentPage === "settings") {
    return <SettingsPage />;
  }

  if (currentPage === "activity") {
    return (
      <main className="flex-1 overflow-auto p-4 sm:p-6 space-y-6 bg-background w-full">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">กิจกรรมล่าสุด</h2>
        </div>
        <ActivityTimeline />
      </main>
    );
  }

  return (
    <main className="flex-1 overflow-auto p-4 sm:p-6 space-y-6 bg-background w-full">
      <WelcomeSection />
      <StatsCards />

      {/* View Switcher */}
      <ViewSwitcher />

      {/* Conditional content */}
      {viewMode === "table" ? (
        <>
          <div className="flex flex-col lg:flex-row gap-4 sm:gap-6">
            <LeadsChart />
            <div className="flex flex-col gap-4 sm:gap-6 lg:w-[320px]">
              <TopPerformers />
            </div>
          </div>
          <LeadsTable />
        </>
      ) : (
        <KanbanBoard />
      )}
    </main>
  );
}
