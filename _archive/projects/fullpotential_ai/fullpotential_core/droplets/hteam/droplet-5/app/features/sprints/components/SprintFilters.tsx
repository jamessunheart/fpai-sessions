import { Search, Filter, Calendar, User } from 'lucide-react';
import { useState } from 'react';

interface SprintFiltersProps {
  onSearch: (query: string) => void;
  onStatusFilter: (status: string) => void;
  onDeveloperFilter: (developer: string) => void;
  developers: string[];
  selectedStatus: string;
  selectedDeveloper: string;
}

export default function SprintFilters({
  onSearch,
  onStatusFilter,
  onDeveloperFilter,
  developers,
  selectedStatus,
  selectedDeveloper
}: SprintFiltersProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (value: string) => {
    setSearchQuery(value);
    onSearch(value);
  };

  const statuses = ['All', 'Pending', 'Active', 'Done'];

  return (
    <div className="flex flex-col sm:flex-row gap-4 mb-6">
      {/* Search */}
      <div className="relative flex-1">
        <Search size={20} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search sprints..."
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-black dark:text-white"
        />
      </div>

      {/* Status Filter */}
      <div className="relative">
        <Filter size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
        <select
          value={selectedStatus}
          onChange={(e) => onStatusFilter(e.target.value)}
          className="pl-10 pr-8 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 text-black dark:text-white min-w-32"
        >
          {statuses.map(status => (
            <option key={status} value={status}>{status}</option>
          ))}
        </select>
      </div>

      {/* Developer Filter */}
      <div className="relative">
        <User size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
        <select
          value={selectedDeveloper}
          onChange={(e) => onDeveloperFilter(e.target.value)}
          className="pl-10 pr-8 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 text-black dark:text-white min-w-40"
        >
          <option value="All">All Developers</option>
          {developers.map(dev => (
            <option key={dev} value={dev}>{dev}</option>
          ))}
        </select>
      </div>
    </div>
  );
}