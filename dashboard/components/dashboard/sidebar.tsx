"use client";

import * as React from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Search,
  Inbox,
  BarChart3,
  CheckSquare,
  Layers,
  Calendar,
  FileText,
  Settings,
  Activity,
  Globe,
  Folder,
  File,
  Megaphone,
  Code,
  Headphones,
  Plus,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  LogOut,
  UserCog,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDashboardStore } from "@/store/dashboard-store";
import { useDashboardRequests } from "@/hooks/use-dashboard-data";
import { showToast, openUrl } from "@/hooks/use-toast";
import { API_DOCS, FORMS_URL, SHAREPOINT_URL, POWER_AUTOMATE_URL } from "@/lib/constants";

type NavItem = {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  shortcut?: string;
  isActive?: boolean;
  action?: string;
};

const navItems: NavItem[] = [
  { title: "ค้นหา", icon: Search, shortcut: "/", action: "search" },
  { title: "กล่องข้อความ", icon: Inbox, action: "inbox" },
  { title: "Dashboard", icon: BarChart3, isActive: true, action: "dashboard" },
  { title: "คำร้อง", icon: CheckSquare, action: "requests" },
  { title: "การอนุมัติ", icon: Layers, action: "approvals" },
  { title: "วิเคราะห์", icon: Calendar, action: "analytics" },
  { title: "เอกสาร", icon: FileText, action: "documents" },
  { title: "กิจกรรมล่าสุด", icon: Activity, action: "activity" },
  { title: "ตั้งค่า", icon: Settings, action: "settings" },
];

function useFormGroups(requests: { formType: string; status: string }[]) {
  return React.useMemo(() => {
    const count = (form: string, status?: string) =>
      requests.filter(r => r.formType === form && (!status || r.status === status)).length;
    const f4p = count("แบบ 4", "pending"), f4a = count("แบบ 4", "approved");
    const f18p = count("แบบ 18", "pending"), f18a = count("แบบ 18", "approved");
    const f20p = count("แบบ 20", "pending"), f20a = count("แบบ 20", "approved");
    return [
      {
        id: "all-forms",
        name: "แบบฟอร์มทั้งหมด",
        icon: Globe,
        children: [
          {
            id: "form-4",
            name: "แบบ 4 — ลงทะเบียนเรียนควบ",
            icon: Folder,
            children: [
              { id: "form-4-pending", name: `รออนุมัติ (${f4p})`, icon: File },
              { id: "form-4-approved", name: `อนุมัติแล้ว (${f4a})`, icon: File },
            ],
          },
          {
            id: "form-18",
            name: "แบบ 18 — ขอคืนเงิน",
            icon: Folder,
            children: [
              { id: "form-18-pending", name: `รออนุมัติ (${f18p})`, icon: File },
              { id: "form-18-approved", name: `อนุมัติแล้ว (${f18a})`, icon: File },
            ],
          },
          {
            id: "form-20",
            name: "แบบ 20 — ขอถอนรายวิชา",
            icon: Folder,
            children: [
              { id: "form-20-pending", name: `รออนุมัติ (${f20p})`, icon: File },
              { id: "form-20-approved", name: `อนุมัติแล้ว (${f20a})`, icon: File },
            ],
          },
        ],
      },
      { id: "ocr-results", name: "ผลการ OCR", icon: Megaphone, action: "ocr" },
      { id: "power-automate", name: "Power Automate", icon: Code, action: "pa" },
      { id: "sharepoint", name: "SharePoint", icon: Headphones, action: "sp" },
    ];
  }, [requests]);
}

export function DashboardSidebar({
  ...props
}: React.ComponentProps<typeof Sidebar>) {
  const { currentPage, setStatusFilter, setFormTypeFilter, setSearchQuery, clearFilters, setViewMode, setCurrentPage } = useDashboardStore();
  const { requests } = useDashboardRequests();
  const pendingCount = React.useMemo(() => requests.filter(r => r.status === "pending").length, [requests]);
  const formGroups = useFormGroups(requests);
  const [activeNav, setActiveNav] = React.useState(currentPage === "settings" ? "settings" : currentPage === "activity" ? "activity" : "dashboard");

  // Sync sidebar highlight when currentPage changes externally (e.g. keyboard shortcut, back button)
  React.useEffect(() => {
    if (currentPage === "settings" || currentPage === "activity") setActiveNav(currentPage);
  }, [currentPage]);
  const [expandedItems, setExpandedItems] = React.useState<string[]>([
    "all-forms",
    "form-4",
  ]);

  const handleNavClick = (action: string) => {
    setActiveNav(action);
    switch (action) {
      case "dashboard":
        setCurrentPage("dashboard");
        clearFilters();
        setViewMode("table");
        break;
      case "inbox":
        setCurrentPage("dashboard");
        clearFilters();
        setStatusFilter("pending");
        setViewMode("table");
        showToast("กรองเฉพาะคำร้องที่รออนุมัติ", "info");
        break;
      case "requests":
        setCurrentPage("dashboard");
        clearFilters();
        setViewMode("table");
        showToast("แสดงคำร้องทั้งหมด", "info");
        break;
      case "approvals":
        setCurrentPage("dashboard");
        clearFilters();
        setStatusFilter("approved");
        setViewMode("kanban");
        showToast("แสดง Kanban — คำร้องที่อนุมัติแล้ว", "info");
        break;
      case "analytics":
        openUrl(`${API_DOCS}#/Dashboard`);
        break;
      case "documents":
        openUrl(`${SHAREPOINT_URL}/Shared%20Documents`);
        break;
      case "activity":
        setCurrentPage("activity");
        break;
      case "settings":
        setCurrentPage("settings");
        break;
      case "search":
        // Focus the search input at top of table
        const searchInput = document.querySelector<HTMLInputElement>('input[placeholder*="ค้นหา"]');
        if (searchInput) { searchInput.focus(); searchInput.scrollIntoView({ behavior: "smooth" }); }
        break;
    }
  };

  const toggleItem = (id: string) => {
    setExpandedItems((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleFormGroupClick = (id: string) => {
    switch (id) {
      case "form-4":
        clearFilters(); setFormTypeFilter("แบบ 4"); setViewMode("table");
        showToast("กรองเฉพาะแบบ 4", "info");
        break;
      case "form-4-pending":
        clearFilters(); setFormTypeFilter("แบบ 4"); setStatusFilter("pending"); setViewMode("table");
        showToast("แบบ 4 — รออนุมัติ", "info");
        break;
      case "form-4-approved":
        clearFilters(); setFormTypeFilter("แบบ 4"); setStatusFilter("approved"); setViewMode("table");
        showToast("แบบ 4 — อนุมัติแล้ว", "info");
        break;
      case "form-18":
        clearFilters(); setFormTypeFilter("แบบ 18"); setViewMode("table");
        showToast("กรองเฉพาะแบบ 18", "info");
        break;
      case "form-18-pending":
        clearFilters(); setFormTypeFilter("แบบ 18"); setStatusFilter("pending"); setViewMode("table");
        showToast("แบบ 18 — รออนุมัติ", "info");
        break;
      case "form-18-approved":
        clearFilters(); setFormTypeFilter("แบบ 18"); setStatusFilter("approved"); setViewMode("table");
        showToast("แบบ 18 — อนุมัติแล้ว", "info");
        break;
      case "form-20":
        clearFilters(); setFormTypeFilter("แบบ 20"); setViewMode("table");
        showToast("กรองเฉพาะแบบ 20", "info");
        break;
      case "form-20-pending":
        clearFilters(); setFormTypeFilter("แบบ 20"); setStatusFilter("pending"); setViewMode("table");
        showToast("แบบ 20 — รออนุมัติ", "info");
        break;
      case "form-20-approved":
        clearFilters(); setFormTypeFilter("แบบ 20"); setStatusFilter("approved"); setViewMode("table");
        showToast("แบบ 20 — อนุมัติแล้ว", "info");
        break;
      case "ocr-results":
        openUrl(`${API_DOCS}#/OCR`);
        break;
      case "power-automate":
        openUrl(POWER_AUTOMATE_URL);
        break;
      case "sharepoint":
        openUrl(SHAREPOINT_URL);
        break;
    }
  };

  const renderFormGroupItem = (
    item: (typeof formGroups)[0],
    level: number = 0
  ) => {
    const hasChildren = "children" in item && item.children;
    const isExpanded = expandedItems.includes(item.id);
    const Icon = item.icon;
    const paddingLeft = level * 12;

    if (hasChildren && level === 0) {
      // Top-level collapsible: SidebarMenuItem (li) is valid here
      return (
        <Collapsible
          key={item.id}
          open={isExpanded}
          onOpenChange={() => toggleItem(item.id)}
        >
          <SidebarMenuItem>
            <CollapsibleTrigger asChild>
              <SidebarMenuButton
                className="h-7 text-sm"
                style={{ paddingLeft: `${8 + paddingLeft}px` }}
              >
                <Icon className="size-3.5" />
                <span className="flex-1">{item.name}</span>
                {isExpanded ? (
                  <ChevronDown className="size-3" />
                ) : (
                  <ChevronRight className="size-3" />
                )}
              </SidebarMenuButton>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <SidebarMenuSub className="mr-0 pr-0">
                {item.children?.map((child) => (
                  <SidebarMenuSubItem key={child.id}>
                    {renderFormGroupItem(
                      child as (typeof formGroups)[0],
                      level + 1
                    )}
                  </SidebarMenuSubItem>
                ))}
              </SidebarMenuSub>
            </CollapsibleContent>
          </SidebarMenuItem>
        </Collapsible>
      );
    }

    if (hasChildren && level > 0) {
      // Nested collapsible: already inside a SidebarMenuSubItem (li),
      // so do NOT wrap in another SidebarMenuItem (li)
      return (
        <Collapsible
          key={item.id}
          open={isExpanded}
          onOpenChange={() => toggleItem(item.id)}
        >
          <CollapsibleTrigger asChild>
            <SidebarMenuButton
              className="h-7 text-sm"
              style={{ paddingLeft: `${8 + paddingLeft}px` }}
            >
              <Icon className="size-3.5" />
              <span className="flex-1">{item.name}</span>
              {isExpanded ? (
                <ChevronDown className="size-3" />
              ) : (
                <ChevronRight className="size-3" />
              )}
            </SidebarMenuButton>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <SidebarMenuSub className="mr-0 pr-0">
              {item.children?.map((child) => (
                <SidebarMenuSubItem key={child.id}>
                  {renderFormGroupItem(
                    child as (typeof formGroups)[0],
                    level + 1
                  )}
                </SidebarMenuSubItem>
              ))}
            </SidebarMenuSub>
          </CollapsibleContent>
        </Collapsible>
      );
    }

    // Leaf item: if nested (level > 0), don't wrap in SidebarMenuItem
    if (level > 0) {
      return (
        <SidebarMenuButton
          key={item.id}
          className="h-7 text-sm cursor-pointer"
          style={{ paddingLeft: `${8 + paddingLeft}px` }}
          onClick={() => handleFormGroupClick(item.id)}
        >
          <Icon className="size-3.5" />
          <span>{item.name}</span>
        </SidebarMenuButton>
      );
    }

    return (
      <SidebarMenuItem key={item.id}>
        <SidebarMenuButton
          className="h-7 text-sm cursor-pointer"
          style={{ paddingLeft: `${8 + paddingLeft}px` }}
          onClick={() => handleFormGroupClick(item.id)}
        >
          <Icon className="size-3.5" />
          <span>{item.name}</span>
        </SidebarMenuButton>
      </SidebarMenuItem>
    );
  };

  return (
    <Sidebar className="lg:border-r-0!" collapsible="icon" {...props}>
      <SidebarHeader className="px-2.5 py-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2.5 w-full hover:bg-sidebar-accent rounded-md p-1 -m-1 transition-colors shrink-0">
              <div className="flex size-7 items-center justify-center rounded-lg bg-foreground text-background shrink-0">
                <span className="text-sm font-bold">📄</span>
              </div>
              <div className="flex items-center gap-1 group-data-[collapsible=icon]:hidden">
                <span className="text-sm font-medium">DocumentAI</span>
                <ChevronsUpDown className="size-3 text-muted-foreground" />
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56">
            <DropdownMenuItem onClick={() => { setCurrentPage("settings"); setActiveNav("settings"); }}>
              <Settings className="size-4" />
              <span>ตั้งค่าระบบ</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => openUrl(`${SHAREPOINT_URL}/Lists/Advisors`)}>
              <UserCog className="size-4" />
              <span>จัดการผู้ใช้</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={() => showToast("ออกจากระบบสำเร็จ (demo)", "success")}>
              <LogOut className="size-4" />
              <span>ออกจากระบบ</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarHeader>

      <SidebarContent className="px-2.5">
        <SidebarGroup className="p-0">
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    isActive={activeNav === item.action}
                    className="h-7 cursor-pointer"
                    onClick={() => item.action && handleNavClick(item.action)}
                  >
                    <item.icon className="size-3.5" />
                    <span className="text-sm">{item.title}</span>
                    {item.action === "inbox" && pendingCount > 0 && (
                      <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-medium text-white px-1.5">
                        {pendingCount}
                      </span>
                    )}
                    {item.shortcut && (
                      <span className="ml-auto flex size-5 items-center justify-center rounded bg-muted text-[10px] font-medium text-muted-foreground">
                        {item.shortcut}
                      </span>
                    )}
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="p-0 mt-4">
          <SidebarGroupLabel className="flex items-center justify-between px-0 h-6">
            <span className="text-[10px] font-medium tracking-wider text-muted-foreground">
              แบบฟอร์ม
            </span>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="size-5" onClick={() => {
                const searchInput = document.querySelector<HTMLInputElement>('input[placeholder*="ค้นหา"]');
                if (searchInput) { searchInput.focus(); searchInput.scrollIntoView({ behavior: "smooth" }); }
              }}>
                <Search className="size-3" />
              </Button>
              <Button variant="ghost" size="icon" className="size-5" onClick={() => openUrl(FORMS_URL)}>
                <Plus className="size-3" />
              </Button>
            </div>
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {formGroups.map((item) => renderFormGroupItem(item))}
              <SidebarMenuItem>
                <SidebarMenuButton className="h-7 text-sm text-muted-foreground cursor-pointer" onClick={() => openUrl(FORMS_URL)}>
                  <Plus className="size-3.5" />
                  <span>เพิ่มแบบฟอร์ม</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="px-2.5 pb-3 group-data-[collapsible=icon]:hidden">
        <div className="group/sidebar relative flex flex-col gap-2 rounded-lg border p-4 text-sm w-full bg-background">
          <div className="text-balance text-lg font-semibold leading-tight group-hover/sidebar:underline">
            ระบบคำร้องเอกสาร
          </div>
          <div className="text-muted-foreground">
            ระบบจัดการคำร้องอัตโนมัติ ด้วย OCR + Power Automate สำหรับมหาวิทยาลัย
          </div>
          <Button size="sm" className="w-full" onClick={() => openUrl(`${API_DOCS}#/Dashboard`)}>
            ดูรายงาน
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
