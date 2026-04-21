import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { analyzePatientRisk } from '../Components/sewa/SepsisEngine';
import PatientCard from '../Components/sewa/PatientCard';
import PatientDetailView from '../Components/sewa/PatientDetailView';
import AlertsPanel from '../Components/sewa/AlertsPanel';
import AdmissionModal from '../Components/sewa/PatientManagement/AdmissionModal';
import DischargeModal from '../Components/sewa/PatientManagement/DischargeModal';
import { useVitalsStream } from '../hooks/useVitalsStream';
import { Users, UserPlus, Stethoscope, Search, Bell, History, Wifi, WifiOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

import { patientsApi } from '../api/patientsApi';
import { alertsApi } from '../api/alertsApi';

// ── Status colour helper ────────────────────────────────────────────────────
function statusFromRisk(riskLevel) {
    if (riskLevel === 'HIGH') return 'Critical';
    if (riskLevel === 'MODERATE') return 'Warning';
    return 'Stable';
}

export default function Dashboard() {
    const [patients, setPatients] = useState([]);
    const [readings, setReadings] = useState({});
    const [alerts, setAlerts] = useState([]);
    const [selectedPatientId, setSelectedPatientId] = useState(null);
    const [isAdmissionOpen, setIsAdmissionOpen] = useState(false);
    const [isDischargeOpen, setIsDischargeOpen] = useState(false);
    const [patientToDischarge, setPatientToDischarge] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [showResolvedAlerts, setShowResolvedAlerts] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [streamConnected, setStreamConnected] = useState(false);
    const resolvedLoadedRef = React.useRef(false);

    // ── Bootstrap: load patients + existing alerts from REST API ──────────
    useEffect(() => {
        const bootstrap = async () => {
            setIsLoading(true);
            try {
                const apiPatients = await patientsApi.getPatients();
                if (apiPatients && apiPatients.length > 0) {
                    setPatients(apiPatients);
                    setSelectedPatientId(apiPatients[0]?.patient_id || null);
                }
                const apiAlerts = await alertsApi.getAlerts({ activeOnly: true });
                if (apiAlerts.length > 0) setAlerts(apiAlerts);
            } catch (err) {
                console.error('[Dashboard] Bootstrap error:', err.message);
                setPatients([]);
            } finally {
                setIsLoading(false);
            }
        };
        bootstrap();
    }, []);

    // ── WebSocket callbacks ───────────────────────────────────────────────
    const handleVital = useCallback((reading) => {
        const { patient_id } = reading;

        setReadings(prev => {
            const existing = prev[patient_id] || [];
            const updated = [...existing, reading].slice(-50);

            // Defer patient status update to avoid nested state updates which can trigger
            // infinite loops or stale renders in React 18+ Concurrent mode
            setTimeout(() => {
                setPatients(prevPatients => prevPatients.map(p => {
                    if (p.patient_id !== patient_id) return p;
                    const risk = analyzePatientRisk(updated, p);
                    const newStatus = statusFromRisk(risk.riskLevel);
                    return p.status !== newStatus ? { ...p, status: newStatus } : p;
                }));
            }, 0);

            return { ...prev, [patient_id]: updated };
        });
    }, []);

    const handleAlert = useCallback((alert) => {
        setAlerts(prev => {
            const exists = prev.find(a => a.id === alert.id);
            return exists ? prev : [alert, ...prev];
        });
    }, []);

    const handleStatus = useCallback((status) => {
        if (status?.connected) {
            setStreamConnected(true);
        } else {
            setStreamConnected(false);
        }
    }, []);

    // Patient IDs to subscribe to
    const patientIds = patients.map(p => p.patient_id);

    // ── WebSocket connection (backend streams vitals + alerts) ─────────
    useVitalsStream({
        patientIds,
        onVital: handleVital,
        onAlert: handleAlert,
        onStatus: handleStatus,
        enabled: !isLoading && patientIds.length > 0,
    });

    // ── Derived ───────────────────────────────────────────────────────────
    const selectedPatient = patients.find(p => p.patient_id === selectedPatientId);
    const selectedPatientReadings = selectedPatientId ? readings[selectedPatientId] || [] : [];
    const selectedPatientRisk = selectedPatient
        ? analyzePatientRisk(selectedPatientReadings, selectedPatient)
        : null;
    const filteredPatients = patients.filter(p =>
        p.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // ── Loading ───────────────────────────────────────────────────────────
    if (isLoading) {
        return (
            <div className="h-screen flex items-center justify-center bg-slate-50">
                <div className="text-center">
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                        className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"
                    />
                    <p className="text-slate-500 font-bold text-xs uppercase tracking-widest animate-pulse">
                        Synchronizing Clinical Data...
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-[calc(100vh-4rem)] bg-slate-50 flex overflow-hidden font-sans selection:bg-blue-100">

            {/* ── LEFT SIDEBAR: PATIENT REGISTRY ── */}
            <aside className="w-85 bg-white border-r border-slate-200 flex flex-col shadow-sm z-20">
                <div className="p-6 border-b border-slate-100 bg-white sticky top-0 z-10">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <Users className="w-5 h-5 text-blue-600" />
                            <h2 className="font-black text-slate-900 uppercase tracking-tight text-sm">
                                Patient Registry
                            </h2>
                        </div>
                        <div className="flex items-center gap-2">
                            {/* Stream status indicator */}
                            <div
                                title={streamConnected ? 'Live stream active' : 'Waiting for stream'}
                                className={`flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${streamConnected
                                    ? 'bg-emerald-50 text-emerald-600'
                                    : 'bg-slate-100 text-slate-400'
                                    }`}
                            >
                                {streamConnected
                                    ? <><Wifi className="w-3 h-3" /> Live</>
                                    : <><WifiOff className="w-3 h-3" /> Offline</>
                                }
                            </div>
                            <Badge className="bg-blue-50 text-blue-700 border-none font-bold">
                                {patients.length}
                            </Badge>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                            <Input
                                placeholder="Search census..."
                                className="pl-9 h-10 bg-slate-50 border-none text-xs rounded-xl focus:ring-2 focus:ring-blue-500/20"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                        <Button
                            onClick={() => setIsAdmissionOpen(true)}
                            className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-xl h-10 font-bold text-xs transition-all active:scale-95 shadow-lg shadow-blue-100"
                        >
                            <UserPlus className="w-3.5 h-3.5 mr-2" /> Admit Patient
                        </Button>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-3 no-scrollbar">
                    <AnimatePresence mode="popLayout">
                        {filteredPatients.map((patient, idx) => (
                            <motion.div
                                key={patient.patient_id}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                transition={{ delay: idx * 0.04 }}
                            >
                                <PatientCard
                                    patient={patient}
                                    latestVitals={
                                        readings[patient.patient_id]?.[
                                        readings[patient.patient_id].length - 1
                                        ]
                                    }
                                    isSelected={patient.patient_id === selectedPatientId}
                                    onClick={() => setSelectedPatientId(patient.patient_id)}
                                />
                                {/* Live pulse indicator under selected patient */}
                                {streamConnected && patient.patient_id === selectedPatientId && (
                                    <motion.div
                                        className="h-0.5 bg-blue-500 mt-1 rounded-full mx-4"
                                        animate={{ opacity: [0.2, 1, 0.2] }}
                                        transition={{ duration: 1.5, repeat: Infinity }}
                                    />
                                )}
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            </aside>

            {/* ── CENTER: CLINICAL COMMAND CENTER ── */}
            <main className="flex-1 overflow-y-auto relative no-scrollbar">
                <div className="max-w-6xl mx-auto p-8">
                    {selectedPatient ? (
                        <motion.div
                            key={selectedPatient.patient_id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.4 }}
                        >
                            <PatientDetailView
                                patient={selectedPatient}
                                readings={selectedPatientReadings}
                                riskAssessment={selectedPatientRisk}
                                notes={selectedPatient.clinical_notes}
                                treatmentStatus={selectedPatient.treatment_bundle}
                                onAddNote={async (note) => {
                                    setPatients(prev => prev.map(p =>
                                        p.patient_id === selectedPatientId
                                            ? { ...p, clinical_notes: [note, ...(p.clinical_notes || [])] }
                                            : p
                                    ));
                                    try { await patientsApi.addNote(selectedPatientId, note); } catch { }
                                }}
                                onUpdateTreatment={async (key, val) => {
                                    setPatients(prev => prev.map(p =>
                                        p.patient_id === selectedPatientId
                                            ? { ...p, treatment_bundle: { ...p.treatment_bundle, [key]: val } }
                                            : p
                                    ));
                                    try { await patientsApi.updateTreatment(selectedPatientId, key, val); } catch { }
                                }}
                                onDischarge={(id) => {
                                    setPatientToDischarge(id);
                                    setIsDischargeOpen(true);
                                }}
                            />
                        </motion.div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-center py-24">
                            <div className="w-20 h-20 bg-blue-50 rounded-3xl flex items-center justify-center mb-6">
                                <Stethoscope className="w-10 h-10 text-blue-600" />
                            </div>
                            <h2 className="text-2xl font-black text-slate-900 mb-2">No Selection</h2>
                            <p className="text-slate-500 max-w-sm">
                                Select a patient from the registry to view real-time diagnostics
                                and sepsis risk stratification.
                            </p>
                        </div>
                    )}
                </div>
            </main>

            {/* ── RIGHT SIDEBAR: LIVE ALERTS ── */}
            <aside className="w-96 bg-white border-l border-slate-200 flex flex-col shadow-sm">
                <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Bell className="w-5 h-5 text-violet-600" />
                        <h2 className="font-black text-slate-900 uppercase tracking-tight text-sm">
                            Live Alerts
                        </h2>
                        {alerts.filter(a => a.is_active).length > 0 && (
                            <span className="flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-red-400 opacity-75" />
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
                            </span>
                        )}
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        className={`text-[10px] font-black uppercase tracking-widest ${showResolvedAlerts ? 'text-violet-600' : 'text-slate-400'}`}
                        onClick={async () => {
                            const next = !showResolvedAlerts;
                            setShowResolvedAlerts(next);
                            // Lazy-load resolved alerts the first time archive is opened
                            if (next && !resolvedLoadedRef.current) {
                                resolvedLoadedRef.current = true;
                                try {
                                    const all = await alertsApi.getAlerts({ activeOnly: false });
                                    setAlerts(all);
                                } catch { }
                            }
                        }}
                    >
                        <History className="w-3 h-3 mr-1" /> Archive
                    </Button>
                </div>

                <div className="flex-1 overflow-hidden p-2">
                    <AlertsPanel
                        alerts={alerts}
                        patients={patients}
                        onFeedback={async (id, feedback) => {
                            setAlerts(prev => prev.map(a => a.id === id ? {
                                ...a,
                                feedback,
                                // Immediately deactivate locally so it leaves the active panel
                                is_active: feedback === 'approved' || feedback === 'false_positive' ? false : a.is_active
                            } : a));
                            try { await alertsApi.submitFeedback(id, feedback); } catch { }
                        }}
                        onSelect={setSelectedPatientId}
                        showResolved={showResolvedAlerts}
                        onToggleResolved={() => setShowResolvedAlerts(!showResolvedAlerts)}
                    />
                </div>
            </aside>

            {/* ── MODALS ── */}
            <AdmissionModal
                isOpen={isAdmissionOpen}
                onClose={() => setIsAdmissionOpen(false)}
                onAdmit={async (newP) => {
                    try {
                        const admitted = await patientsApi.admitPatient(newP);
                        setPatients(prev => [admitted, ...prev]);
                        setSelectedPatientId(admitted.patient_id);
                        setIsAdmissionOpen(false);
                        // Backend will start streaming vitals for this patient automatically
                        // once useVitalsStream sees the new patient_id in the list
                    } catch {
                        alert('Admission failed. Please check your connection and try again.');
                    }
                }}
            />

            <DischargeModal
                isOpen={isDischargeOpen}
                onClose={() => setIsDischargeOpen(false)}
                onDischarge={async () => {
                    try { await patientsApi.dischargePatient(patientToDischarge); } catch { }
                    const next = patients.filter(p => p.patient_id !== patientToDischarge);
                    setPatients(next);
                    setReadings(prev => {
                        const copy = { ...prev };
                        delete copy[patientToDischarge];
                        return copy;
                    });
                    setSelectedPatientId(next.length > 0 ? next[0].patient_id : null);
                    setIsDischargeOpen(false);
                    setPatientToDischarge(null);
                }}
                patientName={patients.find(p => p.patient_id === patientToDischarge)?.name}
            />
        </div>
    );
}