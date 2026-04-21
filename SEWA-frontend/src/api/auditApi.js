import apiClient from './apiClient';

export const auditApi = {
    /**
     * Get audit logs with optional filters.
     * @param {Object} filters - { eventType, severity, sinceDays, patientId }
     */
    async getAuditLogs({ eventType, severity, sinceDays, patientId } = {}) {
        const params = {};
        if (eventType && eventType !== 'all') params.event_type = eventType;
        if (severity && severity !== 'all') params.severity = severity;
        if (sinceDays != null) params.since_days = sinceDays;
        if (patientId) params.patient_id = patientId;

        const { data } = await apiClient.get('/audit', { params });
        return data;
    },
};
