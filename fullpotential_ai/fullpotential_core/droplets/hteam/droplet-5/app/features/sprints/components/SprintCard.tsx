import { Sprint } from '../../../types';
import { Card } from '../../../shared/components';
import { Clock, User, Shield, MoreVertical } from 'lucide-react';
import { useState } from 'react';
import ProofModal from './ProofModal';

interface SprintCardProps {
  sprint: Sprint;
  onEdit: (sprint: Sprint) => void;
  onDelete: (id: string) => void;
  onSelect: (id: string, selected: boolean) => void;
  isSelected: boolean;
  isDragging?: boolean;
}

export default function SprintCard({ 
  sprint, 
  onEdit, 
  onDelete, 
  onSelect, 
  isSelected,
  isDragging = false 
}: SprintCardProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [showProofModal, setShowProofModal] = useState(false);

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'Done': return 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400';
      case 'Active': return 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400';
      case 'Pending': return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-500/20 dark:text-yellow-400';
      default: return 'bg-gray-100 text-gray-700 dark:bg-gray-500/20 dark:text-gray-400';
    }
  };

  return (
    <Card 
      className={`relative transition-all duration-200 ${
        isDragging ? 'rotate-2 scale-105 shadow-2xl' : ''
      } ${isSelected ? 'ring-2 ring-blue-500' : ''}`}
      hover
    >
      {/* Selection Checkbox */}
      <div className="absolute top-3 left-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelect(sprint.id, e.target.checked)}
          className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
        />
      </div>

      {/* Menu Button */}
      <div className="absolute top-3 right-3">
        <button
          onClick={() => setShowMenu(!showMenu)}
          className="p-1 hover:bg-gray-100 dark:hover:bg-slate-700 rounded transition-colors"
        >
          <MoreVertical size={16} className="text-gray-500 dark:text-gray-400" />
        </button>
        
        {showMenu && (
          <div className="absolute right-0 top-8 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg z-10 min-w-32">
            <button
              onClick={() => { onEdit(sprint); setShowMenu(false); }}
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-slate-700 text-black dark:text-white"
            >
              Edit
            </button>
            <button
              onClick={() => { onDelete(sprint.id); setShowMenu(false); }}
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-slate-700 text-red-600"
            >
              Delete
            </button>
          </div>
        )}
      </div>

      <div className="pt-8">
        {/* Header */}
        <div className="mb-3">
          <h3 className="font-semibold text-black dark:text-white truncate">
            {sprint.fields.Name || 'Untitled Sprint'}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {sprint.fields.Sprint_ID}
          </p>
        </div>

        {/* Status */}
        <div className="mb-3">
          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(sprint.fields.Status)}`}>
            {sprint.fields.Status || 'Unknown'}
          </span>
        </div>

        {/* Developer & Time */}
        <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 mb-3">
          <div className="flex items-center gap-1">
            <User size={14} />
            <span>{sprint.fields.Dev_Name || 'Unassigned'}</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock size={14} />
            <span>{sprint.fields.Time_Spent_hr || 0}h</span>
          </div>
        </div>

        {/* Notes */}
        {sprint.fields.Notes && (
          <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-3">
            {sprint.fields.Notes}
          </p>
        )}

        {/* Proof Button */}
        <button
          onClick={() => setShowProofModal(true)}
          className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 px-2 py-1 rounded transition-colors"
        >
          <Shield size={14} />
          View Proofs
        </button>
      </div>
      
      {/* Proof Modal */}
      <ProofModal
        isOpen={showProofModal}
        onClose={() => setShowProofModal(false)}
        sprintId={sprint.fields.Sprint_ID || ''}
        sprintName={sprint.fields.Name || 'Untitled Sprint'}
      />
    </Card>
  );
}