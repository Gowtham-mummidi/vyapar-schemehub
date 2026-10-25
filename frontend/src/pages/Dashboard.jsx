import React, { useState, useEffect } from 'react';
import {
  Award, IndianRupee, CheckSquare, FileText, ArrowRight, AlertTriangle,
  ShieldCheck, Lightbulb, FolderOpen, Info, TrendingUp, Users,
  Building2, ExternalLink, Sparkles, Target, User
} from 'lucide-react';
import api from '../utils/api';
import SchemeCard from '../components/SchemeCard';
import { useAuth } from '../context/AuthContext';

const Dashboard = ({ setActiveTab, setSelectedScheme, profile }) => {
  const { user } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [schemeCount, setSchemeCount] = useState(0);
  const [recs, setRecs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSchemeCount = async () => {
      try {
        const res = await api.get('/schemes');
        setSchemeCount(res.data?.length || 0);
      } catch {}
    };
    fetchSchemeCount();
  }, []);

  useEffect(() => {
    if (!profile) { setLoading(false); return; }
    const load = async () => {
      setError(null);
      setLoading(true);
      try {
        const [a, r] = await Promise.all([
          api.get('/recommendations/analytics', { timeout: 60000 }),
          api.get('/recommendations?limit=3', { timeout: 60000 })
        ]);
        setAnalytics(a.data);
        setRecs(r.data);
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'Failed to load recommendations');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [profile]);

  const rawUser = typeof window !== 'undefined' ? (localStorage.getItem('mock_user') ? JSON.parse(localStorage.getItem('mock_user')) : {}) : {};
  const personName =
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
    (rawUser?.name && rawUser.name !== 'User' ? rawUser.name : null) ||
    (user?.email ? user.email.split('@')[0] : null);

  const t = parseFloat(profile?.annual_turnover || 0);
  const inv = parseFloat(profile?.investment_in_plant_machinery || 0);
  let cat = 'Micro';
  if (inv > 10000000 || t > 50000000) cat = 'Small';
  if (inv > 100000000 || t > 500000000) cat = 'Medium';
  if (inv > 500000000 || t > 2500000000) cat = 'Large';

  const regs = profile?.registrations || {};
  const projects = regs.projects || (profile?.project_title ? [{ title: profile.project_title, desc: profile.project_description }] : []);

  const hasProfileData = profile && (
    (profile.company_name && profile.company_name !== 'My Business') ||
    parseFloat(profile.annual_turnover) > 0 ||
    profile.sector ||
    projects.length > 0 ||
    Object.values(regs).some(Boolean)
  );

  return (
    <div className="space-y-5">
      <Banner cat={cat} personName={personName} schemeCount={schemeCount} projects={projects} hasProfileData={hasProfileData} setActiveTab={setActiveTab} />

      {!hasProfileData && (
        <div className="card border-dashed border-2 border-gray-200 bg-white">
          <div className="card-body text-center py-10">
            <Target className="w-12 h-12 mx-auto text-gray-300 mb-3" />
            <h2 className="text-lg font-semibold text-gray-700">Welcome to Vyapar SchemeHub</h2>
            <p className="text-sm text-gray-500 mt-1 max-w-md mx-auto">
              Set up your business profile to discover government schemes tailored to your enterprise.
              Add your financial details, location, and projects to get AI-powered recommendations.
            </p>
            <button onClick={() => setActiveTab('profile')} className="btn btn-primary mt-5">
              <Building2 className="w-4 h-4" />
              Set Up Business Profile
            </button>
          </div>
        </div>
      )}

      <div className="card bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
        <div className="card-body flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-100 border border-blue-200 flex items-center justify-center shrink-0">
            <Info className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-blue-900">About Vyapar SchemeHub</h3>
            <p className="text-sm text-blue-800 mt-1 leading-relaxed">
              This portal helps MSMEs discover suitable government schemes by matching your business profile
              (turnover, investment, sector, location) against <strong>{schemeCount || 'many'}</strong> central & state government schemes.
              Get AI-powered recommendations, check real-time eligibility, and track applications — all in one place.
            </p>
            <div className="flex flex-wrap gap-2 mt-3">
              {['Subsidies', 'Grants', 'Loans', 'Equity Support', 'Credit Guarantees', 'Tax Benefits'].map(b =>
                <span key={b} className="text-xs font-medium px-2.5 py-1 rounded-full bg-white border border-blue-200 text-blue-700">{b}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {hasProfileData && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KPI icon={<Award className="w-4 h-4" />} label="Eligible Schemes"
              value={analytics?.eligible_schemes_count ?? (loading ? '...' : 0)}
              color="text-emerald-600" bg="bg-emerald-50 border-emerald-200" />
            <KPI icon={<IndianRupee className="w-4 h-4" />} label="Potential Benefit"
              value={analytics ? `\u20B9${((analytics.total_potential_benefit || 0) / 100000).toFixed(1)}L` : (loading ? '...' : '\u20B90')}
              color="text-blue-600" bg="bg-blue-50 border-blue-200" />
            <KPI icon={<CheckSquare className="w-4 h-4" />} label="Profile"
              value={analytics ? `${analytics.profile_completion_percentage || 0}%` : (loading ? '...' : '0%')}
              color="text-purple-600" bg="bg-purple-50 border-purple-200" />
            <KPI icon={<FileText className="w-4 h-4" />} label="Verified Docs"
              value={`${Object.values(profile?.registrations || {}).filter(Boolean).length}/4`}
              color="text-amber-600" bg="bg-amber-50 border-amber-200" />
          </div>

          {error && (
            <div className="card border-amber-200 bg-amber-50">
              <div className="card-body flex items-center gap-3 text-sm text-amber-800">
                <AlertTriangle className="w-4 h-4 shrink-0 text-amber-500" />
                <span className="flex-1">{error}</span>
                <button onClick={() => window.location.reload()} className="btn btn-ghost text-xs px-3 py-1">Retry</button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div className="lg:col-span-2 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  Top Matches
                </h2>
                <button onClick={() => setActiveTab('recommendations')} className="text-sm text-[#1a365d] hover:underline flex items-center gap-1 font-medium">
                  View all <ArrowRight className="w-3 h-3" />
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {loading ? (
                  <div className="col-span-2 card p-8 text-center">
                    <div className="w-5 h-5 border-2 border-gray-300 border-t-[#1a365d] rounded-full animate-spin mx-auto"></div>
                    <p className="text-sm text-gray-500 mt-2">Finding your best scheme matches...</p>
                  </div>
                ) : recs.length > 0 ? recs.slice(0, 2).map(r => (
                  <SchemeCard key={r.id} rec={r} onViewDetails={(s) => { setSelectedScheme(s); setActiveTab('recommendations'); }} />
                )) : (
                  <div className="col-span-2 card p-8 text-center">
                    <Target className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                    <p className="text-sm text-gray-500">Complete your profile to get matched with schemes.</p>
                    <button onClick={() => setActiveTab('profile')} className="btn btn-primary text-sm mt-3">Complete Profile</button>
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5" />
                Status
              </h2>

              {projects.length > 0 && (
                <div className="card border-indigo-200">
                  <div className="card-body">
                    <h3 className="text-xs font-bold text-indigo-600 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                      <FolderOpen className="w-3.5 h-3.5" />
                      Your Projects
                    </h3>
                    {projects.map((p, i) => (
                      <button key={i} onClick={() => setActiveTab('profile')} className="w-full text-left py-1.5 hover:bg-indigo-50/50 rounded px-1 -mx-1 transition-colors">
                        <p className="text-sm font-medium text-gray-800">{p.title}</p>
                        {p.desc && <p className="text-xs text-gray-500 line-clamp-2 mt-0.5">{p.desc}</p>}
                      </button>
                    ))}
                    <button onClick={() => setActiveTab('profile')} className="btn btn-ghost w-full text-xs mt-1">Manage Projects</button>
                  </div>
                </div>
              )}

              <div className="card">
                <div className="card-body">
                  {analytics?.critical_missing_documents?.length > 0 ? (
                    <div className="space-y-2">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                        <p className="text-sm font-medium text-gray-700">Missing Registrations</p>
                      </div>
                      {analytics.critical_missing_documents.map((d, i) => (
                        <div key={i} className="flex items-center justify-between py-1.5 px-3 rounded-lg bg-gray-50 text-sm">
                          <span className="text-gray-600">{d}</span>
                          <button onClick={() => setActiveTab('verification')} className="text-[#1a365d] font-medium text-sm hover:underline">Upload</button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <ShieldCheck className="w-8 h-8 text-green-500 mx-auto mb-1" />
                      <p className="text-sm font-medium text-gray-700">All Verified</p>
                      <p className="text-sm text-gray-500">Documents are in order.</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="card">
                <div className="card-body">
                  <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-1.5 mb-2">
                    <Lightbulb className="w-4 h-4 text-amber-500" />
                    Project Concept
                  </h3>
                  {projects.length > 0 ? (
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-gray-700 truncate">{projects[0].title}</p>
                      {projects[0].desc && <p className="text-sm text-gray-500 line-clamp-2">{projects[0].desc}</p>}
                      <span className="badge badge-blue">{projects.length} project{projects.length > 1 ? 's' : ''}</span>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-sm text-gray-500">Add your project for AI-powered scheme matching.</p>
                      <button onClick={() => setActiveTab('profile')} className="btn btn-ghost w-full text-sm">Add Project Idea</button>
                    </div>
                  )}
                </div>
              </div>

              <div className="card bg-gradient-to-br from-[#1a365d] to-[#153056] text-white text-center p-5">
                <Sparkles className="w-6 h-6 mx-auto mb-2 text-amber-300" />
                <p className="text-sm font-semibold">Find Your Schemes</p>
                <p className="text-xs text-blue-200 mt-1">Let AI match you with the best schemes.</p>
                <button onClick={() => setActiveTab('recommendations')} className="mt-3 w-full bg-white/20 hover:bg-white/30 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-all">
                  <ExternalLink className="w-3.5 h-3.5 inline mr-1" />
                  Explore Matches
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const Banner = ({ cat, personName, schemeCount, projects, hasProfileData, setActiveTab }) => (
  <div className="rounded-xl bg-gradient-to-r from-[#1a365d] via-[#1e4d7a] to-[#153056] p-6 text-white shadow-lg">
    <div className="flex items-center gap-2 mb-1">
      {hasProfileData && (
        <span className="badge text-[10px] bg-amber-500/20 text-amber-300 border border-amber-400/30">{cat} Enterprise</span>
      )}
      {projects.length > 0 && (
        <span className="badge text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 flex items-center gap-1">
          <FolderOpen className="w-3 h-3" />
          {projects.length} Project{projects.length > 1 ? 's' : ''}
        </span>
      )}
    </div>
    <h1 className="text-2xl font-bold mt-2">
      {personName ? `Welcome, ${personName}!` : 'Welcome to Vyapar SchemeHub'}
    </h1>
    <p className="text-sm text-blue-200 mt-1 max-w-xl leading-relaxed">
      {hasProfileData
        ? 'Discover, match, and apply for government schemes tailored to your business.'
        : 'Your one-stop platform to discover government schemes tailored to your enterprise.'}
    </p>
    <p className="text-xs text-blue-300 mt-2 flex items-center gap-1">
      <Building2 className="w-3 h-3" />
      {schemeCount > 0
        ? `${schemeCount} schemes from central & state governments in our database.`
        : 'Loading scheme database...'}
    </p>
    {projects.length > 0 && (
      <div className="mt-4 bg-white/10 backdrop-blur rounded-lg p-3 border border-white/10">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-200 uppercase tracking-wider mb-1">
          <FolderOpen className="w-3.5 h-3.5" />
          Your Projects
        </div>
        {projects.map((p, i) => (
          <button key={i} onClick={() => setActiveTab('profile')} className="text-sm text-white font-medium hover:text-blue-200 transition-colors text-left w-full">
            {p.title}
          </button>
        ))}
      </div>
    )}
  </div>
);

const KPI = ({ icon, label, value, color, bg }) => (
  <div className={`card border ${bg} hover:shadow-md transition-shadow`}>
    <div className="card-body flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center ${color} shrink-0`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">{label}</p>
        <p className={`text-lg font-bold ${color} truncate`}>{value}</p>
      </div>
    </div>
  </div>
);

export default Dashboard;
