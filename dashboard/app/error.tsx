"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[Dashboard Error]", error);
  }, [error]);

  return (
    <div className="flex min-h-svh items-center justify-center bg-background p-4">
      <div className="flex flex-col items-center gap-4 text-center max-w-sm">
        <div className="p-3 rounded-full bg-destructive/10">
          <AlertTriangle className="size-8 text-destructive" />
        </div>
        <h2 className="text-lg font-semibold">เกิดข้อผิดพลาด</h2>
        <p className="text-sm text-muted-foreground">
          ระบบพบปัญหาที่ไม่คาดคิด กรุณาลองใหม่อีกครั้ง
        </p>
        {error.message && (
          <code className="text-xs bg-muted px-3 py-1.5 rounded-md max-w-full truncate">
            {error.message}
          </code>
        )}
        <Button onClick={reset} className="gap-2">
          <RotateCcw className="size-4" />
          ลองใหม่
        </Button>
      </div>
    </div>
  );
}
