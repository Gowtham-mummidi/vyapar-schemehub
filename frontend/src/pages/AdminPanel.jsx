import React, { useState, useEffect, useRef } from 'react';
import api from '../utils/api';
import * as XLSX from 'xlsx';
import { Plus, Trash2, FileUp, FileJson, CheckCircle2, AlertTriangle, Upload, Table } from 'lucide-react';

const AdminPanel = () => {
  const [schemes, setSchemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [uploadingId, setUploadingId] = useState(null);
  const [bulkFile, setBulkFile] = useState(null);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const [pdfAsSchemeFile, setPdfAsSchemeFile] = useState(null);
  const [pdfAsSchemeUploading, setPdfAsSchemeUploading] = useState(false);
  const fileInputRef = useRef(null);
  const pdfAsSchemeInputRef = useRef(null);

  const [newScheme, setNewScheme] = useState({
    name: '',
    description: '',
    ministry: 'Ministry of MSME',
    funding_type: 'Subsidy',
    max_benefit_amount: 0,
    official_link: '',
    eligibility_rules: {
      max_turnover: 50000000,
      max_investment: 10000000,
      min_business_age: 1,
      allowed_sectors: ['All'],
      allowed_states: ['All'],
      allowed_owner_categories: ['All'],
      required_registrations: ['udyam']
    },
    required_documents: ['Udyam']
  });

  useEffect(() => {
     loadSchemes();
  }, []);

  const loadSchemes = async () => {
     try {
        setLoading(true);
        const res = await api.get('/schemes');
        setSchemes(res.data);
     } catch (err) {
        console.error('Error fetching schemes:', err);
     } finally {
        setLoading(false);
     }
  };

  const showSuccess = (msg) => {
    setSuccessMsg(msg);
    setErrorMsg('');
    setTimeout(() => setSuccessMsg(''), 5000);
  };

  const showError = (msg) => {
    setErrorMsg(msg);
    setSuccessMsg('');
    setTimeout(() => setErrorMsg(''), 5000);
  };

  const handleCreateScheme = async (e) => {
    e.preventDefault();
    try {
      await api.post('/admin/schemes', newScheme);
      showSuccess('Scheme created.');
      setNewScheme({
        name: '', description: '', ministry: 'Ministry of MSME', funding_type: 'Subsidy',
        max_benefit_amount: 0, official_link: '',
        eligibility_rules: { max_turnover: 50000000, max_investment: 10000000, min_business_age: 1, allowed_sectors: ['All'], allowed_states: ['All'], allowed_owner_categories: ['All'], required_registrations: ['udyam'] },
        required_documents: ['Udyam']
      });
      loadSchemes();
    } catch (err) {
      showError('Failed to create scheme.');
    }
  };

  const handleDeleteScheme = async (id) => {
     if (!window.confirm('Delete this scheme and its vector indexes?')) return;
     try {
        await api.delete(`/admin/schemes/${id}`);
        showSuccess('Scheme deleted.');
        loadSchemes();
     } catch (err) {
        showError('Delete failed.');
     }
  };

  const handleClearAll = async () => {
     if (!window.confirm('Delete ALL schemes? This cannot be undone.')) return;
     try {
        const res = await api.delete('/admin/schemes');
        showSuccess(res.data.message);
        setBulkResult(null);
        loadSchemes();
     } catch (err) {
        showError('Failed to clear schemes.');
     }
  };

  const handlePDFUpload = async (e, id) => {
     const file = e.target.files[0];
     if (!file) return;
     setUploadingId(id);
     const formData = new FormData();
     formData.append('file', file);
     try {
        await api.post(`/admin/schemes/${id}/upload-pdf`, formData, {
           headers: { 'Content-Type': 'multipart/form-data' }
        });
        showSuccess('PDF ingested and indexed.');
        loadSchemes();
     } catch (err) {
        showError('PDF ingestion failed.');
     } finally {
        setUploadingId(null);
     }
  };

  const handlePdfAsSchemeUpload = async () => {
    if (!pdfAsSchemeFile) return;
    setPdfAsSchemeUploading(true);
    const formData = new FormData();
    formData.append('file', pdfAsSchemeFile);
    try {
      const res = await api.post('/admin/schemes/from-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      showSuccess(`Scheme "${res.data.scheme.name}" created from PDF.`);
      setPdfAsSchemeFile(null);
      if (pdfAsSchemeInputRef.current) pdfAsSchemeInputRef.current.value = '';
      loadSchemes();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      showError(`PDF upload failed: ${detail}`);
    } finally {
      setPdfAsSchemeUploading(false);
    }
  };

  const parseFile = async (file) => {
    const ext = file.name.split('.').pop().toLowerCase();

    if (ext === 'json') {
      const text = await file.text();
      const data = JSON.parse(text);
      return Array.isArray(data) ? data : data.schemes || [];
    }

    const buffer = await file.arrayBuffer();
    const workbook = XLSX.read(buffer, { type: 'array' });
    const sheetName = workbook.SheetNames[0];
    if (!sheetName) return [];
    const rows = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { defval: '' });

    return rows.map(row => {
      const scheme = {
        name: row.name || row.Name || row['Scheme Name'] || '',
        description: row.description || row.Description || '',
        ministry: row.ministry || row.Ministry || '',
        funding_type: row.funding_type || row['Funding Type'] || row.fundingType || 'Subsidy',
        max_benefit_amount: parseFloat(row.max_benefit_amount || row['Max Benefit'] || row.maxBenefitAmount || 0),
        official_link: row.official_link || row['Official Link'] || row.officialLink || '',
        eligibility_rules: {},
        required_documents: [],
      };

      if (row.eligibility_rules || row['Eligibility Rules'] || row.eligibilityRules) {
        try {
          const raw = row.eligibility_rules || row['Eligibility Rules'] || row.eligibilityRules;
          scheme.eligibility_rules = typeof raw === 'string' ? JSON.parse(raw) : raw;
        } catch {}
      }
      if (row.required_documents || row['Required Documents'] || row.requiredDocuments) {
        const raw = row.required_documents || row['Required Documents'] || row.requiredDocuments;
        scheme.required_documents = typeof raw === 'string'
          ? raw.split(',').map(s => s.trim()).filter(Boolean)
          : Array.isArray(raw) ? raw : [];
      }

      return scheme;
    }).filter(s => s.name);
  };

  const handleBulkFileChange = (e) => {
    const file = e.target.files[0];
    setBulkFile(file);
    setBulkResult(null);
  };

  const handleBulkUpload = async () => {
    if (!bulkFile) return;
    setBulkUploading(true);
    setBulkResult(null);
    try {
      const schemesArray = await parseFile(bulkFile);
      if (!schemesArray.length) {
        showError('No schemes found. Bulk upload accepts JSON (.json), Excel (.xlsx/.xls), or CSV files. PDFs are uploaded per-scheme below.');
        setBulkUploading(false);
        return;
      }
      const res = await api.post('/admin/schemes/bulk-upload', schemesArray);
      setBulkResult(res.data);
      showSuccess(`Uploaded ${res.data.created} schemes (${res.data.skipped} skipped).`);
      setBulkFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      loadSchemes();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      showError(`Bulk upload failed: ${detail}`);
    } finally {
      setBulkUploading(false);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-bold text-gray-900">Admin Panel</h1>
        <p className="text-sm text-gray-500">Manage schemes, bulk upload, and clear demo data.</p>
      </div>

      {successMsg && (
        <div className="flex items-center gap-1.5 text-green-700 text-sm font-medium bg-green-50 border border-green-200 px-4 py-3 rounded-lg">
           <CheckCircle2 className="w-4 h-4" />
           <span>{successMsg}</span>
        </div>
      )}
      {errorMsg && (
        <div className="flex items-center gap-1.5 text-red-700 text-sm font-medium bg-red-50 border border-red-200 px-4 py-3 rounded-lg">
           <AlertTriangle className="w-4 h-4" />
           <span>{errorMsg}</span>
        </div>
      )}

      {/* Bulk Upload Section */}
      <div className="card">
        <div className="card-body space-y-3">
          <h3 className="font-bold text-gray-900 flex items-center gap-2">
            <Upload className="w-4 h-4 text-blue-600" />
            Bulk Upload Schemes
          </h3>
          <p className="text-xs text-gray-500">
            Upload <strong>JSON</strong>, <strong>Excel (.xlsx/.xls)</strong>, or <strong>CSV</strong> files. Existing schemes (by name) are skipped.
            See below for the expected column format.
          </p>
          <div className="flex items-center gap-3 flex-wrap">
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,.xlsx,.xls,.csv"
              onChange={handleBulkFileChange}
              className="text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-gray-300 file:text-sm file:font-medium file:bg-white file:text-gray-700 hover:file:bg-gray-50"
            />
            <button
              onClick={handleBulkUpload}
              disabled={!bulkFile || bulkUploading}
              className="btn btn-primary text-sm"
            >
              <Table className="w-3.5 h-3.5" />
              {bulkUploading ? 'Uploading...' : 'Upload'}
            </button>
            {bulkFile && (
              <span className="text-xs text-gray-500 truncate max-w-[200px]">{bulkFile.name}</span>
            )}
            <button
              onClick={handleClearAll}
              className="btn text-sm text-red-600 hover:bg-red-50 ml-auto"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear All Schemes
            </button>
          </div>
          <details className="text-xs text-gray-500">
            <summary className="cursor-pointer hover:text-gray-700 font-medium">Expected columns (Excel/CSV)</summary>
            <div className="mt-2 bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-1 font-mono">
              <p><span className="text-blue-600">name</span> (required) — Scheme name</p>
              <p><span className="text-blue-600">description</span> (required) — Scheme description</p>
              <p><span className="text-blue-600">ministry</span> — Ministry name (default: "Ministry of MSME")</p>
              <p><span className="text-blue-600">funding_type</span> — Subsidy/Grant/Loan/Equity/Guarantee</p>
              <p><span className="text-blue-600">max_benefit_amount</span> — Max payout in INR</p>
              <p><span className="text-blue-600">official_link</span> — Official website URL</p>
              <p><span className="text-blue-600">eligibility_rules</span> — JSON string (e.g. {'{"max_turnover": 50000000}'})</p>
              <p><span className="text-blue-600">required_documents</span> — Comma-separated list (e.g. "Udyam, PAN")</p>
            </div>
          </details>
          {bulkResult && (
            <div className="text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
              Created: <span className="font-semibold text-green-600">{bulkResult.created}</span>
              {' | '}Skipped (duplicates): <span className="font-semibold text-amber-600">{bulkResult.skipped}</span>
            </div>
          )}
        </div>
      </div>

      {/* Upload PDF as New Scheme */}
      <div className="card">
        <div className="card-body space-y-3">
          <h3 className="font-bold text-gray-900 flex items-center gap-2">
            <FileUp className="w-4 h-4 text-blue-600" />
            Upload PDF as New Scheme
          </h3>
          <p className="text-xs text-gray-500">
            Upload a PDF containing scheme details. Gemini will extract the name, description, eligibility rules, and documents automatically. If a scheme with the same name exists, the PDF will be ingested for that scheme instead.
          </p>
          <div className="flex items-center gap-3">
            <input
              ref={pdfAsSchemeInputRef}
              type="file"
              accept=".pdf"
              onChange={(e) => setPdfAsSchemeFile(e.target.files[0])}
              className="text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-gray-300 file:text-sm file:font-medium file:bg-white file:text-gray-700 hover:file:bg-gray-50"
            />
            <button
              onClick={handlePdfAsSchemeUpload}
              disabled={!pdfAsSchemeFile || pdfAsSchemeUploading}
              className="btn btn-primary text-sm"
            >
              <FileUp className="w-3.5 h-3.5" />
              {pdfAsSchemeUploading ? 'Processing...' : 'Create from PDF'}
            </button>
            {pdfAsSchemeFile && (
              <span className="text-xs text-gray-500 truncate max-w-[200px]">{pdfAsSchemeFile.name}</span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="card">
          <div className="card-body space-y-4">
            <h3 className="font-bold text-gray-900 flex items-center gap-2">
              <Plus className="w-4 h-4 text-blue-600" />
              Create Scheme
            </h3>
            <form onSubmit={handleCreateScheme} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
                <input type="text" value={newScheme.name} onChange={(e) => setNewScheme(p => ({ ...p, name: e.target.value }))} required placeholder="e.g. CGTMSE Guarantee" className="input text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
                <textarea value={newScheme.description} onChange={(e) => setNewScheme(p => ({ ...p, description: e.target.value }))} required rows="3" placeholder="Brief summary..." className="input text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Ministry</label>
                  <input type="text" value={newScheme.ministry} onChange={(e) => setNewScheme(p => ({ ...p, ministry: e.target.value }))} className="input text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Funding Type</label>
                  <select value={newScheme.funding_type} onChange={(e) => setNewScheme(p => ({ ...p, funding_type: e.target.value }))} className="select text-sm">
                    <option value="Subsidy">Subsidy</option>
                    <option value="Grant">Grant</option>
                    <option value="Loan">Loan</option>
                    <option value="Equity">Equity</option>
                    <option value="Guarantee">Guarantee</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Max Payout (INR)</label>
                  <input type="number" value={newScheme.max_benefit_amount} onChange={(e) => setNewScheme(p => ({ ...p, max_benefit_amount: parseFloat(e.target.value) }))} className="input text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Official Link</label>
                  <input type="url" value={newScheme.official_link} onChange={(e) => setNewScheme(p => ({ ...p, official_link: e.target.value }))} placeholder="https://..." className="input text-sm" />
                </div>
              </div>
              <button type="submit" className="btn btn-primary w-full text-sm justify-center">
                <Plus className="w-4 h-4" /> Register Scheme
              </button>
            </form>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <h3 className="font-bold text-gray-900 flex items-center gap-2">
            <span>Active Schemes ({schemes.length})</span>
          </h3>

          {loading ? (
             <div className="flex h-40 items-center justify-center">
                <div className="w-8 h-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
             </div>
          ) : schemes.length === 0 ? (
             <div className="card p-12 text-center">
               <p className="text-sm text-gray-400">No schemes yet. Upload a JSON file above or create one.</p>
             </div>
          ) : (
             <div className="space-y-3">
                {schemes.map((scheme) => (
                   <div key={scheme.id} className="card">
                     <div className="card-body flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                       <div className="max-w-md">
                         <span className="text-xs text-gray-400 font-medium">{scheme.funding_type} · {scheme.ministry}</span>
                         <h4 className="text-sm font-bold text-gray-900 mt-0.5">{scheme.name}</h4>
                         <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{scheme.description}</p>
                         <div className="flex items-center gap-2 mt-2">
                            <span className={`w-2 h-2 rounded-full ${scheme.pdf_storage_path ? 'bg-green-500' : 'bg-amber-500'}`}></span>
                            <span className="text-xs text-gray-400">
                               {scheme.pdf_storage_path ? 'Vector index ready' : 'No PDF ingested'}
                            </span>
                         </div>
                       </div>
                       <div className="flex items-center gap-2 w-full md:w-auto justify-between md:justify-end">
                         <label className="btn text-sm cursor-pointer select-none">
                            <FileUp className="w-3.5 h-3.5" />
                            <span>{uploadingId === scheme.id ? 'Ingesting...' : 'Upload PDF'}</span>
                            <input type="file" accept=".pdf" className="hidden" disabled={uploadingId !== null} onChange={(e) => handlePDFUpload(e, scheme.id)} />
                         </label>
                         <button onClick={() => handleDeleteScheme(scheme.id)} className="btn text-sm text-red-600 hover:bg-red-50">
                            <Trash2 className="w-3.5 h-3.5" />
                         </button>
                       </div>
                     </div>
                   </div>
                ))}
             </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;
