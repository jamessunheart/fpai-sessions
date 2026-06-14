export type MissionVisibility = "public" | "internal";
export type MissionStatus =
  | "available"
  | "claimed"
  | "in_progress"
  | "completed"
  | "failed";

export interface MissionHistoryEntry {
  action: "CLAIMED" | "COMPLETED";
  by: string;
  notes?: string;
  at: string;
}

export interface Mission {
  id: string;
  title: string;
  status?: MissionStatus | string;
  status_text?: string | null;
  priority?: string | null;
  owner?: string | null;
  principle?: string | null;
  regenerative_impact?: string | null;
  path?: string | null;
  visibility?: MissionVisibility | string | null;
  role_needed?: string | null;
  time_estimate_minutes?: number | null;
  category?: string | null;
  instructions?: string | null;
  success_criteria?: string | null;
  resources?: string[] | null;
  internal_notes?: string | null;
  history?: MissionHistoryEntry[];
}

export interface Paper {
  file: string;
  type: string;
  size: string;
  keywords: string[];
}
