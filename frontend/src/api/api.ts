import axios from 'axios';

// URL de votre backend Render
const API_URL = import.meta.env.VITE_API_URL || 'https://dmakeynotesmanager.onrender.com';

console.log('API URL:', API_URL);

// Créer une instance axios
const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour ajouter le token JWT à chaque requête
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('🔐 Token ajouté pour:', config.url);
    } else {
      console.log('⚠️ Aucun token pour:', config.url);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Intercepteur pour gérer les erreurs 401
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      console.log('❌ Token expiré ou invalide');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/connexion';
    }
    return Promise.reject(error);
  }
);

// Service d'authentification
export const authService = {
  inscription: (data: {
    nom: string;
    prenom: string;
    email: string;
    mot_de_passe: string;
    confirmer_mot_de_passe: string;
  }) => api.post('/auth/register', data),

  connexion: (data: { email: string; mot_de_passe: string }) =>
    api.post('/auth/login', data),
};

// Service projets
export const projetsService = {
  getAll: () => api.get('/projets'),
  getOne: (id: number) => api.get(`/projets/${id}`),
  create: (nom_projet: string) => api.post('/projets', { nom_projet }),
};

export default api;