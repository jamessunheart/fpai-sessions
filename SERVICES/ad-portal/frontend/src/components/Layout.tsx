import { Outlet, NavLink } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Package, 
  Megaphone, 
  Palette, 
  BarChart3,
  Sparkles
} from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/offers', label: 'Offers', icon: Package },
  { path: '/campaigns', label: 'Campaigns', icon: Megaphone },
  { path: '/creatives', label: 'Creatives', icon: Palette },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
]

export default function Layout() {
  return (
    <div className="min-h-screen bg-slate-950 gradient-mesh">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-screen w-64 bg-slate-900/80 backdrop-blur-xl border-r border-slate-800/50 z-50">
        {/* Logo */}
        <div className="p-6 border-b border-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-display font-bold text-lg text-white">Ad Portal</h1>
              <p className="text-xs text-slate-500">Full Potential AI</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200',
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                )
              }
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Bottom section */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-800/50">
          <div className="card p-4">
            <p className="text-xs text-slate-500 mb-1">Quick Stats</p>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Today's Profit</span>
              <span className="text-emerald-400 font-mono">+$0.00</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="ml-64 min-h-screen">
        <Outlet />
      </main>
    </div>
  )
}


