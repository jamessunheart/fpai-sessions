'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { Mission, MissionStatus } from '@/types';

type StatusFilter = 'available' | 'claimed' | 'completed';
type VisibilityFilter = 'all' | 'public' | 'internal';
type TimeFilter = 'any' | '15' | '60' | '120';

type ActionState = 'idle' | 'submitting';

type ClaimFormState = {
  name: string;
  notes: string;
};

type CompleteFormState = {
  name: string;
  notes: string;
};

const STATUS_META: Record<StatusFilter, { label: string; accent: string; description: string }> = {
  available: {
    label: 'Available',
    accent: 'text-emerald-300 bg-emerald-900/20',
    description: 'Unclaimed missions ready for action',
  },
  claimed: {
    label: 'In Progress',
    accent: 'text-amber-300 bg-amber-900/20',
    description: 'Claimed missions awaiting completion',
  },
  completed: {
    label: 'Completed',
    accent: 'text-slate-300 bg-slate-800/60',
    description: 'Recently completed or archived missions',
  },
};

const PRIORITY_ORDER: Record<string, number> = {
  P0: 0,
  HIGH: 0,
  P1: 1,
  MEDIUM: 2,
  P2: 2,
  P3: 3,
  LOW: 4,
};

const TIME_FILTERS: Array<{ id: TimeFilter; label: string; min?: number; max?: number }> = [
  { id: 'any', label: 'Any duration' },
  { id: '15', label: '≤ 15 min', max: 15 },
  { id: '60', label: '30 – 60 min', min: 30, max: 60 },
  { id: '120', label: '2+ hours', min: 120 },
];

const defaultClaimForm: ClaimFormState = { name: '', notes: '' };
const defaultCompleteForm: CompleteFormState = { name: '', notes: '' };

const toUiStatus = (status?: MissionStatus | string | null): StatusFilter => {
  const normalized = (status ?? 'available').toString().toLowerCase();
  if (normalized === 'completed' || normalized === 'done') return 'completed';
  if (normalized === 'claimed' || normalized === 'in_progress') return 'claimed';
  if (normalized === 'failed') return 'completed';
  return 'available';
};

const formatTimeEstimate = (minutes?: number | null): string => {
  if (!minutes) return 'Flexible';
  if (minutes <= 15) return '≤ 15 min';
  if (minutes <= 30) return '≈ 30 min';
  if (minutes <= 60) return '≈ 1 hr';
  if (minutes <= 120) return '≈ 2 hrs';
  return `${Math.round(minutes / 60)} hrs`;
};

const missionMatchesTime = (mission: Mission, filter: TimeFilter): boolean => {
  if (filter === 'any') return true;
  const minutes = mission.time_estimate_minutes;
  if (!minutes) return false;
  const rule = TIME_FILTERS.find((item) => item.id === filter);
  if (!rule) return true;
  if (typeof rule.min === 'number' && minutes < rule.min) return false;
  if (typeof rule.max === 'number' && minutes > rule.max) return false;
  return true;
};

const missionMatchesSearch = (mission: Mission, query: string): boolean => {
  if (!query.trim()) return true;
  const haystack = [
    mission.id,
    mission.title,
    mission.priority,
    mission.role_needed,
    mission.principle,
    mission.regenerative_impact,
    mission.status_text,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return haystack.includes(query.trim().toLowerCase());
};

const getPrioritySortWeight = (priority?: string | null): number => {
  if (!priority) return 10;
  return PRIORITY_ORDER[priority.toUpperCase()] ?? 10;
};

const visibilityOf = (mission: Mission): VisibilityFilter => {
  const value = (mission.visibility ?? 'public').toString().toLowerCase();
  return value === 'internal' ? 'internal' : 'public';
};
export default function MissionsPage() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('available');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('any');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [visibilityFilter, setVisibilityFilter] = useState<VisibilityFilter>('public');
  const [searchQuery, setSearchQuery] = useState('');
  const [operatorMode, setOperatorMode] = useState(false);
  const [operatorKey, setOperatorKey] = useState<string | null>(null);
  const [selectedMission, setSelectedMission] = useState<Mission | null>(null);
  const [claimForm, setClaimForm] = useState<ClaimFormState>(defaultClaimForm);
  const [completeForm, setCompleteForm] = useState<CompleteFormState>(defaultCompleteForm);
  const [claimState, setClaimState] = useState<ActionState>('idle');
  const [completeState, setCompleteState] = useState<ActionState>('idle');
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [localClaims, setLocalClaims] = useState<Record<string, string>>({});

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const storedClaims = window.localStorage.getItem('mission-claims');
    if (storedClaims) {
      try {
        setLocalClaims(JSON.parse(storedClaims));
      } catch {
        setLocalClaims({});
      }
    }
    const storedKey = window.localStorage.getItem('mission-operator-key');
    if (storedKey) {
      setOperatorKey(storedKey);
      setOperatorMode(true);
    }
  }, []);

  useEffect(() => {
    setVisibilityFilter(operatorMode ? 'all' : 'public');
  }, [operatorMode]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem('mission-claims', JSON.stringify(localClaims));
  }, [localClaims]);

  const fetchMissions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const headers: HeadersInit = { Accept: 'application/json' };
      if (operatorMode && operatorKey) {
        headers['x-operator-key'] = operatorKey;
      }
      const response = await fetch('/api/missions', {
        headers,
        cache: 'no-store',
      });
      if (response.status === 403) {
        setOperatorMode(false);
        setOperatorKey(null);
        if (typeof window !== 'undefined') {
          window.localStorage.removeItem('mission-operator-key');
        }
        throw new Error('Operator access denied');
      }
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error ?? 'Unable to load missions');
      }
      const payload = await response.json();
      setMissions(payload.missions ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load missions');
    } finally {
      setLoading(false);
    }
  }, [operatorMode, operatorKey]);

  useEffect(() => {
    fetchMissions();
  }, [fetchMissions]);

  const roleOptions = useMemo(() => {
    const set = new Set<string>();
    missions.forEach((mission) => {
      if (mission.role_needed) {
        set.add(mission.role_needed);
      }
    });
    return Array.from(set).sort();
  }, [missions]);

  const statusCounts = useMemo(() => {
    return missions.reduce(
      (acc, mission) => {
        const status = toUiStatus(mission.status);
        acc[status] += 1;
        return acc;
      },
      { available: 0, claimed: 0, completed: 0 } as Record<StatusFilter, number>,
    );
  }, [missions]);

  const filteredMissions = useMemo(() => {
    return missions
      .filter((mission) => (visibilityFilter === 'all' ? true : visibilityOf(mission) === visibilityFilter))
      .filter((mission) => toUiStatus(mission.status) === statusFilter)
      .filter((mission) => {
        if (priorityFilter === 'all') return true;
        return (mission.priority ?? '').toUpperCase().startsWith(priorityFilter.toUpperCase());
      })
      .filter((mission) => (roleFilter === 'all' ? true : mission.role_needed === roleFilter))
      .filter((mission) => missionMatchesTime(mission, timeFilter))
      .filter((mission) => missionMatchesSearch(mission, searchQuery))
      .sort((a, b) => {
        const priorityDiff = getPrioritySortWeight(a.priority) - getPrioritySortWeight(b.priority);
        if (priorityDiff !== 0) return priorityDiff;
        return a.title.localeCompare(b.title);
      });
  }, [missions, visibilityFilter, statusFilter, priorityFilter, roleFilter, timeFilter, searchQuery]);

  const setMissionClaimName = (missionId: string, name: string) => {
    setLocalClaims((prev) => ({ ...prev, [missionId]: name }));
  };

  const handleOperatorToggle = () => {
    if (operatorMode) {
      setOperatorMode(false);
      setOperatorKey(null);
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem('mission-operator-key');
      }
      return;
    }
    if (typeof window === 'undefined') return;
    const input = window.prompt('Enter operator access key');
    if (!input?.trim()) return;
    const key = input.trim();
    setOperatorKey(key);
    window.localStorage.setItem('mission-operator-key', key);
    setOperatorMode(true);
  };

  const handleClaim = async () => {
    if (!selectedMission) return;
    if (!claimForm.name.trim()) {
      setActionError('Name is required to claim a mission.');
      setActionSuccess(null);
      return;
    }
    try {
      setClaimState('submitting');
      setActionError(null);
      setActionSuccess(null);
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (operatorMode && operatorKey) {
        headers['x-operator-key'] = operatorKey;
      }
      const response = await fetch('/api/missions/claim', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          missionId: selectedMission.id,
          claimer: claimForm.name.trim(),
          notes: claimForm.notes?.trim() || undefined,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error ?? 'Unable to claim mission');
      }
      const payload = await response.json();
      const updatedMission: Mission = payload.mission;
      setMissions((prev) => prev.map((mission) => (mission.id === updatedMission.id ? updatedMission : mission)));
      setSelectedMission(updatedMission);
      setMissionClaimName(updatedMission.id, claimForm.name.trim());
      setActionSuccess('Mission claimed successfully.');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Unable to claim mission');
    } finally {
      setClaimState('idle');
    }
  };

  const handleComplete = async () => {
    if (!selectedMission) return;
    if (!completeForm.name.trim()) {
      setActionError('Name is required to complete a mission.');
      setActionSuccess(null);
      return;
    }
    try {
      setCompleteState('submitting');
      setActionError(null);
      setActionSuccess(null);
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (operatorMode && operatorKey) {
        headers['x-operator-key'] = operatorKey;
      }
      const response = await fetch('/api/missions/complete', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          missionId: selectedMission.id,
          actor: completeForm.name.trim(),
          notes: completeForm.notes?.trim() || undefined,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error ?? 'Unable to complete mission');
      }
      const payload = await response.json();
      const updatedMission: Mission = payload.mission;
      setMissions((prev) => prev.map((mission) => (mission.id === updatedMission.id ? updatedMission : mission)));
      setSelectedMission(updatedMission);
      setActionSuccess('Mission marked as complete. Thank you!');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Unable to complete mission');
    } finally {
      setCompleteState('idle');
    }
  };

  const closeDetail = () => {
    setSelectedMission(null);
    setClaimForm(defaultClaimForm);
    setCompleteForm(defaultCompleteForm);
    setActionError(null);
    setActionSuccess(null);
  };

  const renderStatusTabs = () => (
    <div className="grid gap-4 md:grid-cols-3">
      {Object.entries(STATUS_META).map(([key, meta]) => {
        const id = key as StatusFilter;
        const active = statusFilter === id;
        return (
          <button
            key={id}
            onClick={() => setStatusFilter(id)}
            className={`rounded-xl border px-4 py-3 text-left transition ${
              active
                ? 'border-emerald-500 bg-emerald-500/10'
                : 'border-slate-700 hover:border-slate-500'
            }`}
          >
            <div className="flex items-center justify-between text-sm text-slate-400">
              <span className={`${meta.accent} rounded-full px-2 py-0.5 text-xs font-semibold`}>{meta.label}</span>
              <span className="font-semibold text-white">{statusCounts[id]}</span>
            </div>
            <p className="mt-2 text-sm text-slate-400">{meta.description}</p>
          </button>
        );
      })}
    </div>
  );

  const renderFilters = () => (
    <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <label className="flex flex-col text-sm text-slate-400">
        Priority
        <select
          className="mt-1 rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
          value={priorityFilter}
          onChange={(event) => setPriorityFilter(event.target.value)}
        >
          <option value="all">All priorities</option>
          <option value="P0">P0 · Critical</option>
          <option value="P1">P1 · High</option>
          <option value="P2">P2 · Strategic</option>
          <option value="P3">P3 · Stretch</option>
        </select>
      </label>
      <label className="flex flex-col text-sm text-slate-400">
        Role
        <select
          className="mt-1 rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
          value={roleFilter}
          onChange={(event) => setRoleFilter(event.target.value)}
        >
          <option value="all">Any contributor</option>
          {roleOptions.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col text-sm text-slate-400">
        Time budget
        <select
          className="mt-1 rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
          value={timeFilter}
          onChange={(event) => setTimeFilter(event.target.value as TimeFilter)}
        >
          {TIME_FILTERS.map((filter) => (
            <option key={filter.id} value={filter.id}>
              {filter.label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col text-sm text-slate-400">
        Visibility
        <select
          className={`mt-1 rounded-lg border px-3 py-2 text-white focus:outline-none ${
            operatorMode ? 'border-slate-700 bg-slate-900/60 focus:border-emerald-500' : 'border-slate-800 bg-slate-900/30 text-slate-500'
          }`}
          value={visibilityFilter}
          onChange={(event) => setVisibilityFilter(event.target.value as VisibilityFilter)}
          disabled={!operatorMode}
        >
          <option value="public">Public missions</option>
          <option value="all">All missions</option>
          <option value="internal">Internal only</option>
        </select>
      </label>
    </div>
  );

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-white md:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-emerald-400">Mission Control</p>
            <h1 className="mt-2 text-4xl font-semibold">Adaptive Mission Board</h1>
            <p className="mt-2 max-w-2xl text-slate-400">
              Claim regenerative work that fits your expertise and time budget. Operators can toggle internal mode to review sensitive queues.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={fetchMissions}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 hover:border-emerald-500"
              disabled={loading}
            >
              {loading ? 'Refreshing…' : 'Refresh feed'}
            </button>
            <button
              onClick={handleOperatorToggle}
              className={`rounded-lg px-4 py-2 text-sm font-semibold ${
                operatorMode
                  ? 'border border-emerald-500 text-emerald-300'
                  : 'border border-slate-700 text-slate-200 hover:border-emerald-500'
              }`}
            >
              {operatorMode ? 'Exit operator mode' : 'Operator access'}
            </button>
          </div>
        </header>

        <div className="mt-6">
          {renderStatusTabs()}
          <div className="mt-6 flex flex-col gap-4 md:flex-row">
            <input
              type="search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search by mission, role, or principle"
              className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2 text-sm focus:border-emerald-500 focus:outline-none"
            />
          </div>
          {renderFilters()}
        </div>

        {error && (
          <div className="mt-6 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}

        <section className="mt-8">
          {loading ? (
            <p className="text-slate-400">Loading missions…</p>
          ) : filteredMissions.length === 0 ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 px-6 py-10 text-center text-slate-400">
              <p>No missions match the current filters. Try broadening your search.</p>
            </div>
          ) : (
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {filteredMissions.map((mission) => {
                const status = toUiStatus(mission.status);
                const isInternal = visibilityOf(mission) === 'internal';
                return (
                  <button
                    key={mission.id}
                    onClick={() => {
                      setSelectedMission(mission);
                      setClaimForm({ name: localClaims[mission.id] ?? '', notes: '' });
                      setCompleteForm({ name: localClaims[mission.id] ?? '', notes: '' });
                      setActionError(null);
                      setActionSuccess(null);
                    }}
                    className="relative h-full rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-left transition hover:border-emerald-500 hover:bg-slate-900"
                  >
                    <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
                      <span className="font-semibold text-emerald-300">{mission.priority ?? 'P2'}</span>
                      <span>{mission.id}</span>
                    </div>
                    <h3 className="mt-3 text-xl font-semibold leading-snug">{mission.title}</h3>
                    <p className="mt-2 text-sm text-slate-400 line-clamp-2">
                      {mission.regenerative_impact ?? mission.principle ?? 'Autonomy requires evidence. Help the Nervous System see the truth faster.'}
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-400">
                      <span className="rounded-full border border-slate-700 px-2 py-0.5">
                        {mission.role_needed ?? 'Any role'}
                      </span>
                      <span className="rounded-full border border-slate-700 px-2 py-0.5">
                        {formatTimeEstimate(mission.time_estimate_minutes)}
                      </span>
                      <span className={`rounded-full px-2 py-0.5 ${STATUS_META[status].accent}`}>
                        {STATUS_META[status].label}
                      </span>
                      {isInternal && (
                        <span className="rounded-full border border-amber-400/40 px-2 py-0.5 text-amber-300">
                          Internal
                        </span>
                      )}
                    </div>
                    <div className="mt-4 text-sm text-slate-400">
                      <span className="text-slate-500">Owner:</span> {mission.owner ?? 'OPEN'}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </section>
      </div>

      {selectedMission && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 px-4 py-8">
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.4em] text-emerald-400">Mission Brief</p>
                <h2 className="mt-2 text-3xl font-semibold leading-tight">{selectedMission.title}</h2>
                <p className="mt-2 text-sm text-slate-400">
                  {selectedMission.regenerative_impact ?? 'This mission ladders up to the regenerative arc.'}
                </p>
              </div>
              <button
                onClick={closeDetail}
                className="rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-400 hover:border-emerald-500"
              >
                Close
              </button>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
                <p><span className="text-slate-500">Mission ID:</span> {selectedMission.id}</p>
                <p className="mt-2"><span className="text-slate-500">Priority:</span> {selectedMission.priority ?? 'P2'}</p>
                <p className="mt-2"><span className="text-slate-500">Owner:</span> {selectedMission.owner ?? 'OPEN'}</p>
                <p className="mt-2"><span className="text-slate-500">Status:</span> {selectedMission.status ?? 'Available'}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
                <p><span className="text-slate-500">Constitution principle:</span> {selectedMission.principle ?? '—'}</p>
                <p className="mt-2"><span className="text-slate-500">Role needed:</span> {selectedMission.role_needed ?? 'Any contributor'}</p>
                <p className="mt-2"><span className="text-slate-500">Time estimate:</span> {formatTimeEstimate(selectedMission.time_estimate_minutes)}</p>
                <p className="mt-2"><span className="text-slate-500">Visibility:</span> {visibilityOf(selectedMission) === 'internal' ? 'Internal (operators only)' : 'Public'}</p>
              </div>
            </div>

            {selectedMission.status_text && (
              <div className="mt-4 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
                {selectedMission.status_text}
              </div>
            )}

            <div className="mt-6 grid gap-6 md:grid-cols-2">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Mission details</h3>
                <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-300">
                  <li>
                    <span className="text-slate-500">Regenerative impact:</span> {selectedMission.regenerative_impact ?? 'Extend the nervous system with verifiable action.'}
                  </li>
                  <li>
                    <span className="text-slate-500">Brief path:</span> {selectedMission.path ?? 'Refer to missions repository'}
                  </li>
                </ul>
              </div>
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Activity</h3>
                <div className="mt-3 space-y-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
                  {selectedMission.history && selectedMission.history.length > 0 ? (
                    selectedMission.history
                      .slice()
                      .reverse()
                      .map((entry) => (
                        <div key={entry.at} className="border-b border-slate-800 pb-3 last:border-0 last:pb-0">
                          <p className="text-xs uppercase tracking-wide text-slate-500">{entry.action}</p>
                          <p className="mt-1 text-white">{entry.by}</p>
                          <p className="text-xs text-slate-500">{new Date(entry.at).toLocaleString()}</p>
                          {entry.notes && <p className="mt-1 text-slate-400">{entry.notes}</p>}
                        </div>
                      ))
                  ) : (
                    <p className="text-slate-400">No activity recorded yet.</p>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-6 grid gap-6 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                <h4 className="text-sm font-semibold uppercase tracking-wide text-emerald-300">Claim this mission</h4>
                <p className="mt-2 text-sm text-slate-400">
                  Enter your name or handle to take ownership. The system will log this entry publicly.
                </p>
                <input
                  type="text"
                  value={claimForm.name}
                  onChange={(event) => setClaimForm((prev) => ({ ...prev, name: event.target.value }))}
                  placeholder="Your name or handle"
                  className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                />
                <textarea
                  value={claimForm.notes}
                  onChange={(event) => setClaimForm((prev) => ({ ...prev, notes: event.target.value }))}
                  placeholder="Optional note (e.g., plan, contact info)"
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                  rows={3}
                />
                <button
                  onClick={handleClaim}
                  disabled={claimState === 'submitting'}
                  className="mt-4 w-full rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {claimState === 'submitting' ? 'Claiming…' : 'Claim mission'}
                </button>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-200">Mark as complete</h4>
                <p className="mt-2 text-sm text-slate-400">Provide proof-of-work links or context. Operators review completion logs daily.</p>
                <input
                  type="text"
                  value={completeForm.name}
                  onChange={(event) => setCompleteForm((prev) => ({ ...prev, name: event.target.value }))}
                  placeholder="Your name"
                  className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                />
                <textarea
                  value={completeForm.notes}
                  onChange={(event) => setCompleteForm((prev) => ({ ...prev, notes: event.target.value }))}
                  placeholder="Evidence, links, or completion notes"
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                  rows={3}
                />
                <button
                  onClick={handleComplete}
                  disabled={completeState === 'submitting'}
                  className="mt-4 w-full rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 hover:border-emerald-500 disabled:opacity-50"
                >
                  {completeState === 'submitting' ? 'Submitting…' : 'Complete mission'}
                </button>
              </div>
            </div>

            {(actionError || actionSuccess) && (
              <div className="mt-4 rounded-lg border px-4 py-3 text-sm"
                style={{
                  borderColor: actionError ? 'rgba(248,113,113,0.4)' : 'rgba(16,185,129,0.4)',
                  backgroundColor: actionError ? 'rgba(248,113,113,0.1)' : 'rgba(16,185,129,0.1)',
                  color: actionError ? '#fecaca' : '#6ee7b7',
                }}
              >
                {actionError ?? actionSuccess}
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
