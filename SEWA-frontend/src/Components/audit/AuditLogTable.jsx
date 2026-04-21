import React, { useState } from 'react';
import { cn } from "@/lib/utils";
import { format } from 'date-fns';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Pause,
  Play,
  Eye,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  FileText,
  User
} from 'lucide-react';
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const eventTypeConfig = {
  vital_reading_generated: {
    icon: Activity,
    label: 'Vital Reading',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200'
  },
  alert_generated: {
    icon: AlertTriangle,
    label: 'Alert Generated',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200'
  },
  alert_feedback_submitted: {
    icon: CheckCircle,
    label: 'Alert Feedback',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200'
  },
  risk_level_changed: {
    icon: RefreshCw,
    label: 'Risk Changed',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200'
  },
  patient_status_changed: {
    icon: User,
    label: 'Status Changed',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200'
  },
  simulation_paused: {
    icon: Pause,
    label: 'Simulation Paused',
    color: 'text-slate-600',
    bgColor: 'bg-slate-50',
    borderColor: 'border-slate-200'
  },
  simulation_resumed: {
    icon: Play,
    label: 'Simulation Resumed',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200'
  },
  patient_selected: {
    icon: Eye,
    label: 'Patient Viewed',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
    borderColor: 'border-indigo-200'
  },
  system_initialized: {
    icon: Play,
    label: 'System Initialized',
    color: 'text-slate-600',
    bgColor: 'bg-slate-50',
    borderColor: 'border-slate-200'
  }
};

const severityConfig = {
  info: {
    badge: 'bg-slate-100 text-slate-700',
    label: 'Info'
  },
  warning: {
    badge: 'bg-amber-100 text-amber-700',
    label: 'Warning'
  },
  critical: {
    badge: 'bg-red-100 text-red-700',
    label: 'Critical'
  }
};

function AuditLogRow({ log }) {
  const [expanded, setExpanded] = useState(false);
  const config = eventTypeConfig[log.event_type] || eventTypeConfig.system_initialized;
  const EventIcon = config.icon;
  const severityStyle = severityConfig[log.severity] || severityConfig.info;

  const hasDetails = log.event_metadata || log.previous_state || log.new_state;

  return (
    <div className={cn(
      "border rounded-lg overflow-hidden transition-all",
      config.borderColor,
      expanded ? config.bgColor : 'bg-white hover:bg-slate-50'
    )}>
      <div 
        className={cn(
          "flex items-start gap-4 p-4",
          hasDetails && "cursor-pointer"
        )}
        onClick={hasDetails ? () => setExpanded(!expanded) : undefined}
      >
        {/* Icon */}
        <div className={cn(
          "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0",
          config.bgColor
        )}>
          <EventIcon className={cn("w-5 h-5", config.color)} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 mb-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-slate-800">{config.label}</span>
              <Badge variant="secondary" className={cn("text-xs", severityStyle.badge)}>
                {severityStyle.label}
              </Badge>
              {log.risk_level && (
                <Badge variant="outline" className="text-xs">
                  {log.risk_level}
                </Badge>
              )}
            </div>
            <span className="text-xs text-slate-400 whitespace-nowrap">
              {format(new Date(log.timestamp), 'MMM d, HH:mm:ss')}
            </span>
          </div>

          <p className="text-sm text-slate-600 mb-1">{log.event_description}</p>

          <div className="flex items-center gap-3 text-xs text-slate-500">
            {log.patient_name && (
              <span className="flex items-center gap-1">
                <User className="w-3 h-3" />
                {log.patient_name}
              </span>
            )}
            {log.user_email && (
              <span>by {log.user_email}</span>
            )}
          </div>
        </div>

        {/* Expand button */}
        {hasDetails && (
          <button className="text-slate-400 hover:text-slate-600">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}
      </div>

      {/* Expanded Details */}
      {expanded && hasDetails && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-200 space-y-3">
          {/* Metadata */}
          {log.event_metadata && Object.keys(log.event_metadata).length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase mb-1.5">Event Details</h4>
              <div className="bg-white rounded-lg p-3 border border-slate-200">
                <pre className="text-xs text-slate-700 whitespace-pre-wrap">
                  {JSON.stringify(log.event_metadata, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* State Changes */}
          {(log.previous_state || log.new_state) && (
            <div className="grid grid-cols-2 gap-3">
              {log.previous_state && (
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase mb-1.5">Previous State</h4>
                  <div className="bg-red-50 rounded-lg p-2 border border-red-100">
                    <pre className="text-xs text-slate-700">
                      {JSON.stringify(log.previous_state, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
              {log.new_state && (
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase mb-1.5">New State</h4>
                  <div className="bg-green-50 rounded-lg p-2 border border-green-100">
                    <pre className="text-xs text-slate-700">
                      {JSON.stringify(log.new_state, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Alert ID */}
          {log.alert_id && (
            <div>
              <span className="text-xs text-slate-500">Alert ID: </span>
              <code className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded">{log.alert_id}</code>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AuditLogTable({ logs, isLoading }) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array(5).fill(0).map((_, i) => (
          <div key={i} className="h-20 bg-slate-100 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-400">
        <FileText className="w-12 h-12 mb-3 opacity-50" />
        <p className="text-sm">No audit logs found</p>
        <p className="text-xs mt-1">Events will appear here as they occur</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {logs.map((log) => (
        <AuditLogRow key={log.id} log={log} />
      ))}
    </div>
  );
}