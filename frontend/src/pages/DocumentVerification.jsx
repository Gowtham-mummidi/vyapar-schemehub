import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { FileUp, CheckCircle2, AlertTriangle, XCircle, Loader2, ShieldCheck, RefreshCw } from 'lucide-react';

const DocumentVerification = () => {
  const { profile, reloadProfile } = useAuth();
  const [verifyingDoc, setVerifyingDoc] = useState(null);
  const [ocrResults, setOcrResults] = useState({});

  const documents = [
    { type: 'GST', label: 'GST registration certificate', code: 'gst', desc: 'Validates state-level operations and company name check.' },
    { type: 'UDYAM', label: 'Udyam Registration Certificate', code: 'udyam', desc: 'Checks MSME classification parameters and registrations.' },
    { type: 'PAN', label: 'Permanent Account Number (PAN)', code: 'pan', desc: 'Confirms financial identification and taxpayer data.' },
    { type: 'AADHAAR', label: 'Aadhaar of Business Owner', code: 'aadhaar', desc: 'Confirms identification verification check.' }
  ];

  useEffect(() => {
    const fetchVerifications = async () => {
      try {
        const res = await api.get('/ocr/verifications');
        if (res.data && Array.isArray(res.data)) {
          const mapped = {};
          res.data.forEach(v => {
            if (!mapped[v.document_type]) {
              mapped[v.document_type] = v;
            }
          });
          setOcrResults(mapped);
        }
      } catch (err) {
        console.warn('Could not load past verifications:', err);
      }
    };
    fetchVerifications();
  }, []);

  const handleFileUpload = async (e, docType) => {
    const file = e.target.files[0];
    if (!file) return;

    setVerifyingDoc(docType);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', docType);

    // Reset input so re-selecting same file triggers change
    e.target.value = '';

    try {
      // Post without explicit manual Content-Type header so browser adds proper multipart boundary
      const res = await api.post('/ocr/verify', formData);
      setOcrResults(prev => ({ ...prev, [docType]: res.data }));
      await reloadProfile();
    } catch (err) {
      console.error('OCR Verification failed:', err);
      const serverMsg = err.response?.data?.detail || err.message || 'Error processing document.';
      setOcrResults(prev => ({
        ...prev,
        [docType]: {
          document_type: docType,
          verification_status: 'Failed',
          mismatch_details: { error: serverMsg }
        }
      }));
    } finally {
      setVerifyingDoc(null);
    }
  };

  const getStatusDisplay = (docCode, docType) => {
    if (verifyingDoc === docType) {
      return (
        <span className="flex items-center gap-1 text-xs text-blue-600 font-medium">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          OCR Processing...
        </span>
      );
    }

    const result = ocrResults[docType];
    const profileStatus = profile?.registrations?.[docCode];

    if (profileStatus === true || (result && result.verification_status === 'Verified')) {
      return <span className="badge badge-green flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Verified</span>;
    }

    if (profileStatus === false || (result && result.verification_status === 'Mismatched')) {
      return <span className="badge flex items-center gap-1" style={{background:'#fef3c7', color:'#92400e', border:'1px solid #fde68a'}}><AlertTriangle className="w-3 h-3" /> Mismatch</span>;
    }

    if (result && result.verification_status === 'Failed') {
      return <span className="badge flex items-center gap-1" style={{background:'#fee2e2', color:'#991b1b', border:'1px solid #fecaca'}}><XCircle className="w-3 h-3" /> Failed</span>;
    }

    return <span className="text-xs text-gray-400">Not uploaded</span>;
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-bold text-gray-900">Document Verification</h1>
        <p className="text-sm text-gray-500">Upload certificates for OCR-based verification to unlock higher match scores.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-3">
          {documents.map((doc) => (
            <div key={doc.type} className="card">
              <div className="card-body flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="space-y-0.5 max-w-md">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">{doc.type}</h3>
                    <span className="text-xs text-gray-400">— {doc.label}</span>
                  </div>
                  <p className="text-xs text-gray-500">{doc.desc}</p>
                </div>
                <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
                  {getStatusDisplay(doc.code, doc.type)}
                  <label className="btn text-sm cursor-pointer select-none">
                    <FileUp className="w-3.5 h-3.5" />
                    Upload
                    <input
                      type="file"
                      accept=".pdf, image/*"
                      className="hidden"
                      disabled={verifyingDoc !== null}
                      onChange={(e) => handleFileUpload(e, doc.type)}
                    />
                  </label>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-3">
          <h3 className="font-bold text-gray-900 text-sm">OCR Audit Log</h3>
          <div className="card">
            <div className="card-body">
              {Object.keys(ocrResults).length === 0 ? (
                <div className="text-center py-8 text-xs text-gray-400 space-y-2">
                  <ShieldCheck className="w-8 h-8 mx-auto text-gray-300" />
                  <p>Upload a document to run real-time OCR extraction and verification.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {Object.entries(ocrResults).map(([type, res]) => (
                    <div key={type} className="border-b border-gray-100 pb-3 last:border-b-0 last:pb-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-gray-700 uppercase">{type}</span>
                        <span className={`text-xs font-bold ${
                          res.verification_status === 'Verified' ? 'text-green-600' :
                          res.verification_status === 'Mismatched' ? 'text-amber-600' : 'text-red-600'
                        }`}>
                          {res.verification_status}
                        </span>
                      </div>

                      {res.extracted_data && Object.keys(res.extracted_data).length > 0 && (
                        <div className="mt-2 bg-gray-50 border border-gray-200 p-2.5 rounded-lg text-xs space-y-1 text-gray-600 font-mono">
                          <span className="block font-bold text-gray-400 uppercase tracking-wider text-[10px] mb-1">Extracted:</span>
                          {Object.entries(res.extracted_data).map(([k, v]) => (
                            <div key={k} className="flex justify-between">
                              <span className="capitalize">{k.replace(/_/g, ' ')}:</span>
                              <span className="text-gray-900 font-semibold truncate max-w-[140px] text-right">{v || 'N/A'}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {res.mismatch_details && Object.keys(res.mismatch_details).length > 0 && (
                        <div className={`mt-2 text-xs p-2.5 rounded-lg border ${
                          res.verification_status === 'Failed'
                            ? 'text-red-700 bg-red-50 border-red-200'
                            : 'text-amber-700 bg-amber-50 border-amber-200'
                        }`}>
                          <span className="block font-bold uppercase tracking-wider text-[10px] mb-1">
                            {res.verification_status === 'Failed' ? 'Failure Reason:' : 'Discrepancy:'}
                          </span>
                          {Object.entries(res.mismatch_details).map(([k, v]) => (
                            <p key={k} className="leading-relaxed">{v}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentVerification;
