import React from 'react';
import { cn } from "@/lib/utils";
import { 
  Heart, 
  Wind, 
  Gauge, 
  Thermometer, 
  Activity,
  Droplets,
  TestTube
} from 'lucide-react';

const vitalConfigs = {
  heart_rate: {
    label: 'Heart Rate',
    unit: 'bpm',
    icon: Heart,
    normalRange: [60, 100],
    color: 'rose'
  },
  respiratory_rate: {
    label: 'Resp. Rate',
    unit: '/min',
    icon: Wind,
    normalRange: [12, 20],
    color: 'emerald'
  },
  map: {
    label: 'MAP',
    unit: 'mmHg',
    icon: Gauge,
    normalRange: [65, 100],
    color: 'indigo'
  },
  temperature: {
    label: 'Temp',
    unit: '°C',
    icon: Thermometer,
    normalRange: [36, 38],
    color: 'violet'
  },
  spo2: {
    label: 'SpO₂',
    unit: '%',
    icon: Activity,
    normalRange: [94, 100],
    color: 'blue'
  },
  lactate: {
    label: 'Lactate',
    unit: 'mmol/L',
    icon: Droplets,
    normalRange: [0.5, 2],
    color: 'amber'
  },
  wbc: {
    label: 'WBC',
    unit: '×10³/μL',
    icon: TestTube,
    normalRange: [4, 12],
    color: 'slate'
  },
  creatinine: {
    label: 'Creatinine',
    unit: 'mg/dL',
    icon: TestTube,
    normalRange: [0.6, 1.2],
    color: 'slate'
  }
};

function getValueStatus(value, normalRange) {
  if (value == null) return 'unknown';
  if (value < normalRange[0]) return 'low';
  if (value > normalRange[1]) return 'high';
  return 'normal';
}

function VitalItem({ vitalKey, value }) {
  const config = vitalConfigs[vitalKey];
  if (!config) return null;
  
  const Icon = config.icon;
  const status = getValueStatus(value, config.normalRange);
  
  const statusStyles = {
    normal: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    low: 'bg-blue-50 border-blue-200 text-blue-700',
    high: 'bg-red-50 border-red-200 text-red-700',
    unknown: 'bg-slate-50 border-slate-200 text-slate-500'
  };

  const iconStyles = {
    normal: 'text-emerald-500',
    low: 'text-blue-500',
    high: 'text-red-500',
    unknown: 'text-slate-400'
  };

  const displayValue = value != null 
    ? (typeof value === 'number' && !Number.isInteger(value) ? value.toFixed(1) : value)
    : '--';

  return (
    <div className={cn(
      "flex items-center gap-3 p-3 rounded-xl border transition-all",
      statusStyles[status]
    )}>
      <div className={cn("p-2 rounded-lg bg-white/60", iconStyles[status])}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-slate-500 font-medium">{config.label}</p>
        <div className="flex items-baseline gap-1">
          <span className="text-lg font-bold">{displayValue}</span>
          <span className="text-xs text-slate-400">{config.unit}</span>
        </div>
      </div>
      {status !== 'normal' && status !== 'unknown' && (
        <span className={cn(
          "text-xs font-medium px-2 py-0.5 rounded-full",
          status === 'high' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
        )}>
          {status === 'high' ? '↑' : '↓'}
        </span>
      )}
    </div>
  );
}

export default function VitalsPanel({ vitals }) {
  if (!vitals) {
    return (
      <div className="text-center py-8 text-slate-400">
        No vital signs data available
      </div>
    );
  }

  const vitalsList = ['heart_rate', 'respiratory_rate', 'map', 'spo2', 'temperature', 'lactate', 'wbc', 'creatinine'];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {vitalsList.map(key => (
        <VitalItem key={key} vitalKey={key} value={vitals[key]} />
      ))}
    </div>
  );
}