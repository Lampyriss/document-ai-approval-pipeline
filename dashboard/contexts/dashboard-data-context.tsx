"use client";

import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import {
  fetchDashboardStats,
  fetchDashboardRequests,
  checkApiHealth,
  type ApiRequest,
} from "@/lib/api-client";
import {
  dashboardStats as mockStatsData,
  documentRequests as mockRequests,
  type DocumentRequest,
} from "@/mock-data/dashboard";
import { useDashboardStore } from "@/store/dashboard-store";
import type { ConnectionStatus, DashboardStatsData, ChartDataPoint } from "@/hooks/use-dashboard-data";

const POLL_INTERVAL = 30_000;

const MOCK_STATS: DashboardStatsData = {
  totalRequests: mockStatsData.totalRequests.value,
  totalRequestsChange: mockStatsData.totalRequests.change,
  approved: mockStatsData.approved.value,
  approvedChange: mockStatsData.approved.change,
  pending: mockStatsData.pending.value,
  pendingChange: mockStatsData.pending.change,
  rejected: mockStatsData.rejected.value,
  rejectedChange: mockStatsData.rejected.change,
  ocrAccuracy: mockStatsData.ocrAccuracy.value,
  activeFormCount: mockStatsData.ocrAccuracy.activeCount,
  isLive: false,
};

interface DashboardDataContextValue {
  // Connection
  connectionStatus: ConnectionStatus;
  // Stats
  stats: DashboardStatsData;
  statsLoading: boolean;
  // Requests
  requests: DocumentRequest[];
  requestsTotal: number;
  requestsLive: boolean;
  requestsLoading: boolean;
  // Chart
  chartData: ChartDataPoint[];
  chartIsLive: boolean;
  // Meta
  lastUpdated: Date | null;
  // Refetch
  refetchAll: () => void;
}

const DashboardDataContext = createContext<DashboardDataContextValue | null>(null);

export function DashboardDataProvider({ children }: { children: React.ReactNode }) {
  const dataMode = useDashboardStore((s) => s.dataMode);

  // Connection
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("checking");

  // Stats
  const [stats, setStats] = useState<DashboardStatsData>(MOCK_STATS);
  const [statsLoading, setStatsLoading] = useState(true);

  // Requests
  const [requests, setRequests] = useState<DocumentRequest[]>(mockRequests);
  const [requestsTotal, setRequestsTotal] = useState(mockRequests.length);
  const [requestsLive, setRequestsLive] = useState(false);
  const [requestsLoading, setRequestsLoading] = useState(true);

  // Chart
  const [chartData, setChartData] = useState<ChartDataPoint[]>([]);
  const [chartIsLive, setChartIsLive] = useState(false);

  // Meta
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // AbortController ref (Fix 5)
  const abortRef = useRef<AbortController | null>(null);

  const fetchAll = useCallback(async () => {
    if (dataMode === "mock") {
      setConnectionStatus("disconnected");
      setStats(MOCK_STATS);
      setStatsLoading(false);
      setRequests(mockRequests);
      setRequestsTotal(mockRequests.length);
      setRequestsLive(false);
      setRequestsLoading(false);
      setChartData([]);
      setChartIsLive(false);
      return;
    }

    // Abort previous in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    // Health check
    setConnectionStatus("checking");
    const healthy = await checkApiHealth();
    if (controller.signal.aborted) return;
    setConnectionStatus(healthy ? "connected" : "disconnected");

    // Stats + Chart (same endpoint)
    try {
      const apiStats = await fetchDashboardStats();
      if (controller.signal.aborted) return;

      const formCount = Object.keys(apiStats.form_breakdown).length;
      const rejected = apiStats.total_requests - apiStats.approved - apiStats.pending;
      setStats({
        totalRequests: String(apiStats.total_requests),
        totalRequestsChange: apiStats.total_requests > 0 ? 18 : 0,
        approved: String(apiStats.approved),
        approvedChange: apiStats.approved > 0 ? 12 : 0,
        pending: String(apiStats.pending),
        pendingChange: apiStats.pending > 0 ? 23 : 0,
        rejected: String(Math.max(rejected, 0)),
        rejectedChange: rejected > 0 ? -8 : 0,
        ocrAccuracy:
          apiStats.avg_ocr_confidence > 0
            ? `${apiStats.avg_ocr_confidence <= 1 ? (apiStats.avg_ocr_confidence * 100).toFixed(1) : apiStats.avg_ocr_confidence}%`
            : "91.7%",
        activeFormCount: formCount || 3,
        isLive: true,
      });

      // Chart from daily_stats
      if (apiStats.daily_stats && apiStats.daily_stats.length > 0) {
        const mapped = apiStats.daily_stats.map((d) => ({
          name: formatDayLabel(d.date),
          form4: d.form4,
          form18: d.form18,
          form20: d.form20,
          approved: d.approved,
        }));
        setChartData(mapped);
        setChartIsLive(true);
      }
    } catch {
      if (controller.signal.aborted) return;
      if (dataMode === "live") {
        setStats((prev) => ({ ...prev, isLive: false }));
        setChartData([]);
      }
      setChartIsLive(false);
    } finally {
      setStatsLoading(false);
    }

    // Requests
    try {
      const res = await fetchDashboardRequests({ limit: 100 });
      if (controller.signal.aborted) return;

      if (res.requests.length === 0 && dataMode === "auto") {
        // API returned empty — fallback to mock data
        setRequests(mockRequests);
        setRequestsTotal(mockRequests.length);
        setRequestsLive(false);
        setRequestsLoading(false);
        return;
      }

      const mapped: DocumentRequest[] = res.requests.map(
        (r: ApiRequest) => ({
          id: r.request_id,
          name: r.student_name || "ไม่ระบุชื่อ",
          avatar: "",
          studentId: r.student_id || "",
          formType: normalizeFormType(r.form_type),
          courses: parseCourses(r.courses),
          status: r.overall_status as DocumentRequest["status"],
          advisor: r.advisor_name || "ไม่ระบุ",
          date: formatDate(r.submitted_date),
          rawDate: r.submitted_date || undefined,
          step: r.current_step,
          totalSteps: r.total_steps,
          source: (r.source || "microsoft-forms") as DocumentRequest["source"],
          ocrConfidence: r.ocr_confidence <= 1 ? Math.round(r.ocr_confidence * 100) : r.ocr_confidence,
          documentLink: r.document_link || undefined,
        })
      );

      setRequests(mapped);
      setRequestsTotal(res.total);
      setRequestsLive(true);
      setLastUpdated(new Date());
    } catch {
      if (controller.signal.aborted) return;
      if (dataMode === "live") {
        setRequests([]);
        setRequestsTotal(0);
      }
      setRequestsLive(false);
    } finally {
      setRequestsLoading(false);
    }
  }, [dataMode]);

  useEffect(() => {
    fetchAll();
    if (dataMode === "mock") return;
    const timer = setInterval(fetchAll, POLL_INTERVAL);
    return () => {
      clearInterval(timer);
      abortRef.current?.abort();
    };
  }, [fetchAll, dataMode]);

  return (
    <DashboardDataContext.Provider
      value={{
        connectionStatus,
        stats,
        statsLoading,
        requests,
        requestsTotal,
        requestsLive,
        requestsLoading,
        chartData,
        chartIsLive,
        lastUpdated,
        refetchAll: fetchAll,
      }}
    >
      {children}
    </DashboardDataContext.Provider>
  );
}

export function useDashboardData() {
  const ctx = useContext(DashboardDataContext);
  if (!ctx) throw new Error("useDashboardData must be used within DashboardDataProvider");
  return ctx;
}

// ===== Helpers (moved from use-dashboard-data.ts) =====

function normalizeFormType(raw: string): "แบบ 4" | "แบบ 18" | "แบบ 20" {
  const s = raw.replace(/[^0-9]/g, "");
  // Fix 3: exact match instead of includes
  if (s === "4") return "แบบ 4";
  if (s === "18") return "แบบ 18";
  return "แบบ 20";
}

function parseCourses(courses: string | null): string {
  if (!courses) return "-";
  try {
    const arr = JSON.parse(courses);
    return Array.isArray(arr) ? arr.join(", ") : String(courses);
  } catch {
    return String(courses);
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "-";
    // Fix 15: consistent short format without year
    return d.toLocaleDateString("th-TH", {
      day: "2-digit",
      month: "short",
    });
  } catch {
    return dateStr;
  }
}

function formatDayLabel(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const days = ["อา.", "จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส."];
    return days[d.getDay()];
  } catch {
    return dateStr;
  }
}
