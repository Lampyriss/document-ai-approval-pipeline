"use client";

import { useMemo, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  MoreHorizontal,
  Calendar,
  FileText,
  ExternalLink,
  Copy,
} from "lucide-react";
import { DocumentRequest } from "@/mock-data/dashboard";
import { useDashboardStore } from "@/store/dashboard-store";
import { useDashboardRequests } from "@/hooks/use-dashboard-data";
import {
  FormTypeBadge,
  OcrScoreBadge,
  SourceBadge,
  StepProgress,
} from "./leads-table";
import { RequestDetailDialog } from "./request-detail-dialog";
import { copyToClipboard, openUrl } from "@/hooks/use-toast";
import { SHAREPOINT_URL } from "@/lib/constants";
import { avatarColor } from "@/lib/utils";

interface KanbanColumn {
  id: string;
  title: string;
  color: string;
  borderColor: string;
  bgColor: string;
  dotColor: string;
}

const COLUMNS: KanbanColumn[] = [
  {
    id: "step1",
    title: "ส่งคำร้อง",
    color: "text-blue-400",
    borderColor: "border-blue-500/30",
    bgColor: "bg-blue-500/5",
    dotColor: "bg-blue-500",
  },
  {
    id: "step2",
    title: "ที่ปรึกษาพิจารณา",
    color: "text-violet-400",
    borderColor: "border-violet-500/30",
    bgColor: "bg-violet-500/5",
    dotColor: "bg-violet-500",
  },
  {
    id: "step3",
    title: "ผู้สอนพิจารณา",
    color: "text-cyan-400",
    borderColor: "border-cyan-500/30",
    bgColor: "bg-cyan-500/5",
    dotColor: "bg-cyan-500",
  },
  {
    id: "approved",
    title: "อนุมัติแล้ว",
    color: "text-emerald-400",
    borderColor: "border-emerald-500/30",
    bgColor: "bg-emerald-500/5",
    dotColor: "bg-emerald-500",
  },
  {
    id: "rejected",
    title: "ปฏิเสธ",
    color: "text-red-400",
    borderColor: "border-red-500/30",
    bgColor: "bg-red-500/5",
    dotColor: "bg-red-500",
  },
];

function getColumnId(req: DocumentRequest): string {
  if (req.status === "approved") return "approved";
  if (req.status === "rejected") return "rejected";
  if (req.step <= 1) return "step1";
  if (req.step === 2) return "step2";
  return "step3";
}

function RequestCard({ req, onViewDetail }: { req: DocumentRequest; onViewDetail: (req: DocumentRequest) => void }) {
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${req.name} — ${req.formType}`}
      className="bg-card border border-border/60 rounded-xl p-3.5 space-y-3 hover:border-border focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none transition-colors group cursor-pointer"
      onClick={() => onViewDetail(req)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onViewDetail(req); } }}
    >
      {/* Header: form badge + menu */}
      <div className="flex items-center justify-between">
        <FormTypeBadge formType={req.formType} />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              aria-label="เมนูเพิ่มเติม"
              className="size-6 flex items-center justify-center rounded-md opacity-0 group-hover:opacity-100 focus-visible:opacity-100 hover:bg-muted transition-all"
              onClick={(e) => e.stopPropagation()}
            >
              <MoreHorizontal className="size-3.5 text-muted-foreground" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onViewDetail(req); }}>
              <ExternalLink className="size-3.5 mr-2" />
              ดูรายละเอียด
            </DropdownMenuItem>
            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); copyToClipboard(req.id, "Request ID"); }}>
              <Copy className="size-3.5 mr-2" />
              คัดลอก ID
            </DropdownMenuItem>
            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openUrl(`${SHAREPOINT_URL}/Lists/FormRequests/DispForm.aspx?ID=${req.id.replace(/\D/g, "") || "0"}`); }}>
              <FileText className="size-3.5 mr-2" />
              ดูเอกสาร
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Student info */}
      <div>
        <p className="text-sm font-medium leading-tight">{req.name}</p>
        <p className="text-[11px] text-muted-foreground mt-0.5">
          {req.studentId}
        </p>
        {req.courses && req.courses !== "-" && (
          <p className="text-xs text-muted-foreground mt-1 truncate">
            {req.courses}
          </p>
        )}
      </div>

      {/* Date */}
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Calendar className="size-3" />
        <span>{req.date}</span>
      </div>

      {/* Progress + OCR */}
      <div className="flex items-center justify-between">
        <StepProgress step={req.step} totalSteps={req.totalSteps} status={req.status} />
        <OcrScoreBadge score={req.ocrConfidence} />
      </div>

      {/* Footer: advisor + source */}
      <div className="flex items-center justify-between pt-1 border-t border-border/40">
        <div className="flex items-center gap-1.5 min-w-0">
          <Avatar className="size-5 shrink-0">
            <AvatarImage
              src={`https://api.dicebear.com/9.x/initials/svg?seed=${encodeURIComponent(req.advisor)}&backgroundColor=${avatarColor(req.advisor)}`}
            />
            <AvatarFallback className="text-[9px]">
              {req.advisor[0]}
            </AvatarFallback>
          </Avatar>
          <span className="text-[11px] text-muted-foreground truncate">
            {req.advisor}
          </span>
        </div>
        <SourceBadge source={req.source} />
      </div>
    </div>
  );
}

export function KanbanBoard() {
  const { searchQuery, formTypeFilter, statusFilter, sourceFilter } =
    useDashboardStore();
  const { requests: documentRequests, loading: kanbanLoading } = useDashboardRequests();
  const [detailRequest, setDetailRequest] = useState<DocumentRequest | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const handleViewDetail = (req: DocumentRequest) => {
    setDetailRequest(req);
    setDetailOpen(true);
  };

  // Apply same filters as table
  const filtered = useMemo(() => {
    return documentRequests.filter((req) => {
      const matchesSearch =
        searchQuery === "" ||
        req.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        req.studentId.includes(searchQuery) ||
        req.id.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesFormType =
        formTypeFilter === "all" || req.formType === formTypeFilter;
      const matchesStatus =
        statusFilter === "all" || req.status === statusFilter;
      const matchesSource =
        sourceFilter === "all" || req.source === sourceFilter;

      return matchesSearch && matchesFormType && matchesStatus && matchesSource;
    });
  }, [documentRequests, searchQuery, formTypeFilter, statusFilter, sourceFilter]);

  // Group by column
  const grouped = useMemo(() => {
    const map: Record<string, DocumentRequest[]> = {};
    for (const col of COLUMNS) map[col.id] = [];
    for (const req of filtered) {
      const colId = getColumnId(req);
      if (map[colId]) map[colId].push(req);
    }
    return map;
  }, [filtered]);

  return (
    <div className="space-y-4">
      <RequestDetailDialog request={detailRequest} open={detailOpen} onOpenChange={setDetailOpen} />

      {/* Filter bar - simplified */}
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <span>
          {filtered.length} คำร้อง
        </span>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-3">
          {COLUMNS.map((col) => (
            <div key={col.id} className="flex items-center gap-1.5">
              <div className={`size-2 rounded-full ${col.dotColor}`} />
              <span className="text-xs">
                {col.title} ({grouped[col.id].length})
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Kanban columns */}
      <div className="flex gap-4 overflow-x-auto pb-4 -mx-4 px-4 sm:-mx-6 sm:px-6">
        {COLUMNS.map((col) => (
          <div
            key={col.id}
            className={`flex-shrink-0 w-[280px] sm:w-[300px] rounded-xl border ${col.borderColor} ${col.bgColor} flex flex-col max-h-[calc(100vh-320px)]`}
          >
            {/* Column header */}
            <div className="flex items-center justify-between px-3.5 py-3 border-b border-border/30">
              <div className="flex items-center gap-2">
                <div className={`size-2 rounded-full ${col.dotColor}`} />
                <h3 className={`text-sm font-medium ${col.color}`}>
                  {col.title}
                </h3>
              </div>
              <span className="text-xs text-muted-foreground bg-muted/50 px-2 py-0.5 rounded-full">
                {grouped[col.id].length}
              </span>
            </div>

            {/* Cards */}
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {kanbanLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <div key={`skel-${i}`} className="bg-card border rounded-lg p-3 space-y-2.5">
                    <div className="flex items-center gap-2">
                      <Skeleton className="size-6 rounded-full" />
                      <div className="space-y-1 flex-1">
                        <Skeleton className="h-3.5 w-24" />
                        <Skeleton className="h-2.5 w-16" />
                      </div>
                    </div>
                    <Skeleton className="h-5 w-16 rounded-full" />
                    <Skeleton className="h-3 w-full" />
                    <div className="flex justify-between">
                      <Skeleton className="h-3 w-20" />
                      <Skeleton className="h-3 w-12" />
                    </div>
                  </div>
                ))
              ) : grouped[col.id].length === 0 ? (
                <div className="flex items-center justify-center h-20 text-xs text-muted-foreground">
                  ไม่มีรายการ
                </div>
              ) : (
                grouped[col.id].map((req) => (
                  <RequestCard key={req.id} req={req} onViewDetail={handleViewDetail} />
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
