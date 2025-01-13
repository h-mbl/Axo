import axios from 'axios';

const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 seconde

const apiClient = axios.create({
    baseURL: 'http://localhost:8000',
    timeout: 180000, // 3 minutes
    withCredentials: true,
    maxContentLength: 50 * 1024 * 1024, // 50 MB
    maxBodyLength: 50 * 1024 * 1024, // 50 MB
    headers: {
        'Accept': 'application/json',
    }
});

// Fonction utilitaire pour attendre
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

// Intercepteur de requête amélioré
apiClient.interceptors.request.use(async config => {
    // Ne pas définir Content-Type pour FormData
    if (config.data instanceof FormData) {
        delete config.headers['Content-Type'];
    }

    console.log('Envoi requête:', {
        url: config.url,
        method: config.method,
        size: config.data instanceof FormData ?
            Array.from(config.data.entries())
                .reduce((total, [_, value]) =>
                    total + (value instanceof File ? value.size : value.length), 0) :
            null
    });

    return config;
}, error => {
    console.error('Erreur de configuration requête:', error);
    return Promise.reject(error);
});

// Intercepteur de réponse avec retry
apiClient.interceptors.response.use(
    response => response,
    async error => {
        const originalRequest = error.config;

        if (!originalRequest || !originalRequest._retry) {
            originalRequest._retry = 0;
        }

        if (originalRequest._retry < MAX_RETRIES &&
            (error.code === 'ERR_NETWORK' || error.response?.status === 500)) {

            originalRequest._retry++;

            console.log(`Tentative de reconnexion ${originalRequest._retry}/${MAX_RETRIES}`);

            await delay(RETRY_DELAY * originalRequest._retry);

            return apiClient(originalRequest);
        }

        return Promise.reject(error);
    }
);

export default apiClient;