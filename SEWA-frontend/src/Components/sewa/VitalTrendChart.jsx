import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { format } from 'date-fns';

const vitalConfigs = {
  map: {
    label: 'Mean Arterial Pressure',
    unit: 'mmHg',
    color: '#6366f1',
    thresholds: { low: 65, high: 100 },
    domain: [40, 120]
  },
  lactate: {
    label: 'Lactate',
    unit: 'mmol/L',
    color: '#f59e0b',
    thresholds: { high: 2 },
    domain: [0, 6]
  },
  respiratory_rate: {
    label: 'Respiratory Rate',
    unit: '/min',
    color: '#10b981',
    thresholds: { high: 22 },
    domain: [8, 40]
  },
  heart_rate: {
    label: 'Heart Rate',
    unit: 'bpm',
    color: '#ef4444',
    thresholds: { high: 100, low: 60 },
    domain: [40, 160]
  },
  spo2: {
    label: 'Oxygen Saturation',
    unit: '%',
    color: '#3b82f6',
    thresholds: { low: 94 },
    domain: [85, 100]
  },
  temperature: {
    label: 'Temperature',
    unit: '°C',
    color: '#8b5cf6',
    thresholds: { high: 38.3, low: 36 },
    domain: [35, 41]
  }
};

export default function VitalTrendChart({ readings, vitalKey, height = 180 }) {
  const config = vitalConfigs[vitalKey];
  
  if (!config || !readings || readings.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 bg-slate-50 rounded-lg text-slate-400 text-sm">
        No data available
      </div>
    );
  }

  const chartData = readings.map(r => ({
    time: format(new Date(r.timestamp), 'HH:mm'),
    value: r[vitalKey],
    timestamp: r.timestamp
  })).filter(d => d.value != null);

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 bg-slate-50 rounded-lg text-slate-400 text-sm">
        No {config.label} data
      </div>
    );
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white px-3 py-2 rounded-lg shadow-lg border border-slate-200">
          <p className="text-xs text-slate-500">{label}</p>
          <p className="text-sm font-semibold" style={{ color: config.color }}>
            {payload[0].value} {config.unit}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-700">{config.label}</h3>
        <span className="text-xs text-slate-400">{config.unit}</span>
      </div>
      
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis 
            dataKey="time" 
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
          />
          <YAxis 
            domain={config.domain}
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
            width={35}
          />
          <Tooltip content={<CustomTooltip />} />
          
          {/* Threshold reference lines */}
          {config.thresholds.low && (
            <ReferenceLine 
              y={config.thresholds.low} 
              stroke="#ef4444" 
              strokeDasharray="5 5"
              strokeWidth={1}
            />
          )}
          {config.thresholds.high && (
            <ReferenceLine 
              y={config.thresholds.high} 
              stroke="#ef4444" 
              strokeDasharray="5 5"
              strokeWidth={1}
            />
          )}
          
          <Line
            type="monotone"
            dataKey="value"
            stroke={config.color}
            strokeWidth={2}
            dot={{ fill: config.color, r: 3 }}
            activeDot={{ r: 5, fill: config.color }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}