'use client';

import { useState, useEffect } from 'react';
import { Sprint } from '../../../types';
import { useApi } from '../../../shared/hooks/useApi';
import { api } from '../../../lib/api';
import { useNotifications } from '../../../shared/contexts/NotificationContext';
import SprintFilters from './SprintFilters';
import SprintKanban from './SprintKanban';
import SprintModal from './SprintModal';
import SprintCard from './SprintCard';
import { Plus, Grid, List, Trash2, Edit } from 'lucide-react';

export default function SprintManagement() {
  const { data: sprintsData, loading, refetch } = useApi(() => api.getSprints(), []);
  const { addNotification } = useNotifications();
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [filteredSprints, setFilteredSprints] = useState<Sprint[]>([]);
  const [selectedSprints, setSelectedSprints] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<'kanban' | 'grid'>('kanban');
  const [showModal, setShowModal] = useState(false);
  const [editingSprint, setEditingSprint] = useState<Sprint | undefined>();
  
  // Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [developerFilter, setDeveloperFilter] = useState('All');

  useEffect(() => {
    if (sprintsData?.records) {
      setSprints(sprintsData.records);
      setFilteredSprints(sprintsData.records);
    }
  }, [sprintsData]);

  // Apply filters
  useEffect(() => {
    let filtered = sprints;

    if (searchQuery) {
      filtered = filtered.filter(sprint => 
        sprint.fields.Name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        sprint.fields.Sprint_ID?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        sprint.fields.Dev_Name?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    if (statusFilter !== 'All') {
      filtered = filtered.filter(sprint => sprint.fields.Status === statusFilter);
    }

    if (developerFilter !== 'All') {
      filtered = filtered.filter(sprint => sprint.fields.Dev_Name === developerFilter);
    }

    setFilteredSprints(filtered);
  }, [sprints, searchQuery, statusFilter, developerFilter]);

  const developers = Array.from(new Set(
    sprints.map(sprint => sprint.fields.Dev_Name).filter(Boolean)
  )) as string[];

  const handleCreateSprint = async (sprintData: Partial<Sprint['fields']>) => {
    try {
      console.log('Creating sprint:', sprintData);
      await api.createSprint(sprintData);
      console.log('Sprint created successfully, adding notification');
      addNotification({
        type: 'success',
        title: 'Sprint Created',
        message: `${sprintData.Name || sprintData.Sprint_ID} assigned to ${sprintData.Dev_Name}`,
        data: { fields: sprintData, eventTime: new Date() }
      });
      console.log('Notification added, refetching data');
      refetch();
    } catch (error) {
      console.error('Failed to create sprint:', error);
      addNotification({
        type: 'error',
        title: 'Failed to Create Sprint',
        message: 'An error occurred while creating the sprint',
      });
    }
  };

  const handleUpdateSprint = async (sprintData: Partial<Sprint['fields']>) => {
    if (!editingSprint) return;
    try {
      await api.updateSprint(editingSprint.id, sprintData);
      
      // Notify if status changed to Done
      if (sprintData.Status === 'Done' && editingSprint.fields.Status !== 'Done') {
        addNotification({
          type: 'proof',
          title: 'Sprint Completed',
          message: `${editingSprint.fields.Name || editingSprint.fields.Sprint_ID} completed by ${editingSprint.fields.Dev_Name}`,
          data: { ...editingSprint, fields: { ...editingSprint.fields, ...sprintData }, eventTime: new Date() }
        });
      }
      
      refetch();
    } catch (error) {
      console.error('Failed to update sprint:', error);
      addNotification({
        type: 'error',
        title: 'Failed to Update Sprint',
        message: 'An error occurred while updating the sprint',
      });
    }
  };

  const handleDeleteSprint = async (id: string) => {
    if (confirm('Are you sure you want to delete this sprint?')) {
      try {
        await api.deleteSprint(id);
        addNotification({
          type: 'warning',
          title: 'Sprint Deleted',
          message: 'Sprint has been removed from the system',
        });
        refetch();
      } catch (error) {
        console.error('Failed to delete sprint:', error);
        addNotification({
          type: 'error',
          title: 'Failed to Delete Sprint',
          message: 'An error occurred while deleting the sprint',
        });
      }
    }
  };

  const handleStatusChange = async (sprintId: string, newStatus: string) => {
    try {
      await api.updateSprint(sprintId, { Status: newStatus as 'Done' | 'Active' | 'Pending' });
      refetch();
    } catch (error) {
      console.error('Failed to update sprint status:', error);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedSprints.length === 0) return;
    if (confirm(`Delete ${selectedSprints.length} selected sprints?`)) {
      try {
        await Promise.all(selectedSprints.map(id => api.deleteSprint(id)));
        setSelectedSprints([]);
        refetch();
      } catch (error) {
        console.error('Failed to delete sprints:', error);
      }
    }
  };

  const handleSelectSprint = (id: string, selected: boolean) => {
    if (selected) {
      setSelectedSprints([...selectedSprints, id]);
    } else {
      setSelectedSprints(selectedSprints.filter(sprintId => sprintId !== id));
    }
  };

  const handleSelectAll = () => {
    if (selectedSprints.length === filteredSprints.length) {
      setSelectedSprints([]);
    } else {
      setSelectedSprints(filteredSprints.map(sprint => sprint.id));
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-48 bg-gray-200 dark:bg-slate-700 rounded-xl animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-black dark:text-white">Sprint Management</h2>
          <p className="text-gray-600 dark:text-gray-400">
            {filteredSprints.length} of {sprints.length} sprints
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Bulk Actions */}
          {selectedSprints.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {selectedSprints.length} selected
              </span>
              <button
                onClick={handleBulkDelete}
                className="p-2 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/20 rounded-lg transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </div>
          )}

          {/* View Toggle */}
          <div className="flex bg-gray-100 dark:bg-slate-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode('kanban')}
              className={`p-2 rounded ${viewMode === 'kanban' ? 'bg-white dark:bg-slate-700 shadow' : ''}`}
            >
              <Grid size={16} />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded ${viewMode === 'grid' ? 'bg-white dark:bg-slate-700 shadow' : ''}`}
            >
              <List size={16} />
            </button>
          </div>

          {/* Create Button */}
          <button
            onClick={() => {
              setEditingSprint(undefined);
              setShowModal(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <Plus size={16} />
            New Sprint
          </button>
        </div>
      </div>

      {/* Filters */}
      <SprintFilters
        onSearch={setSearchQuery}
        onStatusFilter={setStatusFilter}
        onDeveloperFilter={setDeveloperFilter}
        developers={developers}
        selectedStatus={statusFilter}
        selectedDeveloper={developerFilter}
      />

      {/* Select All */}
      {filteredSprints.length > 0 && (
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={selectedSprints.length === filteredSprints.length}
            onChange={handleSelectAll}
            className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
          />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Select all visible sprints
          </span>
        </div>
      )}

      {/* Content */}
      {viewMode === 'kanban' ? (
        <SprintKanban
          sprints={filteredSprints}
          onEdit={(sprint) => {
            setEditingSprint(sprint);
            setShowModal(true);
          }}
          onDelete={handleDeleteSprint}
          onStatusChange={handleStatusChange}
          onSelect={handleSelectSprint}
          selectedSprints={selectedSprints}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSprints.map(sprint => (
            <SprintCard
              key={sprint.id}
              sprint={sprint}
              onEdit={(sprint) => {
                setEditingSprint(sprint);
                setShowModal(true);
              }}
              onDelete={handleDeleteSprint}
              onSelect={handleSelectSprint}
              isSelected={selectedSprints.includes(sprint.id)}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {filteredSprints.length === 0 && !loading && (
        <div className="text-center py-12">
          <div className="text-gray-400 dark:text-gray-600 mb-4">
            <Grid size={48} className="mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-black dark:text-white mb-2">
            No sprints found
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {searchQuery || statusFilter !== 'All' || developerFilter !== 'All'
              ? 'Try adjusting your filters'
              : 'Create your first sprint to get started'
            }
          </p>
          <button
            onClick={() => {
              setEditingSprint(undefined);
              setShowModal(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <Plus size={16} />
            Create Sprint
          </button>
        </div>
      )}

      {/* Modal */}
      <SprintModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSave={editingSprint ? handleUpdateSprint : handleCreateSprint}
        sprint={editingSprint}
        developers={developers}
      />
    </div>
  );
}