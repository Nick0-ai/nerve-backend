import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Play, ShieldCheck, Globe, Zap } from 'lucide-react'

const links = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/simulate', label: 'Simulate', icon: Play },
  { to: '/checkpoint', label: 'Checkpoint', icon: ShieldCheck },
  { to: '/map', label: 'World Map', icon: Globe },
]

export default function Sidebar() {
  return (
    <aside className="w-64 border-r border-border bg-white flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center gap-3 px-6 border-b border-border">
        <div className="w-8 h-8 rounded-lg bg-nerve flex items-center justify-center">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <div>
          <span className="font-bold text-lg tracking-tight">NERVE</span>
          <span className="text-xs text-text-secondary ml-1.5 font-mono">v1.0</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-nerve/10 text-nerve-dark'
                  : 'text-text-secondary hover:bg-surface-2 hover:text-text'
              }`
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Status */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 px-4 py-2">
          <div className="w-2 h-2 rounded-full bg-green-accent animate-pulse-dot" />
          <span className="text-xs text-text-secondary">Engine running</span>
        </div>
        <div className="px-4 text-[10px] font-mono text-text-secondary/60">
          3 regions monitored
        </div>
      </div>
    </aside>
  )
}
