"use client";

import { useDashboardStats, useApiConnection } from "@/hooks/use-dashboard-data";
import {
  ClipboardList,
  CheckCircle,
  Clock,
  XCircle,
  Target,
  TrendingUp,
  TrendingDown,
  Wifi,
  WifiOff,
  Database,
  RefreshCw,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnimatedNumber } from "@/hooks/use-animated-number";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDashboardStore, type DataMode } from "@/store/dashboard-store";
import { showToast } from "@/hooks/use-toast";

function AnimatedValue({ value }: { value: string }) {
  const num = parseFloat(value);
  const isPercent = value.includes("%");
  const animated = useAnimatedNumber(isNaN(num) ? 0 : num);
  if (isNaN(num)) return <>{value}</>;
  return <>{animated}{isPercent ? "%" : ""}</>;
}

const MODE_LABELS: Record<DataMode, string> = {
  auto: "อัตโนมัติ",
  mock: "ข้อมูลตัวอย่าง",
  live: "API จริง",
};

function formatLastUpdated(date: Date | null): string {
  if (!date) return "";
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 10) return "เมื่อสักครู่";
  if (diffSec < 60) return `${diffSec} วินาทีที่แล้ว`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} นาทีที่แล้ว`;
  return date.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" });
}

export function StatsCards() {
  const { data, loading, lastUpdated } = useDashboardStats();
  const connection = useApiConnection();
  const { dataMode, setDataMode } = useDashboardStore();

  const handleSetMode = (mode: DataMode) => {
    setDataMode(mode);
    showToast(`โหมดข้อมูล: ${MODE_LABELS[mode]}`, "info");
  };

  const stats = [
    {
      title: "คำร้องทั้งหมด",
      value: data.totalRequests,
      change: data.totalRequestsChange,
      icon: ClipboardList,
      trend: "up" as const,
    },
    {
      title: "อนุมัติแล้ว",
      value: data.approved,
      change: data.approvedChange,
      icon: CheckCircle,
      trend: "up" as const,
    },
    {
      title: "รออนุมัติ",
      value: data.pending,
      change: data.pendingChange,
      icon: Clock,
      trend: "down" as const,
    },
    {
      title: "ปฏิเสธ",
      value: data.rejected,
      change: data.rejectedChange,
      icon: XCircle,
      trend: "down" as const,
    },
    {
      title: "OCR Accuracy",
      value: data.ocrAccuracy,
      extra: { active: data.activeFormCount },
      icon: Target,
    },
  ];

  return (
    <div className="space-y-2">
      {/* Data mode selector */}
      <div className="flex items-center gap-2 text-xs">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border/50 hover:bg-muted/50 transition-colors cursor-pointer">
              {dataMode === "mock" ? (
                <>
                  <Database className="size-3 text-amber-400" />
                  <span className="text-amber-400">Mock Data</span>
                </>
              ) : dataMode === "live" ? (
                data.isLive ? (
                  <>
                    <Wifi className="size-3 text-green-400" />
                    <span className="text-green-400">Live API</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="size-3 text-red-400" />
                    <span className="text-red-400">API ไม่พร้อม</span>
                  </>
                )
              ) : connection === "connected" ? (
                <>
                  <RefreshCw className="size-3 text-green-400" />
                  <span className="text-green-400">
                    {data.isLive ? "Auto — Live" : "Auto — Connected"}
                  </span>
                </>
              ) : connection === "disconnected" ? (
                <>
                  <RefreshCw className="size-3 text-amber-400" />
                  <span className="text-amber-400">Auto — Mock</span>
                </>
              ) : (
                <span className="text-muted-foreground">กำลังเชื่อมต่อ...</span>
              )}
              <ChevronDown className="size-3 text-muted-foreground ml-0.5" />
            </button>
          </DropdownMenuTrigger>
          {lastUpdated && data.isLive && (
            <span className="text-muted-foreground ml-2">
              อัปเดต: {formatLastUpdated(lastUpdated)}
            </span>
          )}
          <DropdownMenuContent align="start" className="w-64">
            <DropdownMenuItem onClick={() => handleSetMode("auto")} className="flex-col items-start gap-0.5">
              <div className="flex items-center gap-2 w-full">
                <RefreshCw className="size-3.5" />
                <span>อัตโนมัติ (Auto)</span>
                {dataMode === "auto" && <CheckCircle className="size-3.5 ml-auto text-green-500" />}
              </div>
              <span className="text-[10px] text-muted-foreground ml-5.5">ลอง API ก่อน ถ้าไม่ได้ใช้ข้อมูลตัวอย่าง</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleSetMode("mock")} className="flex-col items-start gap-0.5">
              <div className="flex items-center gap-2 w-full">
                <Database className="size-3.5" />
                <span>ข้อมูลตัวอย่าง (Mock)</span>
                {dataMode === "mock" && <CheckCircle className="size-3.5 ml-auto text-green-500" />}
              </div>
              <span className="text-[10px] text-muted-foreground ml-5.5">ใช้ข้อมูลจำลอง 47 รายการ</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleSetMode("live")} className="flex-col items-start gap-0.5">
              <div className="flex items-center gap-2 w-full">
                <Wifi className="size-3.5" />
                <span>API จริง (Live)</span>
                {dataMode === "live" && <CheckCircle className="size-3.5 ml-auto text-green-500" />}
              </div>
              <span className="text-[10px] text-muted-foreground ml-5.5">ดึงข้อมูลจาก API เท่านั้น</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {stats.map((stat, index) => (
          <div
            key={index}
            className="bg-card text-card-foreground rounded-xl border p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium">{stat.title}</span>
              <stat.icon className="size-4 text-muted-foreground" />
            </div>

            <div className="bg-muted/50 border rounded-lg p-4">
              <div className="flex items-center justify-between">
                {loading ? (
                  <Skeleton className="h-8 w-16" />
                ) : (
                  <span className="text-2xl sm:text-3xl font-medium tracking-tight">
                    <AnimatedValue value={stat.value} />
                  </span>
                )}

                <div className="flex items-center gap-3">
                  <div className="h-9 w-px bg-border" />

                  {loading ? (
                    <Skeleton className="h-5 w-12" />
                  ) : stat.change !== undefined && stat.trend ? (
                    <div
                      className={cn(
                        "flex items-center gap-1.5",
                        stat.trend === "up" ? "text-green-400" : "text-pink-400"
                      )}
                      style={{
                        textShadow:
                          stat.trend === "up"
                            ? "0 1px 6px rgba(68, 255, 118, 0.25)"
                            : "0 1px 6px rgba(255, 68, 193, 0.25)",
                      }}
                    >
                      {stat.trend === "up" ? (
                        <TrendingUp className="size-3.5" />
                      ) : (
                        <TrendingDown className="size-3.5" />
                      )}
                      <span className="text-sm font-medium">{stat.change}%</span>
                    </div>
                  ) : stat.extra ? (
                    <div className="text-sm font-medium">
                      <span className="text-foreground">{stat.extra.active}</span>{" "}
                      <span className="text-muted-foreground">แบบฟอร์ม</span>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
