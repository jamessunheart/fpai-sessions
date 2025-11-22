'use client';

import { useState } from 'react';
import { 
  LayoutDashboard, 
  Zap, 
  Server, 
  BarChart3, 
  MessageSquare,
  Settings,
  Menu,
  X,
  LogOut,
  Cloud,
  Network
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../shared/contexts/AuthContext';
import ThemeToggle from '../shared/components/ThemeToggle';
import NotificationBell from '../shared/components/NotificationBell';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const menuItems = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'droplets', label: 'Droplets', icon: Network },
  { id: 'sprints', label: 'Sprints', icon: Zap },
  { id: 'infrastructure', label: 'Infrastructure', icon: Server },
  { id: 'multi-cloud', label: 'Multi-Cloud', icon: Cloud },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'team-support', label: 'Team Support', icon: MessageSquare },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { logout } = useAuth();
  const router = useRouter();

  return (
    <aside className={`${collapsed ? 'w-20' : 'w-64'} h-screen bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-slate-800 flex flex-col transition-all duration-300 ease-in-out`}>
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200 dark:border-slate-800">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Network className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-gray-900 dark:text-white">Dashboard</span>
          </div>
        )}
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            setCollapsed(!collapsed);
          }}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors text-gray-700 dark:text-gray-300"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <Menu className="w-5 h-5" /> : <X className="w-5 h-5" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    onTabChange(item.id);
                  }}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800'
                  }`}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  {!collapsed && <span className="font-medium text-sm">{item.label}</span>}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-gray-200 dark:border-slate-800 space-y-2">
        {!collapsed && (
          <div className="flex items-center gap-2 px-3 py-2">
            <NotificationBell />
            <ThemeToggle />
          </div>
        )}
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            logout();
            router.push('/login');
          }}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
          title={collapsed ? 'Logout' : undefined}
        >
          <LogOut className="w-5 h-5 flex-shrink-0" />
          {!collapsed && <span className="font-medium text-sm">Logout</span>}
        </button>
      </div>
    </aside>
  );
}