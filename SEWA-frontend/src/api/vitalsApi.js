import apiClient from './apiClient';

export const vitalsApi = {
    /**
     * Post a vital reading to the API.
     * The backend runs sepsis risk scoring and returns { reading, risk_assessment, alert? }
     */
    async postVitalReading(patientId, vitals) {
        try {
            const { data } = await apiClient.post(`/vitals/${patientId}`, vitals);
            return data;
        } catch (err) {
            // Don't break the UI simulation if the API is temporarily down
            console.warn(`[vitalsApi] POST failed for ${patientId}:`, err.message);
            return null;
        }
    },

    /** Get last N vital readings for a patient (chronological order) */
    async getPatientReadings(patientId, limit = 50) {
        const { data } = await apiClient.get(`/vitals/${patientId}`, {
            params: { limit },
        });
        return data;
    },
};
