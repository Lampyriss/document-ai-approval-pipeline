"use client";

import { useMemo } from "react";
import {
  FileText,
  CheckCircle,
  Clock,
  XCircle,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useDashboardRequests } from "@/hooks/use-dashboard-data";

interface Activity {
  id: string;
  action: string;
  name: string;
  formType: string;
  time: string;
  icon: typeof FileText;
  color: string;
}

export function ActivityTimeline() {
  const { requests } = useDashboardRequests();

  const activities: Activity[] = useMemo(() => {
    // Take latest 10 requests (already sorted by date from API/mock)
    // Note: req.date is Thai-formatted ("28 ก.พ.") — new Date() can't parse it
    const sorted = requests.slice(0, 20);

    return sorted.map((req, i) => {
      const actions = [
        {
          action: "ส่งคำร้อง",
          icon: FileText,
          color: "text-blue-400 bg-blue-400/10",
        },
        {
          action: "อนุมัติแล้ว",
          icon: CheckCircle,
          color: "text-green-400 bg-green-400/10",
        },
        {
          action: "รออนุมัติ",
          icon: Clock,
          color: "text-amber-400 bg-amber-400/10",
        },
        {
          action: "ปฏิเสธ",
          icon: XCircle,
          color: "text-red-400 bg-red-400/10",
        },
        {
          action: "OCR สแกนเสร็จ",
          icon: Eye,
          color: "text-cyan-400 bg-cyan-400/10",
        },
      ];

      const statusAction =
        req.status === "approved"
          ? actions[1]
          : req.status === "rejected"
            ? actions[3]
            : actions[i % 2 === 0 ? 0 : 4];

      // Use raw ISO date if available, fallback to Thai date parsing
      const time = req.rawDate ? isoToTimeAgo(req.rawDate) : parseDateToTimeAgo(req.date);

      return {
        id: req.id,
        action: statusAction.action,
        name: req.name,
        formType: req.formType,
        time,
        icon: statusAction.icon,
        color: statusAction.color,
      };
    });
  }, [requests]);

  return (
    <div className="bg-card text-card-foreground rounded-xl border">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h3 className="text-sm font-medium">กิจกรรมล่าสุด</h3>
        <span className="text-xs text-muted-foreground">ล่าสุด</span>
      </div>

      <div className="p-3 space-y-0.5">
        {activities.map((activity, i) => (
          <div
            key={activity.id}
            className="flex items-start gap-3 px-2 py-2 rounded-lg hover:bg-muted/50 transition-colors"
          >
            {/* Icon + line */}
            <div className="flex flex-col items-center">
              <div className={cn("p-1.5 rounded-md", activity.color)}>
                <activity.icon className="size-3.5" />
              </div>
              {i < activities.length - 1 && (
                <div className="w-px h-6 bg-border mt-1" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <p className="text-sm leading-tight">
                <span className="font-medium">{activity.name}</span>{" "}
                <span className="text-muted-foreground">{activity.action}</span>
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-muted-foreground">
                  {activity.formType}
                </span>
                <span className="text-xs text-muted-foreground">·</span>
                <span className="text-xs text-muted-foreground">
                  {activity.time}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function isoToTimeAgo(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    const diffMs = Date.now() - d.getTime();
    const diffMin = Math.max(0, Math.floor(diffMs / 60000));
    if (diffMin < 1) return "เมื่อสักครู่";
    if (diffMin < 60) return `${diffMin} นาทีที่แล้ว`;
    const hours = Math.floor(diffMin / 60);
    if (hours < 24) return `${hours} ชั่วโมงที่แล้ว`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} วันที่แล้ว`;
    const months = Math.floor(days / 30);
    return `${months} เดือนที่แล้ว`;
  } catch {
    return isoStr;
  }
}

const thaiMonths: Record<string, number> = {
  "ม.ค.": 0, "ก.พ.": 1, "มี.ค.": 2, "เม.ย.": 3,
  "พ.ค.": 4, "มิ.ย.": 5, "ก.ค.": 6, "ส.ค.": 7,
  "ก.ย.": 8, "ต.ค.": 9, "พ.ย.": 10, "ธ.ค.": 11,
};

function parseDateToTimeAgo(dateStr: string): string {
  // Parse "28 ก.พ." or "28 ก.พ. 2569" format
  const parts = dateStr.match(/(\d+)\s+(\S+)/);
  if (!parts) return dateStr;
  const day = parseInt(parts[1]);
  // Strip trailing year or dots if present
  const monthKey = parts[2].replace(/\s.*$/, "");
  const month = thaiMonths[monthKey];
  if (month === undefined) return dateStr;

  const now = new Date();
  const date = new Date(now.getFullYear(), month, day);
  // If computed date is in the future, assume it was last year
  if (date.getTime() > now.getTime()) {
    date.setFullYear(date.getFullYear() - 1);
  }
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.max(0, Math.floor(diffMs / 60000));

  if (diffMin < 60) return `${Math.max(1, diffMin)} นาทีที่แล้ว`;
  const hours = Math.floor(diffMin / 60);
  if (hours < 24) return `${hours} ชั่วโมงที่แล้ว`;
  const days = Math.floor(hours / 24);
  return `${days} วันที่แล้ว`;
}
