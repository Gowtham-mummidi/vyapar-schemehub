import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Building2, Eye, EyeOff, Lock, Mail, User } from 'lucide-react';

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-[#1a365d] rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!user) return <AuthScreen />;

  return children;
};

const AuthScreen = () => {
  const { signIn, signUp } = useAuth();
  const [isSignUp, setIsSignUp] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setError('Please enter your email address.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }
    if (isSignUp && password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setBusy(true);
    try {
      const res = isSignUp
        ? await signUp(cleanEmail, password, name.trim())
        : await signIn(cleanEmail, password);

      if (res?.error) {
        setError(res.error.message);
      } else if (isSignUp && !res?.data?.session) {
        setSuccessMsg('Account created successfully in Supabase! If confirmation is required, please check your email inbox to confirm, or try signing in.');
        setIsSignUp(false);
        setPassword('');
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setBusy(false);
    }
  };

  const handleToggleMode = () => {
    setIsSignUp(!isSignUp);
    setError('');
    setSuccessMsg('');
    setEmail('');
    setPassword('');
    setName('');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4 py-8">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-[#1a365d] text-white flex items-center justify-center mx-auto mb-3 shadow-md">
            <Building2 className="w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold text-gray-900">Vyapar SchemeHub</h1>
          <p className="text-sm text-gray-500 mt-0.5">Government Scheme Recommendation Portal</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <div className="mb-5 pb-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-base font-bold text-gray-900">
              {isSignUp ? 'Create your Account' : 'Sign in to your Account'}
            </h2>
            <div className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-semibold" title="Authentication powered by Supabase">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Supabase Auth</span>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-xs font-medium text-red-600 leading-relaxed">
              {error}
            </div>
          )}

          {successMsg && (
            <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-medium text-emerald-800 leading-relaxed">
              {successMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isSignUp && (
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1.5">
                  Your Name
                </label>
                <div className="flex items-center w-full border border-gray-300 rounded-lg px-3 py-2.5 bg-white focus-within:ring-2 focus-within:ring-[#1a365d] focus-within:border-transparent transition-all">
                  <User className="w-4 h-4 text-gray-400 shrink-0 mr-2.5" />
                  <input
                    type="text"
                    required={isSignUp}
                    autoComplete="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-transparent border-none outline-none text-sm text-gray-900 placeholder:text-gray-400 p-0 focus:ring-0"
                    placeholder="e.g. Ramesh Kumar"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1.5">
                Email Address
              </label>
              <div className="flex items-center w-full border border-gray-300 rounded-lg px-3 py-2.5 bg-white focus-within:ring-2 focus-within:ring-[#1a365d] focus-within:border-transparent transition-all">
                <Mail className="w-4 h-4 text-gray-400 shrink-0 mr-2.5" />
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-transparent border-none outline-none text-sm text-gray-900 placeholder:text-gray-400 p-0 focus:ring-0"
                  placeholder="name@example.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1.5">
                Password
              </label>
              <div className="flex items-center w-full border border-gray-300 rounded-lg px-3 py-2.5 bg-white focus-within:ring-2 focus-within:ring-[#1a365d] focus-within:border-transparent transition-all">
                <Lock className="w-4 h-4 text-gray-400 shrink-0 mr-2.5" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete={isSignUp ? 'new-password' : 'current-password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-transparent border-none outline-none text-sm text-gray-900 placeholder:text-gray-400 p-0 focus:ring-0"
                  placeholder={isSignUp ? 'Create password (min. 6 chars)' : 'Enter password'}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-gray-400 hover:text-gray-600 p-0.5 shrink-0 ml-1.5 focus:outline-none"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={busy}
              className="btn btn-primary w-full py-2.5 font-semibold text-sm shadow-sm hover:shadow transition-all"
            >
              {busy ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span>Please wait...</span>
                </span>
              ) : isSignUp ? (
                'Create Account in Supabase'
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div className="mt-5 pt-4 border-t border-gray-100 flex items-center justify-between text-xs">
            <button
              type="button"
              onClick={handleToggleMode}
              className="text-[#1a365d] font-semibold hover:underline"
            >
              {isSignUp ? '← Already have an account? Sign In' : 'New user? Create Account'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProtectedRoute;
