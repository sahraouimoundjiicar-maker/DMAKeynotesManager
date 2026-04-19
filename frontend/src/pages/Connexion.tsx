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
    } else if (password.length < 8) {
      nouvErreurs.password = 'Le mot de passe doit contenir au moins 8 caractères';
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
    console.log('Email:', email.trim());

    if (!validerConnexion()) {
      console.log('❌ Validation locale échouée');
      return;
    }

    setIsLoading(true);
    console.log('⏳ isLoading = true');

    try {
      console.log('📡 Appel API authService.connexion...');
      const reponse = await authService.connexion({
        email: email.trim(),
        mot_de_passe: password,
      });

      console.log('📥 Réponse API reçue:', reponse);
      console.log('📥 reponse.data:', reponse.data);
      console.log('📥 reponse.data?.access_token:', reponse.data?.access_token);

      if (reponse.data?.access_token) {
        console.log('✅ Token reçu - Connexion réussie');

        localStorage.setItem('token', reponse.data.access_token);
        localStorage.setItem('user_role', reponse.data.role || 'utilisateur');
        localStorage.setItem('user_email', email.trim());

        setIsLoading(false);
        console.log('⏳ isLoading = false (succès)');

        afficherNotification('Connexion réussie ! Bienvenue', 'success');

        const role = reponse.data.role || 'utilisateur';
        console.log(`👤 Rôle détecté: ${role}, redirection dans 1.5s`);

        setTimeout(() => {
          if (role === 'super_admin') {
            console.log('🚀 Redirection vers /utilisateurs');
            navigate('/utilisateurs');
          } else {
            console.log('🚀 Redirection vers /keynotes');
            navigate('/keynotes');
          }
        }, 1500);
      } else {
        console.log('⚠️ Pas de token dans la réponse');
        setIsLoading(false);
        afficherNotification('Réponse du serveur invalide. Veuillez réessayer.', 'error');
      }

    } catch (erreur: any) {
      console.log('=== 🔴 DÉBUT CATCH ERREUR ===');
      console.log('Erreur complète:', erreur);
      console.log('Type de erreur:', typeof erreur);
      console.log('erreur?.response:', erreur?.response);
      console.log('erreur?.response?.status:', erreur?.response?.status);
      console.log('erreur?.response?.data:', erreur?.response?.data);
      console.log('erreur?.response?.data?.detail:', erreur?.response?.data?.detail);
      console.log('erreur?.message:', erreur?.message);
      console.log('=== 🔴 FIN CATCH ERREUR ===');

      setIsLoading(false);
      console.log('⏳ isLoading = false (erreur)');

      const codeHttp = erreur?.response?.status;
      console.log(`📊 Code HTTP détecté: ${codeHttp}`);

      if (codeHttp === 403) {
        console.log('✅ CAS 403 DÉTECTÉ - Compte en attente');
        console.log('📢 Affichage notification WARNING (jaune)');
        afficherNotification(
          "Compte en attente d'approbation. Veuillez patienter jusqu'à validation par l'administrateur.",
          'warning'
        );
      } else if (codeHttp === 401) {
        console.log('✅ CAS 401 DÉTECTÉ - Identifiants incorrects');
        console.log('📢 Affichage notification ERROR (rouge)');
        afficherNotification('Email ou mot de passe incorrect. Veuillez réessayer.', 'error');
      } else {
        console.log(`⚠️ AUTRE CODE HTTP: ${codeHttp} - Erreur inconnue`);
        console.log('📢 Affichage notification ERROR générique');
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
                      placeholder="Dupont"
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
                      placeholder="Jean"
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
                  placeholder="jean.dupont@dma.com"
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