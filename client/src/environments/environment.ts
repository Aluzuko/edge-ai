export const environment = {
    production: false,
    apiUrl: 'http://localhost:8000',

    endpoints: {
        health: '/health',
        species: '/species',
        cameras: '/cameras',
        rangers: '/rangers',
        requests: '/requests',
        detections: '/detections',
        images: '/images',
        devices: '/devices',
        modelRuns: '/model-runs'
    }
};