import React from 'react';
import { CheckCircle2, XCircle, ExternalLink, ArrowRight, Sparkles, Globe } from 'lucide-react';

const SchemeCard = ({ rec, onViewDetails }) => {
  const { scheme, match_score, is_eligible, recommendation_reason } = rec;
  const score = parseFloat(rec.match_percentage || match_score || 0);

  const badgeConfig = score >= 85
    ? { bg: 'bg-emerald-600 text-white', label: `${score}% Top Match`, icon: Sparkles }
    : score >= 70
    ? { bg: 'bg-blue-600 text-white', label: `${score}% Match`, icon: Sparkles }
    : score >= 50
    ? { bg: 'bg-amber-600 text-white', label: `${score}% Match`, icon: null }
    : { bg: 'bg-gray-600 text-white', label: `${score}% Match`, icon: null };

  const barColor = score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-blue-500' : score >= 40 ? 'bg-amber-500' : 'bg-gray-400';
  const textColor = score >= 80 ? 'text-emerald-700' : score >= 60 ? 'text-blue-700' : score >= 40 ? 'text-amber-700' : 'text-gray-700';

  return (
    <div className="card border-t-[3px] border-t-[#1a365d] flex flex-col h-full relative group hover:shadow-md transition-shadow">
      {/* AI Match Percentage Badge */}
      <div className={`absolute top-0 right-0 ${badgeConfig.bg} text-[11px] font-bold px-2.5 py-0.5 rounded-bl-lg flex items-center gap-1 shadow-sm`}>
        {badgeConfig.icon && <badgeConfig.icon className="w-3 h-3" />}
        <span>{badgeConfig.label}</span>
      </div>

      <div className="p-4 flex-1">
        <div className="flex items-center gap-2 text-xs text-gray-400 font-medium uppercase tracking-wider mb-1.5 pr-20">
          <span className="truncate">{scheme.ministry}</span>
          <span>·</span>
          <span className="text-[#1a365d] font-semibold">{scheme.funding_type || 'Subsidy'}</span>
        </div>

        <h3 className="text-sm font-bold text-gray-900 mb-1 line-clamp-1 group-hover:text-[#1a365d] transition-colors">{scheme.name}</h3>
        <p className="text-sm text-gray-500 mb-3 line-clamp-2">{scheme.description}</p>

        <div className="flex items-center gap-2 mb-3 py-1 px-2 rounded-lg bg-gray-50 border border-gray-200">
          {is_eligible ? (
            <span className="flex items-center gap-1 text-xs font-semibold text-emerald-700">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Criteria Met
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs font-semibold text-amber-700">
              <XCircle className="w-3.5 h-3.5 text-amber-600" /> Verify Criteria
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2.5 border-t border-gray-100">
          <div>
            <div className="flex items-baseline justify-between">
              <p className="text-[11px] text-gray-400 font-bold uppercase tracking-wider">AI Match</p>
              <span className={`text-sm font-extrabold ${textColor}`}>{score}%</span>
            </div>
            <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden mt-1 border border-gray-200">
              <div className={`h-full rounded-full ${barColor} transition-all duration-500`} style={{ width: `${Math.min(score, 100)}%` }}></div>
            </div>
          </div>
          <div>
            <p className="text-[11px] text-gray-400 font-bold uppercase tracking-wider">Max Funding</p>
            <p className="text-sm font-bold text-[#1a365d] mt-0.5">
              {scheme.max_benefit_amount > 0 ? `₹${(parseFloat(scheme.max_benefit_amount) / 100000).toFixed(1)}L` : 'Variable'}
            </p>
          </div>
        </div>

        {recommendation_reason && (
          <p className="text-xs text-gray-600 bg-blue-50/70 p-2 rounded-lg border border-blue-100 mt-3 leading-relaxed line-clamp-2">
            {recommendation_reason}
          </p>
        )}
      </div>

      <div className="px-4 pb-3 pt-0">
        <button onClick={() => onViewDetails(rec)} className="btn btn-primary w-full text-sm">
          View Details <ArrowRight className="w-3.5 h-3.5" />
        </button>
        <div className="flex items-center gap-2 mt-2">
          <a href="https://www.udyamregistration.gov.in/UdyamRegistration.aspx" target="_blank" rel="noopener noreferrer" className="flex-1 text-center text-xs text-gray-500 hover:text-[#1a365d] bg-gray-50 border border-gray-200 rounded-lg px-2 py-1.5 hover:bg-gray-100 transition-colors">
            Udyam Register
          </a>
          <a href="https://msme.gov.in" target="_blank" rel="noopener noreferrer" className="flex-1 text-center text-xs text-gray-500 hover:text-[#1a365d] bg-gray-50 border border-gray-200 rounded-lg px-2 py-1.5 hover:bg-gray-100 transition-colors">
            msme.gov.in
          </a>
        </div>
      </div>
    </div>
  );
};

export default SchemeCard;
