import React from 'react';
import { LayoutDashboard, User, FileSpreadsheet, FileCheck2, BarChart3, Shield } from 'lucide-react';

const items = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'profile', label: 'Business Profile', icon: User },
  { id: 'recommendations', label: 'Scheme Matches', icon: FileSpreadsheet },
  { id: 'verification', label: 'Document OCR', icon: FileCheck2 },
  { id: 'analytics', label: 'Analytics Hub', icon: BarChart3 },
  { id: 'admin', label: 'Admin Panel', icon: Shield },
];

const Sidebar = ({ activeTab, setActiveTab }) => {
  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col shrink-0">
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-[#1a365d] text-white'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="px-3 pb-4">
        <div className="rounded-lg bg-gray-50 border border-gray-200 p-3">
          <p className="text-xs font-semibold text-gray-700">Need help?</p>
          <p className="text-xs text-gray-500 mt-0.5">
            Use the chat button on the bottom right to ask questions about schemes.
          </p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
