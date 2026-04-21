import apiClient from './apiClient';

export const patientsApi = {
    /** List all active patients assigned to the current doctor */
    async getPatients() {
        const { data } = await apiClient.get('/patients');
        return data;
    },

    /** Admit a new patient (assigned to the logged-in doctor automatically) */
    async admitPatient(patientData) {
        const { data } = await apiClient.post('/patients', patientData);
        return data;
    },

    /** Get a single patient */
    async getPatient(patientId) {
        const { data } = await apiClient.get(`/patients/${patientId}`);
        return data;
    },

    /** Discharge a patient */
    async dischargePatient(patientId) {
        const { data } = await apiClient.put(`/patients/${patientId}/discharge`);
        return data;
    },

    /** Update treatment bundle { key, value } */
    async updateTreatment(patientId, key, value) {
        const { data } = await apiClient.put(`/patients/${patientId}/treatment`, { key, value });
        return data;
    },

    /** Add a clinical note { text, author } */
    async addNote(patientId, noteData) {
        const { data } = await apiClient.post(`/patients/${patientId}/notes`, noteData);
        return data;
    },
};
