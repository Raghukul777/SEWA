import React from 'react';
import { cn } from "@/lib/utils";
import { Bell, BellOff, Filter } from 'lucide-react';
import { Button } from "@/components/ui/button";
import AlertCard from './AlertCard';

export default function AlertsPanel({
  alerts,
  patients,
  onFeedback,
  onSelect,
  showResolved = false,
  onToggleResolved
}) {
  // Get patient name by ID
  const getPatientName = (patientId) => {
    const patient = patients.find(p => p.patient_id === patientId);
    return patient ? patient.name : patientId;
  };

  // Strictly active = is_active true + doctor hasn't reviewed yet
  const isActiveAlert = (a) => a.is_active === true && a.feedback === 'pending';
  // Resolved = doctor approved/rejected, OR system auto-resolved
  const isResolvedAlert = (a) => !isActiveAlert(a);

  // Filter and sort alerts
  const filteredAlerts = alerts
    .filter(alert => showResolved ? isResolvedAlert(alert) : isActiveAlert(alert))
    .sort((a, b) => {
      const riskOrder = { CRITICAL: 0, HIGH: 1, MODERATE: 2, LOW: 3 };
      const riskDiff = (riskOrder[a.risk_level] || 2) - (riskOrder[b.risk_level] || 2);
      if (riskDiff !== 0) return riskDiff;
      return new Date(b.timestamp) - new Date(a.timestamp);
    });

  const activeCount = alerts.filter(isActiveAlert).length;
  const highRiskCount = alerts.filter(a => isActiveAlert(a) && (a.risk_level === 'HIGH' || a.risk_level === 'CRITICAL')).length;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Bell className="w-5 h-5 text-slate-600" />
            {activeCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center font-bold">
                {activeCount}
              </span>
            )}
          </div>
          <h2 className="font-semibold text-slate-800">Alerts</h2>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleResolved}
          className="text-xs"
        >
          <Filter className="w-3.5 h-3.5 mr-1.5" />
          {showResolved ? 'Active Only' : 'Show All'}
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="flex gap-2 mb-4">
        <div className="flex-1 bg-red-50 rounded-lg px-3 py-2 border border-red-100">
          <p className="text-xs text-red-600 font-medium">High Risk</p>
          <p className="text-xl font-bold text-red-700">{highRiskCount}</p>
        </div>
        <div className="flex-1 bg-amber-50 rounded-lg px-3 py-2 border border-amber-100">
          <p className="text-xs text-amber-600 font-medium">Moderate</p>
          <p className="text-xl font-bold text-amber-700">
            {alerts.filter(a => isActiveAlert(a) && a.risk_level === 'MODERATE').length}
          </p>
        </div>
        <div className="flex-1 bg-slate-50 rounded-lg px-3 py-2 border border-slate-200">
          <p className="text-xs text-slate-500 font-medium">Resolved</p>
          <p className="text-xl font-bold text-slate-700">
            {alerts.filter(isResolvedAlert).length}
          </p>
        </div>
      </div>

      {/* Alerts List */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {filteredAlerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400">
            <BellOff className="w-10 h-10 mb-3 opacity-50" />
            <p className="text-sm">{showResolved ? 'No archived alerts' : 'No active alerts'}</p>
            <p className="text-xs mt-1">{showResolved ? 'No resolved alerts yet' : 'All patients are stable'}</p>
          </div>
        ) : (
          filteredAlerts.map(alert => (
            <div key={alert.id} onClick={() => onSelect && onSelect(alert.patient_id)} className="cursor-pointer hover:bg-slate-50 transition-colors rounded-lg">
              <AlertCard
                alert={alert}
                patientName={getPatientName(alert.patient_id)}
                onFeedback={onFeedback}
              />
            </div>
          ))
        )}
      </div>
    </div>
  );
}