import apiClient from './apiClient';

export const alertsApi = {
    /** Get alerts (optionally filtered by patientId / active_only) */
    async getAlerts({ patientId, activeOnly = false } = {}) {
        const params = {};
        if (patientId) params.patient_id = patientId;
        if (activeOnly) params.active_only = true;
        const { data } = await apiClient.get('/alerts', { params });
        return data;
    },

    /** Submit clinician feedback on an alert */
    async submitFeedback(alertId, feedback) {
        const { data } = await apiClient.put(`/alerts/${alertId}/feedback`, { feedback });
        return data;
    },
};
