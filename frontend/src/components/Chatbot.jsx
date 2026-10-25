import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Bot, User } from 'lucide-react';
import api from '../utils/api';

const Chatbot = ({ activeSchemeId = null }) => {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState([
    { id: 'welcome', sender: 'bot', text: 'Welcome to MSME Helpdesk! Ask about schemes, eligibility, or documents.' }
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  const quick = [
    "What is CGTMSE?",
    "How does turnover affect eligibility?",
    "Benefits for Women Entrepreneurs?",
    "Documents for MSME registration?"
  ];

  const send = async (text) => {
    if (!text.trim()) return;
    setMsgs(p => [...p, { id: Date.now().toString(), sender: 'user', text }]);
    setInput('');
    setBusy(true);
    try {
      const res = await api.post('/schemes/chat', { message: text, scheme_id: activeSchemeId });
      setMsgs(p => [...p, { id: (Date.now() + 1).toString(), sender: 'bot', text: res.data.response, sources: res.data.sources }]);
    } catch (err) {
      let errorMsg = err.response?.data?.detail || err.message;
      if (err.message === 'Network Error' || !err.response) {
        errorMsg = 'Could not connect to backend server. Please ensure the backend server is running on http://localhost:8000.';
      }
      setMsgs(p => [...p, { id: (Date.now() + 1).toString(), sender: 'bot', text: 'Error: ' + errorMsg }]);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs, open]);

  return (
    <div className="fixed bottom-5 right-5 z-50">
      {!open && (
        <button onClick={() => setOpen(true)} className="w-10 h-10 rounded-xl bg-[#1a365d] text-white shadow-lg hover:bg-[#153056] transition-all flex items-center justify-center">
          <MessageSquare className="w-5 h-5" />
        </button>
      )}
      {open && (
        <div className="w-80 rounded-xl shadow-xl border border-gray-200 bg-white flex flex-col overflow-hidden" style={{ height: '460px' }}>
          <div className="bg-[#1a365d] px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4 text-white" />
              <span className="text-sm font-semibold text-white">Scheme Assistant</span>
            </div>
            <button onClick={() => setOpen(false)} className="text-white/60 hover:text-white p-0.5"><X className="w-4 h-4" /></button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-gray-50/50">
            {msgs.map(m => (
              <div key={m.id} className={`flex items-start gap-2 ${m.sender === 'user' ? 'justify-end' : ''}`}>
                {m.sender === 'bot' && <Bot className="w-5 h-5 text-gray-400 mt-0.5 shrink-0" />}
                <div className={`max-w-[80%] px-3 py-2 rounded-lg text-sm leading-relaxed whitespace-pre-wrap ${m.sender === 'user' ? 'bg-[#1a365d] text-white rounded-br-none' : 'bg-white border border-gray-200 text-gray-700 rounded-bl-none'}`}>
                  {m.text}
                </div>
                {m.sender === 'user' && <User className="w-5 h-5 text-gray-400 mt-0.5 shrink-0" />}
              </div>
            ))}
            {busy && <div className="text-sm text-gray-400 pl-7">Thinking...</div>}
            <div ref={endRef} />
          </div>

          {msgs.length === 1 && (
            <div className="px-3 py-2 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-400 mb-1.5">Quick questions:</p>
              <div className="flex flex-wrap gap-1">
                {quick.map((q, i) => (
                  <button key={i} onClick={() => send(q)} className="text-xs px-2 py-1 rounded-md bg-gray-50 border border-gray-200 text-gray-600 hover:bg-gray-100">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="p-3 border-t border-gray-200 flex gap-2 bg-white">
            <input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask a question..." className="input flex-1 text-sm" />
            <button type="submit" disabled={busy || !input.trim()} className="w-8 h-8 rounded-lg bg-[#1a365d] text-white flex items-center justify-center disabled:opacity-40 shrink-0">
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default Chatbot;
