"use client";

import { useMemo } from "react";
import { FileText, Star, BarChart3 } from "lucide-react";
import { useDashboardRequests } from "@/hooks/use-dashboard-data";
import { FormType } from "@/mock-data/dashboard";
import { cn } from "@/lib/utils";

const formConfig: Record<
  FormType,
  { label: string; desc: string; barBorder: string; barGradient: string; textColor: string }
> = {
  "แบบ 4": {
    label: "แบบ 4",
    desc: "ลงทะเบียนเรียนควบ",
    barBorder: "border-blue-500",
    barGradient: "bg-linear-to-r from-blue-500/40 via-blue-500/20 to-transparent",
    textColor: "text-blue-400",
  },
  "แบบ 18": {
    label: "แบบ 18",
    desc: "ขอคืนเงิน",
    barBorder: "border-violet-500",
    barGradient: "bg-linear-to-r from-violet-500/40 via-violet-500/20 to-transparent",
    textColor: "text-violet-400",
  },
  "แบบ 20": {
    label: "แบบ 20",
    desc: "ขอถอนรายวิชา",
    barBorder: "border-cyan-500",
    barGradient: "bg-linear-to-r from-cyan-500/40 via-cyan-500/20 to-transparent",
    textColor: "text-cyan-400",
  },
};

export function TopPerformers() {
  const { requests } = useDashboardRequests();

  const formCounts = useMemo(() => {
    const counts: Record<FormType, { total: number; approved: number; pending: number; rejected: number }> = {
      "แบบ 4": { total: 0, approved: 0, pending: 0, rejected: 0 },
      "แบบ 18": { total: 0, approved: 0, pending: 0, rejected: 0 },
      "แบบ 20": { total: 0, approved: 0, pending: 0, rejected: 0 },
    };
    for (const req of requests) {
      if (counts[req.formType]) {
        counts[req.formType].total++;
        counts[req.formType][req.status]++;
      }
    }
    return counts;
  }, [requests]);

  const sorted = useMemo(() => {
    return (Object.keys(formCounts) as FormType[]).sort(
      (a, b) => formCounts[b].total - formCounts[a].total
    );
  }, [formCounts]);

  const maxCount = useMemo(() => {
    return Math.max(...sorted.map((f) => formCounts[f].total), 1);
  }, [sorted, formCounts]);

  const totalRequests = requests.length;

  return (
    <div className="bg-card text-card-foreground rounded-lg border w-full lg:w-[332px] shrink-0">
      <div className="flex items-center justify-between p-4 border-b border-border/50">
        <h3 className="font-medium text-sm sm:text-base">
          ฟอร์มที่ส่งมากที่สุด
        </h3>
        <div className="flex items-center gap-1">
          <BarChart3 className="size-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">{totalRequests} ทั้งหมด</span>
        </div>
      </div>
      <div className="p-4 space-y-4">
        {sorted.map((formType, index) => {
          const config = formConfig[formType];
          const data = formCounts[formType];
          const progressWidth = (data.total / maxCount) * 100;
          const isFirst = index === 0;
          const pct = totalRequests > 0 ? ((data.total / totalRequests) * 100).toFixed(0) : "0";

          return (
            <div key={formType} className="space-y-2">
              <div className="flex items-center gap-3">
                <div className={cn("flex items-center justify-center size-10 rounded-lg border", config.barBorder + "/40", "bg-card")}>
                  <FileText className={cn("size-5", config.textColor)} />
                </div>
                <div className="flex-1 relative">
                  <div
                    className={cn(
                      "relative h-[42px] rounded-lg border overflow-hidden",
                      config.barBorder,
                      isFirst ? "border-solid" : "border-dashed"
                    )}
                  >
                    <div
                      className={cn(
                        "absolute inset-0 transition-all duration-300",
                        config.barGradient
                      )}
                      style={{
                        width: `${Math.max(progressWidth, 30)}%`,
                      }}
                    />
                    <div className="absolute left-2 top-1/2 -translate-y-1/2 flex items-center gap-1.5 bg-card/90 dark:bg-neutral-900/90 border border-border rounded-md px-2 py-1 shadow-sm">
                      {isFirst && (
                        <Star className="size-3.5 text-amber-400 fill-amber-400" />
                      )}
                      <span
                        className={cn(
                          "text-sm font-medium",
                          isFirst ? "text-foreground" : "text-muted-foreground"
                        )}
                      >
                        {data.total} คำร้อง ({pct}%)
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              {/* Sub-stats row */}
              <div className="flex items-center gap-3 pl-[52px] text-[11px] text-muted-foreground">
                <span>{config.label} — {config.desc}</span>
                <span className="ml-auto flex items-center gap-2">
                  <span className="text-emerald-400">{data.approved} อนุมัติ</span>
                  <span className="text-amber-400">{data.pending} รอ</span>
                  {data.rejected > 0 && <span className="text-red-400">{data.rejected} ปฏิเสธ</span>}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
