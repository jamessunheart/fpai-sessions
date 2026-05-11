// API Response Types
export interface ApiResponse<T> {
  records: T[];
}

// Airtable Record Types
export interface Sprint {
  id: string;
  createdTime: string;
  fields: {
    Sprint_ID?: string;
    Name?: string;
    Dev_Name?: string;
    Status?: 'Pending' | 'Active' | 'Done';
    Proof_URL?: string;
    Time_Spent_hr?: number;
    Notes?: string;
  };
}

export interface Cell {
  id: string;
  createdTime: string;
  fields: {
    Cell_ID?: string;
    Role?: 'Builder' | 'Verifier' | 'Connector';
    IP_Address?: string;
    Health_Status?: 'OK' | 'Warning' | 'Offline';
    Cost_per_hr?: number;
  };
}

export interface Proof {
  id: string;
  createdTime: string;
  fields: {
    Proof_ID?: string;
    Sprint_ID?: string;
    Result?: string;
    Token?: string;
    Timestamp?: string;
  };
}

export interface Heartbeat {
  id: string;
  createdTime: string;
  fields: {
    Cell_ID?: string;
    CPU_Usage?: number;
    RAM_Usage?: number;
    Status?: string;
    Timestamp?: string;
  };
}

export interface DailyDigest {
  id: string;
  createdTime: string;
  fields: {
    Date?: string;
    Total_Droplets?: number;
    Active_Droplets?: number;
    Uptime_Percentage?: number;
    New_Sprints_Today?: number;
    Total_Sprints?: number;
    Completed_Sprints?: number;
    Active_Sprints?: number;
    Pending_Sprints?: number;
    Total_Proofs?: number;
    Verified_Proofs?: number;
    Average_CPU?: number;
    Average_RAM?: number;
    Daily_Summary?: string;
  };
}

// Dashboard Stats
export interface Droplet {
  id: string;
  name?: string;
  host?: string;
  ip?: string;
  status?: string;
  role?: string;
  env?: string;
  version?: string;
  droplet_id?: string;
  metadata?: Record<string, any>;
  registered_at?: string;
  last_updated?: string;
  last_heartbeat?: number;
  health?: {
    available: boolean;
    status?: string;
    name?: string;
    cost_usd?: number;
    yield_usd?: number;
    proof?: string;
    updated_at?: string;
  };
  // Legacy fields (Registry v1)
  cost_hour?: number;
  cpu?: number;
  disk?: number;
  fqdn?: string;
  last_seen?: number;
  mem?: number;
}

export interface DashboardResponse {
  droplets: Droplet[];
  summary: {
    cost_hour_total: number;
    down: number;
    healthy: number;
    total: number;
  };
}

export interface DashboardStats {
  totalSprints: number;
  activeSprints: number;
  completedSprints: number;
  totalDroplets: number;
  activeDroplets: number;
  uptime: number;
  avgCpu: number;
  avgRam: number;
}