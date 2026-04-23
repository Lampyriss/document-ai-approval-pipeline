import { create } from "zustand";
import { persist } from "zustand/middleware";
import { FormType, RequestStatus, RequestSource } from "@/mock-data/dashboard";

export type ViewMode = "table" | "kanban";
export type PageView = "dashboard" | "settings" | "activity";
export type DataMode = "auto" | "mock" | "live";

export interface NotificationSettings {
  newRequest: boolean;
  statusChange: boolean;
  teams: boolean;
  email: boolean;
}

interface DashboardStore {
  currentPage: PageView;
  viewMode: ViewMode;
  dataMode: DataMode;
  notifications: NotificationSettings;
  searchQuery: string;
  formTypeFilter: FormType | "all";
  statusFilter: RequestStatus | "all";
  sourceFilter: RequestSource | "all";
  setCurrentPage: (page: PageView) => void;
  setViewMode: (mode: ViewMode) => void;
  setDataMode: (mode: DataMode) => void;
  setNotifications: (patch: Partial<NotificationSettings>) => void;
  setSearchQuery: (query: string) => void;
  setFormTypeFilter: (filter: FormType | "all") => void;
  setStatusFilter: (filter: RequestStatus | "all") => void;
  setSourceFilter: (filter: RequestSource | "all") => void;
  clearFilters: () => void;
}

export const useDashboardStore = create<DashboardStore>()(
  persist(
    (set) => ({
      currentPage: "dashboard",
      viewMode: "table",
      dataMode: "auto",
      notifications: { newRequest: true, statusChange: true, teams: false, email: false },
      searchQuery: "",
      formTypeFilter: "all",
      statusFilter: "all",
      sourceFilter: "all",
      setCurrentPage: (page) => set({ currentPage: page }),
      setViewMode: (mode) => set({ viewMode: mode }),
      setDataMode: (mode) => set({ dataMode: mode }),
      setNotifications: (patch) =>
        set((state) => ({ notifications: { ...state.notifications, ...patch } })),
      setSearchQuery: (query) => set({ searchQuery: query }),
      setFormTypeFilter: (filter) => set({ formTypeFilter: filter }),
      setStatusFilter: (filter) => set({ statusFilter: filter }),
      setSourceFilter: (filter) => set({ sourceFilter: filter }),
      clearFilters: () =>
        set({
          searchQuery: "",
          formTypeFilter: "all",
          statusFilter: "all",
          sourceFilter: "all",
        }),
    }),
    {
      name: "dashboard-settings",
      partialize: (state) => ({
        dataMode: state.dataMode,
        viewMode: state.viewMode,
        notifications: state.notifications,
      }),
    }
  )
);
