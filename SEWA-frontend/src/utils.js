export const createPageUrl = (pageName) => {
    if (pageName === 'Dashboard') return '/dashboard';
    if (pageName === 'AuditLog') return '/audit';
    if (pageName === 'Admin') return '/admin';
    return '/';
};
