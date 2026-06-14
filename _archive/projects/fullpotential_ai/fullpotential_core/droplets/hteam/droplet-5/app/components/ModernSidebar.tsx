'use client';

import { LayoutDashboard, Network, Zap, Server, Cloud, BarChart3, MessageSquare, Settings, LogOut, Menu, X, Users } from 'lucide-react';
import { useRouter, usePathname } from 'next/navigation';
import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../shared/contexts/AuthContext';
import ThemeToggle from '../shared/components/ThemeToggle';
import NotificationBell from '../shared/components/NotificationBell';

const menuItems = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, path: '/dashboard' },
  { id: 'droplets', label: 'Droplets', icon: Network, path: '/dashboard?view=droplets' },
  { id: 'sprints', label: 'Sprints', icon: Zap, path: '/sprints' },
  { id: 'infrastructure', label: 'Infrastructure', icon: Server, path: '/infrastructure' },
  { id: 'multi-cloud', label: 'Multi-Cloud', icon: Cloud, path: '/multi-cloud' },
  { id: 'chat', label: 'Chat Console', icon: MessageSquare, path: '/chat' },
  { id: 'team-support', label: 'Team Support', icon: Users, path: '/team-support' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, path: '/analytics' },
  { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
];

export default function ModernSidebar() {
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('sidebarCollapsed') === 'true';
    }
    return false;
  });
  const [rotatingIcon, setRotatingIcon] = useState<string | null>(null);
  const { logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  
  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', collapsed.toString());
  }, [collapsed]);
  
  const getActiveId = () => {
    if (typeof window === 'undefined') return 'overview';
    const searchParams = new URLSearchParams(window.location.search);
    const currentView = searchParams.get('view');

    if (pathname === '/dashboard' && currentView === 'droplets') return 'droplets';
    if (pathname === '/dashboard') return 'overview';
    const found = menuItems.find(item => pathname === item.path.split('?')[0]);
    return found?.id || 'overview';
  };

  const [activeId, setActiveId] = useState(getActiveId);

  useEffect(() => {
    const handleRouteChange = () => {
      setActiveId(getActiveId());
    };
    
    handleRouteChange();
    window.addEventListener('popstate', handleRouteChange);
    
    return () => window.removeEventListener('popstate', handleRouteChange);
  }, [pathname]);

  useEffect(() => {
    setActiveId(getActiveId());
  }, []);

  const handleNavigation = (item: typeof menuItems[0]) => {
    setActiveId(item.id);
    if (collapsed) {
      setRotatingIcon(item.id);
      setTimeout(() => {
        setRotatingIcon(null);
        router.push(item.path);
      }, 300);
    } else {
      router.push(item.path);
    }
  };

  return (
    <aside className={`${collapsed ? 'w-20' : 'w-72'} h-screen bg-gradient-to-b from-slate-50 via-slate-50 to-slate-100 dark:from-slate-900 dark:via-slate-900 dark:to-slate-950 border-r border-slate-200 dark:border-slate-800 flex flex-col transition-all duration-300 ease-in-out shadow-xl`}>
      <div className="h-20 flex items-center justify-between px-5 border-b border-slate-200 dark:border-slate-800">
        {!collapsed && (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Network className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Dashboard</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">Control Center</p>
            </div>
          </div>
        )}
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          className="p-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-all text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 shadow-sm"
        >
          {collapsed ? <Menu className="w-5 h-5" /> : <X className="w-5 h-5" />}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto py-6 px-4">
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeId === item.id;
            
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => handleNavigation(item)}
                  className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/20 dark:shadow-blue-500/30'
                      : 'text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-white dark:hover:bg-slate-800 hover:shadow-sm'
                  }`}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon className={`w-5 h-5 flex-shrink-0 transition-transform duration-300 ${rotatingIcon === item.id ? 'rotate-[360deg] scale-110' : ''}`} />
                  {!collapsed && <span className="font-medium text-sm">{item.label}</span>}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="p-4 border-t border-slate-200 dark:border-slate-800 space-y-3">
        {!collapsed && (
          <div className="flex items-center justify-center gap-3 px-4 py-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm">
            <NotificationBell />
            <ThemeToggle />
          </div>
        )}
        <button
          type="button"
          onClick={() => {
            if (collapsed) {
              setRotatingIcon('logout');
              setTimeout(() => setRotatingIcon(null), 300);
            }
            logout();
            router.push('/login');
          }}
          className="w-full flex items-center gap-4 px-4 py-3.5 rounded-xl text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all hover:shadow-md"
          title={collapsed ? 'Logout' : undefined}
        >
          <LogOut className={`w-5 h-5 flex-shrink-0 transition-transform duration-300 ${rotatingIcon === 'logout' ? 'rotate-[360deg] scale-110' : ''}`} />
          {!collapsed && <span className="font-medium text-sm">Logout</span>}
        </button>
      </div>
    </aside>
  );
}
