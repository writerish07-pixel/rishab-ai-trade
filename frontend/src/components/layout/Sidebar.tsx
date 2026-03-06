'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, TrendingUp, Briefcase, Bell,
  Settings, BarChart2, BookOpen, LogOut, Zap
} from 'lucide-react';
import { authAPI } from '@/services/api';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/signals', label: 'AI Signals', icon: Zap },
  { href: '/portfolio', label: 'Portfolio', icon: Briefcase },
  { href: '/orders', label: 'Orders', icon: BookOpen },
  { href: '/charts', label: 'Charts', icon: BarChart2 },
  { href: '/alerts', label: 'Alerts', icon: Bell },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-14 bg-bg-secondary border-r border-border flex flex-col items-center py-3 gap-1 flex-shrink-0">
      {/* Logo */}
      <div className="w-9 h-9 bg-accent-blue rounded-xl flex items-center justify-center mb-4">
        <TrendingUp className="w-5 h-5 text-white" />
      </div>

      {/* Nav items */}
      <nav className="flex-1 flex flex-col gap-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all group relative ${
                active
                  ? 'bg-accent-blue text-white'
                  : 'text-text-muted hover:bg-bg-hover hover:text-text-primary'
              }`}
            >
              <Icon className="w-5 h-5" />
              {/* Tooltip */}
              <span className="absolute left-12 bg-bg-card text-text-primary text-xs px-2 py-1 rounded-md
                border border-border whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-50
                transition-opacity">
                {label}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <button
        onClick={authAPI.logout}
        title="Logout"
        className="w-10 h-10 rounded-xl text-text-muted hover:bg-bear/20 hover:text-bear transition-all flex items-center justify-center"
      >
        <LogOut className="w-5 h-5" />
      </button>
    </aside>
  );
}
