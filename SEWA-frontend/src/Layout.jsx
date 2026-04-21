import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { createPageUrl } from './utils';
import { Activity, FileText, Shield, LogOut, User } from 'lucide-react';
import { cn } from "@/lib/utils";

function getStoredUser() {
  try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; }
}

export default function Layout({ children, currentPageName }) {
  const navigate = useNavigate();
  const user = getStoredUser();
  const isAdmin = user?.role === 'Administrator';

  // Nav items depend on role
  const navItems = isAdmin
    ? [
      { name: 'Admin Panel', page: 'Admin', icon: Shield },
      { name: 'Audit Log', page: 'AuditLog', icon: FileText },
    ]
    : [
      { name: 'Dashboard', page: 'Dashboard', icon: Activity },
      { name: 'Audit Log', page: 'AuditLog', icon: FileText },
    ];

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('user');
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-slate-50">

      {/* Top Navigation Bar */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-[1800px] mx-auto px-4 lg:px-6">
          <div className="flex items-center justify-between h-14">

            {/* Left: Logo + Nav links */}
            <div className="flex items-center gap-6">
              {/* Logo */}
              <Link to="/" className="flex items-center gap-2 mr-2">
                <div className="bg-indigo-600 p-1.5 rounded-md">
                  <Activity className="w-4 h-4 text-white" />
                </div>
                <span className="font-bold text-slate-800 text-sm hidden sm:block">SEWA</span>
              </Link>

              {/* Nav links */}
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = currentPageName === item.page;
                return (
                  <Link
                    key={item.page}
                    to={createPageUrl(item.page)}
                    className={cn(
                      "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                      isActive
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-slate-600 hover:text-slate-800 hover:bg-slate-50"
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {item.name}
                  </Link>
                );
              })}
            </div>

            {/* Right: User info + logout */}
            <div className="flex items-center gap-3">
              {user && (
                <div className="flex items-center gap-2 text-sm">
                  <div className={cn(
                    "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white",
                    isAdmin ? "bg-purple-600" : "bg-indigo-600"
                  )}>
                    {user.name?.charAt(0) ?? <User className="w-3 h-3" />}
                  </div>
                  <div className="hidden md:block">
                    <p className="font-medium text-slate-800 leading-none">{user.name}</p>
                    <p className={cn(
                      "text-xs leading-none mt-0.5",
                      isAdmin ? "text-purple-600 font-semibold" : "text-slate-400"
                    )}>
                      {user.role}
                      {user.department ? ` · ${user.department}` : ''}
                    </p>
                  </div>
                </div>
              )}
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-slate-500 hover:text-red-600 hover:bg-red-50 transition-colors"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {children}
    </div>
  );
}