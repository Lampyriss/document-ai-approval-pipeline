// API Client สำหรับเชื่อมต่อ FastAPI Backend
// ดึงข้อมูลจาก /api/dashboard/* endpoints

const API_BASE = "/backend/dashboard";

// ===== Types =====

export interface ApiStats {
  success: boolean;
  total_requests: number;
  approved: number;
  pending: number;
  rejected: number;
  avg_ocr_confidence: number;
  form_breakdown: Record<string, number>;
  daily_stats: DailyStat[];
}

export interface DailyStat {
  date: string;
  total: number;
  form4: number;
  form18: number;
  form20: number;
  approved: number;
}

export interface ApiRequest {
  request_id: string;
  form_type: string;
  student_id: string | null;
  student_name: string | null;
  student_email: string | null;
  faculty: string | null;
  major: string | null;
  phone: string | null;
  advisor_name: string | null;
  advisor_email: string | null;
  current_step: number;
  total_steps: number;
  overall_status: "pending" | "approved" | "rejected";
  courses: string | null;
  ocr_confidence: number;
  source: string;
  submitted_date: string;
  updated_at: string;
  document_link?: string;
}

export interface ApiRequestsResponse {
  success: boolean;
  requests: ApiRequest[];
  total: number;
}

// ===== Fetch Functions =====

export async function fetchDashboardStats(): Promise<ApiStats> {
  const res = await fetch(`${API_BASE}/stats`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Stats API error: ${res.status}`);
  return res.json();
}

export async function fetchDashboardRequests(params?: {
  limit?: number;
  offset?: number;
  status?: string;
  search?: string;
}): Promise<ApiRequestsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  if (params?.status && params.status !== "all")
    searchParams.set("status", params.status);
  if (params?.search) searchParams.set("search", params.search);

  const url = `${API_BASE}/requests${searchParams.toString() ? "?" + searchParams.toString() : ""}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`Requests API error: ${res.status}`);
  return res.json();
}

export async function checkApiHealth(): Promise<boolean> {
  try {
    // /backend/health -> proxy -> backend /api/health
    const res = await fetch("/backend/health", {
      signal: AbortSignal.timeout(5000),
    });
    return res.ok;
  } catch {
    return false;
  }
}
