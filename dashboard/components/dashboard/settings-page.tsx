"use client";

import { useState } from "react";
import { useTheme } from "next-themes";
import {
  Settings,
  Bell,
  Plug,
  Keyboard,
  Info,
  ArrowLeft,
  Sun,
  Moon,
  Monitor,
  ExternalLink,
  CheckCircle,
  XCircle,
  Loader2,
  RefreshCw,
  Database,
  Wifi,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useDashboardStore, type DataMode } from "@/store/dashboard-store";
import { useApiConnection } from "@/hooks/use-dashboard-data";
import { showToast, openUrl } from "@/hooks/use-toast";
import { checkApiHealth } from "@/lib/api-client";
import {
  APP_VERSION,
  API_DOCS,
  FORMS_URL,
  SHAREPOINT_URL,
  POWER_AUTOMATE_URL,
} from "@/lib/constants";

type Section = "general" | "notifications" | "connections" | "shortcuts" | "about";

const sections: { id: Section; label: string; icon: typeof Settings }[] = [
  { id: "general", label: "ทั่วไป", icon: Settings },
  { id: "notifications", label: "การแจ้งเตือน", icon: Bell },
  { id: "connections", label: "API & เชื่อมต่อ", icon: Plug },
  { id: "shortcuts", label: "คีย์ลัด", icon: Keyboard },
  { id: "about", label: "เกี่ยวกับ", icon: Info },
];

export function SettingsPage() {
  const [activeSection, setActiveSection] = useState<Section>("general");
  const { setCurrentPage } = useDashboardStore();

  return (
    <main className="flex-1 overflow-auto p-4 sm:p-6 bg-background w-full">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Button
          variant="ghost"
          size="icon"
          className="size-8"
          onClick={() => setCurrentPage("dashboard")}
        >
          <ArrowLeft className="size-4" />
        </Button>
        <div>
          <h1 className="text-lg font-semibold">ตั้งค่าระบบ</h1>
          <p className="text-sm text-muted-foreground">
            จัดการการตั้งค่าระบบและการเชื่อมต่อ
          </p>
        </div>
      </div>

      {/* Layout */}
      <div className="flex flex-col md:flex-row gap-6">
        {/* Sidebar nav */}
        <nav className="md:w-[200px] shrink-0">
          <div className="flex md:flex-col gap-1 overflow-x-auto md:overflow-x-visible pb-2 md:pb-0">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors",
                  activeSection === section.id
                    ? "bg-card text-foreground border shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                )}
              >
                <section.icon className="size-4" />
                {section.label}
              </button>
            ))}
          </div>
        </nav>

        {/* Content */}
        <div className="flex-1 max-w-2xl">
          <div className="bg-card border rounded-xl p-6">
            {activeSection === "general" && <GeneralSection />}
            {activeSection === "notifications" && <NotificationsSection />}
            {activeSection === "connections" && <ConnectionsSection />}
            {activeSection === "shortcuts" && <ShortcutsSection />}
            {activeSection === "about" && <AboutSection />}
          </div>
        </div>
      </div>
    </main>
  );
}

// ===== General Section =====

function GeneralSection() {
  const { theme, setTheme } = useTheme();
  const { viewMode, setViewMode } = useDashboardStore();

  const themes = [
    { id: "light", label: "สว่าง", icon: Sun },
    { id: "dark", label: "มืด", icon: Moon },
    { id: "system", label: "ตามระบบ", icon: Monitor },
  ];

  const views = [
    { id: "table" as const, label: "ตาราง" },
    { id: "kanban" as const, label: "Kanban" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-medium">ทั่วไป</h2>
        <p className="text-sm text-muted-foreground mt-1">
          ตั้งค่าพื้นฐานของระบบ
        </p>
      </div>

      <Separator />

      {/* Theme */}
      <SettingRow label="ธีม" description="เลือกธีมการแสดงผล">
        <div className="flex gap-2">
          {themes.map((t) => (
            <button
              key={t.id}
              onClick={() => setTheme(t.id)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border transition-colors",
                theme === t.id
                  ? "bg-foreground text-background border-foreground"
                  : "bg-card text-muted-foreground border-border hover:text-foreground"
              )}
            >
              <t.icon className="size-3.5" />
              {t.label}
            </button>
          ))}
        </div>
      </SettingRow>

      <Separator />

      {/* Default View */}
      <SettingRow label="มุมมองเริ่มต้น" description="เลือกมุมมองหลักของ Dashboard">
        <div className="flex gap-2">
          {views.map((v) => (
            <button
              key={v.id}
              onClick={() => setViewMode(v.id)}
              className={cn(
                "px-3 py-1.5 rounded-md text-sm border transition-colors",
                viewMode === v.id
                  ? "bg-foreground text-background border-foreground"
                  : "bg-card text-muted-foreground border-border hover:text-foreground"
              )}
            >
              {v.label}
            </button>
          ))}
        </div>
      </SettingRow>

      <Separator />

      {/* Language */}
      <SettingRow label="ภาษา" description="เลือกภาษาของระบบ">
        <div className="flex items-center gap-2">
          <span className="text-sm">ไทย</span>
          <Badge variant="secondary" className="text-[10px]">
            เร็วๆ นี้
          </Badge>
        </div>
      </SettingRow>
    </div>
  );
}

// ===== Notifications Section =====

function NotificationsSection() {
  const { notifications, setNotifications } = useDashboardStore();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-medium">การแจ้งเตือน</h2>
        <p className="text-sm text-muted-foreground mt-1">
          ตั้งค่าการแจ้งเตือนของระบบ
        </p>
      </div>

      <Separator />

      <SettingRow
        label="คำร้องใหม่"
        description="แจ้งเตือนเมื่อมีคำร้องใหม่เข้ามา"
      >
        <Switch checked={notifications.newRequest} onCheckedChange={(v) => setNotifications({ newRequest: v })} />
      </SettingRow>

      <Separator />

      <SettingRow
        label="สถานะอนุมัติ"
        description="แจ้งเตือนเมื่อสถานะคำร้องเปลี่ยน"
      >
        <Switch checked={notifications.statusChange} onCheckedChange={(v) => setNotifications({ statusChange: v })} />
      </SettingRow>

      <Separator />

      <SettingRow
        label="แจ้งเตือนผ่าน Teams"
        description="ส่งการแจ้งเตือนไปที่ Microsoft Teams"
      >
        <Switch checked={notifications.teams} onCheckedChange={(v) => setNotifications({ teams: v })} />
      </SettingRow>

      <Separator />

      <SettingRow
        label="แจ้งเตือนผ่าน Email"
        description="ส่งการแจ้งเตือนไปที่อีเมล"
      >
        <Switch checked={notifications.email} onCheckedChange={(v) => setNotifications({ email: v })} />
      </SettingRow>
    </div>
  );
}

// ===== Connections Section =====

const dataModes: { id: DataMode; label: string; icon: typeof RefreshCw }[] = [
  { id: "auto", label: "อัตโนมัติ", icon: RefreshCw },
  { id: "mock", label: "ตัวอย่าง", icon: Database },
  { id: "live", label: "API จริง", icon: Wifi },
];

function ConnectionsSection() {
  const connection = useApiConnection();
  const { dataMode, setDataMode } = useDashboardStore();
  const [testing, setTesting] = useState(false);

  const handleTestConnection = async () => {
    setTesting(true);
    const ok = await checkApiHealth();
    setTesting(false);
    if (ok) {
      showToast("เชื่อมต่อ API สำเร็จ", "success");
    } else {
      showToast("ไม่สามารถเชื่อมต่อ API ได้", "error");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-medium">API & การเชื่อมต่อ</h2>
        <p className="text-sm text-muted-foreground mt-1">
          ตั้งค่าการเชื่อมต่อกับ OCR API
        </p>
      </div>

      <Separator />

      {/* Data Mode */}
      <SettingRow label="โหมดข้อมูล" description="เลือกแหล่งข้อมูลที่ใช้แสดงผล">
        <div className="flex gap-2">
          {dataModes.map((m) => (
            <button
              key={m.id}
              onClick={() => setDataMode(m.id)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border transition-colors",
                dataMode === m.id
                  ? "bg-foreground text-background border-foreground"
                  : "bg-card text-muted-foreground border-border hover:text-foreground"
              )}
            >
              <m.icon className="size-3.5" />
              {m.label}
            </button>
          ))}
        </div>
      </SettingRow>

      <Separator />

      {/* API URL */}
      <SettingRow label="API URL" description="URL ของ Document AI API">
        <Input
          value={process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"}
          readOnly
          className="max-w-sm text-sm bg-muted/50"
        />
      </SettingRow>

      <Separator />

      {/* Connection Status */}
      <SettingRow label="สถานะการเชื่อมต่อ" description="สถานะปัจจุบันของ API">
        <div className="flex items-center gap-2">
          {connection === "connected" ? (
            <>
              <CheckCircle className="size-4 text-green-500" />
              <span className="text-sm text-green-500">เชื่อมต่อแล้ว</span>
            </>
          ) : connection === "disconnected" ? (
            <>
              <XCircle className="size-4 text-red-500" />
              <span className="text-sm text-red-500">ไม่สามารถเชื่อมต่อ</span>
            </>
          ) : (
            <>
              <Loader2 className="size-4 animate-spin text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                กำลังตรวจสอบ...
              </span>
            </>
          )}
        </div>
      </SettingRow>

      <Separator />

      {/* Test Connection */}
      <SettingRow
        label="ทดสอบการเชื่อมต่อ"
        description="ตรวจสอบว่า API พร้อมใช้งาน"
      >
        <Button
          variant="outline"
          size="sm"
          onClick={handleTestConnection}
          disabled={testing || dataMode === "mock"}
        >
          {testing ? (
            <Loader2 className="size-3.5 animate-spin mr-1.5" />
          ) : (
            <Plug className="size-3.5 mr-1.5" />
          )}
          {testing ? "กำลังทดสอบ..." : "ทดสอบ"}
        </Button>
      </SettingRow>

      <Separator />

      {/* Auto Refresh */}
      <SettingRow
        label="รีเฟรชอัตโนมัติ"
        description="ระบบจะดึงข้อมูลใหม่จาก API อัตโนมัติ"
      >
        <span className="text-sm text-muted-foreground">
          {dataMode === "mock" ? "ปิดใช้งาน (โหมดตัวอย่าง)" : "ทุก 30 วินาที"}
        </span>
      </SettingRow>
    </div>
  );
}

// ===== Shortcuts Section =====

const shortcuts = [
  { key: "/", description: "ค้นหาคำร้อง" },
  { key: "k", description: "สลับมุมมอง ตาราง / Kanban" },
  { key: "t", description: "สลับธีม สว่าง / มืด / ระบบ" },
  { key: "d", description: "สลับโหมดข้อมูล (อัตโนมัติ / ตัวอย่าง / API จริง)" },
  { key: "s", description: "เปิด/ปิด หน้าตั้งค่า" },
  { key: "Esc", description: "ล้าง filter / ปิด dialog" },
];

function ShortcutsSection() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-medium">คีย์ลัด</h2>
        <p className="text-sm text-muted-foreground mt-1">
          ใช้คีย์ลัดเพื่อเข้าถึงฟังก์ชันต่างๆ ได้เร็วขึ้น
        </p>
      </div>

      <Separator />

      <div className="space-y-3">
        {shortcuts.map((s) => (
          <div key={s.key} className="flex items-center justify-between py-1">
            <span className="text-sm">{s.description}</span>
            <kbd className="inline-flex items-center justify-center min-w-[28px] h-7 px-2 rounded-md border bg-muted text-xs font-mono font-medium">
              {s.key}
            </kbd>
          </div>
        ))}
      </div>
    </div>
  );
}

// ===== About Section =====

function AboutSection() {
  const links = [
    { label: "API Documentation", url: API_DOCS },
    { label: "Microsoft Forms (Example)", url: FORMS_URL },
    { label: "SharePoint Site (Example)", url: SHAREPOINT_URL },
    { label: "Power Automate", url: POWER_AUTOMATE_URL },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-medium">เกี่ยวกับระบบ</h2>
        <p className="text-sm text-muted-foreground mt-1">
          ข้อมูลเกี่ยวกับระบบจัดการคำร้องเอกสาร
        </p>
      </div>

      <Separator />

      <div className="space-y-4">
        <InfoRow label="ชื่อระบบ" value="Document AI OCR" />
        <InfoRow label="เวอร์ชัน" value={APP_VERSION} />
        <InfoRow
          label="แบบฟอร์มที่รองรับ"
          value="แบบ 4, แบบ 18, แบบ 20"
        />
        <InfoRow label="เฟรมเวิร์ค" value="Next.js + FastAPI" />
        <InfoRow label="AI Engine" value="Google Gemini Vision" />
      </div>

      <Separator />

      <div>
        <p className="text-sm font-medium mb-3">ลิงก์ที่เกี่ยวข้อง</p>
        <div className="space-y-2">
          {links.map((link) => (
            <button
              key={link.label}
              onClick={() => openUrl(link.url)}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-full text-left"
            >
              <ExternalLink className="size-3.5" />
              {link.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ===== Shared Components =====

function SettingRow({
  label,
  description,
  children,
}: {
  label: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}
