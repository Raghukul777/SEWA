import apiClient from './apiClient';

export const adminApi = {
    /** Hospital-wide KPI stats */
    async getStats() {
        const { data } = await apiClient.get('/admin/stats');
        return data;
    },

    /** All doctors with per-doctor patient counts */
    async getDoctors() {
        const { data } = await apiClient.get('/admin/doctors');
        return data;
    },

    /** All active patients across all doctors */
    async getAllPatients({ status = null, search = null } = {}) {
        const params = {};
        if (status && status !== 'all') params.status = status;
        if (search) params.search = search;
        const { data } = await apiClient.get('/admin/patients', { params });
        return data;
    },

    /** Toggle a doctor active/inactive */
    async toggleDoctorActive(doctorId) {
        const { data } = await apiClient.put(`/admin/doctors/${doctorId}/toggle-active`);
        return data;
    },

    /** Refresh analytics materialized view */
    async refreshStats() {
        const { data } = await apiClient.post('/admin/refresh-stats');
        return data;
    },
};
