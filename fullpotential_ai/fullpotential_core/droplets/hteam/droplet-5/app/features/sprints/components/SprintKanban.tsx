import { Sprint } from '../../../types';
import SprintCard from './SprintCard';
import { Card } from '../../../shared/components';

interface SprintKanbanProps {
  sprints: Sprint[];
  onEdit: (sprint: Sprint) => void;
  onDelete: (id: string) => void;
  onStatusChange: (sprintId: string, newStatus: string) => void;
  onSelect: (id: string, selected: boolean) => void;
  selectedSprints: string[];
}

export default function SprintKanban({
  sprints,
  onEdit,
  onDelete,
  onStatusChange,
  onSelect,
  selectedSprints
}: SprintKanbanProps) {
  const columns = [
    { id: 'Pending', title: 'Pending', color: 'border-yellow-500' },
    { id: 'Active', title: 'Active', color: 'border-blue-500' },
    { id: 'Done', title: 'Done', color: 'border-green-500' }
  ];

  const getSprintsByStatus = (status: string) => {
    return sprints.filter(sprint => sprint.fields.Status === status);
  };

  const handleDrop = (e: React.DragEvent, newStatus: string) => {
    e.preventDefault();
    const sprintId = e.dataTransfer.getData('text/plain');
    onStatusChange(sprintId, newStatus);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {columns.map(column => {
        const columnSprints = getSprintsByStatus(column.id);
        
        return (
          <div key={column.id} className="space-y-4">
            {/* Column Header */}
            <div className={`border-l-4 ${column.color} pl-4`}>
              <h3 className="font-semibold text-black dark:text-white">
                {column.title}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {columnSprints.length} sprint{columnSprints.length !== 1 ? 's' : ''}
              </p>
            </div>

            {/* Drop Zone */}
            <div
              onDrop={(e) => handleDrop(e, column.id)}
              onDragOver={handleDragOver}
              className="min-h-96 space-y-3 p-2 rounded-lg border-2 border-dashed border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 transition-colors"
            >
              {columnSprints.map(sprint => (
                <div
                  key={sprint.id}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('text/plain', sprint.id);
                  }}
                  className="cursor-move"
                >
                  <SprintCard
                    sprint={sprint}
                    onEdit={onEdit}
                    onDelete={onDelete}
                    onSelect={onSelect}
                    isSelected={selectedSprints.includes(sprint.id)}
                  />
                </div>
              ))}
              
              {columnSprints.length === 0 && (
                <div className="flex items-center justify-center h-32 text-gray-400 dark:text-gray-600">
                  <p className="text-sm">Drop sprints here</p>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}