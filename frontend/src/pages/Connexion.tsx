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
// Utilise useEffect pour nettoyer le setTimeout proprement
// et éviter les fuites mémoire si le composant est démonté.
// ============================================================

interface PropsNotification {
  message: string;
  type: TypeNotification;
  onClose: () => void;
}

const Notification: React.FC<PropsNotification> = ({ message, type, onClose }) => {
  React.useEffect(() => {
    const minuterie = setTimeout(onClose, 6000);
    return () => clearTimeout(minuterie); // Nettoyage si démonté avant 6 secondes
  }, [onClose]);

  return <div className={`notification ${type}`}>{message}</div>;
};

// ============================================================
// SECTION 3 — COMPOSANT PRINCIPAL
// ============================================================

const Connexion: React.FC = () => {
  const navigate = useNavigate();

  // --- Mode du formulaire ---
  const [isRegisterMode, setIsRegisterMode] = useState(false);

  // --- Champs du formulaire ---
  const [nom, setNom] = useState('');
  const [prenom, setPrenom] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // --- État de chargement ---
  const [isLoading, setIsLoading] = useState(false);

  // --- Erreurs de validation ---
  const [errors, setErrors] = useState<EtatErreurs>(ERREURS_VIDES);

  // --- Notification (clé unique pour forcer le re-montage à chaque nouvelle notification) ---
  const [notification, setNotification] = useState<{
    message: string;
    type: TypeNotification;
    cle: number;
  } | null>(null);

  // ============================================================
  // SECTION 4 — FONCTIONS UTILITAIRES
  // ============================================================

  function afficherNotification(message: string, type: TypeNotification) {
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
  // Réinitialise tous les champs et toutes les erreurs
  // pour éviter un état incohérent entre les deux modes.
  // ============================================================

  function basculerMode() {
    setIsRegisterMode((prev) => !prev);
    effacerErreurs();
    // Réinitialise tous les champs — pas seulement ceux spécifiques à l'inscription
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
  // Centralisé pour éviter la duplication dans handleLogin/handleRegister.
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

        afficherNotification('Connexion réussie ! Bienvenue', 'success');

        // Redirige selon le rôle :
        // - super_admin → page Utilisateurs (gestion de l'équipe)
        // - utilisateur → page Keynotes (accès aux keynotes)
        const role = reponse.data.role || 'utilisateur';
        setTimeout(() => {
          if (role === 'super_admin') {
            navigate('/utilisateurs');
          } else {
            navigate('/keynotes');
          }
        }, 1500);
      } else {
        afficherNotification('Réponse du serveur invalide', 'error');
      }

    } catch (erreur: any) {
      console.error('Erreur connexion:', erreur);

      const messageErreur = extraireMessageErreurApi(
        erreur,
        'Erreur de connexion. Veuillez réessayer.'
      );

      // Affiche en "warning" si le compte est en attente d'approbation
      const typeErreur: TypeNotification =
        messageErreur.toLowerCase().includes('attente') ||
        messageErreur.toLowerCase().includes('approbation')
          ? 'warning'
          : 'error';

      afficherNotification(messageErreur, typeErreur);
    } finally {
      setIsLoading(false);
    }
  }

  // ============================================================
  // SECTION 9 — INSCRIPTION
  // ============================================================

  async function handleRegister() {
    if (!validerInscription()) return;

    setIsLoading(true);
    try {
      await authService.inscription({
        nom: nom.trim(),
        prenom: prenom.trim(),
        email: email.trim(),
        mot_de_passe: password,
        confirmer_mot_de_passe: confirmPassword,
      });

      // Une seule notification — claire et suffisante
      afficherNotification(
        "Inscription réussie ! Votre compte est en attente d'approbation par l'administrateur.",
        'success'
      );

      // Réinitialise le formulaire et repasse en mode connexion après 2 secondes
      setTimeout(() => {
        setIsRegisterMode(false);
        setNom('');
        setPrenom('');
        setEmail('');
        setPassword('');
        setConfirmPassword('');
        effacerErreurs();
      }, 2000);

    } catch (erreur: any) {
      console.error('Erreur inscription:', erreur);
      const messageErreur = extraireMessageErreurApi(
        erreur,
        "Erreur lors de l'inscription. Veuillez réessayer."
      );
      afficherNotification(messageErreur, 'error');
    } finally {
      setIsLoading(false);
    }
  }

  // ============================================================
  // SECTION 10 — SOUMISSION DU FORMULAIRE
  // ============================================================

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
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

      {/* Notification flottante — re-montée à chaque nouvelle via la clé */}
      {notification && (
        <Notification
          key={notification.cle}
          message={notification.message}
          type={notification.type}
          onClose={() => setNotification(null)}
        />
      )}

      <div className="section">
        <div className="section-header">
          <h2>{isRegisterMode ? 'Inscription' : 'Connexion'}</h2>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid-1x1">
            <div className="cell">

              {/* Champs Nom + Prénom — visibles uniquement en mode inscription */}
              <div
                className={`register-fields register-fields-top ${isRegisterMode ? 'expanded' : ''}`}
              >
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
                    {errors.nom && (
                      <span className="error-message">{errors.nom}</span>
                    )}
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
                    {errors.prenom && (
                      <span className="error-message">{errors.prenom}</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Email — toujours visible */}
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
                {errors.email && (
                  <span className="error-message">{errors.email}</span>
                )}
              </div>

              {/* Mot de passe — toujours visible */}
              <div className="form-group form-group-password">
                <label className="cell-title">
                  Mot de passe <span style={{ color: '#dc3545' }}>*</span>
                </label>
                <input
                  type="password"
                  autoComplete="new-password"
                  className={`form-input ${errors.password ? 'error' : ''}`}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
                {errors.password && (
                  <span className="error-message">{errors.password}</span>
                )}
              </div>

              {/* Confirmation mot de passe — visible uniquement en mode inscription */}
              <div
                className={`register-fields register-fields-bottom ${isRegisterMode ? 'expanded' : ''}`}
              >
                <div>
                  <div className="form-group">
                    <label className="cell-title">
                      Confirmer le mot de passe{' '}
                      <span style={{ color: '#dc3545' }}>*</span>
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
                    {errors.confirmPassword && (
                      <span className="error-message">{errors.confirmPassword}</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Bouton de soumission */}
              <div className="button-group">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isLoading}
                >
                  {isLoading
                    ? 'Chargement...'
                    : isRegisterMode
                    ? "S'inscrire"
                    : 'Se connecter'}
                </button>
              </div>

              {/* Lien pour basculer entre connexion et inscription */}
              <div className="switch-mode">
                <span>
                  {isRegisterMode ? 'Déjà un compte ? ' : 'Nouveau ? '}
                </span>
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
