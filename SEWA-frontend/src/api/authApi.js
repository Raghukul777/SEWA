import apiClient from './apiClient';

export const authApi = {
    /** Login — returns { access_token, user } */
    async login(email, password) {
        const { data } = await apiClient.post('/auth/login', { email, password });
        return data;
    },

    /** Register — returns { access_token, user } */
    async register({ name, email, password, hospital_name, department = '', phone = '', role = 'Doctor' }) {
        const { data } = await apiClient.post('/auth/register', {
            name, email, password, hospital_name, department, phone, role,
        });
        return data;
    },

    /** Get current user info */
    async getMe() {
        const { data } = await apiClient.get('/auth/me');
        return data;
    },
};
