'use client';

import { useState } from 'react';
import { Sprint } from '../types';
import { Edit, Trash2, ExternalLink, Plus } from 'lucide-react';

interface SprintTableProps {
  sprints: Sprint[];
  loading?: boolean;
  onEdit?: (sprint: Sprint) => void;
  onDelete?: (id: string) => void;
  onCreate?: () => void;
}

export default function SprintTable({ 
  sprints, 
  loading = false, 
  onEdit, 
  onDelete, 
  onCreate 
}: SprintTableProps) {
  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'Done': return 'bg-green-100 text-green-700 border-green-200 dark:bg-green-500/20 dark:text-green-400 dark:border-green-500/30';
      case 'Active': return 'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-500/20 dark:text-blue-400 dark:border-blue-500/30';
      case 'Pending': return 'bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-500/20 dark:text-yellow-400 dark:border-yellow-500/30';
      default: return 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-500/20 dark:text-slate-400 dark:border-slate-500/30';
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700 shadow-md">
        <div className="animate-pulse">
          <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded w-32 mb-4"></div>
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex space-x-4 mb-3">
              <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded flex-1"></div>
              <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20"></div>
              <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-16"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-700 shadow-md">
      {/* Header */}
      <div className="p-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Sprints</h3>
          {onCreate && (
            <button
              onClick={onCreate}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
            >
              <Plus size={16} />
              New Sprint
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-100 dark:bg-slate-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Sprint
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Developer
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Time (hrs)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {sprints.map((sprint) => (
              <tr key={sprint.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                <td className="px-6 py-4">
                  <div>
                    <div className="text-sm font-medium text-slate-900 dark:text-white">
                      {sprint.fields.Name || 'Untitled Sprint'}
                    </div>
                    <div className="text-sm text-slate-500 dark:text-slate-400">
                      {sprint.fields.Sprint_ID}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-slate-700 dark:text-slate-300">
                  {sprint.fields.Dev_Name || 'Unassigned'}
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full border ${getStatusColor(sprint.fields.Status)}`}>
                    {sprint.fields.Status || 'Unknown'}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-slate-700 dark:text-slate-300">
                  {sprint.fields.Time_Spent_hr || 0}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    {sprint.fields.Proof_URL && (
                      <a
                        href={sprint.fields.Proof_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1 text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-primary-400 transition-colors"
                      >
                        <ExternalLink size={16} />
                      </a>
                    )}
                    {onEdit && (
                      <button
                        onClick={() => onEdit(sprint)}
                        className="p-1 text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 transition-colors"
                      >
                        <Edit size={16} />
                      </button>
                    )}
                    {onDelete && (
                      <button
                        onClick={() => onDelete(sprint.id)}
                        className="p-1 text-slate-500 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {sprints.length === 0 && (
        <div className="p-12 text-center">
          <div className="text-slate-600 dark:text-slate-400 mb-2">No sprints found</div>
          <div className="text-sm text-slate-500 dark:text-slate-500">Create your first sprint to get started</div>
        </div>
      )}
    </div>
  );
}