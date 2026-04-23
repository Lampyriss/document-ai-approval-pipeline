"use client";

import { useState } from "react";

export interface Toast {
  id: number;
  message: string;
  type: "success" | "info" | "error";
}

let toastId = 0;
let globalSetToasts: React.Dispatch<React.SetStateAction<Toast[]>> | null = null;

// Track paused toasts (hovered)
const pausedToasts = new Set<number>();

export function showToast(message: string, type: Toast["type"] = "success") {
  if (!globalSetToasts) return;
  const id = ++toastId;
  globalSetToasts((prev) => [...prev, { id, message, type }]);

  const scheduleRemove = () => {
    setTimeout(() => {
      if (pausedToasts.has(id)) {
        scheduleRemove();
        return;
      }
      globalSetToasts?.((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  };
  scheduleRemove();
}

export function pauseToast(id: number) {
  pausedToasts.add(id);
}

export function resumeToast(id: number) {
  pausedToasts.delete(id);
}

export function useToastState() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  globalSetToasts = setToasts;
  return toasts;
}

// Utility actions
export function copyToClipboard(text: string, label?: string) {
  navigator.clipboard.writeText(text).then(
    () => showToast(`${label || text} คัดลอกแล้ว`, "success"),
    () => showToast("ไม่สามารถคัดลอกได้", "error")
  );
}

export function openUrl(url: string) {
  window.open(url, "_blank", "noopener,noreferrer");
}

export function exportCsv(
  data: Record<string, unknown>[],
  filename: string
) {
  if (data.length === 0) {
    showToast("ไม่มีข้อมูลสำหรับส่งออก", "info");
    return;
  }
  const headers = Object.keys(data[0]);
  const csvContent = [
    "\uFEFF" + headers.join(","),
    ...data.map((row) =>
      headers
        .map((h) => {
          const val = String(row[h] ?? "");
          return val.includes(",") || val.includes('"')
            ? `"${val.replace(/"/g, '""')}"`
            : val;
        })
        .join(",")
    ),
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filename}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  showToast(`ส่งออก ${filename}.csv สำเร็จ`, "success");
}

export function exportExcel(
  data: Record<string, unknown>[],
  filename: string
) {
  if (data.length === 0) {
    showToast("ไม่มีข้อมูลสำหรับส่งออก", "info");
    return;
  }
  const headers = Object.keys(data[0]);
  // Tab-separated values with .xls extension — opens natively in Excel
  const tsvContent = [
    "\uFEFF" + headers.join("\t"),
    ...data.map((row) =>
      headers
        .map((h) => {
          const val = String(row[h] ?? "").replace(/\t/g, " ").replace(/\n/g, " ");
          return val;
        })
        .join("\t")
    ),
  ].join("\n");

  const blob = new Blob([tsvContent], { type: "application/vnd.ms-excel;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filename}.xls`;
  a.click();
  URL.revokeObjectURL(url);
  showToast(`ส่งออก ${filename}.xls สำเร็จ`, "success");
}
