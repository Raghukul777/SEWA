import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { cn } from "@/lib/utils";
import { auditApi } from '../api/auditApi';
import { patientsApi } from '../api/patientsApi';
import {
  FileText,
  Filter,
  Download,
  Search,
  Calendar,
  RefreshCw,
  UserCircle
} from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { format, subDays } from 'date-fns';
import AuditLogTable from '../Components/audit/AuditLogTable';



const EVENT_TYPES = [
  { value: 'all', label: 'All Events' },
  { value: 'vital_reading_generated', label: 'Vital Readings' },
  { value: 'alert_generated', label: 'Alerts Generated' },
  { value: 'alert_feedback_submitted', label: 'Alert Feedback' },
  { value: 'risk_level_changed', label: 'Risk Changes' },
  { value: 'patient_status_changed', label: 'Status Changes' },
  { value: 'simulation_paused', label: 'Simulation Paused' },
  { value: 'simulation_resumed', label: 'Simulation Resumed' }
];

const SEVERITY_LEVELS = [
  { value: 'all', label: 'All Severities' },
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'critical', label: 'Critical' }
];

const TIME_RANGES = [
  { value: 'today', label: 'Today', days: 0 },
  { value: 'last24h', label: 'Last 24 Hours', days: 1 },
  { value: 'last7d', label: 'Last 7 Days', days: 7 },
  { value: 'last30d', label: 'Last 30 Days', days: 30 },
  { value: 'all', label: 'All Time', days: null }
];

export default function AuditLog() {
  const [eventTypeFilter, setEventTypeFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [timeRangeFilter, setTimeRangeFilter] = useState('last24h');
  const [searchQuery, setSearchQuery] = useState('');
  const [patientFilter, setPatientFilter] = useState('all');

  // Fetch the doctor's patient list for the dropdown
  const { data: patients = [] } = useQuery({
    queryKey: ['patients'],
    queryFn: patientsApi.getPatients,
  });

  // Fetch audit logs from real API with filters
  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['auditLogs', eventTypeFilter, severityFilter, timeRangeFilter, patientFilter],
    queryFn: async () => {
      const timeRange = TIME_RANGES.find(t => t.value === timeRangeFilter);
      return auditApi.getAuditLogs({
        eventType: eventTypeFilter,
        severity: severityFilter,
        sinceDays: timeRange?.days ?? undefined,
        patientId: patientFilter !== 'all' ? patientFilter : undefined,
      });
    },
    refetchInterval: 15000, // Refresh every 15 seconds
    initialData: []
  });

  // Apply search filter
  const filteredLogs = logs.filter(log => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      log.event_description?.toLowerCase().includes(query) ||
      log.patient_name?.toLowerCase().includes(query) ||
      log.patient_id?.toLowerCase().includes(query) ||
      log.user_email?.toLowerCase().includes(query)
    );
  });

  // Export to CSV
  const handleExport = () => {
    const headers = ['Timestamp', 'Event Type', 'Severity', 'Patient ID', 'Patient Name', 'User', 'Description'];
    const rows = filteredLogs.map(log => [
      format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm:ss'),
      log.event_type,
      log.severity,
      log.patient_id || '',
      log.patient_name || '',
      log.user_email || '',
      log.event_description
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sewa-audit-log-${format(new Date(), 'yyyy-MM-dd-HHmmss')}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Statistics
  const stats = {
    total: filteredLogs.length,
    critical: filteredLogs.filter(l => l.severity === 'critical').length,
    alerts: filteredLogs.filter(l => l.event_type === 'alert_generated').length,
    feedback: filteredLogs.filter(l => l.event_type === 'alert_feedback_submitted').length
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-7xl mx-auto px-4 lg:px-6 py-6">

        {/* Header */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-indigo-100 flex items-center justify-center">
                <FileText className="w-6 h-6 text-indigo-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-800">Audit Log</h1>
                <p className="text-sm text-slate-500">
                  Comprehensive trail of all system events and clinical actions
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
                className="gap-1.5"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
                disabled={filteredLogs.length === 0}
                className="gap-1.5"
              >
                <Download className="w-4 h-4" />
                Export CSV
              </Button>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-6">
            <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
              <p className="text-xs text-slate-500 font-medium">Total Events</p>
              <p className="text-2xl font-bold text-slate-800">{stats.total}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-3 border border-red-200">
              <p className="text-xs text-red-600 font-medium">Critical Events</p>
              <p className="text-2xl font-bold text-red-700">{stats.critical}</p>
            </div>
            <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
              <p className="text-xs text-amber-600 font-medium">Alerts Generated</p>
              <p className="text-2xl font-bold text-amber-700">{stats.alerts}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-3 border border-green-200">
              <p className="text-xs text-green-600 font-medium">Feedback Submitted</p>
              <p className="text-2xl font-bold text-green-700">{stats.feedback}</p>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="w-4 h-4 text-slate-500" />
            <span className="text-sm font-medium text-slate-700">Filters</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Search */}
            <div className="lg:col-span-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search events, patients, users..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>

            {/* Patient Filter */}
            <Select value={patientFilter} onValueChange={setPatientFilter}>
              <SelectTrigger className="gap-2">
                <UserCircle className="w-4 h-4 text-slate-400 flex-shrink-0" />
                <SelectValue placeholder="All Patients" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Patients</SelectItem>
                {patients.map(p => (
                  <SelectItem key={p.patient_id} value={String(p.patient_id)}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Event Type */}
            <Select value={eventTypeFilter} onValueChange={setEventTypeFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Event Type" />
              </SelectTrigger>
              <SelectContent>
                {EVENT_TYPES.map(type => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Severity – full width row */}
          <div className="mt-3">
            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger className="w-full md:w-48">
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                {SEVERITY_LEVELS.map(level => (
                  <SelectItem key={level.value} value={level.value}>
                    {level.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Time Range */}
          <div className="flex items-center gap-2 mt-3">
            <Calendar className="w-4 h-4 text-slate-400" />
            <div className="flex gap-2">
              {TIME_RANGES.map(range => (
                <Button
                  key={range.value}
                  variant={timeRangeFilter === range.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setTimeRangeFilter(range.value)}
                  className={cn(
                    "text-xs",
                    timeRangeFilter === range.value && "bg-indigo-600"
                  )}
                >
                  {range.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Active Filters Summary */}
          {(eventTypeFilter !== 'all' || severityFilter !== 'all' || searchQuery || patientFilter !== 'all') && (
            <div className="mt-3 pt-3 border-t border-slate-200 flex flex-wrap items-center gap-2 text-xs text-slate-600">
              <span className="font-medium">Active filters:</span>
              {patientFilter !== 'all' && (
                <span className="px-2 py-0.5 bg-violet-100 text-violet-700 rounded flex items-center gap-1">
                  <UserCircle className="w-3 h-3" />
                  {patients.find(p => String(p.patient_id) === patientFilter)?.name ?? patientFilter}
                </span>
              )}
              {eventTypeFilter !== 'all' && (
                <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded">
                  {EVENT_TYPES.find(t => t.value === eventTypeFilter)?.label}
                </span>
              )}
              {severityFilter !== 'all' && (
                <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded">
                  {SEVERITY_LEVELS.find(s => s.value === severityFilter)?.label}
                </span>
              )}
              {searchQuery && (
                <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded">
                  Search: "{searchQuery}"
                </span>
              )}
              <button
                onClick={() => {
                  setEventTypeFilter('all');
                  setSeverityFilter('all');
                  setSearchQuery('');
                  setPatientFilter('all');
                }}
                className="ml-2 text-indigo-600 hover:text-indigo-700 underline"
              >
                Clear all
              </button>
            </div>
          )}
        </div>

        {/* Audit Log Table */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <AuditLogTable logs={filteredLogs} isLoading={isLoading} />
        </div>

        {/* Compliance Notice */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-xl p-4">
          <div className="flex gap-3">
            <FileText className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">Audit Trail Compliance</p>
              <p className="text-blue-700">
                All events are permanently logged with timestamps and user attribution.
                This audit trail supports clinical reviews, quality assurance, and regulatory compliance.
                Logs cannot be modified or deleted to ensure data integrity.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}