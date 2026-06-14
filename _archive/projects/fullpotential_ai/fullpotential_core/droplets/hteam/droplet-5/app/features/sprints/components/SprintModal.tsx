import { useState, useEffect } from 'react';
import { X, Save, User, Clock, FileText, Link } from 'lucide-react';
import { Sprint } from '../../../types';

interface SprintModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (sprintData: Partial<Sprint['fields']>) => void;
  sprint?: Sprint;
  developers: string[];
}

export default function SprintModal({
  isOpen,
  onClose,
  onSave,
  sprint,
  developers
}: SprintModalProps) {
  const [formData, setFormData] = useState<{
    Name: string;
    Sprint_ID: string;
    Dev_Name: string;
    Status: 'Done' | 'Active' | 'Pending';
    Time_Spent_hr: number;
    Notes: string;
    Proof_URL: string;
  }>({
    Name: '',
    Sprint_ID: '',
    Dev_Name: '',
    Status: 'Pending',
    Time_Spent_hr: 0,
    Notes: '',
    Proof_URL: ''
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (sprint) {
      setFormData({
        Name: sprint.fields.Name || '',
        Sprint_ID: sprint.fields.Sprint_ID || '',
        Dev_Name: sprint.fields.Dev_Name || '',
        Status: (sprint.fields.Status as 'Done' | 'Active' | 'Pending') || 'Pending',
        Time_Spent_hr: sprint.fields.Time_Spent_hr || 0,
        Notes: sprint.fields.Notes || '',
        Proof_URL: sprint.fields.Proof_URL || ''
      });
    } else {
      setFormData({
        Name: '',
        Sprint_ID: `SPRINT-${Date.now()}`,
        Dev_Name: '',
        Status: 'Pending' as 'Done' | 'Active' | 'Pending',
        Time_Spent_hr: 0,
        Notes: '',
        Proof_URL: ''
      });
    }
    setErrors({});
  }, [sprint, isOpen]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.Name.trim()) {
      newErrors.Name = 'Sprint name is required';
    }
    if (!formData.Sprint_ID.trim()) {
      newErrors.Sprint_ID = 'Sprint ID is required';
    }
    if (!formData.Dev_Name.trim()) {
      newErrors.Dev_Name = 'Developer is required';
    }
    if (formData.Time_Spent_hr < 0) {
      newErrors.Time_Spent_hr = 'Time cannot be negative';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateForm()) {
      onSave(formData);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-slate-700">
          <h2 className="text-2xl font-bold text-black dark:text-white">
            {sprint ? 'Edit Sprint' : 'Create New Sprint'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X size={20} className="text-black dark:text-white" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Sprint Name */}
          <div>
            <label className="block text-sm font-medium text-black dark:text-white mb-2">
              Sprint Name *
            </label>
            <input
              type="text"
              value={formData.Name}
              onChange={(e) => setFormData({ ...formData, Name: e.target.value })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 text-black dark:text-white"
              placeholder="Enter sprint name"
            />
            {errors.Name && <p className="text-red-500 text-sm mt-1">{errors.Name}</p>}
          </div>

          {/* Sprint ID */}
          <div>
            <label className="block text-sm font-medium text-black dark:text-white mb-2">
              Sprint ID *
            </label>
            <input
              type="text"
              value={formData.Sprint_ID}
              onChange={(e) => setFormData({ ...formData, Sprint_ID: e.target.value })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 text-black dark:text-white"
              placeholder="SPRINT-001"
            />
            {errors.Sprint_ID && <p className="text-red-500 text-sm mt-1">{errors.Sprint_ID}</p>}
          </div>

          {/* Developer & Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-black dark:text-white mb-2">
                Developer *
              </label>
              <select
                value={formData.Dev_Name}
                onChange={(e) => setFormData({ ...formData, Dev_Name: e.target.value })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 text-black dark:text-white"
              >
                <option value="">Select Developer</option>
                {developers.map(dev => (
                  <option key={dev} value={dev}>{dev}</option>
                ))}
              </select>
              {errors.Dev_Name && <p className="text-red-500 text-sm mt-1">{errors.Dev_Name}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-black dark:text-white mb-2">
                Status
              </label>
              <select
                value={formData.Status}
                onChange={(e) => setFormData({ ...formData, Status: e.target.value as 'Done' | 'Active' | 'Pending' })}
                className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 text-black dark:text-white"
              >
                <option value="Pending">Pending</option>
                <option value="Active">Active</option>
                <option value="Done">Done</option>
              </select>
            </div>
          </div>

          {/* Time Spent */}
          <div>
            <label className="block text-sm font-medium text-black dark:text-white mb-2">
              Time Spent (hours)
            </label>
            <input
              type="number"
              min="0"
              step="0.5"
              value={formData.Time_Spent_hr}
              onChange={(e) => setFormData({ ...formData, Time_Spent_hr: parseFloat(e.target.value) || 0 })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 text-black dark:text-white"
            />
            {errors.Time_Spent_hr && <p className="text-red-500 text-sm mt-1">{errors.Time_Spent_hr}</p>}
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-black dark:text-white mb-2">
              Notes
            </label>
            <textarea
              rows={3}
              value={formData.Notes}
              onChange={(e) => setFormData({ ...formData, Notes: e.target.value })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 text-black dark:text-white"
              placeholder="Add any notes or comments..."
            />
          </div>

          {/* Proof URL */}
          <div>
            <label className="block text-sm font-medium text-black dark:text-white mb-2">
              Proof URL
            </label>
            <input
              type="url"
              value={formData.Proof_URL}
              onChange={(e) => setFormData({ ...formData, Proof_URL: e.target.value })}
              className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 text-black dark:text-white"
              placeholder="https://..."
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              <Save size={16} />
              {sprint ? 'Update Sprint' : 'Create Sprint'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}