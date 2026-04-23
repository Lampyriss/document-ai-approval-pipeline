"use client";

import { Button } from "@/components/ui/button";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  BarChart3,
  Sparkles,
  Share2,
  Plus,
  FilePlus,
  Upload,
  Mail,
  Link2,
  Users,
  FileDown,
  FileSpreadsheet,
  Printer,
  Eye,
  ShieldCheck,
  FileBarChart,
} from "lucide-react";
import { copyToClipboard, openUrl, showToast } from "@/hooks/use-toast";
import { API_DOCS, FORMS_URL, SHAREPOINT_URL } from "@/lib/constants";

const advisorContacts = [
  {
    id: "advisor-1",
    name: "Advisor A",
    email: "advisor.one@example.edu",
    initials: "AA",
    seed: "AA",
    backgroundColor: "7c5cfc",
  },
  {
    id: "advisor-2",
    name: "Advisor B",
    email: "advisor.two@example.edu",
    initials: "AB",
    seed: "AB",
    backgroundColor: "3b82f6",
  },
  {
    id: "advisor-3",
    name: "Program Chair",
    email: "chair@example.edu",
    initials: "PC",
    seed: "PC",
    backgroundColor: "06b6d4",
  },
];

export function DashboardHeader() {
  return (
    <header className="flex items-center justify-between gap-4 px-4 sm:px-6 py-3 border-b bg-card sticky top-0 z-10 w-full">
      <div className="flex items-center gap-3">
        <SidebarTrigger className="-ml-2" />
        <div className="hidden sm:flex items-center gap-2 text-muted-foreground">
          <BarChart3 className="size-4" />
          <span className="text-sm font-medium">Dashboard</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="hidden lg:flex items-center">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex -space-x-2 mr-3 cursor-pointer hover:opacity-80 transition-opacity">
                {advisorContacts.map((advisor) => (
                  <Avatar key={advisor.id} className="size-6 border-2 border-card">
                    <AvatarImage
                      src={`https://api.dicebear.com/9.x/initials/svg?seed=${advisor.seed}&backgroundColor=${advisor.backgroundColor}`}
                    />
                    <AvatarFallback>{advisor.initials}</AvatarFallback>
                  </Avatar>
                ))}
                <div className="flex size-6 items-center justify-center rounded-full border-2 border-card bg-muted">
                  <Plus className="size-3" />
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              <div className="px-2 py-1.5">
                <p className="text-xs font-medium text-muted-foreground">
                  Approval Contacts
                </p>
              </div>
              {advisorContacts.map((advisor) => (
                <DropdownMenuItem
                  key={advisor.id}
                  onClick={() => showToast(`${advisor.name} - ${advisor.email}`, "info")}
                >
                  <Avatar className="size-5 mr-2">
                    <AvatarImage
                      src={`https://api.dicebear.com/9.x/initials/svg?seed=${advisor.seed}&backgroundColor=${advisor.backgroundColor}`}
                    />
                    <AvatarFallback>{advisor.initials}</AvatarFallback>
                  </Avatar>
                  <span>{advisor.name}</span>
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() =>
                  openUrl(
                    "mailto:document-ai-ops@example.edu?subject=Document%20AI%20Approval%20Update"
                  )
                }
              >
                <Mail className="size-4 mr-2" />
                <span>ส่งอีเมลแจ้งเตือน</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => copyToClipboard(window.location.href, "ลิงก์ Dashboard")}>
                <Link2 className="size-4 mr-2" />
                <span>คัดลอกลิงก์</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => openUrl(`${SHAREPOINT_URL}/Lists/Advisors`)}>
                <Users className="size-4 mr-2" />
                <span>จัดการอาจารย์</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <div className="h-5 w-px bg-border mx-2" />
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="h-7 gap-1.5 hidden sm:flex"
            >
              <Sparkles className="size-3.5" />
              <span className="text-sm">OCR วิเคราะห์</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => openUrl(API_DOCS + "#/OCR/ocr_binary_api_ocr_binary_post")}>
              <Eye className="size-4 mr-2" />
              วิเคราะห์เอกสาร
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => openUrl(API_DOCS + "#/Health/health_check_api_health_get")}>
              <ShieldCheck className="size-4 mr-2" />
              ตรวจสอบความถูกต้อง
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => openUrl(API_DOCS + "#/Dashboard")}>
              <FileBarChart className="size-4 mr-2" />
              สร้างรายงาน OCR
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="h-7 gap-1.5 hidden sm:flex"
            >
              <Share2 className="size-3.5" />
              <span className="text-sm">ส่งออก</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => copyToClipboard(window.location.href, "ลิงก์ Dashboard")}>
              <Link2 className="size-4 mr-2" />
              คัดลอกลิงก์
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => window.print()}>
              <Printer className="size-4 mr-2" />
              ส่งออก PDF
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => showToast("ใช้ปุ่มส่งออกในตารางด้านล่าง", "info")}>
              <FileSpreadsheet className="size-4 mr-2" />
              ส่งออก Excel
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <ThemeToggle />
      </div>
    </header>
  );
}

export function WelcomeSection() {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 className="text-xl sm:text-2xl font-semibold tracking-tight">
          ยินดีต้อนรับ!
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          ระบบตัวอย่างสำหรับ OCR และ workflow อนุมัติคำร้องนิสิต
        </p>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          className="h-9 gap-1.5 bg-card hover:bg-card/80 border-border/50"
          onClick={() => openUrl(FORMS_URL)}
        >
          <FilePlus className="size-4" />
          <span className="hidden sm:inline">คำร้องใหม่</span>
        </Button>
        <Button
          className="h-9 gap-1.5 bg-foreground hover:bg-foreground/90 text-background border border-border/50"
          onClick={() => openUrl(API_DOCS)}
        >
          <Upload className="size-4" />
          <span className="hidden sm:inline">อัปโหลดเอกสาร</span>
        </Button>
      </div>
    </div>
  );
}
