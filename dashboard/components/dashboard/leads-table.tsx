"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuCheckboxItem,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Search,
  SlidersHorizontal,
  ArrowUpDown,
  Upload,
  PieChart,
  Check,
  X,
  Clock,
  User,
  FileText,
  Calendar,
  Activity,
  Target,
  Cloud,
  Zap,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  CheckCheck,
  Trash2,
  XCircle,
  SearchX,
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  FormType,
  RequestStatus,
  RequestSource,
} from "@/mock-data/dashboard";
import { useDashboardStore } from "@/store/dashboard-store";
import { useDashboardRequests } from "@/hooks/use-dashboard-data";
import { RequestDetailDialog } from "./request-detail-dialog";
import { DocumentRequest } from "@/mock-data/dashboard";
import { exportCsv, exportExcel, showToast, copyToClipboard, openUrl } from "@/hooks/use-toast";
import { Skeleton } from "@/components/ui/skeleton";
import { API_DOCS } from "@/lib/constants";

type SortField = "name" | "formType" | "date" | "status" | "ocrConfidence";
type SortOrder = "asc" | "desc";

function getSortIcon(
  sortField: SortField,
  sortOrder: SortOrder,
  field: SortField
) {
  if (sortField !== field) return <ArrowUpDown className="size-3" />;
  return sortOrder === "asc" ? (
    <ArrowUp className="size-3" />
  ) : (
    <ArrowDown className="size-3" />
  );
}

export function FormTypeBadge({ formType }: { formType: FormType }) {
  const config: Record<
    FormType,
    { label: string; borderClass: string; textClass: string; bgGradient: string }
  > = {
    "แบบ 4": {
      label: "แบบ 4",
      borderClass: "border-blue-500/40",
      textClass: "text-blue-400",
      bgGradient:
        "linear-gradient(90deg, rgba(59, 130, 246, 0.12) 0%, rgba(59, 130, 246, 0.06) 30%, rgba(59, 130, 246, 0) 100%), linear-gradient(90deg, hsl(var(--card)) 0%, hsl(var(--card)) 100%)",
    },
    "แบบ 18": {
      label: "แบบ 18",
      borderClass: "border-violet-500/40",
      textClass: "text-violet-400",
      bgGradient:
        "linear-gradient(90deg, rgba(139, 92, 246, 0.12) 0%, rgba(139, 92, 246, 0.06) 30%, rgba(139, 92, 246, 0) 100%), linear-gradient(90deg, hsl(var(--card)) 0%, hsl(var(--card)) 100%)",
    },
    "แบบ 20": {
      label: "แบบ 20",
      borderClass: "border-cyan-500/40",
      textClass: "text-cyan-400",
      bgGradient:
        "linear-gradient(90deg, rgba(6, 182, 212, 0.12) 0%, rgba(6, 182, 212, 0.06) 30%, rgba(6, 182, 212, 0) 100%), linear-gradient(90deg, hsl(var(--card)) 0%, hsl(var(--card)) 100%)",
    },
  };

  const c = config[formType];
  return (
    <div
      className={`flex items-center gap-1 px-2 py-1 rounded-lg border ${c.borderClass} w-fit`}
      style={{ backgroundImage: c.bgGradient }}
    >
      <FileText className={`size-3.5 ${c.textClass}`} />
      <span className={`text-sm font-medium ${c.textClass}`}>{c.label}</span>
    </div>
  );
}

export function StatusBadge({ status }: { status: RequestStatus }) {
  const config: Record<
    RequestStatus,
    { icon: React.ReactNode; label: string; borderClass: string; textClass: string; bgGradient: string }
  > = {
    approved: {
      icon: <Check className="size-3.5 text-emerald-400" />,
      label: "อนุมัติ",
      borderClass: "border-emerald-500/40",
      textClass: "text-emerald-400",
      bgGradient:
        "linear-gradient(90deg, rgba(16, 185, 129, 0.12) 0%, rgba(16, 185, 129, 0.06) 30%, rgba(16, 185, 129, 0) 100%), linear-gradient(90deg, hsl(var(--card)) 0%, hsl(var(--card)) 100%)",
    },
    pending: {
      icon: <Clock className="size-3.5 text-amber-400" />,
      label: "รออนุมัติ",
      borderClass: "border-amber-500/40",
      textClass: "text-amber-400",
      bgGradient:
        "linear-gradient(90deg, rgba(245, 158, 11, 0.12) 0%, rgba(245, 158, 11, 0.06) 30%, rgba(245, 158, 11, 0) 100%), linear-gradient(90deg, hsl(var(--card)) 0%, hsl(var(--card)) 100%)",
    },
    rejected: {
      icon: <X className="size-3.5 text-red-400" />,
      label: "ปฏิเสธ",
      borderClass: "border-red-500/40",
      textClass: "text-red-400",
      bgGradient:
        "linear-gradient(90deg, rgba(239, 68, 68, 0.12) 0%, rgba(239, 68, 68, 0.06) 30%, rgba(239, 68, 68, 0) 100%), linear-gradient(90deg, hsl(var(--card)) 0%, hsl(var(--card)) 100%)",
    },
  };

  const c = config[status];
  return (
    <div
      className={`flex items-center gap-1 px-2 py-1 rounded-lg border ${c.borderClass} w-fit`}
      style={{ backgroundImage: c.bgGradient }}
    >
      {c.icon}
      <span className={`text-sm font-medium ${c.textClass}`}>{c.label}</span>
    </div>
  );
}

export function OcrScoreBadge({ score }: { score: number }) {
  const getScoreStyle = () => {
    if (score >= 93)
      return { barClass: "bg-emerald-500", textClass: "text-emerald-400" };
    if (score >= 90)
      return { barClass: "bg-cyan-500", textClass: "text-cyan-400" };
    return { barClass: "bg-amber-500", textClass: "text-amber-400" };
  };

  const { barClass, textClass } = getScoreStyle();

  return (
    <div className="flex items-center gap-2">
      <div className="relative w-12 h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all ${barClass}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className={`text-xs font-semibold min-w-[36px] ${textClass}`}>
        {score}%
      </span>
    </div>
  );
}

export function SourceBadge({ source }: { source: RequestSource }) {
  const sourceConfig: Record<
    RequestSource,
    { icon: React.ReactNode; label: string; bgClass: string; textClass: string }
  > = {
    "microsoft-forms": {
      icon: <FileText className="size-3" />,
      label: "MS Forms",
      bgClass: "bg-blue-500/10",
      textClass: "text-blue-400",
    },
    "power-automate": {
      icon: <Zap className="size-3" />,
      label: "PA Flow",
      bgClass: "bg-violet-500/10",
      textClass: "text-violet-400",
    },
  };

  const config = sourceConfig[source];
  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-1 rounded-md w-fit ${config.bgClass}`}
    >
      <span className={config.textClass}>{config.icon}</span>
      <span className={`text-xs font-medium ${config.textClass}`}>
        {config.label}
      </span>
    </div>
  );
}

export function HighlightText({ text, query }: { text: string; query: string }) {
  if (!query || query.length < 2) return <>{text}</>;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return <>{text}</>;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-amber-400/40 dark:bg-amber-400/50 text-inherit rounded-sm px-0.5">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

export function StepProgress({
  step,
  totalSteps,
  status,
}: {
  step: number;
  totalSteps: number;
  status?: string;
}) {
  const isRejected = status === "rejected";
  return (
    <div className="flex items-center gap-1.5">
      <div className="flex gap-0.5">
        {Array.from({ length: totalSteps }, (_, i) => (
          <div
            key={i}
            className={`size-1.5 rounded-full ${
              isRejected
                ? i < step ? "bg-red-400" : "bg-muted"
                : i < step ? "bg-primary" : "bg-muted"
            }`}
          />
        ))}
      </div>
      <span className="text-xs text-muted-foreground">
        {isRejected ? `ปฏิเสธขั้น ${step}` : `${step}/${totalSteps}`}
      </span>
    </div>
  );
}

export function LeadsTable() {
  const {
    searchQuery,
    formTypeFilter,
    statusFilter,
    sourceFilter,
    setSearchQuery,
    setFormTypeFilter,
    setStatusFilter,
    setSourceFilter,
    clearFilters,
  } = useDashboardStore();

  const [sortField, setSortField] = useState<SortField>("name");
  const [sortOrder, setSortOrder] = useState<SortOrder>("asc");
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [detailRequest, setDetailRequest] = useState<DocumentRequest | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [localSearch, setLocalSearch] = useState(searchQuery);
  const [bulkOverrides, setBulkOverrides] = useState<Record<string, DocumentRequest["status"]>>({});
  const debounceRef = useRef<NodeJS.Timeout>(undefined);

  const handleSearchChange = useCallback((value: string) => {
    setLocalSearch(value);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setSearchQuery(value), 300);
  }, [setSearchQuery]);

  // Sync local state when store is cleared externally (e.g. clearFilters)
  useEffect(() => {
    setLocalSearch(searchQuery);
  }, [searchQuery]);

  const { requests: documentRequests, loading: requestsLoading } = useDashboardRequests();

  // Apply bulk status overrides
  const effectiveRequests = useMemo(() => {
    if (Object.keys(bulkOverrides).length === 0) return documentRequests;
    return documentRequests.map((req) =>
      bulkOverrides[req.id] ? { ...req, status: bulkOverrides[req.id] } : req
    );
  }, [documentRequests, bulkOverrides]);

  const filteredAndSorted = useMemo(() => {
    const result = effectiveRequests.filter((req) => {
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

    result.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case "name":
          comparison = a.name.localeCompare(b.name, "th");
          break;
        case "formType":
          comparison = a.formType.localeCompare(b.formType);
          break;
        case "date":
          comparison = a.date.localeCompare(b.date);
          break;
        case "status":
          comparison = a.status.localeCompare(b.status);
          break;
        case "ocrConfidence":
          comparison = a.ocrConfidence - b.ocrConfidence;
          break;
      }
      return sortOrder === "asc" ? comparison : -comparison;
    });

    return result;
  }, [effectiveRequests, searchQuery, formTypeFilter, statusFilter, sourceFilter, sortField, sortOrder]);

  const totalPages = Math.max(1, Math.ceil(filteredAndSorted.length / itemsPerPage));

  // Reset to page 1 when any filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, formTypeFilter, statusFilter, sourceFilter]);

  const paginated = useMemo(() => {
    const safePage = Math.min(currentPage, totalPages);
    const startIndex = (safePage - 1) * itemsPerPage;
    return filteredAndSorted.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredAndSorted, currentPage, totalPages, itemsPerPage]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
    setCurrentPage(1);
  };

  const toggleSelectAll = () => {
    if (selectedItems.length === paginated.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(paginated.map((r) => r.id));
    }
  };

  const toggleSelectItem = (id: string) => {
    setSelectedItems((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const hasActiveFilters =
    searchQuery !== "" ||
    formTypeFilter !== "all" ||
    statusFilter !== "all" ||
    sourceFilter !== "all";

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    setSelectedItems([]);
  };

  const handleItemsPerPageChange = (value: string) => {
    setItemsPerPage(Number(value));
    setCurrentPage(1);
    setSelectedItems([]);
  };

  return (
    <div className="bg-card text-card-foreground rounded-xl border overflow-hidden">
      {/* ===== Header ===== */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-4 py-3.5 border-b">
        <div className="flex items-center gap-3">
          <h3 className="font-medium text-base">จัดการคำร้อง</h3>
          <div className="h-5 w-px bg-border hidden sm:block" />
          <div className="hidden sm:flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
              <Input
                placeholder="ค้นหาชื่อ, รหัสนิสิต, ID..."
                value={localSearch}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="pl-8 h-8 w-[220px] text-sm bg-muted/50 border-border/50"
              />
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 bg-muted/50 border-border/50"
                >
                  <SlidersHorizontal className="size-3.5" />
                  <span>กรอง</span>
                  {hasActiveFilters && (
                    <span className="size-1.5 rounded-full bg-primary" />
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-48">
                {/* — แบบฟอร์ม — */}
                <div className="px-2 py-1.5">
                  <p className="text-xs font-medium text-muted-foreground mb-1.5">
                    แบบฟอร์ม
                  </p>
                  <div className="space-y-1">
                    <DropdownMenuCheckboxItem
                      checked={formTypeFilter === "all"}
                      onCheckedChange={() => setFormTypeFilter("all")}
                    >
                      ทั้งหมด
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={formTypeFilter === "แบบ 4"}
                      onCheckedChange={() => setFormTypeFilter("แบบ 4")}
                    >
                      <FileText className="size-3 mr-1.5 text-blue-400" />
                      แบบ 4
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={formTypeFilter === "แบบ 18"}
                      onCheckedChange={() => setFormTypeFilter("แบบ 18")}
                    >
                      <FileText className="size-3 mr-1.5 text-violet-400" />
                      แบบ 18
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={formTypeFilter === "แบบ 20"}
                      onCheckedChange={() => setFormTypeFilter("แบบ 20")}
                    >
                      <FileText className="size-3 mr-1.5 text-cyan-400" />
                      แบบ 20
                    </DropdownMenuCheckboxItem>
                  </div>
                </div>
                <DropdownMenuSeparator />
                {/* — สถานะ — */}
                <div className="px-2 py-1.5">
                  <p className="text-xs font-medium text-muted-foreground mb-1.5">
                    สถานะ
                  </p>
                  <div className="space-y-1">
                    <DropdownMenuCheckboxItem
                      checked={statusFilter === "all"}
                      onCheckedChange={() => setStatusFilter("all")}
                    >
                      ทั้งหมด
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={statusFilter === "approved"}
                      onCheckedChange={() => setStatusFilter("approved")}
                    >
                      <Check className="size-3 mr-1.5 text-emerald-400" />
                      อนุมัติแล้ว
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={statusFilter === "pending"}
                      onCheckedChange={() => setStatusFilter("pending")}
                    >
                      <Clock className="size-3 mr-1.5 text-amber-400" />
                      รออนุมัติ
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={statusFilter === "rejected"}
                      onCheckedChange={() => setStatusFilter("rejected")}
                    >
                      <X className="size-3 mr-1.5 text-red-400" />
                      ปฏิเสธ
                    </DropdownMenuCheckboxItem>
                  </div>
                </div>
                <DropdownMenuSeparator />
                {/* — แหล่งที่มา — */}
                <div className="px-2 py-1.5">
                  <p className="text-xs font-medium text-muted-foreground mb-1.5">
                    แหล่งที่มา
                  </p>
                  <div className="space-y-1">
                    <DropdownMenuCheckboxItem
                      checked={sourceFilter === "all"}
                      onCheckedChange={() => setSourceFilter("all")}
                    >
                      ทั้งหมด
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={sourceFilter === "microsoft-forms"}
                      onCheckedChange={() =>
                        setSourceFilter("microsoft-forms")
                      }
                    >
                      <FileText className="size-3 mr-1.5 text-blue-400" />
                      MS Forms
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={sourceFilter === "power-automate"}
                      onCheckedChange={() =>
                        setSourceFilter("power-automate")
                      }
                    >
                      <Zap className="size-3 mr-1.5 text-violet-400" />
                      PA Flow
                    </DropdownMenuCheckboxItem>
                  </div>
                </div>
                {hasActiveFilters && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={clearFilters}>
                      ล้างตัวกรอง
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 bg-muted/50 border-border/50"
                >
                  <ArrowUpDown className="size-3.5" />
                  <span>เรียง</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem onClick={() => toggleSort("name")}>
                  ชื่อ{" "}
                  {sortField === "name" && (sortOrder === "asc" ? "↑" : "↓")}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => toggleSort("formType")}>
                  แบบฟอร์ม{" "}
                  {sortField === "formType" &&
                    (sortOrder === "asc" ? "↑" : "↓")}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => toggleSort("date")}>
                  วันที่{" "}
                  {sortField === "date" && (sortOrder === "asc" ? "↑" : "↓")}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => toggleSort("status")}>
                  สถานะ{" "}
                  {sortField === "status" &&
                    (sortOrder === "asc" ? "↑" : "↓")}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => toggleSort("ocrConfidence")}>
                  OCR{" "}
                  {sortField === "ocrConfidence" &&
                    (sortOrder === "asc" ? "↑" : "↓")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1.5 bg-muted/50 border-border/50"
              >
                <Upload className="size-3.5" />
                <span className="hidden sm:inline">ส่งออก</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => {
                const data = filteredAndSorted.map((r) => ({
                  ID: r.id,
                  ชื่อ: r.name,
                  รหัสนิสิต: r.studentId,
                  แบบฟอร์ม: r.formType,
                  รายวิชา: r.courses,
                  วันที่: r.date,
                  สถานะ: r.status,
                  OCR: r.ocrConfidence,
                  ขั้นตอน: `${r.step}/${r.totalSteps}`,
                  อาจารย์: r.advisor,
                  แหล่งที่มา: r.source,
                }));
                exportCsv(data, "document_requests");
              }}>ส่งออก CSV</DropdownMenuItem>
              <DropdownMenuItem onClick={() => {
                const data = filteredAndSorted.map((r) => ({
                  ID: r.id,
                  ชื่อ: r.name,
                  รหัสนิสิต: r.studentId,
                  แบบฟอร์ม: r.formType,
                  รายวิชา: r.courses,
                  วันที่: r.date,
                  สถานะ: r.status === "approved" ? "อนุมัติ" : r.status === "pending" ? "รออนุมัติ" : "ปฏิเสธ",
                  OCR: r.ocrConfidence,
                  ขั้นตอน: `${r.step}/${r.totalSteps}`,
                  อาจารย์: r.advisor,
                  แหล่งที่มา: r.source === "microsoft-forms" ? "MS Forms" : "PA Flow",
                }));
                exportExcel(data, "document_requests");
              }}>ส่งออก Excel</DropdownMenuItem>
              <DropdownMenuItem onClick={() => window.print()}>ส่งออก PDF</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="size-8 bg-muted/50 border-border/50"
              >
                <PieChart className="size-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => {
                const total = filteredAndSorted.length;
                const approved = filteredAndSorted.filter(r => r.status === "approved").length;
                const pending = filteredAndSorted.filter(r => r.status === "pending").length;
                const rejected = filteredAndSorted.filter(r => r.status === "rejected").length;
                showToast(`ทั้งหมด ${total} | อนุมัติ ${approved} | รอ ${pending} | ปฏิเสธ ${rejected}`, "info");
              }}>ดูสถิติ</DropdownMenuItem>
              <DropdownMenuItem onClick={() => {
                const f4 = filteredAndSorted.filter(r => r.formType === "แบบ 4").length;
                const f18 = filteredAndSorted.filter(r => r.formType === "แบบ 18").length;
                const f20 = filteredAndSorted.filter(r => r.formType === "แบบ 20").length;
                showToast(`แบบ 4: ${f4} | แบบ 18: ${f18} | แบบ 20: ${f20}`, "info");
              }}>การกระจายแบบฟอร์ม</DropdownMenuItem>
              <DropdownMenuItem onClick={() => {
                const total = filteredAndSorted.length;
                const approved = filteredAndSorted.filter(r => r.status === "approved").length;
                const rate = total > 0 ? ((approved / total) * 100).toFixed(1) : "0";
                showToast(`อัตราอนุมัติ: ${rate}% (${approved}/${total})`, "info");
              }}>อัตราอนุมัติ</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => openUrl(`${API_DOCS}#/Dashboard`)}>สร้างรายงาน</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* ===== Mobile filters ===== */}
      <div className="sm:hidden flex flex-wrap items-center gap-2 px-4 py-3 border-b">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
          <Input
            placeholder="ค้นหา..."
            value={localSearch}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-8 h-8 w-full text-sm bg-muted/50 border-border/50"
          />
        </div>
        {/* Mobile filter button */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="icon" className="size-8 shrink-0">
              <SlidersHorizontal className="size-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem className="text-xs text-muted-foreground" disabled>ประเภทแบบฟอร์ม</DropdownMenuItem>
            {(["all", "แบบ 4", "แบบ 18", "แบบ 20"] as const).map((f) => (
              <DropdownMenuCheckboxItem key={f} checked={formTypeFilter === f} onCheckedChange={() => setFormTypeFilter(f)}>
                {f === "all" ? "ทั้งหมด" : f}
              </DropdownMenuCheckboxItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-xs text-muted-foreground" disabled>สถานะ</DropdownMenuItem>
            {(["all", "approved", "pending", "rejected"] as const).map((s) => (
              <DropdownMenuCheckboxItem key={s} checked={statusFilter === s} onCheckedChange={() => setStatusFilter(s)}>
                {s === "all" ? "ทั้งหมด" : s === "approved" ? "อนุมัติ" : s === "pending" ? "รอ" : "ปฏิเสธ"}
              </DropdownMenuCheckboxItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-xs text-muted-foreground" disabled>เรียงตาม</DropdownMenuItem>
            {([["date", "วันที่"], ["name", "ชื่อ"], ["status", "สถานะ"], ["ocrConfidence", "OCR"]] as const).map(([field, label]) => (
              <DropdownMenuItem key={field} onClick={() => toggleSort(field as "date" | "name" | "status" | "ocrConfidence")}>
                {label} {sortField === field && (sortOrder === "asc" ? "↑" : "↓")}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* ===== Active Filter Chips ===== */}
      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-1.5 px-4 py-2 border-b bg-muted/20">
          <span className="text-xs text-muted-foreground mr-1">ตัวกรอง:</span>
          {formTypeFilter !== "all" && (
            <button onClick={() => setFormTypeFilter("all")} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-500 text-xs hover:bg-blue-500/20 transition-colors">
              {formTypeFilter}
              <X className="size-3" />
            </button>
          )}
          {statusFilter !== "all" && (
            <button onClick={() => setStatusFilter("all")} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-500 text-xs hover:bg-violet-500/20 transition-colors">
              {statusFilter === "approved" ? "อนุมัติ" : statusFilter === "pending" ? "รอ" : "ปฏิเสธ"}
              <X className="size-3" />
            </button>
          )}
          {sourceFilter !== "all" && (
            <button onClick={() => setSourceFilter("all")} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-500 text-xs hover:bg-cyan-500/20 transition-colors">
              {sourceFilter}
              <X className="size-3" />
            </button>
          )}
          {searchQuery && (
            <button onClick={() => { setSearchQuery(""); setLocalSearch(""); }} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 text-xs hover:bg-amber-500/20 transition-colors">
              &quot;{searchQuery}&quot;
              <X className="size-3" />
            </button>
          )}
          <button onClick={clearFilters} className="text-xs text-muted-foreground hover:text-foreground ml-1 underline underline-offset-2">
            ล้างทั้งหมด
          </button>
        </div>
      )}

      {/* ===== Table ===== */}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent bg-muted/30">
              <TableHead className="w-[180px]" aria-sort={sortField === "name" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>
                <div className="flex items-center gap-2">
                  <Checkbox
                    aria-label="เลือกทั้งหมด"
                    checked={
                      selectedItems.length === paginated.length &&
                      paginated.length > 0
                    }
                    onCheckedChange={toggleSelectAll}
                    className="border-border/50 bg-background/70"
                  />
                  <button
                    className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground"
                    onClick={() => toggleSort("name")}
                  >
                    <span>ชื่อนิสิต</span>
                    {getSortIcon(sortField, sortOrder, "name")}
                  </button>
                </div>
              </TableHead>
              <TableHead className="w-[90px]">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <FileText className="size-3.5" />
                  <span>แบบฟอร์ม</span>
                </div>
              </TableHead>
              <TableHead className="w-[160px]">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <User className="size-3.5" />
                  <span>รายวิชา</span>
                </div>
              </TableHead>
              <TableHead className="w-[80px]" aria-sort={sortField === "date" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>
                <button
                  className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground"
                  onClick={() => toggleSort("date")}
                >
                  <Calendar className="size-3.5" />
                  <span>วันที่</span>
                  {getSortIcon(sortField, sortOrder, "date")}
                </button>
              </TableHead>
              <TableHead className="w-[95px]" aria-sort={sortField === "status" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>
                <button
                  className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground"
                  onClick={() => toggleSort("status")}
                >
                  <Activity className="size-3.5" />
                  <span>สถานะ</span>
                  {getSortIcon(sortField, sortOrder, "status")}
                </button>
              </TableHead>
              <TableHead className="w-[90px]" aria-sort={sortField === "ocrConfidence" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>
                <button
                  className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground"
                  onClick={() => toggleSort("ocrConfidence")}
                >
                  <Target className="size-3.5" />
                  <span>OCR</span>
                  {getSortIcon(sortField, sortOrder, "ocrConfidence")}
                </button>
              </TableHead>
              <TableHead className="w-[85px]">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Cloud className="size-3.5" />
                  <span>ที่มา</span>
                </div>
              </TableHead>
              <TableHead className="w-[100px]">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Activity className="size-3.5" />
                  <span>ขั้นตอน</span>
                </div>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {requestsLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={`skel-${i}`} className="border-border/50">
                  <TableCell>
                    <div className="flex items-center gap-2.5">
                      <Skeleton className="size-4 rounded" />
                      <Skeleton className="size-6 rounded-full" />
                      <div className="space-y-1">
                        <Skeleton className="h-3.5 w-24" />
                        <Skeleton className="h-2.5 w-16" />
                      </div>
                    </div>
                  </TableCell>
                  <TableCell><Skeleton className="h-5 w-16 rounded-full" /></TableCell>
                  <TableCell><Skeleton className="h-3.5 w-28" /></TableCell>
                  <TableCell><Skeleton className="h-3.5 w-20" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-16 rounded-full" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-12 rounded-full" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-14 rounded-full" /></TableCell>
                  <TableCell><Skeleton className="h-3.5 w-16" /></TableCell>
                </TableRow>
              ))
            ) : paginated.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="h-40">
                  <div className="flex flex-col items-center justify-center gap-2 text-muted-foreground">
                    <SearchX className="size-10 opacity-30" />
                    <p className="text-sm font-medium">ไม่พบคำร้อง</p>
                    <p className="text-xs">ลองเปลี่ยนคำค้นหา หรือตัวกรอง</p>
                    {hasActiveFilters && (
                      <Button variant="outline" size="sm" className="mt-1 h-7 text-xs" onClick={clearFilters}>
                        ล้างตัวกรองทั้งหมด
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ) : null}
            {paginated.map((req) => (
              <TableRow key={req.id} className="border-border/50 cursor-pointer hover:bg-muted/30" onClick={() => { setDetailRequest(req); setDetailOpen(true); }}>
                <TableCell>
                  <div className="flex items-center gap-2.5">
                    <Checkbox
                      aria-label={`เลือก ${req.name}`}
                      checked={selectedItems.includes(req.id)}
                      onCheckedChange={() => toggleSelectItem(req.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="border-border/50 bg-background/70"
                    />
                    <Avatar className="size-6">
                      <AvatarImage src={req.avatar} />
                      <AvatarFallback className="text-xs">
                        {req.name[0]}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <span className="font-medium text-sm"><HighlightText text={req.name} query={searchQuery} /></span>
                      <p className="text-[10px] text-muted-foreground">
                        <HighlightText text={req.studentId} query={searchQuery} />
                      </p>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <FormTypeBadge formType={req.formType} />
                </TableCell>
                <TableCell className="max-w-[160px]">
                  <span className="text-sm truncate block">{req.courses}</span>
                </TableCell>
                <TableCell>
                  <span className="text-sm whitespace-nowrap">{req.date}</span>
                </TableCell>
                <TableCell>
                  <StatusBadge status={req.status} />
                </TableCell>
                <TableCell>
                  <OcrScoreBadge score={req.ocrConfidence} />
                </TableCell>
                <TableCell>
                  <SourceBadge source={req.source} />
                </TableCell>
                <TableCell>
                  <StepProgress step={req.step} totalSteps={req.totalSteps} status={req.status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <RequestDetailDialog request={detailRequest} open={detailOpen} onOpenChange={setDetailOpen} />

      {/* ===== Bulk Actions Bar ===== */}
      {selectedItems.length > 0 && (
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 border-t bg-primary/5">
          <span className="text-sm font-medium">
            เลือก {selectedItems.length} รายการ
          </span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="h-7 gap-1.5 text-xs" onClick={() => {
              const selected = filteredAndSorted.filter(r => selectedItems.includes(r.id));
              const data = selected.map(r => ({
                ID: r.id, ชื่อ: r.name, รหัสนิสิต: r.studentId, แบบฟอร์ม: r.formType,
                รายวิชา: r.courses, วันที่: r.date, สถานะ: r.status, OCR: r.ocrConfidence,
                ขั้นตอน: `${r.step}/${r.totalSteps}`, อาจารย์: r.advisor, แหล่งที่มา: r.source,
              }));
              exportCsv(data, `selected_${selectedItems.length}_requests`);
            }}>
              <Upload className="size-3" />
              ส่งออก
            </Button>
            <Button variant="outline" size="sm" className="h-7 gap-1.5 text-xs" onClick={() => {
              if (!confirm(`อนุมัติ ${selectedItems.length} รายการ?`)) return;
              setBulkOverrides((prev) => {
                const next = { ...prev };
                for (const id of selectedItems) next[id] = "approved";
                return next;
              });
              showToast(`อนุมัติ ${selectedItems.length} รายการสำเร็จ`, "success");
              setSelectedItems([]);
            }}>
              <CheckCheck className="size-3" />
              อนุมัติทั้งหมด
            </Button>
            <Button variant="outline" size="sm" className="h-7 gap-1.5 text-xs text-destructive hover:text-destructive" onClick={() => {
              if (!confirm(`ปฏิเสธ ${selectedItems.length} รายการ? การกระทำนี้ไม่สามารถย้อนกลับได้`)) return;
              setBulkOverrides((prev) => {
                const next = { ...prev };
                for (const id of selectedItems) next[id] = "rejected";
                return next;
              });
              showToast(`ปฏิเสธ ${selectedItems.length} รายการสำเร็จ`, "info");
              setSelectedItems([]);
            }}>
              <Trash2 className="size-3" />
              ปฏิเสธ
            </Button>
            <Button variant="ghost" size="icon" className="size-7" onClick={() => setSelectedItems([])}>
              <XCircle className="size-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* ===== Pagination ===== */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 border-t">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>
            แสดง {(currentPage - 1) * itemsPerPage + 1} ถึง{" "}
            {Math.min(currentPage * itemsPerPage, filteredAndSorted.length)}{" "}
            จาก {filteredAndSorted.length} รายการ
          </span>
          <div className="h-4 w-px bg-border hidden sm:block" />
          <div className="flex items-center gap-2">
            <span className="hidden sm:inline">แสดง</span>
            <Select
              value={itemsPerPage.toString()}
              onValueChange={handleItemsPerPageChange}
            >
              <SelectTrigger className="h-8 w-[70px] bg-muted/50">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="5">5</SelectItem>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
                <SelectItem value="50">50</SelectItem>
              </SelectContent>
            </Select>
            <span className="hidden sm:inline">ต่อหน้า</span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            className="size-8"
            aria-label="หน้าแรก"
            onClick={() => handlePageChange(1)}
            disabled={currentPage === 1}
          >
            <ChevronsLeft className="size-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="size-8"
            aria-label="หน้าก่อนหน้า"
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
          >
            <ChevronLeft className="size-4" />
          </Button>

          <div className="flex items-center gap-1 mx-2">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }
              return (
                <Button
                  key={pageNum}
                  variant={currentPage === pageNum ? "default" : "outline"}
                  size="icon"
                  className="size-8"
                  onClick={() => handlePageChange(pageNum)}
                >
                  {pageNum}
                </Button>
              );
            })}
          </div>

          <Button
            variant="outline"
            size="icon"
            className="size-8"
            aria-label="หน้าถัดไป"
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
          >
            <ChevronRight className="size-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="size-8"
            aria-label="หน้าสุดท้าย"
            onClick={() => handlePageChange(totalPages)}
            disabled={currentPage === totalPages}
          >
            <ChevronsRight className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
