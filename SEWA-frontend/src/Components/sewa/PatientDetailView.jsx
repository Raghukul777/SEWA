import React, { useState } from 'react';
import { cn } from "@/lib/utils";
import { User, Bed, FileText, Activity, AlertCircle, LogOut, Stethoscope, ClipboardList, Phone, Droplets, MapPin, Users } from 'lucide-react';
import { format } from 'date-fns';
import { Button } from "@/components/ui/button";
import VitalsPanel from './VitalsPanel';
import VitalTrendChart from './VitalTrendChart';
import ClinicalNotes from './PatientManagement/ClinicalNotes';
import TreatmentPathway from './PatientManagement/TreatmentPathway';

export default function PatientDetailView({
  patient,
  readings,
  riskAssessment,
  onDischarge,
  notes,
  onAddNote,
  treatmentStatus,
  onUpdateTreatment
}) {
  const [activeTab, setActiveTab] = useState('overview');

  if (!patient) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-slate-400">
        <User className="w-12 h-12 mb-3 opacity-50" />
        <p className="text-lg">Select a patient to view details</p>
      </div>
    );
  }

  const latestVitals = readings && readings.length > 0
    ? readings[readings.length - 1]
    : null;

  const statusColors = {
    Stable: 'bg-emerald-100 text-emerald-700 border-emerald-300',
    Warning: 'bg-amber-100 text-amber-700 border-amber-300',
    Critical: 'bg-red-100 text-red-700 border-red-300'
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'treatment', label: 'Treatment Plan', icon: Stethoscope },
    { id: 'notes', label: 'Clinical Notes', icon: ClipboardList },
  ];

  return (
    <div className="space-y-6">
      {/* Patient Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center flex-shrink-0">
              <User className="w-7 h-7 text-slate-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-800">{patient.name}</h2>
              <div className="flex flex-wrap items-center gap-3 mt-1 text-sm text-slate-500">
                <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">{patient.patient_id}</span>
                <span>•</span>
                <span>{patient.age} y/o {patient.gender}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Bed className="w-4 h-4" />
                  Bed {patient.bed_number || 'N/A'}
                </span>
                {patient.admission_date && (
                  <>
                    <span>•</span>
                    <span className="text-slate-400">
                      Admitted {format(new Date(patient.admission_date), 'MMM d')} (Day {Math.ceil((new Date() - new Date(patient.admission_date)) / (1000 * 60 * 60 * 24))})
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 self-end lg:self-center">
            <div className={cn(
              "px-4 py-2 rounded-full border font-medium",
              statusColors[patient.status] || statusColors.Stable
            )}>
              {patient.status || 'Stable'}
            </div>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => onDischarge(patient.patient_id)}
              className="hidden lg:flex"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Discharge
            </Button>
          </div>
        </div>

        {/* Custom Tab Navigation */}
        <div className="mt-8 flex border-b border-slate-200">
          {tabs.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-all",
                  isActive
                    ? "border-slate-800 text-slate-800"
                    : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
                )}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* Risk Assessment */}
          {riskAssessment && riskAssessment.criteria.length > 0 && (
            <div className={cn(
              "rounded-2xl border p-5",
              riskAssessment.riskLevel === 'HIGH'
                ? 'bg-red-50 border-red-200'
                : riskAssessment.riskLevel === 'MODERATE'
                  ? 'bg-amber-50 border-amber-200'
                  : 'bg-slate-50 border-slate-200'
            )}>
              <div className="flex items-center gap-2 mb-3">
                <AlertCircle className={cn(
                  "w-5 h-5",
                  riskAssessment.riskLevel === 'HIGH'
                    ? 'text-red-600'
                    : riskAssessment.riskLevel === 'MODERATE'
                      ? 'text-amber-600'
                      : 'text-slate-600'
                )} />
                <h3 className="font-semibold text-slate-800">
                  Risk Assessment: {riskAssessment.riskLevel}
                </h3>
              </div>
              <p className="text-sm text-slate-600 mb-3">{riskAssessment.summary}</p>

              {riskAssessment.criteria.map((criterion, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm text-slate-700 ml-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-2 flex-shrink-0" />
                  {criterion}
                </div>
              ))}
            </div>
          )}

          {/* Medical History & Admission Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4" /> Admission Reason
              </h3>
              <p className="text-slate-700">{patient.admission_reason || 'Not specified'}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                <ClipboardList className="w-4 h-4" /> Medical History
              </h3>
              <div className="flex flex-wrap gap-2">
                {patient.medical_history && patient.medical_history.length > 0 ? (
                  patient.medical_history.map((h, i) => (
                    <span key={i} className="px-2.5 py-1 bg-slate-100 text-slate-600 rounded-md text-sm">
                      {h}
                    </span>
                  ))
                ) : (
                  <span className="text-slate-400 text-sm">No history recorded</span>
                )}
              </div>
            </div>
          </div>

          {/* Extended Patient Details */}
          {(patient.blood_group || patient.phone || patient.emergency_contact_name || patient.address) && (
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                <Users className="w-4 h-4" /> Patient Details
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                {patient.blood_group && (
                  <div className="flex items-start gap-2">
                    <Droplets className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-slate-400 font-medium">Blood Group</p>
                      <p className="text-slate-700 font-semibold">{patient.blood_group}</p>
                    </div>
                  </div>
                )}
                {patient.phone && (
                  <div className="flex items-start gap-2">
                    <Phone className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-slate-400 font-medium">Phone</p>
                      <p className="text-slate-700">{patient.phone}</p>
                    </div>
                  </div>
                )}
                {patient.emergency_contact_name && (
                  <div className="flex items-start gap-2">
                    <User className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-slate-400 font-medium">Emergency Contact</p>
                      <p className="text-slate-700">{patient.emergency_contact_name}</p>
                      {patient.emergency_contact_phone && (
                        <p className="text-slate-500 text-xs">{patient.emergency_contact_phone}</p>
                      )}
                    </div>
                  </div>
                )}
                {patient.address && (
                  <div className="flex items-start gap-2">
                    <MapPin className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-slate-400 font-medium">Address</p>
                      <p className="text-slate-700 line-clamp-2">{patient.address}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Vitals */}
          <div>
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
              Current Vital Signs
            </h3>
            <VitalsPanel vitals={latestVitals} />
          </div>

          {/* Charts */}
          <div>
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
              Vital Trends
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <VitalTrendChart readings={readings} vitalKey="map" />
              <VitalTrendChart readings={readings} vitalKey="lactate" />
              <VitalTrendChart readings={readings} vitalKey="respiratory_rate" />
              <VitalTrendChart readings={readings} vitalKey="heart_rate" />
              <VitalTrendChart readings={readings} vitalKey="wbc" />
              <VitalTrendChart readings={readings} vitalKey="creatinine" />
            </div>
          </div>

          {/* Recent History Table */}
          {readings && readings.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
                Recent Readings History
              </h3>
              <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200">
                        <th className="px-4 py-3 text-left font-medium text-slate-600">Time</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-600">HR</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-600">RR</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-600">MAP</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-600">SpO₂</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-600">Temp</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-600">Lactate</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-600">WBC</th>
                        <th className="px-4 py-3 text-right font-medium text-slate-600">Cr</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...readings].reverse().slice(0, 10).map((reading, idx) => {
                        const formatVal = (val) => {
                          if (val == null) return '--';
                          const num = Number(val);
                          return isNaN(num) ? val : parseFloat(num.toFixed(3));
                        };
                        return (
                          <tr key={idx} className="border-b border-slate-100 last:border-0">
                            <td className="px-4 py-2.5 text-slate-600">
                              {format(new Date(reading.timestamp), 'HH:mm:ss')}
                            </td>
                            <td className="px-4 py-2.5 text-right font-mono">
                              {formatVal(reading.heart_rate)}
                            </td>
                            <td className="px-4 py-2.5 text-right font-mono">
                              {formatVal(reading.respiratory_rate)}
                            </td>
                            <td className="px-4 py-2.5 text-right font-mono">
                              {formatVal(reading.map)}
                            </td>
                            <td className="px-4 py-2.5 text-right font-mono">
                              {formatVal(reading.spo2)}%
                            </td>
                            <td className="px-4 py-2.5 text-right font-mono">
                              {formatVal(reading.temperature)}°
                            </td>
                            <td className="px-4 py-2.5 text-right font-mono">
                              {formatVal(reading.lactate)}
                            </td>
                            <td className="px-4 py-2.5 text-right font-mono">
                              {formatVal(reading.wbc)}
                            </td>
                            <td className="px-4 py-2.5 text-right font-mono">
                              {formatVal(reading.creatinine)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'treatment' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in duration-300">
          <div className="space-y-6">
            <TreatmentPathway
              status={treatmentStatus}
              onUpdateStatus={onUpdateTreatment}
              riskLevel={riskAssessment ? riskAssessment.riskLevel : 'LOW'}
            />
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 h-fit">
            <h3 className="font-semibold text-slate-800 mb-2">Hospital Protocols</h3>
            <div className="space-y-4 text-sm text-slate-600">
              <p>
                <strong>Sepsis Alert:</strong> Initiate Hour-1 bundle immediately upon trigger of High Risk warning.
              </p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Target MAP ≥ 65 mmHg</li>
                <li>Normalize Lactate levels</li>
                <li>Obtain cultures before antibiotics</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'notes' && (
        <div className="animate-in fade-in duration-300">
          <ClinicalNotes
            notes={notes}
            onAddNote={onAddNote}
          />
        </div>
      )}
    </div>
  );
} 