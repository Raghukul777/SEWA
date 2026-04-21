export const MOCK_USERS = [
    {
        id: 'D-1001',
        email: 'doctor@sewa.com',
        password: 'Sewa@123', // In a real app, this would be hashed!
        name: 'Dr. Sarah Smith',
        hospital_name: 'City General Hospital',
        role: 'Intensivist'
    },
    {
        id: 'D-1002',
        email: 'admin@sewa.com',
        password: 'Sewa@123',
        name: 'Dr. Admin',
        hospital_name: 'Central Medical Center',
        role: 'Administrator'
    }
];

export const MOCK_AUTH_RESPONSE = {
    token: 'mock-jwt-token-xyz-123',
    expires_in: 3600
};
