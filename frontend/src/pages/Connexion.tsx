// src/pages/Connexion.tsx

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../api/api';

// ============================================================
// SECTION 1 — TYPES
// ============================================================

type TypeNotification = 'success' | 'error' | 'warning' | 'info';

interface EtatErreurs {
  nom: string;
  prenom: string;
  email: string;
  password: string;
  confirmPassword: string;
}

const ERREURS_VIDES: EtatErreurs = {
  nom: '',
  prenom: '',
  email: '',
  password: '',
  confirmPassword: '',
};

// ============================================================
// SECTION 2 — SOUS-COMPOSANT : Notification
// ============================================================

interface PropsNotification {
  message: string;
  type: TypeNotification;
  onClose: () => void;
}

const Notification: React.FC<PropsNotification> = ({ message, type, onClose }) => {
  console.log('🔔 NOTIFICATION CRÉÉE:', { message, type });

  // Fermeture automatique uniquement pour success et info
  React.useEffect(() => {
    console.log(`📋 useEffect Notification - type: ${type}`);

    if (type === 'success' || type === 'info') {
      console.log(`⏰ Fermeture automatique programmée dans 5 secondes pour ${type}`);
      const minuterie = setTimeout(() => {
        console.log(`❌ Fermeture automatique déclenchée pour ${type}`);
        onClose();
      }, 5000);
      return () => {
        console.log(`🧹 Nettoyage de la minuterie pour ${type}`);
        clearTimeout(minuterie);
      };
    } else {
      console.log(`🚫 Pas de fermeture automatique pour ${type} (attend clic sur ✖)`);
    }
  }, [type, onClose]);

  return (
    <div className={`notification ${type}`}>
      <span>{message}</span>
      {(type === 'error' || type === 'warning') && (
        <button
          onClick={() => {
            console.log(`🖱️ Clic sur le bouton ✖ pour fermer la notification ${type}`);
            onClose();
          }}
          aria-label="Fermer"
          className="notification-close"
        >
          ✖
        </button>
      )}
    </div>
  );
};

// ============================================================
// SECTION 3 — COMPOSANT PRINCIPAL
// ============================================================

const Connexion: React.FC = () => {
  const navigate = useNavigate();

  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [nom, setNom] = useState('');
  const [prenom, setPrenom] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<EtatErreurs>(ERREURS_VIDES);
  const [notification, setNotification] = useState<{
    message: string;
    type: TypeNotification;
    cle: number;
  } | null>(null);

  // ============================================================
  // SECTION 4 — FONCTIONS UTILITAIRES
  // ============================================================

  function afficherNotification(message: string, type: TypeNotification) {
    console.log(`📢 afficherNotification appelée: "${message}" (type: ${type})`);
    setNotification({ message, type, cle: Date.now() });
  }

  function effacerErreurs() {
    setErrors(ERREURS_VIDES);
  }

  function validerEmail(adresseEmail: string): boolean {
    const regexEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regexEmail.test(adresseEmail);
  }

  // ============================================================
  // SECTION 5 — BASCULEMENT CONNEXION ↔ INSCRIPTION
  // ============================================================

  function basculerMode() {
    setIsRegisterMode((prev) => !prev);
    effacerErreurs();
    setNom('');
    setPrenom('');
    setEmail('');
    setPassword('');
    setConfirmPassword('');
  }

  // ============================================================
  // SECTION 6 — VALIDATION
  // ============================================================

  function validerInscription(): boolean {
    const nouvErreurs: EtatErreurs = { ...ERREURS_VIDES };
    let estValide = true;

    if (!nom.trim()) {
      nouvErreurs.nom = 'Le nom est obligatoire';
      estValide = false;
    } else if (nom.trim().length < 2) {
      nouvErreurs.nom = 'Le nom doit contenir au moins 2 caractères';
      estValide = false;
    }

    if (!prenom.trim()) {
      nouvErreurs.prenom = 'Le prénom est obligatoire';
      estValide = false;
    } else if (prenom.trim().length < 2) {
      nouvErreurs.prenom = 'Le prénom doit contenir au moins 2 caractères';
      estValide = false;
    }

    if (!email.trim()) {
      nouvErreurs.email = "L'email est obligatoire";
      estValide = false;
    } else if (!validerEmail(email.trim())) {
      nouvErreurs.email = 'Email invalide (ex: nom@domaine.com)';
      estValide = false;
    }

    if (!password) {
      nouvErreurs.password = 'Le mot de passe est obligatoire';
      estValide = false;
    } else if (password.length < 3) {
      nouvErreurs.password = 'Le mot de passe doit contenir au moins 3 caractères';
      estValide = false;
    }

    if (!confirmPassword) {
      nouvErreurs.confirmPassword = 'Veuillez confirmer votre mot de passe';
      estValide = false;
    } else if (password !== confirmPassword) {
      nouvErreurs.confirmPassword = 'Les mots de passe ne correspondent pas';
      estValide = false;
    }

    setErrors(nouvErreurs);
    return estValide;
  }

  function validerConnexion(): boolean {
    const nouvErreurs: EtatErreurs = { ...ERREURS_VIDES };
    let estValide = true;

    if (!email.trim()) {
      nouvErreurs.email = "L'email est obligatoire";
      estValide = false;
    } else if (!validerEmail(email.trim())) {
      nouvErreurs.email = 'Email invalide (ex: nom@domaine.com)';
      estValide = false;
    }

    if (!password) {
      nouvErreurs.password = 'Le mot de passe est obligatoire';
      estValide = false;
    }

    setErrors(nouvErreurs);
    return estValide;
  }

  // ============================================================
  // SECTION 7 — EXTRACTION DU MESSAGE D'ERREUR API
  // ============================================================

  function extraireMessageErreurApi(erreur: any, messageParDefaut: string): string {
    if (erreur?.response?.data) {
      if (typeof erreur.response.data === 'string') return erreur.response.data;
      if (erreur.response.data.detail) return erreur.response.data.detail;
      if (erreur.response.data.message) return erreur.response.data.message;
    }
    return messageParDefaut;
  }

  // ============================================================
  // SECTION 8 — CONNEXION
  // ============================================================

  async function handleLogin() {
  console.log('🔐 handleLogin - Début');

  if (!validerConnexion()) return;

  setIsLoading(true);

  try {
    const reponse = await authService.connexion({
      email: email.trim(),
      mot_de_passe: password,
    });

    if (reponse.data?.access_token) {
      localStorage.setItem('token', reponse.data.access_token);
      localStorage.setItem('user_role', reponse.data.role || 'utilisateur');
      localStorage.setItem('user_email', email.trim());

      setIsLoading(false);
      afficherNotification('Connexion réussie ! Bienvenue', 'success');

      const role = reponse.data.role || 'utilisateur';
      setTimeout(() => {
        if (role === 'super_admin') {
          navigate('/utilisateurs');
        } else {
          navigate('/keynotes');
        }
      }, 1500);
    } else {
      setIsLoading(false);
      afficherNotification('Réponse du serveur invalide', 'error');
    }

  } catch (erreur: any) {
    console.log('=== DÉTAIL COMPLET DE L ERREUR ===');
    console.log('Erreur:', erreur);
    console.log('Status (erreur.response?.status):', erreur.response?.status);
    console.log('Status (erreur.status):', erreur.status);
    console.log('Données (erreur.response?.data):', erreur.response?.data);
    console.log('Données (erreur.data):', erreur.data);
    console.log('Message:', erreur.message);
    console.log('=== FIN DÉTAIL ===');

    setIsLoading(false);

    // ESSAYONS PLUSIEURS FAÇONS DE DÉTECTER LE CODE 403
    const codeHttp = erreur?.response?.status || erreur?.status;
    const message = erreur?.response?.data?.detail || erreur?.response?.data || erreur?.message || '';
    const messageLower = message.toString().toLowerCase();

    console.log('Code HTTP détecté (méthode alternative):', codeHttp);
    console.log('Message détecté:', message);
    console.log('Message en minuscules:', messageLower);

    // DÉTECTION PAR CODE HTTP
    if (codeHttp === 403) {
      console.log('🔥 DÉTECTION 403 - Notification warning');
      afficherNotification(
        "Compte en attente d'approbation. Veuillez patienter.",
        'warning'
      );
    }
    // DÉTECTION PAR MESSAGE (secours)
    else if (messageLower.includes('attente') || messageLower.includes('approbation')) {
      console.log('🔥 DÉTECTION PAR MESSAGE - Notification warning');
      afficherNotification(
        "Compte en attente d'approbation. Veuillez patienter.",
        'warning'
      );
    }
    // DÉTECTION 401
    else if (codeHttp === 401) {
      console.log('🔥 DÉTECTION 401 - Notification error');
      afficherNotification('Email ou mot de passe incorrect', 'error');
    }
    // AUTRE
    else {
      console.log('🔥 CAS PAR DÉFAUT - Notification error');
      afficherNotification('Erreur de connexion. Veuillez réessayer.', 'error');
    }
  }
}

  // ============================================================
  // SECTION 9 — INSCRIPTION
  // ============================================================

  async function handleRegister() {
    console.log('📝 handleRegister - Début');

    if (!validerInscription()) {
      console.log('❌ Validation inscription échouée');
      return;
    }

    setIsLoading(true);
    console.log('⏳ isLoading = true');

    try {
      console.log('📡 Appel API authService.inscription...');
      await authService.inscription({
        nom: nom.trim(),
        prenom: prenom.trim(),
        email: email.trim(),
        mot_de_passe: password,
        confirmer_mot_de_passe: confirmPassword,
      });

      console.log('✅ Inscription réussie');
      afficherNotification(
        "Inscription réussie ! Votre compte est en attente d'approbation par l'administrateur.",
        'success'
      );

      setTimeout(() => {
        console.log('🔄 Basculement vers mode connexion');
        setIsRegisterMode(false);
        setNom('');
        setPrenom('');
        setEmail('');
        setPassword('');
        setConfirmPassword('');
        effacerErreurs();
      }, 2000);

    } catch (erreur: any) {
      console.log('=== 🔴 ERREUR INSCRIPTION ===');
      console.log('Erreur:', erreur);
      console.log('erreur?.response?.status:', erreur?.response?.status);
      console.log('erreur?.response?.data:', erreur?.response?.data);
      console.log('=== 🔴 FIN ERREUR INSCRIPTION ===');

      const messageErreur = extraireMessageErreurApi(
        erreur,
        "Erreur lors de l'inscription. Veuillez réessayer."
      );
      afficherNotification(messageErreur, 'error');
    } finally {
      setIsLoading(false);
      console.log('⏳ isLoading = false (fin inscription)');
    }
  }

  // ============================================================
  // SECTION 10 — SOUMISSION DU FORMULAIRE
  // ============================================================

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    console.log(`📝 Formulaire soumis - mode: ${isRegisterMode ? 'inscription' : 'connexion'}`);
    if (isRegisterMode) {
      handleRegister();
    } else {
      handleLogin();
    }
  }

  // ============================================================
  // SECTION 11 — RENDU (JSX)
  // ============================================================

  return (
    <div className="container-login">

      {notification && (
        <Notification
          key={notification.cle}
          message={notification.message}
          type={notification.type}
          onClose={() => {
            console.log(`❌ Fermeture manuelle de la notification ${notification.type}`);
            setNotification(null);
          }}
        />
      )}

      <div className="section">
        <div className="section-header">
          <h2>{isRegisterMode ? 'Inscription' : 'Connexion'}</h2>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid-1x1">
            <div className="cell">

              <div className={`register-fields register-fields-top ${isRegisterMode ? 'expanded' : ''}`}>
                <div>
                  <div className="form-group">
                    <label className="cell-title">
                      Nom <span style={{ color: '#dc3545' }}>*</span>
                    </label>
                    <input
                      type="text"
                      className={`form-input ${errors.nom ? 'error' : ''}`}
                      placeholder="Votre nom"
                      value={nom}
                      onChange={(e) => setNom(e.target.value)}
                      disabled={isLoading}
                    />
                    {errors.nom && <span className="error-message">{errors.nom}</span>}
                  </div>

                  <div className="form-group">
                    <label className="cell-title">
                      Prénom <span style={{ color: '#dc3545' }}>*</span>
                    </label>
                    <input
                      type="text"
                      className={`form-input ${errors.prenom ? 'error' : ''}`}
                      placeholder="Votre prenom"
                      value={prenom}
                      onChange={(e) => setPrenom(e.target.value)}
                      disabled={isLoading}
                    />
                    {errors.prenom && <span className="error-message">{errors.prenom}</span>}
                  </div>
                </div>
              </div>

              <div className="form-group form-group-email">
                <label className="cell-title">
                  Email <span style={{ color: '#dc3545' }}>*</span>
                </label>
                <input
                  type="email"
                  className={`form-input ${errors.email ? 'error' : ''}`}
                  placeholder="votre@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                />
                {errors.email && <span className="error-message">{errors.email}</span>}
              </div>

              <div className="form-group form-group-password">
                <label className="cell-title">
                  Mot de passe <span style={{ color: '#dc3545' }}>*</span>
                </label>
                <input
                  type="password"
                  autoComplete={isRegisterMode ? 'new-password' : 'current-password'}
                  className={`form-input ${errors.password ? 'error' : ''}`}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
                {errors.password && <span className="error-message">{errors.password}</span>}
              </div>

              <div className={`register-fields register-fields-bottom ${isRegisterMode ? 'expanded' : ''}`}>
                <div>
                  <div className="form-group">
                    <label className="cell-title">
                      Confirmer le mot de passe <span style={{ color: '#dc3545' }}>*</span>
                    </label>
                    <input
                      type="password"
                      autoComplete="new-password"
                      className={`form-input ${errors.confirmPassword ? 'error' : ''}`}
                      placeholder="••••••••"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      disabled={isLoading}
                    />
                    {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
                  </div>
                </div>
              </div>

              <div className="button-group">
                <button type="submit" className="btn btn-primary" disabled={isLoading}>
                  {isLoading ? 'Chargement...' : isRegisterMode ? "S'inscrire" : 'Se connecter'}
                </button>
              </div>

              <div className="switch-mode">
                <span>{isRegisterMode ? 'Déjà un compte ? ' : 'Nouveau ? '}</span>
                <span className="switch-link" onClick={basculerMode}>
                  {isRegisterMode ? 'Se connecter' : 'Enregistrez-vous'}
                </span>
              </div>

            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Connexion;