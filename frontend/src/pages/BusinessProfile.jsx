import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { Save, Building2, TrendingUp, MapPin, Lightbulb, CheckCircle, Sparkles, Plus, Edit3, Trash2, FolderOpen } from 'lucide-react';

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
        project_title: profile.project_title || '',
        project_description: profile.project_description || '',
      });
      const regs = profile.registrations || {};
      setProjects(regs.projects || []);
    }
  }, [profile]);

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(p => ({ ...p, [name]: type === 'checkbox' ? checked : value }));
  };

  const addProject = () => {
    if (!form.project_title.trim()) return;
    const newProj = { title: form.project_title.trim(), description: form.project_description.trim() };
    let updated;
    if (editingProject >= 0 && editingProject < projects.length) {
      updated = projects.map((p, i) => i === editingProject ? newProj : p);
    } else {
      updated = [...projects, newProj];
    }
    setProjects(updated);
    setEditingProject(-1);
    setForm(p => ({ ...p, project_title: '', project_description: '' }));
  };

  const editProject = (idx) => {
    setEditingProject(idx);
    setForm(p => ({ ...p, project_title: projects[idx].title, project_description: projects[idx].description || '' }));
  };

  const deleteProject = (idx) => {
    setProjects(projects.filter((_, i) => i !== idx));
    if (editingProject === idx) {
      setEditingProject(-1);
      setForm(p => ({ ...p, project_title: '', project_description: '' }));
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSuccess(false);
    try {
      const payload = { ...form, registrations: { ...((profile?.registrations) || {}), projects } };
      await api.put('/business/profile', payload);
      await reloadProfile();
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

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-bold text-gray-900">Business Profile</h1>
        <p className="text-sm text-gray-500">Provide accurate financials to find matching schemes.</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-4">
        <Section icon={<Building2 className="w-4 h-4" />} title="Company Details">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="Company Name">
              <input name="company_name" value={form.company_name} onChange={onChange} required className="input" />
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
            {projects.length > 0 && (
              <div className="space-y-2">
                {projects.map((p, i) => (
                  <div key={i} className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-700 truncate">{p.title}</p>
                      {p.description && <p className="text-xs text-gray-400 truncate">{p.description}</p>}
                    </div>
                    <div className="flex items-center gap-1 ml-2">
                      <button type="button" onClick={() => editProject(i)} className="p-1.5 rounded-lg hover:bg-white text-gray-400 hover:text-blue-600 transition-colors">
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button type="button" onClick={() => deleteProject(i)} className="p-1.5 rounded-lg hover:bg-white text-gray-400 hover:text-red-600 transition-colors">
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
                <input name="project_title" value={form.project_title} onChange={onChange} placeholder="e.g. Solar Panel Assembly Line" className="input" />
              </Field>
              <Field label="Description">
                <textarea name="project_description" value={form.project_description} onChange={onChange} rows={3} placeholder="Describe your business idea. AI will match it with relevant schemes." className="input resize-none" />
              </Field>
              <div className="flex items-center gap-2">
                <button type="button" onClick={addProject} className="btn btn-primary text-sm">
                  <Plus className="w-3.5 h-3.5" />
                  {editingProject >= 0 ? 'Update Project' : 'Add to List'}
                </button>
                {editingProject >= 0 && (
                  <button type="button" onClick={() => { setEditingProject(-1); setForm(p => ({ ...p, project_title: '', project_description: '' })); }} className="btn btn-ghost text-sm">
                    Cancel
                  </button>
                )}
              </div>
            </div>

            <p className="text-xs text-gray-400">
              {projects.length > 0
                ? `${projects.length} project${projects.length > 1 ? 's' : ''} saved. Add more or edit existing ones.`
                : 'No projects yet. Add your business projects for AI-powered scheme matching.'}
            </p>
          </div>
        </Section>

        <div className="flex items-center gap-3">
          <button type="submit" disabled={saving} className="btn btn-primary">
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Profile'}
          </button>
          <button type="button" onClick={() => { refreshRecs(); setActiveTab('recommendations'); }} className="btn btn-accent">
            <Sparkles className="w-4 h-4" />
            Find Schemes
          </button>
          {success && (
            <div className="flex items-center gap-1.5 text-sm text-green-700 bg-green-50 border border-green-200 px-3 py-2 rounded-lg">
              <CheckCircle className="w-4 h-4" />
              Saved!
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
