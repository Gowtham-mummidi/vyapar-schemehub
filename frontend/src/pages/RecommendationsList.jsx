import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import SchemeCard from '../components/SchemeCard';
import { Filter, Search, X, CheckCircle, XCircle, Info, Calendar, FileText, Globe, MessageCircle, ExternalLink, FolderOpen, Building2, Target, Sparkles, RefreshCw } from 'lucide-react';
import Chatbot from '../components/Chatbot';

const RecommendationsList = ({ selectedScheme, setSelectedScheme, setActiveTab }) => {
  const { profile } = useAuth();
  const [recs, setRecs] = useState([]);
  const [filteredRecs, setFilteredRecs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [aiSearching, setAiSearching] = useState(false);
  const [activeQuery, setActiveQuery] = useState('');

  const regs = profile?.registrations || {};
  const projects = regs.projects || (profile?.project_title ? [{ title: profile.project_title, desc: profile.project_description }] : []);
  
  // Filters
  const [search, setSearch] = useState('');
  const [fundingType, setFundingType] = useState('All');
  const [eligibilityFilter, setEligibilityFilter] = useState('All'); // All, Eligible, Ineligible

  useEffect(() => {
    loadRecommendations();
  }, [projects.length]);

  const loadRecommendations = async () => {
    try {
      setLoading(true);
      setActiveQuery('');
      // Try fetching user profile recommendations first
      const res = await api.get('/recommendations?limit=50');
      if (res.data && res.data.length > 0) {
        setRecs(res.data);
        setFilteredRecs(res.data);
      } else {
        // If profile has no recommendations, load AI search fallback
        const aiRes = await api.post('/schemes/ai-search', { query: '', funding_type: 'All', limit: 50 });
        setRecs(aiRes.data);
        setFilteredRecs(aiRes.data);
      }
    } catch (err) {
      console.warn('Falling back to AI scheme search:', err);
      try {
        const aiRes = await api.post('/schemes/ai-search', { query: '', funding_type: 'All', limit: 50 });
        setRecs(aiRes.data);
        setFilteredRecs(aiRes.data);
      } catch (e) {
        console.error('Failed to load schemes:', e);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAiSearch = async (e) => {
    if (e) e.preventDefault();
    if (!search.trim()) {
      loadRecommendations();
      return;
    }

    try {
      setAiSearching(true);
      const res = await api.post('/schemes/ai-search', {
        query: search.trim(),
        funding_type: fundingType,
        limit: 50
      });
      setRecs(res.data);
      setActiveQuery(search.trim());
      applyFilters(res.data, search.trim(), fundingType, eligibilityFilter);
    } catch (err) {
      console.error('AI search failed:', err);
    } finally {
      setAiSearching(false);
    }
  };

  const applyFilters = (data, query, funding, eligibility) => {
    let result = data;

    if (funding !== 'All') {
      result = result.filter((r) => r.scheme?.funding_type?.toLowerCase() === funding.toLowerCase());
    }

    if (eligibility === 'Eligible') {
      result = result.filter((r) => r.is_eligible);
    } else if (eligibility === 'Ineligible') {
      result = result.filter((r) => !r.is_eligible);
    }

    setFilteredRecs(result);
  };

  useEffect(() => {
    applyFilters(recs, search, fundingType, eligibilityFilter);
  }, [fundingType, eligibilityFilter, recs]);

  const handleUpdateStatus = async (recId, newStatus) => {
    if (!recId) return;
    try {
      const res = await api.put(`/recommendations/${recId}/status`, { status: newStatus });
      setRecs(prev => prev.map(r => r.id === recId ? { ...r, status: res.data.status } : r));
      if (selectedScheme && selectedScheme.id === recId) {
         setSelectedScheme(prev => ({ ...prev, status: res.data.status }));
      }
    } catch (err) {
      console.error('Error updating recommendation status:', err);
    }
  };

  if (loading) {
     return (
       <div className="flex h-[400px] flex-col items-center justify-center gap-3">
         <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
         <p className="text-sm font-medium text-gray-500">AI is matching schemes and calculating match percentages...</p>
       </div>
     );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <span>Scheme Matches & AI Search</span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
              {filteredRecs.length} Schemes Available
            </span>
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Search with AI keywords or filter schemes. Every scheme displays an AI compatibility match percentage.
          </p>
        </div>

        {projects.length === 0 && (
          <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3 py-2 rounded-lg">
            <Info className="w-4 h-4 shrink-0 text-amber-600" />
            <span>Add your project in Business Profile for personalized eligibility matching.</span>
            {setActiveTab && (
              <button onClick={() => setActiveTab('profile')} className="font-semibold underline ml-1 hover:text-amber-950">
                Setup Profile
              </button>
            )}
          </div>
        )}
      </div>

      {/* Search & Filter Bar */}
      <div className="card shadow-sm border border-gray-200">
        <div className="card-body p-4">
          <form onSubmit={handleAiSearch} className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
            <div className="flex items-center flex-1 border border-gray-300 rounded-lg px-3 py-1.5 bg-white focus-within:ring-2 focus-within:ring-[#1a365d] focus-within:border-transparent transition-all">
              <Search className="w-4 h-4 text-gray-400 shrink-0 mr-2.5" />
              <input
                type="text"
                placeholder="Search with AI (e.g. 'solar subsidy', 'women loan collateral free', 'textile export')..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-transparent border-none outline-none text-sm text-gray-900 placeholder:text-gray-400 p-0 focus:ring-0"
              />
              <button
                type="submit"
                disabled={aiSearching}
                className="shrink-0 ml-2 px-3 py-1.5 bg-[#1a365d] text-white text-xs font-semibold rounded-md hover:bg-[#152c4d] transition-colors flex items-center gap-1 shadow-xs"
              >
                {aiSearching ? (
                  <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                ) : (
                  <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                )}
                <span>AI Search</span>
              </button>
            </div>

            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Funding:</span>
                <select value={fundingType} onChange={(e) => setFundingType(e.target.value)} className="select text-sm py-1.5">
                  <option value="All">All Types</option>
                  <option value="Subsidy">Subsidy</option>
                  <option value="Grant">Grant</option>
                  <option value="Loan">Loan</option>
                  <option value="Equity">Equity</option>
                  <option value="Guarantee">Guarantee</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Status:</span>
                <select value={eligibilityFilter} onChange={(e) => setEligibilityFilter(e.target.value)} className="select text-sm py-1.5">
                  <option value="All">All Status</option>
                  <option value="Eligible">Eligible</option>
                  <option value="Ineligible">Need Review</option>
                </select>
              </div>

              {activeQuery && (
                <button
                  type="button"
                  onClick={() => { setSearch(''); loadRecommendations(); }}
                  className="text-xs font-medium text-gray-500 hover:text-gray-800 flex items-center gap-1 border border-gray-200 px-2.5 py-1.5 rounded-lg hover:bg-gray-50"
                  title="Reset to default recommendations"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Reset</span>
                </button>
              )}
            </div>
          </form>

          {activeQuery && (
            <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-blue-900 bg-blue-50/70 px-3 py-2 rounded-lg">
              <span className="flex items-center gap-1.5 font-medium">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                Showing AI matched schemes for: <strong className="text-blue-950">"{activeQuery}"</strong>
              </span>
              <span className="text-blue-700 font-semibold">
                Ranked by Matched Percentage (%)
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Grid of Matched Schemes */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredRecs.length > 0 ? (
          filteredRecs.map((r) => (
            <SchemeCard
              key={r.id || r.scheme?.id}
              rec={r}
              onViewDetails={setSelectedScheme}
            />
          ))
        ) : (
          <div className="col-span-full card p-12 text-center bg-white border border-gray-200">
            <p className="text-sm font-semibold text-gray-700">No schemes match your criteria.</p>
            <p className="text-xs text-gray-400 mt-1">Try broadening your search or choosing "All" in the filters.</p>
            <button
              onClick={() => { setSearch(''); setFundingType('All'); setEligibilityFilter('All'); loadRecommendations(); }}
              className="btn btn-secondary text-xs mt-4"
            >
              Reset Filters
            </button>
          </div>
        )}
      </div>

      {/* Scheme Detail Modal */}
      {selectedScheme && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs">
          <div className="absolute inset-0" onClick={() => setSelectedScheme(null)}></div>
          <div className="relative w-full max-w-xl bg-white border-l border-gray-200 h-full flex flex-col shadow-2xl overflow-y-auto">
            <div className="sticky top-0 bg-white px-6 py-4 border-b border-gray-200 flex items-center justify-between z-10 shadow-xs">
              <div>
                <span className="text-xs text-gray-400 font-bold uppercase tracking-wider">
                  {selectedScheme.scheme?.funding_type} · {selectedScheme.scheme?.ministry}
                </span>
                <h2 className="text-lg font-bold text-gray-900 mt-0.5">{selectedScheme.scheme?.name}</h2>
              </div>
              <button onClick={() => setSelectedScheme(null)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5 flex-1">
              {/* AI Match Score Hero Card */}
              <div className="bg-gradient-to-r from-blue-900 to-indigo-900 text-white p-5 rounded-xl shadow-md flex items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-1.5 text-xs text-blue-200 font-bold uppercase tracking-wider mb-1">
                    <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                    <span>AI Compatibility Match</span>
                  </div>
                  <h3 className="text-2xl font-black tracking-tight text-white">
                    {parseFloat(selectedScheme.match_percentage || selectedScheme.match_score || 0)}% Match
                  </h3>
                  <p className="text-xs text-blue-100 mt-1 leading-relaxed">
                    {selectedScheme.recommendation_reason || "Evaluated by AI against your business profile and MSME criteria."}
                  </p>
                </div>
                <div className="w-16 h-16 rounded-full border-4 border-blue-400/60 bg-white/10 flex flex-col items-center justify-center shrink-0">
                  <span className="text-base font-extrabold text-white">
                    {Math.round(parseFloat(selectedScheme.match_percentage || selectedScheme.match_score || 0))}%
                  </span>
                  <span className="text-[9px] text-blue-200 uppercase font-semibold">Match</span>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Description</h4>
                <p className="text-sm text-gray-700 leading-relaxed bg-gray-50 p-3 rounded-lg border border-gray-200">
                  {selectedScheme.scheme?.description}
                </p>
              </div>

              {/* Eligibility Checklist */}
              {selectedScheme.eligibility_reasons && Object.keys(selectedScheme.eligibility_reasons).length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Eligibility Checklist</h4>
                  <div className="space-y-1.5">
                    {Object.entries(selectedScheme.eligibility_reasons).map(([param, check]) => {
                       const pass = check?.status;
                       return (
                         <div key={param} className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                           <div>
                             <p className="text-sm font-medium capitalize text-gray-700">{param.replace('_', ' ')}</p>
                             <p className="text-xs text-gray-400">
                               {param === 'turnover' && `₹${check.current_value?.toLocaleString()} / Limit: ₹${check.limit?.toLocaleString() || 'None'}`}
                               {param === 'investment' && `₹${check.current_value?.toLocaleString()} / Limit: ₹${check.limit?.toLocaleString() || 'None'}`}
                               {param === 'state' && `'${check.current_value}' (${check.allowed_values?.join(', ') || 'All'})`}
                               {param === 'sector' && `'${check.current_value}' (${check.allowed_values?.join(', ') || 'All'})`}
                               {param === 'business_age' && `${check.current_value}yrs (${check.min_required || 0}-${check.max_required || '∞'}yrs)`}
                               {param === 'registrations' && `Need: ${check.required_values?.join(', ') || 'None'}`}
                               {param === 'owner_demographics' && `${check.gender}, ${check.social_category}`}
                               {param === 'msme_category' && check.current_value}
                             </p>
                           </div>
                           <span className={`text-xs font-bold px-2 py-0.5 rounded ${pass ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}>
                             {pass ? 'PASS' : 'REVIEW'}
                           </span>
                         </div>
                       );
                    })}
                  </div>
                </div>
              )}

              <div>
                <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Required Documents</h4>
                <div className="flex flex-wrap gap-1.5">
                  {selectedScheme.scheme?.required_documents?.map((doc) => (
                    <span key={doc} className="text-xs font-medium px-2.5 py-1 rounded-lg bg-gray-50 border border-gray-200 text-gray-700">
                      {doc}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1.5">Official Guideline & Links</h4>
                <div className="space-y-1.5">
                  {selectedScheme.scheme?.pdf_storage_path && (
                    <a
                      href={selectedScheme.scheme.pdf_storage_path}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-sm text-[#1a365d] hover:underline p-2 rounded-lg bg-blue-50 border border-blue-200 font-medium"
                    >
                      <FileText className="w-4 h-4 text-blue-700" />
                      View Official Scheme PDF (Supabase Cloud)
                      <ExternalLink className="w-3 h-3 ml-auto text-blue-700" />
                    </a>
                  )}
                  {selectedScheme.scheme?.official_link && (
                    <a href={selectedScheme.scheme.official_link} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-[#1a365d] hover:underline p-2 rounded-lg bg-gray-50 border border-gray-200">
                      <Globe className="w-4 h-4" />
                      Scheme Official Webpage
                      <ExternalLink className="w-3 h-3 ml-auto" />
                    </a>
                  )}
                  <a href="https://www.udyamregistration.gov.in/UdyamRegistration.aspx" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-[#1a365d] hover:underline p-2 rounded-lg bg-gray-50 border border-gray-200">
                    <Building2 className="w-4 h-4" />
                    Udyam Registration Portal
                    <ExternalLink className="w-3 h-3 ml-auto" />
                  </a>
                </div>
              </div>
            </div>

            <div className="sticky bottom-0 bg-white border-t border-gray-200 px-6 py-4 flex items-center justify-between gap-3 shadow-md">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">Status:</span>
                <select
                  value={selectedScheme.status || 'Viewed'}
                  onChange={(e) => handleUpdateStatus(selectedScheme.id, e.target.value)}
                  className="select text-sm py-1"
                >
                  <option value="Viewed">Viewed</option>
                  <option value="Bookmarked">Bookmarked</option>
                  <option value="Applied">Applied</option>
                </select>
              </div>
              <a href="https://www.udyamregistration.gov.in/UdyamRegistration.aspx" target="_blank" rel="noopener noreferrer" className="btn btn-primary text-sm">
                <ExternalLink className="w-4 h-4" /> Register on Udyam
              </a>
            </div>
            <Chatbot activeSchemeId={selectedScheme.scheme?.id} />
          </div>
        </div>
      )}
    </div>
  );
};

export default RecommendationsList;
