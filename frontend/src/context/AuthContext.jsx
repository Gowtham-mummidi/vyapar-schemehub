import React, { createContext, useContext, useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import api from '../utils/api';

const AuthContext = createContext(null);

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://placeholder.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'placeholder_anon_key';

// Initialize Supabase Client
// We handle exceptions in case keys are placeholders
export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSimulated, setIsSimulated] = useState(false);

  const enrichUser = (rawUser) => {
    if (!rawUser) return null;
    const metaName = rawUser.user_metadata?.name || 
                     rawUser.user_metadata?.full_name || 
                     rawUser.user_metadata?.display_name ||
                     (rawUser.name && rawUser.name !== 'User' ? rawUser.name : null);

    const savedName = (typeof window !== 'undefined' && (
      localStorage.getItem(`user_name_${rawUser.id}`) ||
      localStorage.getItem(`user_name_${rawUser.email?.toLowerCase()}`) ||
      localStorage.getItem('last_signup_name')
    )) || null;

    const chosenName = metaName || (savedName && savedName !== 'User' ? savedName : null);

    return {
      ...rawUser,
      name: chosenName || (rawUser.email ? rawUser.email.split('@')[0] : 'User')
    };
  };

  const fetchProfile = async () => {
    try {
      const res = await api.get('/auth/me');
      setProfile(res.data);
      if (res.data?.name && res.data.name !== 'User') {
        setUser(prev => prev ? { ...prev, name: res.data.name } : prev);
      }
    } catch (err) {
      console.error('Failed to fetch business profile:', err);
    }
  };

  useEffect(() => {
    if (isSimulated) {
      const savedMockUser = localStorage.getItem('mock_user');
      if (savedMockUser) {
        const u = JSON.parse(savedMockUser);
        setUser(enrichUser(u));
        api.defaults.headers.common['Authorization'] = 'Bearer simulated-token';
        api.get('/auth/me').then(res => {
          setProfile(res.data);
          if (res.data?.name && res.data.name !== 'User') {
            setUser(prev => prev ? { ...prev, name: res.data.name } : prev);
          }
        });
      }
      setLoading(false);
      return;
    }

    // Check active Supabase session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setUser(enrichUser(session.user));
        api.defaults.headers.common['Authorization'] = `Bearer ${session.access_token}`;
        fetchProfile();
      }
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (session) {
        setUser(enrichUser(session.user));
        api.defaults.headers.common['Authorization'] = `Bearer ${session.access_token}`;
        await fetchProfile();
      } else {
        delete api.defaults.headers.common['Authorization'];
        setUser(null);
        setProfile(null);
      }
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [isSimulated]);

  const reloadProfile = () => fetchProfile();

  const syncNameToDb = async (name) => {
    if (!name || name === 'User') return;
    try {
      await api.put('/business/profile', { name });
    } catch {}
  };

  const signUp = async (email, password, name) => {
    const trimmedName = (name || '').trim();
    if (trimmedName) {
      localStorage.setItem(`user_name_${email.toLowerCase()}`, trimmedName);
      localStorage.setItem('last_signup_name', trimmedName);
    }

    if (isSimulated) {
      const mockUser = { id: '3fa85f64-5717-4562-b3fc-2c963f66afa6', email, name: trimmedName || (email.split('@')[0] || 'User') };
      localStorage.setItem('mock_user', JSON.stringify(mockUser));
      api.defaults.headers.common['Authorization'] = 'Bearer simulated-token';
      setUser(mockUser);
      await fetchProfile();
      await syncNameToDb(trimmedName || mockUser.name);
      await reloadProfile();
      return { data: { user: mockUser }, error: null };
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          name: trimmedName || email.split('@')[0],
          full_name: trimmedName || email.split('@')[0],
        }
      }
    });

    if (error) return { data, error };

    if (data?.user?.id && trimmedName) {
      localStorage.setItem(`user_name_${data.user.id}`, trimmedName);
    }

    if (data?.session) {
      const enriched = enrichUser(data.user);
      if (trimmedName) enriched.name = trimmedName;
      setUser(enriched);
      api.defaults.headers.common['Authorization'] = `Bearer ${data.session.access_token}`;
      await fetchProfile();
      if (trimmedName) {
        await syncNameToDb(trimmedName);
        await reloadProfile();
      }
    }
    return { data, error: null };
  };

  const signIn = async (email, password) => {
    if (isSimulated) {
      const saved = localStorage.getItem('mock_user');
      const prev = saved ? JSON.parse(saved) : {};
      const savedName = localStorage.getItem(`user_name_${email.toLowerCase()}`) || (prev.name && prev.name !== 'User' ? prev.name : null) || 'User';
      const mockUser = { id: '3fa85f64-5717-4562-b3fc-2c963f66afa6', email, name: savedName };
      localStorage.setItem('mock_user', JSON.stringify(mockUser));
      api.defaults.headers.common['Authorization'] = 'Bearer simulated-token';
      setUser(mockUser);
      await fetchProfile();
      return { data: { user: mockUser }, error: null };
    }

    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return { data, error };

    if (data?.session) {
      const enriched = enrichUser(data.user);
      setUser(enriched);
      api.defaults.headers.common['Authorization'] = `Bearer ${data.session.access_token}`;
      await fetchProfile();
      if (enriched.name && enriched.name !== 'User') {
        await syncNameToDb(enriched.name);
      }
    }
    return { data, error: null };
  };

  const signOut = async () => {
    if (isSimulated) {
      localStorage.removeItem('mock_user');
      setUser(null);
      setProfile(null);
      return;
    }
    await supabase.auth.signOut();
  };

  const value = {
    user,
    profile,
    loading,
    isSimulated,
    signUp,
    signIn,
    signOut,
    reloadProfile,
    toggleSimulatedMode: () => {
      const nextMode = !isSimulated;
      setIsSimulated(nextMode);
      setUser(null);
      setProfile(null);
      localStorage.removeItem('mock_user');
    }
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);
