import React from 'react';
import { cn } from "@/lib/utils";
import { Activity, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { format } from 'date-fns';

const statusConfig = {
  Stable: {
    icon: CheckCircle,
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    textColor: 'text-emerald-700',
    iconColor: 'text-emerald-500',
    dotColor: 'bg-emerald-500'
  },
  Warning: {
    icon: Activity,
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    textColor: 'text-amber-700',
    iconColor: 'text-amber-500',
    dotColor: 'bg-amber-500'
  },
  Critical: {
    icon: AlertTriangle,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-700',
    iconColor: 'text-red-500',
    dotColor: 'bg-red-500'
  }
};

export default function PatientCard({ patient, latestVitals, isSelected, onClick }) {
  const status = patient.status || 'Stable';
  const config = statusConfig[status] || statusConfig.Stable;
  const StatusIcon = config.icon;

  const formatVal = (val) => {
    if (val == null) return '--';
    const num = Number(val);
    return isNaN(num) ? val : parseFloat(num.toFixed(3));
  };

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left p-4 rounded-xl border-2 transition-all duration-200",
        "hover:shadow-md focus:outline-none focus:ring-2 focus:ring-slate-300",
        isSelected
          ? "border-slate-800 bg-slate-50 shadow-md"
          : `${config.borderColor} ${config.bgColor}`,
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={cn("w-2 h-2 rounded-full animate-pulse", config.dotColor)} />
            <span className="font-semibold text-slate-800 truncate">
              {patient.name}
            </span>
          </div>

          <div className="mt-1 flex items-center gap-2 text-sm text-slate-500">
            <span className="font-mono">{patient.patient_id}</span>
            <span className="text-slate-300">•</span>
            <span>Bed {patient.bed_number || 'N/A'}</span>
          </div>

          {patient.admission_reason && (
            <p className="mt-1.5 text-xs text-slate-500 truncate">
              {patient.admission_reason}
            </p>
          )}
        </div>

        <div className="flex flex-col items-end gap-1">
          <div className={cn(
            "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
            config.bgColor, config.textColor
          )}>
            <StatusIcon className={cn("w-3.5 h-3.5", config.iconColor)} />
            {status}
          </div>
        </div>
      </div>

      {latestVitals && (
        <div className="mt-3 pt-3 border-t border-slate-200">
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div>
              <span className="text-slate-400">HR</span>
              <p className="font-medium text-slate-700">{formatVal(latestVitals.heart_rate)}</p>
            </div>
            <div>
              <span className="text-slate-400">MAP</span>
              <p className="font-medium text-slate-700">{formatVal(latestVitals.map)}</p>
            </div>
            <div>
              <span className="text-slate-400">RR</span>
              <p className="font-medium text-slate-700">{formatVal(latestVitals.respiratory_rate)}</p>
            </div>
            <div>
              <span className="text-slate-400">SpO₂</span>
              <p className="font-medium text-slate-700">{formatVal(latestVitals.spo2)}%</p>
            </div>
            <div>
              <span className="text-slate-400">Temp</span>
              <p className="font-medium text-slate-700">{formatVal(latestVitals.temperature)}°</p>
            </div>
            <div>
              <span className="text-slate-400">Lactate</span>
              <p className="font-medium text-slate-700">{formatVal(latestVitals.lactate)}</p>
            </div>
          </div>

          <div className="mt-2 flex items-center gap-1 text-xs text-slate-400">
            <Clock className="w-3 h-3" />
            <span>
              {format(new Date(latestVitals.timestamp), 'HH:mm:ss')}
            </span>
          </div>
        </div>
      )}
    </button>
  );
}