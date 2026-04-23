// Backward-compatible hooks that now read from shared DashboardDataContext
// This eliminates 5 independent polling loops → 1 single shared data source

"use client";

import { useDashboardData } from "@/contexts/dashboard-data-context";

// Re-export types
export type ConnectionStatus = "connected" | "disconnected" | "checking";

export interface DashboardStatsData {
  totalRequests: string;
  totalRequestsChange: number;
  approved: string;
  approvedChange: number;
  pending: string;
  pendingChange: number;
  rejected: string;
  rejectedChange: number;
  ocrAccuracy: string;
  activeFormCount: number;
  isLive: boolean;
}

export interface ChartDataPoint {
  name: string;
  form4: number;
  form18: number;
  form20: number;
  approved: number;
}

// ===== Hooks (thin wrappers over context) =====

export function useApiConnection(): ConnectionStatus {
  const { connectionStatus } = useDashboardData();
  return connectionStatus;
}

export function useDashboardStats() {
  const { stats, statsLoading, lastUpdated, refetchAll } = useDashboardData();
  return { data: stats, loading: statsLoading, lastUpdated, refetch: refetchAll };
}

export function useDashboardRequests() {
  const { requests, requestsTotal, requestsLive, requestsLoading, refetchAll } = useDashboardData();
  return { requests, total: requestsTotal, isLive: requestsLive, loading: requestsLoading, refetch: refetchAll };
}

export function useDashboardChart() {
  const { chartData, chartIsLive, refetchAll } = useDashboardData();
  return { chartData, isLive: chartIsLive, refetch: refetchAll };
}
