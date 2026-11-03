import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import {
  Save, Building2, TrendingUp, MapPin, Lightbulb, CheckCircle,
  Sparkles, Plus, Edit3, Trash2, FolderOpen, Award, CheckCircle2,
  AlertCircle
} from 'lucide-react';

const BusinessProfile = ({ setActiveTab, refreshRecs }) => {
  const { profile, reloadProfile } = useAuth();
  const [form, setForm] = useState({
    company_name: '', entity_type: 'Proprietorship', industry_type: 'Manufacturing',
    sector: 'Other', annual_turnover: 0, investment_in_plant_machinery: 0,
    number_of_employees: 0, business_age_years: 0,
    state: 'Delhi', district: '', social_category: 'General',
    gender_of_owner: 'Male', is_minority_owned: false,
    project_title: '', project_description: '',
  });
  const [projects, setProjects] = useState([]);
  const [editingProject, setEditingProject] = useState(-1);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [projectMsg, setProjectMsg] = useState('');

  useEffect(() => {
    if (profile) {
      setForm({
        company_name: profile.company_name || '',
        entity_type: profile.entity_type || 'Proprietorship',
        industry_type: profile.industry_type || 'Manufacturing',
        sector: profile.sector || 'Other',
        annual_turnover: parseFloat(profile.annual_turnover || 0),
        investment_in_plant_machinery: parseFloat(profile.investment_in_plant_machinery || 0),
        number_of_employees: parseInt(profile.number_of_employees || 0),
        business_age_years: parseInt(profile.business_age_years || 0),
        state: profile.state || 'Delhi',
        district: profile.district || '',
        social_category: profile.social_category || 'General',
        gender_of_owner: profile.gender_of_owner || 'Male',
        is_minority_owned: profile.is_minority_owned || false,
        project_title: '',
        project_description: '',
      });

      const regs = profile.registrations || {};
      let loadedProjects = Array.isArray(regs.projects) ? [...regs.projects] : [];
      if (loadedProjects.length === 0 && profile.project_title) {
        loadedProjects = [{
          title: profile.project_title,
          description: profile.project_description || '',
          desc: profile.project_description || ''
        }];
      }
      setProjects(loadedProjects);
    }
  }, [profile]);

  // Dynamic Real-time Completion Percentage Calculation
  const completionStats = useMemo(() => {
    let score = 0;
    const checks = {
      company: false,
      financials: false,
      location: false,
      projects: false,
      documents: false,
    };

    // 1. Company Details (25 points)
    const cname = (form.company_name || '').trim();
    if (cname && cname !== 'My Business') {
      score += 15;
      checks.company = true;
    } else if (cname) {
      score += 5;
    }
    if (form.entity_type) score += 5;
    if (form.sector && form.sector !== 'Other') score += 5;
    else if (form.sector) score += 2;

    // 2. Financials (25 points)
    const t = parseFloat(form.annual_turnover || 0);
    const inv = parseFloat(form.investment_in_plant_machinery || 0);
    if (t > 0) score += 10;
    if (inv > 0) score += 10;
    if (t > 0 || inv > 0) checks.financials = true;
    if (form.number_of_employees > 0 || form.business_age_years > 0) score += 5;

    // 3. Location & Demographics (20 points)
    if (form.state) score += 5;
    if (form.district?.trim()) score += 5;
    if (form.social_category) score += 5;
    if (form.gender_of_owner) score += 5;
    if (form.state && form.district?.trim()) checks.location = true;

    // 4. Projects (15 points)
    const hasAnyProject = projects.length > 0 || form.project_title?.trim();
    if (hasAnyProject) {
      score += 15;
      checks.projects = true;
    }

    // 5. Registrations & Documents (15 points)
    const regs = profile?.registrations || {};
    const regCount = Object.entries(regs).filter(([k, v]) => k !== 'projects' && Boolean(v)).length;
    if (regCount > 0) {
      score += Math.min(15, regCount * 5);
      checks.documents = true;
    }

    return {
      percentage: Math.min(score, 100),
      checks,
      regCount
    };
  }, [form, projects, profile]);

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(p => ({ ...p, [name]: type === 'checkbox' ? checked : value }));
  };

  const addProject = async () => {
    const title = form.project_title?.trim();
    const desc = form.project_description?.trim() || '';
    if (!title) {
      setProjectMsg('Please provide a Project Title before adding to list.');
      setTimeout(() => setProjectMsg(''), 3500);
      return;
    }

    const newProj = { title, description: desc, desc };
    let updated;
    if (editingProject >= 0 && editingProject < projects.length) {
      updated = projects.map((p, i) => (i === editingProject ? newProj : p));
    } else {
      updated = [...projects, newProj];
    }

    setProjects(updated);
    setEditingProject(-1);
    setForm(p => ({ ...p, project_title: '', project_description: '' }));

    // Auto-save projects to backend immediately so they are NEVER lost!
    try {
      const payload = {
        ...form,
        project_title: updated[0]?.title || '',
        project_description: updated.map(p => (p.description ? `${p.title}: ${p.description}` : p.title)).join('\n\n'),
        registrations: { ...((profile?.registrations) || {}), projects: updated }
      };
      await api.put('/business/profile', payload);
      await reloadProfile();
      refreshRecs?.();
      setProjectMsg(editingProject >= 0 ? 'Project updated and saved!' : 'Project added to list and saved!');
      setTimeout(() => setProjectMsg(''), 3500);
    } catch (err) {
      console.error('Failed to auto-save project:', err);
    }
  };

  const editProject = (idx) => {
    setEditingProject(idx);
    const target = projects[idx];
    setForm(p => ({
      ...p,
      project_title: target.title || '',
      project_description: target.description || target.desc || ''
    }));
  };

  const deleteProject = async (idx) => {
    const updated = projects.filter((_, i) => i !== idx);
    setProjects(updated);
    if (editingProject === idx) {
      setEditingProject(-1);
      setForm(p => ({ ...p, project_title: '', project_description: '' }));
    }

    // Auto-save deletion
    try {
      const payload = {
        ...form,
        project_title: updated[0]?.title || '',
        project_description: updated.map(p => (p.description ? `${p.title}: ${p.description}` : p.title)).join('\n\n'),
        registrations: { ...((profile?.registrations) || {}), projects: updated }
      };
      await api.put('/business/profile', payload);
      await reloadProfile();
      refreshRecs?.();
      setProjectMsg('Project removed and profile updated.');
      setTimeout(() => setProjectMsg(''), 3000);
    } catch (err) {
      console.error('Failed to auto-save deletion:', err);
    }
  };

  const onSubmit = async (e) => {
    if (e) e.preventDefault();
    setSaving(true);
    setSuccess(false);

    try {
      // If user typed in project fields but didn't click "Add to List", automatically include it
      let finalProjects = [...projects];
      if (form.project_title?.trim()) {
        const pendingProj = {
          title: form.project_title.trim(),
          description: form.project_description?.trim() || '',
          desc: form.project_description?.trim() || ''
        };
        if (editingProject >= 0 && editingProject < finalProjects.length) {
          finalProjects[editingProject] = pendingProj;
        } else {
          finalProjects.push(pendingProj);
        }
        setProjects(finalProjects);
        setEditingProject(-1);
        setForm(p => ({ ...p, project_title: '', project_description: '' }));
      }

      const payload = {
        ...form,
        project_title: finalProjects[0]?.title || '',
        project_description: finalProjects.map(p => (p.description ? `${p.title}: ${p.description}` : p.title)).join('\n\n'),
        registrations: { ...((profile?.registrations) || {}), projects: finalProjects }
      };

      await api.put('/business/profile', payload);
      await reloadProfile();
      refreshRecs?.();
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error('Save failed:', err);
    } finally {
      setSaving(false);
    }
  };

  const sectors = ['Textiles', 'IT', 'Food Processing', 'Chemicals', 'Agriculture', 'Logistics', 'Retail', 'Automotive', 'Other'];
  const types = ['Proprietorship', 'Partnership', 'LLP', 'Pvt Ltd', 'Public Ltd', 'Cooperative'];
  const states = ['Andhra Pradesh', 'Delhi', 'Gujarat', 'Karnataka', 'Maharashtra', 'Tamil Nadu', 'Telangana', 'Uttar Pradesh', 'West Bengal', 'Other'];

  const pct = completionStats.percentage;
  const barColor = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-blue-600' : 'bg-amber-500';

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-bold text-gray-900">Business Profile</h1>
        <p className="text-sm text-gray-500">Provide accurate enterprise details to get the highest scheme matching scores.</p>
      </div>

      {/* Profile Completion Percentage Card */}
      <div className="card bg-gradient-to-r from-blue-50/70 via-indigo-50/50 to-slate-50 border-blue-200">
        <div className="card-body space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <Award className="w-5 h-5 text-blue-600" />
                <h3 className="text-sm font-bold text-gray-900">Profile Completion: <span className="text-blue-700">{pct}%</span></h3>
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                {pct >= 85
                  ? 'Excellent! Your profile is complete and optimized for scheme recommendations.'
                  : pct >= 50
                  ? 'Good progress! Add your projects and verified documents to reach 100%.'
                  : 'Complete your financial and project details to discover eligible government schemes.'}
              </p>
            </div>
            <div className="text-right shrink-0">
              <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${
                pct >= 80 ? 'bg-emerald-100 text-emerald-800' : pct >= 50 ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
              }`}>
                {pct}% Complete
              </span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="h-2.5 w-full bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${barColor} transition-all duration-500`}
              style={{ width: `${pct}%` }}
            ></div>
          </div>

          {/* Section Indicators */}
          <div className="flex flex-wrap gap-2 pt-1 text-xs">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border ${
              completionStats.checks.company ? 'bg-emerald-50 text-emerald-700 border-emerald-200 font-medium' : 'bg-gray-50 text-gray-400 border-gray-200'
            }`}>
              {completionStats.checks.company ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : '○'} Company Details
            </span>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border ${
              completionStats.checks.financials ? 'bg-emerald-50 text-emerald-700 border-emerald-200 font-medium' : 'bg-gray-50 text-gray-400 border-gray-200'
            }`}>
              {completionStats.checks.financials ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : '○'} Financials
            </span>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border ${
              completionStats.checks.location ? 'bg-emerald-50 text-emerald-700 border-emerald-200 font-medium' : 'bg-gray-50 text-gray-400 border-gray-200'
            }`}>
              {completionStats.checks.location ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : '○'} Location & Demographics
            </span>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border ${
              completionStats.checks.projects ? 'bg-emerald-50 text-emerald-700 border-emerald-200 font-medium' : 'bg-gray-50 text-gray-400 border-gray-200'
            }`}>
              {completionStats.checks.projects ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : '○'} Projects ({projects.length})
            </span>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border ${
              completionStats.checks.documents ? 'bg-emerald-50 text-emerald-700 border-emerald-200 font-medium' : 'bg-gray-50 text-gray-400 border-gray-200'
            }`}>
              {completionStats.checks.documents ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : '○'} Verified Docs ({completionStats.regCount}/4)
            </span>
          </div>
        </div>
      </div>

      <form onSubmit={onSubmit} className="space-y-4">
        <Section icon={<Building2 className="w-4 h-4" />} title="Company Details">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="Company Name">
              <input name="company_name" value={form.company_name} onChange={onChange} required placeholder="e.g. Apex Engineering Pvt Ltd" className="input" />
            </Field>
            <Field label="Entity Type">
              <select name="entity_type" value={form.entity_type} onChange={onChange} className="select">
                {types.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Sector">
              <select name="sector" value={form.sector} onChange={onChange} className="select">
                {sectors.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </Field>
          </div>
        </Section>

        <Section icon={<TrendingUp className="w-4 h-4" />} title="Financials & Size">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Field label="Annual Turnover (₹)">
              <input type="number" name="annual_turnover" value={form.annual_turnover} onChange={onChange} min="0" className="input" />
            </Field>
            <Field label="Investment in P&M (₹)">
              <input type="number" name="investment_in_plant_machinery" value={form.investment_in_plant_machinery} onChange={onChange} min="0" className="input" />
            </Field>
            <Field label="Employees">
              <input type="number" name="number_of_employees" value={form.number_of_employees} onChange={onChange} min="0" className="input" />
            </Field>
            <Field label="Business Age (Yrs)">
              <input type="number" name="business_age_years" value={form.business_age_years} onChange={onChange} min="0" className="input" />
            </Field>
          </div>
        </Section>

        <Section icon={<MapPin className="w-4 h-4" />} title="Location & Demographics">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="State">
              <select name="state" value={form.state} onChange={onChange} className="select">
                {states.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </Field>
            <Field label="District">
              <input name="district" value={form.district} onChange={onChange} placeholder="e.g. Pune" className="input" />
            </Field>
            <Field label="Social Category">
              <select name="social_category" value={form.social_category} onChange={onChange} className="select">
                <option value="General">General</option>
                <option value="OBC">OBC</option>
                <option value="SC">SC</option>
                <option value="ST">ST</option>
              </select>
            </Field>
            <Field label="Owner Gender">
              <select name="gender_of_owner" value={form.gender_of_owner} onChange={onChange} className="select">
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Transgender">Transgender</option>
              </select>
            </Field>
            <div className="flex items-center pt-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" name="is_minority_owned" checked={form.is_minority_owned} onChange={onChange} className="w-4 h-4 rounded border-gray-300 text-[#1a365d] focus:ring-[#1a365d]" />
                <span className="text-sm text-gray-700">Minority-Owned Enterprise</span>
              </label>
            </div>
          </div>
        </Section>

        <Section icon={<Lightbulb className="w-4 h-4" />} title="Your Projects (AI Semantic Matching)">
          <div className="space-y-4">
            {projectMsg && (
              <div className="flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-lg bg-blue-50 text-blue-800 border border-blue-200">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                <span>{projectMsg}</span>
              </div>
            )}

            {projects.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Saved Projects ({projects.length})
                </p>
                {projects.map((p, i) => (
                  <div key={i} className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-3 py-2.5">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-gray-800 truncate">{p.title}</p>
                      {(p.description || p.desc) && (
                        <p className="text-xs text-gray-500 line-clamp-2 mt-0.5">{p.description || p.desc}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-1 ml-3 shrink-0">
                      <button
                        type="button"
                        onClick={() => editProject(i)}
                        className="p-1.5 rounded-lg hover:bg-white text-gray-400 hover:text-blue-600 transition-colors"
                        title="Edit Project"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteProject(i)}
                        className="p-1.5 rounded-lg hover:bg-white text-gray-400 hover:text-red-600 transition-colors"
                        title="Delete Project"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="bg-gray-50 border border-dashed border-gray-300 rounded-lg p-4 space-y-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                {editingProject >= 0 ? 'Edit Project' : 'Add New Project'}
              </p>
              <Field label="Project Title">
                <input
                  name="project_title"
                  value={form.project_title}
                  onChange={onChange}
                  placeholder="e.g. Solar Panel Assembly Line"
                  className="input"
                />
              </Field>
              <Field label="Description">
                <textarea
                  name="project_description"
                  value={form.project_description}
                  onChange={onChange}
                  rows={3}
                  placeholder="Describe your business idea or upgrade. AI will match it with relevant government schemes."
                  className="input resize-none"
                />
              </Field>
              <div className="flex items-center gap-2">
                <button type="button" onClick={addProject} className="btn btn-primary text-sm">
                  <Plus className="w-3.5 h-3.5" />
                  {editingProject >= 0 ? 'Update Project' : 'Add to List'}
                </button>
                {editingProject >= 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingProject(-1);
                      setForm(p => ({ ...p, project_title: '', project_description: '' }));
                    }}
                    className="btn btn-ghost text-sm"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>

            <p className="text-xs text-gray-400">
              {projects.length > 0
                ? `${projects.length} project${projects.length > 1 ? 's' : ''} saved to profile. Projects are automatically matched with government subsidies and grants.`
                : 'No projects added yet. Click "Add to List" above to save your project concept for AI matching.'}
            </p>
          </div>
        </Section>

        <div className="flex items-center gap-3 pt-2">
          <button type="submit" disabled={saving} className="btn btn-primary">
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Profile'}
          </button>
          <button
            type="button"
            onClick={async () => {
              await onSubmit();
              refreshRecs?.();
              setActiveTab('recommendations');
            }}
            className="btn btn-accent"
          >
            <Sparkles className="w-4 h-4" />
            Find Schemes
          </button>
          {success && (
            <div className="flex items-center gap-1.5 text-sm text-green-700 bg-green-50 border border-green-200 px-3 py-2 rounded-lg">
              <CheckCircle className="w-4 h-4" />
              Profile Saved Successfully!
            </div>
          )}
        </div>
      </form>
    </div>
  );
};

const Section = ({ icon, title, children }) => (
  <div className="card">
    <div className="card-header flex items-center gap-2">
      <span className="text-[#1a365d]">{icon}</span>
      {title}
    </div>
    <div className="card-body">{children}</div>
  </div>
);

const Field = ({ label, children }) => (
  <div>
    <label className="input-label">{label}</label>
    {children}
  </div>
);

export default BusinessProfile;
