import React, { useState, useEffect, useCallback } from 'react';
import {
    Users, Activity, AlertTriangle, UserCheck, UserX,
    RefreshCw, Building2, Phone, TrendingUp, Shield,
    Clock, CheckCircle, XCircle, Stethoscope, BarChart3,
} from 'lucide-react';
import { adminApi } from '../api/adminApi';
import { Button } from '@/components/ui/button';

// ── Small reusable KPI card ───────────────────────────────────────────
function StatCard({ icon: Icon, label, value, color = 'indigo', sub }) {
    const colors = {
        indigo: 'bg-indigo-50 text-indigo-600 border-indigo-100',
        red: 'bg-red-50   text-red-600   border-red-100',
        amber: 'bg-amber-50 text-amber-600 border-amber-100',
        green: 'bg-green-50 text-green-600 border-green-100',
        slate: 'bg-slate-50 text-slate-600 border-slate-200',
    };
    return (
        <div className={`rounded-xl border p-5 flex items-start gap-4 ${colors[color]}`}>
            <div className="p-2 rounded-lg bg-white/60">
                <Icon className="w-5 h-5" />
            </div>
            <div>
                <p className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</p>
                <p className="text-2xl font-bold mt-0.5">{value ?? '—'}</p>
                {sub && <p className="text-xs mt-0.5 opacity-60">{sub}</p>}
            </div>
        </div>
    );
}

// ── Status badge ──────────────────────────────────────────────────────
function StatusBadge({ status }) {
    const map = {
        Critical: 'bg-red-100   text-red-700',
        Warning: 'bg-amber-100 text-amber-700',
        Stable: 'bg-green-100 text-green-700',
    };
    return (
        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${map[status] ?? 'bg-slate-100 text-slate-600'}`}>
            {status}
        </span>
    );
}

// ── Main Admin Dashboard ──────────────────────────────────────────────
export default function AdminDashboard() {
    const [stats, setStats] = useState(null);
    const [doctors, setDoctors] = useState([]);
    const [patients, setPatients] = useState([]);
    const [tab, setTab] = useState('overview'); // overview | doctors | patients
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [patientSearch, setPatientSearch] = useState('');
    const [patientStatusFilter, setPatientStatusFilter] = useState('all');
    const [error, setError] = useState('');

    const loadAll = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const [s, d, p] = await Promise.all([
                adminApi.getStats(),
                adminApi.getDoctors(),
                adminApi.getAllPatients(),
            ]);
            setStats(s);
            setDoctors(d);
            setPatients(p);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to load admin data. Is the backend running?');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadAll(); }, [loadAll]);

    const handleToggleDoctor = async (doctorId) => {
        try {
            const res = await adminApi.toggleDoctorActive(doctorId);
            setDoctors(prev => prev.map(d =>
                d.id === doctorId ? { ...d, is_active: res.is_active } : d
            ));
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to update doctor status.');
        }
    };

    const handleRefreshAnalytics = async () => {
        setRefreshing(true);
        try {
            await adminApi.refreshStats();
            await loadAll();
            alert('Analytics refreshed successfully!');
        } catch {
            alert('Refresh failed. Materialized view may not be set up in this DB.');
        } finally {
            setRefreshing(false);
        }
    };

    const filteredPatients = patients.filter(p => {
        const matchStatus = patientStatusFilter === 'all' || p.status === patientStatusFilter;
        const matchSearch = !patientSearch || p.name.toLowerCase().includes(patientSearch.toLowerCase());
        return matchStatus && matchSearch;
    });

    if (loading) {
        return (
            <div className="h-[calc(100vh-3.5rem)] flex items-center justify-center bg-slate-50">
                <div className="flex flex-col items-center gap-3">
                    <div className="w-10 h-10 rounded-full border-4 border-indigo-200 border-t-indigo-600 animate-spin" />
                    <p className="text-slate-500 text-sm font-medium">Loading hospital data…</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="h-[calc(100vh-3.5rem)] flex items-center justify-center bg-slate-50">
                <div className="text-center max-w-md px-6">
                    <Shield className="w-16 h-16 text-red-400 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-slate-800 mb-2">Admin Access Error</h2>
                    <p className="text-slate-500 mb-6">{error}</p>
                    <Button onClick={loadAll}>Retry</Button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-[calc(100vh-3.5rem)] bg-slate-50">
            {/* ── Header ── */}
            <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                        <Shield className="w-5 h-5 text-indigo-600" />
                        Admin Control Panel
                    </h1>
                    <p className="text-sm text-slate-500 mt-0.5">Hospital-wide monitoring & management</p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    className="gap-2"
                    onClick={handleRefreshAnalytics}
                    disabled={refreshing}
                >
                    <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                    {refreshing ? 'Refreshing…' : 'Refresh Analytics'}
                </Button>
            </div>

            {/* ── Tab Bar ── */}
            <div className="bg-white border-b border-slate-200 px-6">
                <div className="flex gap-1">
                    {[
                        { id: 'overview', label: 'Overview', icon: BarChart3 },
                        { id: 'doctors', label: 'Doctor Directory', icon: Stethoscope },
                        { id: 'patients', label: 'All Patients', icon: Users },
                    ].map(({ id, label, icon: Icon }) => (
                        <button
                            key={id}
                            onClick={() => setTab(id)}
                            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${tab === id
                                    ? 'border-indigo-600 text-indigo-700'
                                    : 'border-transparent text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            <Icon className="w-4 h-4" />
                            {label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="p-6 max-w-[1800px] mx-auto">

                {/* ════════════════ OVERVIEW TAB ════════════════ */}
                {tab === 'overview' && stats && (
                    <div className="space-y-6">
                        {/* KPI Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <StatCard icon={Users} label="Active Patients" value={stats.active_patients} color="indigo" />
                            <StatCard icon={AlertTriangle} label="Critical Patients" value={stats.critical_patients} color="red" sub={`${stats.warning_patients} Warning`} />
                            <StatCard icon={Stethoscope} label="Doctors" value={stats.total_doctors} color="green" />
                            <StatCard icon={Activity} label="Pending Alerts" value={stats.pending_alerts} color="amber" sub={`${stats.high_alerts} High-risk`} />
                        </div>

                        {/* Secondary Stats */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <StatCard icon={TrendingUp} label="Total Patients (ever)" value={stats.total_patients} color="slate" />
                            <StatCard icon={AlertTriangle} label="High-Risk Alerts" value={stats.high_alerts} color="red" />
                            <StatCard icon={CheckCircle} label="Moderate Alerts" value={stats.moderate_alerts} color="amber" />
                            <StatCard icon={XCircle} label="False Positives" value={stats.false_positives} color="slate" />
                        </div>

                        {/* Patient status breakdown bar */}
                        <div className="bg-white rounded-xl border border-slate-200 p-5">
                            <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
                                <BarChart3 className="w-4 h-4 text-indigo-500" />
                                Active Patient Status Breakdown
                            </h3>
                            {stats.active_patients > 0 ? (
                                <div className="space-y-3">
                                    {[
                                        { label: 'Critical', count: stats.critical_patients, color: 'bg-red-500' },
                                        { label: 'Warning', count: stats.warning_patients, color: 'bg-amber-400' },
                                        {
                                            label: 'Stable',
                                            count: stats.active_patients - stats.critical_patients - stats.warning_patients,
                                            color: 'bg-green-500',
                                        },
                                    ].map(({ label, count, color }) => (
                                        <div key={label} className="flex items-center gap-3">
                                            <span className="w-20 text-sm text-slate-600 font-medium">{label}</span>
                                            <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full rounded-full transition-all ${color}`}
                                                    style={{ width: `${Math.round((count / stats.active_patients) * 100)}%` }}
                                                />
                                            </div>
                                            <span className="w-8 text-sm font-semibold text-slate-700 text-right">{count}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-slate-400 text-sm">No active patients.</p>
                            )}
                        </div>
                    </div>
                )}

                {/* ════════════════ DOCTORS TAB ════════════════ */}
                {tab === 'doctors' && (
                    <div className="space-y-3">
                        <p className="text-sm text-slate-500">{doctors.length} doctor{doctors.length !== 1 ? 's' : ''} registered</p>
                        {doctors.length === 0 ? (
                            <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-slate-400">
                                No doctors found.
                            </div>
                        ) : (
                            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
                                {doctors.map(doc => (
                                    <div key={doc.id} className="bg-white rounded-xl border border-slate-200 p-5 flex flex-col gap-4">
                                        {/* Header */}
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex items-center gap-3">
                                                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white
                                                    ${doc.is_active ? 'bg-indigo-600' : 'bg-slate-400'}`}>
                                                    {doc.name.charAt(0)}
                                                </div>
                                                <div>
                                                    <p className="font-semibold text-slate-800">{doc.name}</p>
                                                    <p className="text-xs text-slate-400">{doc.id}</p>
                                                </div>
                                            </div>
                                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${doc.is_active
                                                    ? 'bg-green-100 text-green-700'
                                                    : 'bg-slate-100 text-slate-500'
                                                }`}>
                                                {doc.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </div>

                                        {/* Info */}
                                        <div className="space-y-1.5 text-sm text-slate-600">
                                            <div className="flex items-center gap-2">
                                                <Building2 className="w-3.5 h-3.5 text-slate-400" />
                                                <span>{doc.hospital_name || '—'}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Stethoscope className="w-3.5 h-3.5 text-slate-400" />
                                                <span>{doc.department || '—'}</span>
                                            </div>
                                            {doc.phone && (
                                                <div className="flex items-center gap-2">
                                                    <Phone className="w-3.5 h-3.5 text-slate-400" />
                                                    <span>{doc.phone}</span>
                                                </div>
                                            )}
                                            {doc.last_login_at && (
                                                <div className="flex items-center gap-2">
                                                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                                                    <span>Last login: {new Date(doc.last_login_at).toLocaleDateString()}</span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Patient mini-stats */}
                                        <div className="grid grid-cols-3 gap-2 border-t border-slate-100 pt-3">
                                            {[
                                                { label: 'Active', value: doc.active_patients, color: 'text-indigo-600' },
                                                { label: 'Critical', value: doc.critical_patients, color: 'text-red-600' },
                                                { label: 'Total', value: doc.total_patients, color: 'text-slate-700' },
                                            ].map(({ label, value, color }) => (
                                                <div key={label} className="text-center">
                                                    <p className={`text-lg font-bold ${color}`}>{value}</p>
                                                    <p className="text-xs text-slate-400">{label}</p>
                                                </div>
                                            ))}
                                        </div>

                                        {/* Action */}
                                        <Button
                                            size="sm"
                                            variant={doc.is_active ? 'outline' : 'default'}
                                            className={`w-full gap-2 text-xs ${doc.is_active
                                                    ? 'border-red-200 text-red-600 hover:bg-red-50'
                                                    : 'bg-green-600 hover:bg-green-700 text-white'
                                                }`}
                                            onClick={() => handleToggleDoctor(doc.id)}
                                        >
                                            {doc.is_active
                                                ? <><UserX className="w-3.5 h-3.5" /> Deactivate</>
                                                : <><UserCheck className="w-3.5 h-3.5" /> Reactivate</>
                                            }
                                        </Button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* ════════════════ PATIENTS TAB ════════════════ */}
                {tab === 'patients' && (
                    <div className="space-y-4">
                        {/* Filters */}
                        <div className="flex flex-wrap gap-3 items-center">
                            <input
                                className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-56 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                                placeholder="Search patient name…"
                                value={patientSearch}
                                onChange={e => setPatientSearch(e.target.value)}
                            />
                            <div className="flex gap-1">
                                {['all', 'Stable', 'Warning', 'Critical'].map(s => (
                                    <button
                                        key={s}
                                        onClick={() => setPatientStatusFilter(s)}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${patientStatusFilter === s
                                                ? s === 'Critical' ? 'bg-red-600 text-white'
                                                    : s === 'Warning' ? 'bg-amber-500 text-white'
                                                        : s === 'Stable' ? 'bg-green-600 text-white'
                                                            : 'bg-indigo-600 text-white'
                                                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                                            }`}
                                    >
                                        {s === 'all' ? 'All' : s}
                                    </button>
                                ))}
                            </div>
                            <span className="text-sm text-slate-400">{filteredPatients.length} patient{filteredPatients.length !== 1 ? 's' : ''}</span>
                        </div>

                        {/* Table */}
                        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                            <table className="w-full text-sm">
                                <thead className="bg-slate-50 border-b border-slate-200">
                                    <tr>
                                        {['Patient', 'Age / Gender', 'Bed', 'Status', 'Doctor', 'Dept', 'Admitted'].map(h => (
                                            <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {filteredPatients.length === 0 ? (
                                        <tr>
                                            <td colSpan={7} className="px-4 py-10 text-center text-slate-400">
                                                No patients found.
                                            </td>
                                        </tr>
                                    ) : filteredPatients.map(p => (
                                        <tr key={p.patient_id} className="hover:bg-slate-50 transition-colors">
                                            <td className="px-4 py-3 font-medium text-slate-800">
                                                <div>{p.name}</div>
                                                <div className="text-xs text-slate-400">{p.patient_id}</div>
                                            </td>
                                            <td className="px-4 py-3 text-slate-600">{p.age} / {p.gender}</td>
                                            <td className="px-4 py-3 font-mono text-slate-600">{p.bed_number}</td>
                                            <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                                            <td className="px-4 py-3 text-slate-700">{p.doctor_name}</td>
                                            <td className="px-4 py-3 text-slate-500 text-xs">{p.doctor_department || '—'}</td>
                                            <td className="px-4 py-3 text-slate-400 text-xs">
                                                {p.admission_date ? new Date(p.admission_date).toLocaleDateString() : '—'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
