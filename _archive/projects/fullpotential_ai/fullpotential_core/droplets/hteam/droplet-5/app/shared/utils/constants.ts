export const REFRESH_INTERVAL = 30000;

export const STATUS_COLORS = {
  OK: 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400',
  ERROR: 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400',
  WARNING: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-500/20 dark:text-yellow-400',
} as const;

export const CHANGE_TYPES = {
  positive: 'text-green-600 dark:text-green-500',
  negative: 'text-red-600 dark:text-red-500', 
  neutral: 'text-black dark:text-slate-400'
} as const;