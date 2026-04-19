// src/api/api.ts
import axios from 'axios';

// URL du backend Render
const API_URL = import.meta.env.VITE_API_URL || 'https://dmakeynotesmanager.onrender.com';

console.log('API URL:', API_URL);

// Routes publiques — pas de token JWT requis
const ROUTES_PUBLIQUES = [
  '/auth/register',
  '/auth/login',
  '/auth/reinitialiser-mot-de-passe',
];

// Créer une instance axios
const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─────────────────────────────────────────────────────────────
// INTERCEPTEUR — REQUÊTES
// Ajoute le token JWT uniquement sur les routes protégées.
// Les routes publiques (register, login) n'ont pas besoin
// de token et échoueraient si on en envoyait un invalide.
// ─────────────────────────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const url = config.url || '';
    const estRoutePublique = ROUTES_PUBLIQUES.some(
      (route) => url.includes(route)
    );

    if (!estRoutePublique) {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// ─────────────────────────────────────────────────────────────
// INTERCEPTEUR — RÉPONSES
// Redirige vers /connexion si le token est expiré (401).
// ─────────────────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user_role');
      localStorage.removeItem('user_email');
      window.location.href = '/connexion';
    }
    return Promise.reject(error);
  }
);

// ============================================================
// SERVICES AUTHENTIFICATION
// ============================================================
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

// ============================================================
// SERVICES UTILISATEURS
// ============================================================
export const utilisateursService = {
  getAll: () => api.get('/utilisateurs'),
  getDemandes: () => api.get('/utilisateurs/demandes'),
  getDemandesReinitialisation: () => api.get('/utilisateurs/demandes-reinitialisation'),
  approuver: (id: number) => api.put(`/utilisateurs/${id}/approuver`),
  refuser: (id: number) => api.put(`/utilisateurs/${id}/refuser`),
  getById: (id: number) => api.get(`/utilisateurs/${id}`),
  update: (id: number, data: {
    nouveau_nom?   : string;
    nouveau_prenom?: string;
    nouveau_email? : string;
    nouveau_mdp?   : string;
  }) => api.put(`/utilisateurs/${id}`, data),
  delete: (id: number) => api.delete(`/utilisateurs/${id}`),
  approuverReinitialisation: (id: number) =>
    api.put(`/utilisateurs/${id}/approuver-reinitialisation`),
  refuserReinitialisation: (id: number) =>
    api.put(`/utilisateurs/${id}/refuser-reinitialisation`),
};

// ============================================================
// SERVICES PROJETS
// ============================================================
export const projetsService = {
  getAll: () => api.get('/projets'),
  getById: (id: number) => api.get(`/projets/${id}`),
  create: (data: { nom_projet: string; chemin_export?: string }) =>
    api.post('/projets', data),
  update: (id: number, data: { nouveau_nom?: string; chemin_export?: string }) =>
    api.put(`/projets/${id}`, data),
  delete: (id: number) => api.delete(`/projets/${id}`),
  exporter: async (id: number, nomProjet: string): Promise<boolean> => {
    // Étape 1 — Récupérer le fichier depuis le backend
    const token = localStorage.getItem('token');
    const reponse = await fetch(
      `${api.defaults.baseURL}/projets/${id}/exporter`,
      {
        method : 'GET',
        headers: { 'Authorization': `Bearer ${token}` },
      }
    );
    if (!reponse.ok) {
      throw new Error(`Erreur export : ${reponse.status}`);
    }

    const blob        = await reponse.blob();
    const nomFichier  = `keynotes_${nomProjet.toLowerCase().replace(/\s+/g, '_')}.txt`;

    // Étape 2 — Tenter l'API File System Access (Chrome/Edge)
    // Affiche une vraie fenêtre "Enregistrer sous" Windows
    // permettant à l'utilisateur de choisir le dossier exact.
    if ('showSaveFilePicker' in window) {
      try {
        const handle = await (window as any).showSaveFilePicker({
          suggestedName: nomFichier,
          types: [{
            description: 'Fichier Revit Keynotes',
            accept     : { 'text/plain': ['.txt'] },
          }],
        });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        return true; // Succès
      } catch (erreur: any) {
        // L'utilisateur a annulé la fenêtre — retourner false sans erreur
        if (erreur?.name === 'AbortError') return false;
        // Autre erreur — fallback vers téléchargement classique
        console.warn('showSaveFilePicker échoué, fallback téléchargement:', erreur);
      }
    }

    // Étape 3 — Fallback : téléchargement classique (Firefox, Safari)
    // Le fichier est téléchargé dans le dossier Téléchargements
    const url  = window.URL.createObjectURL(blob);
    const lien = document.createElement('a');
    lien.href     = url;
    lien.download = nomFichier;
    document.body.appendChild(lien);
    lien.click();
    document.body.removeChild(lien);
    window.URL.revokeObjectURL(url);
    return true; // Succès
  },
  importer: (id: number, data: {
    mode        : 'remplacer' | 'fusionner';
    contenu_txt : string;
  }) => api.post(`/projets/${id}/importer`, data),
  getKeynotes: (id: number, categorieId?: number) =>
    api.get(`/projets/${id}/keynotes${categorieId ? `?id_categorie=${categorieId}` : ''}`),
  getHistorique: (id: number, page: number = 1, limite: number = 50) =>
    api.get(`/projets/${id}/historique?page=${page}&limite=${limite}`),
};

// ============================================================
// SERVICES ACCÈS
// ============================================================
export const accesService = {
  attribuer: (projetId: number, data: { id_utilisateur: number }) =>
    api.post(`/projets/${projetId}/acces`, data),
  retirer: (projetId: number, utilisateurId: number) =>
    api.delete(`/projets/${projetId}/acces/${utilisateurId}`),
};

// ============================================================
// SERVICES CATÉGORIES
// ============================================================
export const categoriesService = {
  getAll: (projetId: number) =>
    api.get(`/projets/${projetId}/categories`),
  create: (projetId: number, data: { numero: string; description: string }) =>
    api.post(`/projets/${projetId}/categories`, data),
  update: (projetId: number, categorieId: number, data: {
    version_actuelle : number;
    nouveau_numero?  : string;
    nouvelle_desc?   : string;
  }) => api.put(`/projets/${projetId}/categories/${categorieId}`, data),
  delete: (projetId: number, categorieId: number) =>
    api.delete(`/projets/${projetId}/categories/${categorieId}`),
};

// ============================================================
// SERVICES NOTES
// ============================================================
export const notesService = {
  getAll: (projetId: number, categorieId: number) =>
    api.get(`/projets/${projetId}/categories/${categorieId}/notes`),
  create: (projetId: number, categorieId: number, data: {
    numero      : string;
    description : string;
  }) => api.post(`/projets/${projetId}/categories/${categorieId}/notes`, data),
  update: (projetId: number, noteId: number, data: {
    version_actuelle : number;
    nouveau_numero?  : string;
    nouvelle_desc?   : string;
  }) => api.put(`/projets/${projetId}/notes/${noteId}`, data),
  delete: (projetId: number, noteId: number) =>
    api.delete(`/projets/${projetId}/notes/${noteId}`),
};

export default api;
