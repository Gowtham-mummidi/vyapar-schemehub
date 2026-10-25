import React from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, Building2 } from 'lucide-react';

const Navbar = () => {
  const { user, profile, signOut } = useAuth();

  // Resolve user display name prioritizing what was provided at sign up
  const displayName =
    (user?.name && user.name !== 'User' ? user.name : null) ||
    user?.user_metadata?.name ||
    user?.user_metadata?.full_name ||
    user?.user_metadata?.display_name ||
    (profile?.name && profile.name !== 'User' ? profile.name : null) ||
    (typeof window !== 'undefined' && (
      localStorage.getItem(`user_name_${user?.id}`) ||
      localStorage.getItem(`user_name_${user?.email?.toLowerCase()}`) ||
      localStorage.getItem('last_signup_name')
    )) ||
    (user?.email ? user.email.split('@')[0] : 'User');

  const initial = (displayName || 'U').trim().charAt(0).toUpperCase();

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-[#1a365d] text-white">
          <Building2 className="w-4 h-4" />
        </div>
        <div>
          <h1 className="text-sm font-bold text-[#1a365d] leading-tight">
            Vyapar SchemeHub
          </h1>
        </div>
      </div>

      {user && (
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm font-semibold text-gray-800 leading-tight">
              {displayName}
            </p>
            <p className="text-xs text-gray-400">{user.email}</p>
          </div>
          <div className="w-8 h-8 rounded-full bg-[#1a365d] text-white flex items-center justify-center text-sm font-bold shadow-sm">
            {initial}
          </div>
          <button
            onClick={signOut}
            className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
            title="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      )}
    </header>
  );
};

export default Navbar;
