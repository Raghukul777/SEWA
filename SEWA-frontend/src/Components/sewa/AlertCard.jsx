import React, { useState } from 'react';
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';
import { Button } from "@/components/ui/button";
import { format } from 'date-fns';

const riskConfig = {
  CRITICAL: {
    icon: AlertTriangle,
    bgColor: 'bg-rose-50',
    borderColor: 'border-rose-400',
    headerBg: 'bg-rose-100',
    textColor: 'text-rose-900',
    iconColor: 'text-rose-700',
    label: 'CRITICAL RISK'
  },
  HIGH: {
    icon: AlertTriangle,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-300',
    headerBg: 'bg-red-100',
    textColor: 'text-red-800',
    iconColor: 'text-red-600',
    label: 'HIGH RISK'
  },
  MODERATE: {
    icon: AlertCircle,
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-300',
    headerBg: 'bg-amber-100',
    textColor: 'text-amber-800',
    iconColor: 'text-amber-600',
    label: 'MODERATE RISK'
  },
  LOW: {
    icon: Info,
    bgColor: 'bg-slate-50',
    borderColor: 'border-slate-200',
    headerBg: 'bg-slate-100',
    textColor: 'text-slate-700',
    iconColor: 'text-slate-500',
    label: 'LOW RISK'
  }
};

export default function AlertCard({ alert, patientName, onFeedback }) {
  const [expanded, setExpanded] = useState(false);
  const config = riskConfig[alert.risk_level] || riskConfig.LOW;
  const RiskIcon = config.icon;

  const feedbackStatus = alert.feedback || 'pending';

  const formatText = (text) => {
    if (typeof text !== 'string') return text;
    return text.replace(/\d+\.\d{4,}/g, (match) => parseFloat(Number(match).toFixed(3)).toString());
  };

  return (
    <div className={cn(
      "rounded-xl border-2 overflow-hidden transition-all duration-200",
      config.borderColor, config.bgColor,
      feedbackStatus !== 'pending' && 'opacity-75'
    )}>
      {/* Header */}
      <div className={cn("px-4 py-3", config.headerBg)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <RiskIcon className={cn("w-5 h-5", config.iconColor)} />
            <div>
              <div className="flex items-center gap-2">
                <span className={cn("text-sm font-bold", config.textColor)}>
                  {config.label}
                </span>
                {feedbackStatus !== 'pending' && (
                  <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full",
                    feedbackStatus === 'approved'
                      ? "bg-green-100 text-green-700"
                      : "bg-slate-200 text-slate-600"
                  )}>
                    {feedbackStatus === 'approved' ? 'Validated' : 'False Positive'}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-600">{patientName}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Clock className="w-3.5 h-3.5" />
            {format(new Date(alert.timestamp), 'HH:mm')}
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="px-4 py-3 border-b border-slate-200">
        <p className="text-sm text-slate-700">{formatText(alert.clinical_summary)}</p>
      </div>

      {/* Expand Toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2 flex items-center justify-between text-sm text-slate-600 hover:bg-slate-100 transition-colors"
      >
        <span className="font-medium">Why this alert?</span>
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4">
          {/* Triggered Criteria */}
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Triggered Criteria
            </h4>
            <ul className="space-y-1.5">
              {alert.triggered_criteria?.map((criterion, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-2 flex-shrink-0" />
                  {formatText(criterion)}
                </li>
              ))}
            </ul>
          </div>

          {/* Recommended Actions */}
          {alert.recommended_actions?.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                Recommended Actions
              </h4>
              <ol className="space-y-1.5">
                {alert.recommended_actions.map((action, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-slate-700">
                    <span className="w-5 h-5 rounded-full bg-slate-200 flex items-center justify-center text-xs font-medium text-slate-600 flex-shrink-0">
                      {idx + 1}
                    </span>
                    {formatText(action)}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Feedback Buttons */}
          {feedbackStatus === 'pending' && onFeedback && (
            <div className="pt-3 border-t border-slate-200">
              <p className="text-xs text-slate-500 mb-2">Clinician Feedback</p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 text-green-700 border-green-300 hover:bg-green-50"
                  onClick={() => onFeedback(alert.id, 'approved')}
                >
                  <CheckCircle className="w-4 h-4 mr-1.5" />
                  Valid Alert
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 text-slate-600 border-slate-300 hover:bg-slate-100"
                  onClick={() => onFeedback(alert.id, 'false_positive')}
                >
                  <XCircle className="w-4 h-4 mr-1.5" />
                  False Alert
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}