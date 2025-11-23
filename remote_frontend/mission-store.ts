import { promises as fs } from "fs";
import path from "path";
import type { Mission, MissionStatus, MissionVisibility } from "@/types";

const FEED_CANDIDATES = [
  process.env.MISSION_FEED_PATH,
  "/opt/fpai/docs/status/missions.json",
  path.resolve(process.cwd(), "../docs/status/missions.json"),
  path.resolve(process.cwd(), "../../docs/status/missions.json"),
];

const STATE_CANDIDATES = [
  process.env.MISSION_STATE_PATH,
  "/opt/fpai/docs/status/mission_state.json",
  path.resolve(process.cwd(), "../docs/status/mission_state.json"),
  path.resolve(process.cwd(), "../../docs/status/mission_state.json"),
];

const FALLBACK_FEED_URL =
  process.env.MISSION_FEED_URL ?? process.env.NEXT_PUBLIC_MISSION_FEED_URL;

export type MissionAction = "CLAIMED" | "COMPLETED";

export interface MissionHistoryEntry {
  action: MissionAction;
  by: string;
  notes?: string;
  at: string;
}

export interface MissionStateEntry {
  owner?: string;
  status?: "OPEN" | "AVAILABLE" | "IN_PROGRESS" | "DONE" | "FAILED";
  history: MissionHistoryEntry[];
}

export interface MissionStateFile {
  missions: Record<string, MissionStateEntry>;
  updated_at: string;
}

export class MissionStateError extends Error {
  status: number;
  constructor(message: string, status = 400) {
    super(message);
    this.name = "MissionStateError";
    this.status = status;
  }
}

const pickFirstExisting = async (
  candidates: Array<string | undefined>,
): Promise<string | null> => {
  for (const candidate of candidates) {
    if (!candidate) continue;
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      continue;
    }
  }
  return null;
};

const readJsonFromFile = async <T>(filePath: string): Promise<T | null> => {
  try {
    const raw = await fs.readFile(filePath, "utf8");
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
};

const writeJsonAtomically = async (
  filePath: string,
  payload: unknown,
): Promise<void> => {
  const tmpPath = `${filePath}.tmp`;
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(tmpPath, JSON.stringify(payload, null, 2));
  await fs.rename(tmpPath, filePath);
};

const STATUS_MAP: Record<string, MissionStatus> = {
  OPEN: "available",
  AVAILABLE: "available",
  UNASSIGNED: "available",
  READY: "available",
  IN_PROGRESS: "claimed",
  CLAIMED: "claimed",
  ACTIVE: "claimed",
  EXECUTING: "claimed",
  DONE: "completed",
  COMPLETE: "completed",
  COMPLETED: "completed",
  FINISHED: "completed",
  FAILED: "failed",
  BLOCKED: "failed",
};

const normalizeStatus = (value?: string | null): MissionStatus => {
  if (!value) return "available";
  return STATUS_MAP[value.toUpperCase()] ?? "available";
};

const normalizeVisibility = (input?: string | null): MissionVisibility => {
  if (typeof input === "string" && input.toLowerCase() === "internal") {
    return "internal";
  }
  return "public";
};

const coerceMinutes = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const numericPortion = value.match(/\d+/);
    if (numericPortion) {
      const parsed = parseInt(numericPortion[0], 10);
      if (!Number.isNaN(parsed) && parsed > 0) return parsed;
    }
  }
  return null;
};

const standardizeMission = (mission: Mission): Mission => ({
  ...mission,
  visibility: normalizeVisibility(mission.visibility ?? undefined),
  owner: mission.owner ?? null,
  role_needed: mission.role_needed ?? null,
  time_estimate_minutes: coerceMinutes(mission.time_estimate_minutes ?? undefined),
  history: mission.history ?? [],
});

const mergeMission = (
  mission: Mission,
  override?: MissionStateEntry,
): Mission => {
  const normalized = standardizeMission(mission);
  const statusFromState = override?.status
    ? normalizeStatus(override.status)
    : undefined;

  return {
    ...normalized,
    owner: override?.owner ?? normalized.owner ?? null,
    status: statusFromState ?? normalizeStatus(normalized.status),
    history: override?.history ?? normalized.history ?? [],
  };
};

const sanitizePublicMission = (mission: Mission): Mission => {
  const { internal_notes, ...rest } = mission;
  return rest;
};

export const loadMissionFeed = async (): Promise<Mission[]> => {
  const feedPath = await pickFirstExisting(FEED_CANDIDATES);
  if (feedPath) {
    const data = await readJsonFromFile<{ missions?: Mission[] }>(feedPath);
    if (data?.missions) return data.missions;
  }

  if (FALLBACK_FEED_URL) {
    const response = await fetch(FALLBACK_FEED_URL, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Mission feed fetch failed: ${response.status}`);
    }
    const payload = (await response.json()) as { missions?: Mission[] };
    return payload.missions ?? [];
  }

  return [];
};

const resolveStatePath = async (): Promise<string> => {
  const pathFromEnv = await pickFirstExisting(STATE_CANDIDATES);
  if (pathFromEnv) return pathFromEnv;
  // Default to repo-local docs folder
  const fallback = path.resolve(process.cwd(), "../docs/status/mission_state.json");
  await fs.mkdir(path.dirname(fallback), { recursive: true });
  return fallback;
};

export const loadMissionState = async (): Promise<{
  state: MissionStateFile;
  statePath: string;
}> => {
  const statePath = await resolveStatePath();
  const existing = await readJsonFromFile<MissionStateFile>(statePath);
  if (existing) return { state: existing, statePath };
  const empty: MissionStateFile = {
    missions: {},
    updated_at: new Date().toISOString(),
  };
  await writeJsonAtomically(statePath, empty);
  return { state: empty, statePath };
};

export const persistMissionState = async (
  statePath: string,
  state: MissionStateFile,
): Promise<void> => {
  await writeJsonAtomically(statePath, state);
};

export interface GetMergedMissionOptions {
  includeInternal?: boolean;
}

export const getMergedMissions = async (
  options: GetMergedMissionOptions = {},
): Promise<Mission[]> => {
  const { includeInternal = false } = options;
  const [feed, { state }] = await Promise.all([loadMissionFeed(), loadMissionState()]);
  const merged = feed.map((mission) => mergeMission(mission, state.missions[mission.id]));
  if (includeInternal) {
    return merged;
  }
  return merged
    .filter((mission) => normalizeVisibility(mission.visibility) === "public")
    .map(sanitizePublicMission);
};

const ensureMissionExists = (missions: Mission[], missionId: string): Mission => {
  const mission = missions.find((item) => item.id === missionId);
  if (!mission) {
    throw new MissionStateError(`Mission ${missionId} not found`, 404);
  }
  return mission;
};

const sanitizeId = (missionId: string): string => {
  if (!/^M\d{3,}$/i.test(missionId)) {
    throw new MissionStateError("Invalid mission id format");
  }
  return missionId.toUpperCase();
};

const assertVisibilityAccess = (
  mission: Mission,
  allowInternal: boolean,
): void => {
  if (normalizeVisibility(mission.visibility) === "internal" && !allowInternal) {
    throw new MissionStateError("Mission requires operator access", 403);
  }
};

export const isMissionStateError = (error: unknown): error is MissionStateError =>
  error instanceof MissionStateError;

export const claimMission = async (opts: {
  missionId: string;
  claimer: string;
  notes?: string;
  allowInternal?: boolean;
}): Promise<Mission> => {
  const missionId = sanitizeId(opts.missionId);
  const claimer = opts.claimer?.trim();
  if (!claimer) throw new MissionStateError("Claimer name is required");

  const [feed, { state, statePath }] = await Promise.all([
    loadMissionFeed(),
    loadMissionState(),
  ]);
  const mission = ensureMissionExists(feed, missionId);
  assertVisibilityAccess(mission, Boolean(opts.allowInternal));

  const entry = state.missions[missionId] ?? { history: [] };

  if (entry.status === "DONE") {
    throw new MissionStateError("Mission already completed", 409);
  }
  if (entry.status === "IN_PROGRESS" && entry.owner && entry.owner !== claimer) {
    throw new MissionStateError(
      `Mission already claimed by ${entry.owner}. Release before re-claiming.`,
      409,
    );
  }

  const timestamp = new Date().toISOString();
  state.missions[missionId] = {
    owner: claimer,
    status: "IN_PROGRESS",
    history: [
      ...entry.history,
      { action: "CLAIMED", by: claimer, notes: opts.notes?.trim(), at: timestamp },
    ],
  };
  state.updated_at = timestamp;
  await persistMissionState(statePath, state);

  return mergeMission(mission, state.missions[missionId]);
};

export const completeMission = async (opts: {
  missionId: string;
  actor: string;
  notes?: string;
  allowInternal?: boolean;
}): Promise<Mission> => {
  const missionId = sanitizeId(opts.missionId);
  const actor = opts.actor?.trim();
  if (!actor) throw new MissionStateError("Actor name is required");

  const [feed, { state, statePath }] = await Promise.all([
    loadMissionFeed(),
    loadMissionState(),
  ]);
  const mission = ensureMissionExists(feed, missionId);
  assertVisibilityAccess(mission, Boolean(opts.allowInternal));
  const entry = state.missions[missionId] ?? { history: [] };

  if (entry.status === "DONE") {
    throw new MissionStateError("Mission already completed", 409);
  }

  const timestamp = new Date().toISOString();
  state.missions[missionId] = {
    owner: entry.owner ?? actor,
    status: "DONE",
    history: [
      ...entry.history,
      { action: "COMPLETED", by: actor, notes: opts.notes?.trim(), at: timestamp },
    ],
  };
  state.updated_at = timestamp;
  await persistMissionState(statePath, state);

  return mergeMission(mission, state.missions[missionId]);
};
