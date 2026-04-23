"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { DocumentRequest } from "@/mock-data/dashboard";
import {
  FormTypeBadge,
  StatusBadge,
  OcrScoreBadge,
  SourceBadge,
  StepProgress,
} from "./leads-table";
import { Copy, ExternalLink, Calendar, User, BookOpen, Target, CheckCircle, XCircle, Clock, FileText } from "lucide-react";
import { copyToClipboard, openUrl } from "@/hooks/use-toast";
import { SHAREPOINT_URL } from "@/lib/constants";
import { avatarColor } from "@/lib/utils";

interface Props {
  request: DocumentRequest | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function ApprovalSteps({ step, totalSteps, status }: { step: number; totalSteps: number; status: string }) {
  const steps = [];
  const labels: Record<number, string[]> = {
    2: ["อาจารย์ที่ปรึกษา", "ฝ่ายทะเบียน"],
    3: ["อาจารย์ที่ปรึกษา", "อาจารย์ผู้สอน", "ฝ่ายทะเบียน"],
  };
  const stepLabels = labels[totalSteps] || Array.from({ length: totalSteps }, (_, i) => `ขั้นที่ ${i + 1}`);

  for (let i = 0; i < totalSteps; i++) {
    const isCompleted = i < step;
    const isCurrent = i === step;
    const isRejected = status === "rejected" && i === step - 1;

    let stepStatus: "approved" | "rejected" | "current" | "pending" = "pending";
    if (isRejected) stepStatus = "rejected";
    else if (isCompleted) stepStatus = "approved";
    else if (isCurrent) stepStatus = "current";

    steps.push({ label: stepLabels[i], status: stepStatus, index: i });
  }

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground mb-2">ขั้นตอนการอนุมัติ</p>
      {steps.map((s) => (
        <div key={s.index} className="flex items-center gap-2.5 py-1">
          {s.status === "approved" ? (
            <CheckCircle className="size-4 text-emerald-500 shrink-0" />
          ) : s.status === "rejected" ? (
            <XCircle className="size-4 text-red-500 shrink-0" />
          ) : s.status === "current" ? (
            <Clock className="size-4 text-amber-500 shrink-0 animate-pulse" />
          ) : (
            <div className="size-4 rounded-full border-2 border-muted shrink-0" />
          )}
          <span className={`text-sm ${s.status === "pending" ? "text-muted-foreground" : ""}`}>
            {s.label}
          </span>
          <span className="text-xs text-muted-foreground ml-auto">
            {s.status === "approved" ? "อนุมัติ" : s.status === "rejected" ? "ปฏิเสธ" : s.status === "current" ? "รอพิจารณา" : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

export function RequestDetailDialog({ request, open, onOpenChange }: Props) {
  if (!request) return null;

  const rows = [
    { label: "Request ID", value: request.id, icon: Target },
    { label: "รหัสนิสิต", value: request.studentId, icon: User },
    { label: "รายวิชา", value: request.courses, icon: BookOpen },
    { label: "วันที่ส่ง", value: request.date, icon: Calendar },
  ];

  const reqNum = request.id.replace(/\D/g, "") || "0";
  const docLink = request.documentLink
    || `${SHAREPOINT_URL}/Approved_Documents/Forms/AllItems.aspx?id=${encodeURIComponent(`/sites/DocumentAIProject/Approved_Documents/REQ_${reqNum}_${request.formType}`)}`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            รายละเอียดคำร้อง
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5">
          {/* Student + Form Type */}
          <div className="flex items-start gap-3">
            <Avatar className="size-10">
              <AvatarImage
                src={`https://api.dicebear.com/9.x/initials/svg?seed=${encodeURIComponent(request.name)}&backgroundColor=3b82f6`}
              />
              <AvatarFallback>{request.name[0]}</AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="font-medium">{request.name}</p>
              <p className="text-sm text-muted-foreground">{request.studentId}</p>
            </div>
            <FormTypeBadge formType={request.formType} />
          </div>

          {/* Info rows */}
          <div className="space-y-3 bg-muted/30 rounded-lg p-3.5 border border-border/50">
            {rows.map((row) => (
              <div key={row.label} className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <row.icon className="size-3.5" />
                  <span>{row.label}</span>
                </div>
                <span className="text-sm font-medium text-right truncate max-w-[200px]">
                  {row.value || "-"}
                </span>
              </div>
            ))}
          </div>

          {/* Status + Progress */}
          <div className="flex items-center justify-between">
            <StatusBadge status={request.status} />
            <StepProgress step={request.step} totalSteps={request.totalSteps} status={request.status} />
          </div>

          {/* Approval History */}
          <div className="bg-muted/30 rounded-lg p-3.5 border border-border/50">
            <ApprovalSteps step={request.step} totalSteps={request.totalSteps} status={request.status} />
          </div>

          {/* OCR + Source */}
          <div className="flex items-center justify-between">
            <OcrScoreBadge score={request.ocrConfidence} />
            <SourceBadge source={request.source} />
          </div>

          {/* Advisor */}
          <div className="flex items-center gap-2 pt-2 border-t border-border/50">
            <Avatar className="size-6">
              <AvatarImage
                src={`https://api.dicebear.com/9.x/initials/svg?seed=${encodeURIComponent(request.advisor)}&backgroundColor=${avatarColor(request.advisor)}`}
              />
              <AvatarFallback className="text-[9px]">{request.advisor[0]}</AvatarFallback>
            </Avatar>
            <span className="text-sm text-muted-foreground">
              อาจารย์ที่ปรึกษา: <span className="text-foreground">{request.advisor}</span>
            </span>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1 gap-1.5"
              onClick={() => copyToClipboard(request.id, "Request ID")}
            >
              <Copy className="size-3.5" />
              คัดลอก ID
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex-1 gap-1.5"
              onClick={() =>
                openUrl(
                  `${SHAREPOINT_URL}/Lists/FormRequests/DispForm.aspx?ID=${request.id.replace(/\D/g, "") || "0"}`
                )
              }
            >
              <ExternalLink className="size-3.5" />
              SharePoint
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex-1 gap-1.5"
              onClick={() => openUrl(docLink)}
            >
              <FileText className="size-3.5" />
              เอกสาร
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
