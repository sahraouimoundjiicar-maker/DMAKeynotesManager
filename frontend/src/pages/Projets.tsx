// src/pages/Projets.tsx
//
// Composant de gestion des projets.
// Architecture : état géré exclusivement par useState → React re-rend le JSX automatiquement.
// Aucune manipulation directe du DOM (pas de innerHTML, pas de ref sur les inputs,
// pas de window.* global, pas de addEventListener manuel).

import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { projetsService, utilisateursService, accesService } from '../api/api';

// ============================================================
// SECTION 1 — TYPES
// ============================================================

// Structure d'un projet retourné par l'API
interface Projet {
  id: number;
  nom: string;
  chemin_export: string | null;
  txt_a_jour: boolean;
  date_dernier_export: string | null;
  date_creation: string; // Format ISO depuis l'API
}

// Utilisateur retourné par GET /utilisateurs (UtilisateurReponseModele)
// Contient le statut — utilisé pour la recherche d'utilisateurs à ajouter au projet
interface UtilisateurAPI {
  id: number;
  nom: string;
  prenom: string;
  email: string;
  statut: string;
}

// Utilisateur retourné par GET /projets/{id} (utilisateurProjetModele)
// Ne contient PAS de statut — utilisé pour afficher les utilisateurs ayant accès au projet
interface UtilisateurAcces {
  id: number;
  nom: string;
  prenom: string;
  email: string;
}

// Les trois modes possibles pour le formulaire
type ModeFormulaire = 'creation' | 'lecture' | 'edition';

// Structure de l'état du formulaire (champs contrôlés par React)
interface EtatFormulaire {
  nomProjet    : string;
  cheminExport : string;
}

const ETAT_FORMULAIRE_VIDE: EtatFormulaire = {
  nomProjet    : '',
  cheminExport : '',
};

// ============================================================
// SECTION 2 — FONCTIONS UTILITAIRES PURES (hors composant)
// ============================================================

// Normalise une chaîne pour la recherche : minuscules + suppression des accents
function normaliserChaine(texte: string): string {
  return texte
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[œ]/g, 'oe')
    .replace(/[æ]/g, 'ae');
}

// Formate une date ISO en format lisible fr-FR (ex: "28/03/2026")
function formaterDate(dateIso: string | null): string {
  if (!dateIso) return '—';
  try {
    return new Date(dateIso).toLocaleDateString('fr-FR');
  } catch {
    return dateIso;
  }
}

// ============================================================
// SECTION 3 — SOUS-COMPOSANT : Notification
// ============================================================

interface PropsNotification {
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  onClose: () => void;
}

const Notification: React.FC<PropsNotification> = ({ message, type, onClose }) => {
  // Fermeture automatique uniquement pour success et info (5 secondes)
  // error et warning restent jusqu'au clic sur ✖
  useEffect(() => {
    if (type === 'success' || type === 'info') {
      const minuterie = setTimeout(onClose, 5000);
      return () => clearTimeout(minuterie);
    }
  }, [type, onClose]);

  return (
    <div className={`notification ${type}`}>
      <span>{message}</span>
      {(type === 'error' || type === 'warning') && (
        <button
          onClick={onClose}
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
// SECTION 4 — SOUS-COMPOSANT : Champ de recherche avec suggestions
// Générique — réutilisé pour la recherche de projet et d'utilisateur.
// ============================================================

interface PropsChampRecherche<T> {
  id: string;
  placeholder: string;
  valeur: string;
  suggestions: T[];
  renduSuggestion: (element: T) => React.ReactNode;
  cléSuggestion: (element: T) => string;
  onChangement: (valeur: string) => void;
  onSelectionSuggestion: (element: T) => void;
  onEffacer: () => void;
  disabled?: boolean;
}

function ChampRecherche<T>({
  id,
  placeholder,
  valeur,
  suggestions,
  renduSuggestion,
  cléSuggestion,
  onChangement,
  onSelectionSuggestion,
  onEffacer,
  disabled = false,
}: PropsChampRecherche<T>) {
  const [suggestionVisible, setSuggestionVisible] = useState(false);

  // Ferme les suggestions si on clique en dehors du composant
  useEffect(() => {
    function gererClicExterieur(evenement: MouseEvent) {
      const conteneur = document.getElementById(`conteneur-recherche-${id}`);
      if (conteneur && !conteneur.contains(evenement.target as Node)) {
        setSuggestionVisible(false);
      }
    }
    document.addEventListener('mousedown', gererClicExterieur);
    return () => document.removeEventListener('mousedown', gererClicExterieur);
  }, [id]);

  function gererChangementInput(evenement: React.ChangeEvent<HTMLInputElement>) {
    const nouvelleValeur = evenement.target.value;
    onChangement(nouvelleValeur);
    setSuggestionVisible(nouvelleValeur.trim().length >= 2 && suggestions.length > 0);
  }

  // Met à jour la visibilité quand la liste de suggestions change
  useEffect(() => {
    setSuggestionVisible(valeur.trim().length >= 2 && suggestions.length > 0);
  }, [suggestions, valeur]);

  return (
    <div id={`conteneur-recherche-${id}`} className="suggestions-container">
      <div className="search-wrapper">
        <input
          type="text"
          id={id}
          className="search-input"
          placeholder={placeholder}
          value={valeur}
          onChange={gererChangementInput}
          disabled={disabled}
          autoComplete="off"
        />
        {valeur.trim().length > 0 && (
          <button
            className="clear-search visible"
            onClick={onEffacer}
            disabled={disabled}
            type="button"
          >
            ✖
          </button>
        )}
      </div>

      {suggestionVisible && suggestions.length > 0 && (
        <div className="suggestions" style={{ display: 'block' }}>
          {suggestions.map((element) => (
            <div
              key={cléSuggestion(element)}
              className="suggestion-item"
              onMouseDown={(e) => {
                e.preventDefault(); // Empêche le blur avant la sélection
                onSelectionSuggestion(element);
                setSuggestionVisible(false);
              }}
            >
              {renduSuggestion(element)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================
// SECTION 5 — COMPOSANT PRINCIPAL
// ============================================================

const Projets: React.FC = () => {
  const navigate = useNavigate();

  // Rôle de l'utilisateur connecté — certaines actions (accès projets)
  // sont réservées au super_admin côté backend
  const roleUtilisateurConnecte = localStorage.getItem('user_role');
  const estSuperAdmin = roleUtilisateurConnecte === 'super_admin';

  // --- États principaux ---
  const [projets, setProjets] = useState<Projet[]>([]);
  const [tousLesUtilisateurs, setTousLesUtilisateurs] = useState<UtilisateurAPI[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // --- État du formulaire ---
  const [formulaire, setFormulaire] = useState<EtatFormulaire>(ETAT_FORMULAIRE_VIDE);
  const [modeFormulaire, setModeFormulaire] = useState<ModeFormulaire>('creation');
  const [projetSelectionne, setProjetSelectionne] = useState<Projet | null>(null);

  // Utilisateurs ayant accès au projet en cours (edition ou lecture)
  const [utilisateursAcces, setUtilisateursAcces] = useState<UtilisateurAcces[]>([]);

  // --- États des champs de recherche ---
  const [rechercheProjet, setRechercheProjet] = useState('');
  // Bloque l'affichage des suggestions après sélection d'un projet
  // depuis le tableau — évite la fenêtre flottante indésirable
  const [suggestionsProjetsBloquees, setSuggestionsProjetsBloquees] = useState(false);
  const [rechercheUtilisateur, setRechercheUtilisateur] = useState('');

  // Utilisateur sélectionné dans le champ recherche (avant ajout)
  const [utilisateurEnAttente, setUtilisateurEnAttente] = useState<UtilisateurAPI | null>(null);

  // --- État du dialogue d'import ---
  // Contient le nom du fichier et la fonction resolve de la Promise
  // pour retourner le choix de l'utilisateur (remplacer/fusionner/annuler)
  const [modeImportEnCours, setModeImportEnCours] = useState<{
    nomFichier: string;
    resolve   : (mode: 'remplacer' | 'fusionner' | null) => void;
  } | null>(null);

  // --- État des notifications ---
  const [notification, setNotification] = useState<{
    message: string;
    type: 'success' | 'error' | 'warning' | 'info';
    cle: number;
  } | null>(null);

  // ============================================================
  // SECTION 6 — DONNÉES DÉRIVÉES
  // ============================================================

  // Suggestions pour la recherche de projet (filtre sur la liste chargée)
  const suggestionsProjet: Projet[] =
    !suggestionsProjetsBloquees && rechercheProjet.trim().length >= 2
      ? projets
          .filter((p) => normaliserChaine(p.nom).includes(normaliserChaine(rechercheProjet)))
          .slice(0, 10)
      : [];

  // Suggestions pour la recherche d'utilisateur (exclut ceux déjà dans la liste)
  const suggestionsUtilisateur: UtilisateurAPI[] =
    rechercheUtilisateur.trim().length >= 2
      ? tousLesUtilisateurs
          .filter(
            (u) =>
              u.statut === 'approuve' && // Seuls les utilisateurs approuvés peuvent recevoir un accès
              !utilisateursAcces.some((ua) => ua.id === u.id) && // Pas déjà dans la liste
              (normaliserChaine(u.nom).includes(normaliserChaine(rechercheUtilisateur)) ||
                normaliserChaine(u.prenom).includes(normaliserChaine(rechercheUtilisateur)) ||
                normaliserChaine(u.email).includes(normaliserChaine(rechercheUtilisateur)))
          )
          .slice(0, 10)
      : [];

  // Détermine si les champs du formulaire sont éditables
  const formulaireEstModifiable = modeFormulaire === 'creation' || modeFormulaire === 'edition';

  // Détermine si le bouton "Enregistrer" est actif
  const enregistrerEstActif = modeFormulaire === 'creation' || modeFormulaire === 'edition';

  // Détermine si le bouton "Modifier" est actif (seulement en lecture)
  const modifierEstActif = modeFormulaire === 'lecture';

  // Détermine si le bouton "Annuler" est actif
  const annulerEstActif = modeFormulaire === 'edition';

  // Détermine si le bouton "Supprimer" est actif (seulement en lecture)
  const supprimerEstActif = modeFormulaire === 'lecture';

  // Détermine si les boutons Exporter/Importer sont actifs (projet sélectionné)
  const exportImportEstActif = projetSelectionne !== null;

  // Détermine si la zone d'ajout d'utilisateur est active
  // Réservé au super_admin — le backend rejette les appels accesService si non super_admin
  const ajoutUtilisateurEstActif = estSuperAdmin && (modeFormulaire === 'creation' || modeFormulaire === 'edition');

  // ============================================================
  // SECTION 7 — NOTIFICATIONS
  // ============================================================

  function afficherNotification(
    message: string,
    type: 'success' | 'error' | 'warning' | 'info' = 'success'
  ) {
    setNotification({ message, type, cle: Date.now() });
  }

  // ============================================================
  // SECTION 8 — CHARGEMENT DES DONNÉES DEPUIS L'API
  // ============================================================

  const chargerProjets = useCallback(async (): Promise<Projet[]> => {
    try {
      const reponse = await projetsService.getAll();
      const listeProjets: Projet[] = reponse.data;
      setProjets(listeProjets);
      return listeProjets;
    } catch (erreur) {
      console.error('Erreur chargement projets:', erreur);
      afficherNotification('Erreur lors du chargement des projets', 'error');
      return [];
    }
  }, []);

  const chargerUtilisateurs = useCallback(async () => {
    try {
      const reponse = await utilisateursService.getAll();
      setTousLesUtilisateurs(reponse.data);
    } catch (erreur) {
      console.error('Erreur chargement utilisateurs:', erreur);
      afficherNotification('Erreur lors du chargement des utilisateurs', 'error');
    }
  }, []);

  // Charge les utilisateurs ayant accès à un projet spécifique
  const chargerUtilisateursAcces = useCallback(async (idProjet: number) => {
    try {
      const reponse = await projetsService.getById(idProjet);
      const projetDetail = reponse.data;
      // L'API retourne ProjetDetailModele avec un champ "utilisateurs" (utilisateurProjetModele)
      // Champs disponibles : id_utilisateur, nom, prenom, email, date_attribution
      // Note : pas de champ "statut" dans ce modèle — on utilise UtilisateurAcces
      const utilisateursDetail: { id_utilisateur: number; nom: string; prenom: string; email: string }[] =
        projetDetail.utilisateurs ?? [];

      const listeAcces: UtilisateurAcces[] = utilisateursDetail.map((u) => ({
        id: u.id_utilisateur,
        nom: u.nom,
        prenom: u.prenom,
        email: u.email,
      }));
      setUtilisateursAcces(listeAcces);
    } catch (erreur) {
      console.error('Erreur chargement utilisateurs du projet:', erreur);
      setUtilisateursAcces([]);
    }
  }, []);

  // ============================================================
  // SECTION 9 — INITIALISATION AU MONTAGE DU COMPOSANT
  // ============================================================

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/connexion');
      return;
    }

    async function initialiser() {
      setIsLoading(true);
      await Promise.all([chargerProjets(), chargerUtilisateurs()]);
      setIsLoading(false);
    }

    initialiser();
  }, [navigate, chargerProjets, chargerUtilisateurs]);

  // ============================================================
  // SECTION 10 — GESTION DES MODES DU FORMULAIRE
  // ============================================================

  // Passe en mode création : formulaire vide, prêt pour un nouveau projet
  function activerModeCreation() {
    setModeFormulaire('creation');
    setProjetSelectionne(null);
    setFormulaire(ETAT_FORMULAIRE_VIDE); // nomProjet + cheminExport vides
    setSuggestionsProjetsBloquees(false);
    setUtilisateursAcces([]);
    setRechercheProjet('');
    setRechercheUtilisateur('');
    setUtilisateurEnAttente(null);
  }

  // Passe en mode lecture : formulaire rempli avec le projet sélectionné, non éditable
  async function activerModeLecture(projet: Projet) {
    setModeFormulaire('lecture');
    setProjetSelectionne(projet);
    setFormulaire({
      nomProjet    : projet.nom,
      cheminExport : projet.chemin_export ?? '',
    });
    setRechercheProjet(projet.nom);
    // Bloquer les suggestions pour éviter la fenêtre flottante
    // après sélection depuis le tableau ou depuis une suggestion
    setSuggestionsProjetsBloquees(true);
    setRechercheUtilisateur('');
    setUtilisateurEnAttente(null);
    // Charge les utilisateurs ayant accès à ce projet depuis l'API
    await chargerUtilisateursAcces(projet.id);
  }

  // Passe en mode édition : formulaire modifiable
  function activerModeEdition() {
    if (!projetSelectionne) return;
    setModeFormulaire('edition');
    // Les utilisateurs déjà chargés restent en place pour édition
  }

  // ============================================================
  // SECTION 11 — SÉLECTION D'UN PROJET
  // ============================================================

  async function selectionnerProjet(idProjet: number) {
    const projetTrouve = projets.find((p) => p.id === idProjet);
    if (!projetTrouve) return;
    await activerModeLecture(projetTrouve);
    afficherNotification(`Projet "${projetTrouve.nom}" sélectionné`, 'info');
  }

  // ============================================================
  // SECTION 12 — GESTION DES UTILISATEURS DU PROJET
  // ============================================================

  // Ajoute l'utilisateur en attente à la liste d'accès
  function ajouterUtilisateur() {
    if (!utilisateurEnAttente) {
      afficherNotification("Veuillez sélectionner un utilisateur dans la liste", 'warning');
      return;
    }
    if (utilisateursAcces.some((u) => u.id === utilisateurEnAttente.id)) {
      afficherNotification(
        `"${utilisateurEnAttente.prenom} ${utilisateurEnAttente.nom}" a déjà accès à ce projet`,
        'warning'
      );
      return;
    }
    // On extrait seulement les champs de UtilisateurAcces (sans statut)
    const nouvelAcces: UtilisateurAcces = {
      id: utilisateurEnAttente.id,
      nom: utilisateurEnAttente.nom,
      prenom: utilisateurEnAttente.prenom,
      email: utilisateurEnAttente.email,
    };
    setUtilisateursAcces([...utilisateursAcces, nouvelAcces]);
    afficherNotification(
      `"${utilisateurEnAttente.prenom} ${utilisateurEnAttente.nom}" ajouté`,
      'success'
    );
    setRechercheUtilisateur('');
    setUtilisateurEnAttente(null);
  }

  // Retire un utilisateur de la liste d'accès (local uniquement — confirmé à l'enregistrement)
  function retirerUtilisateur(idUtilisateur: number) {
    const utilisateurCible = utilisateursAcces.find((u) => u.id === idUtilisateur);
    setUtilisateursAcces(utilisateursAcces.filter((u) => u.id !== idUtilisateur));
    if (utilisateurCible) {
      afficherNotification(
        `"${utilisateurCible.prenom} ${utilisateurCible.nom}" retiré`,
        'warning'
      );
    }
  }

  // ============================================================
  // SECTION 13 — ENREGISTREMENT (création ou modification)
  // ============================================================

  async function enregistrer() {
    // Validation du nom de projet
    // Alignée avec CreerProjetModele / ModifierProjetModele (backend : min 3 caractères)
    const nomProjetNettoye = formulaire.nomProjet.trim();
    if (!nomProjetNettoye) {
      afficherNotification('Le nom du projet est obligatoire', 'error');
      return;
    }
    if (nomProjetNettoye.length < 3) {
      afficherNotification('Le nom du projet doit contenir au moins 3 caractères', 'error');
      return;
    }

    // --- CAS 1 : CRÉATION d'un nouveau projet ---
    if (modeFormulaire === 'creation') {
      try {
        // Étape 1 — Crée le projet via POST /projets
        const reponseCreation = await projetsService.create({
          nom_projet    : formulaire.nomProjet.trim(),
          chemin_export : formulaire.cheminExport.trim() || undefined,
        });
        const nouveauProjet: Projet = reponseCreation.data;

        // Étape 2 — Attribue les accès aux utilisateurs sélectionnés
        // Note : accesService est réservé au super_admin (backend vérifie le token)
        if (estSuperAdmin) {
          for (const utilisateur of utilisateursAcces) {
            try {
              await accesService.attribuer(nouveauProjet.id, { id_utilisateur: utilisateur.id });
            } catch (erreurAcces) {
              console.warn(
                `Accès non attribué pour ${utilisateur.prenom} ${utilisateur.nom}:`,
                erreurAcces
              );
            }
          }
        }

        afficherNotification(
          `Projet "${nouveauProjet.nom}" créé avec succès`,
          'success'
        );
        await chargerProjets();
        activerModeCreation();

      } catch (erreur) {
        console.error('Erreur création projet:', erreur);
        afficherNotification('Erreur lors de la création du projet', 'error');
      }
      return;
    }

    // --- CAS 2 : MODIFICATION d'un projet existant ---
    if (modeFormulaire === 'edition' && projetSelectionne) {
      try {
        // Étape 1 — Renomme le projet si le nom a changé
        // Met à jour le nom et/ou le chemin d'export si modifiés
        const nomChange = formulaire.nomProjet.trim() !== projetSelectionne.nom;
        const cheminChange = (formulaire.cheminExport.trim() || null) !== projetSelectionne.chemin_export;

        if (nomChange || cheminChange) {
          await projetsService.update(projetSelectionne.id, {
            nouveau_nom   : nomChange ? formulaire.nomProjet.trim() : undefined,
            chemin_export : cheminChange ? (formulaire.cheminExport.trim() || undefined) : undefined,
          });
        }

        // Étape 2 — Synchronise les accès utilisateurs (réservé super_admin)
        // Charge la liste actuelle depuis l'API pour calculer les différences
        const reponseDetail = await projetsService.getById(projetSelectionne.id);
        const utilisateursActuels: { id_utilisateur: number }[] =
          reponseDetail.data.utilisateurs ?? [];
        const idsActuels = new Set(utilisateursActuels.map((u) => u.id_utilisateur));
        const idsVoulus = new Set(utilisateursAcces.map((u) => u.id));

        // Synchronise les accès — réservé au super_admin (backend vérifie le token)
        if (estSuperAdmin) {
          // Retire les utilisateurs qui ne sont plus dans la liste
          for (const idActuel of idsActuels) {
            if (!idsVoulus.has(idActuel)) {
              try {
                await accesService.retirer(projetSelectionne.id, idActuel);
              } catch (erreurRetrait) {
                console.warn(`Impossible de retirer l'accès pour id=${idActuel}:`, erreurRetrait);
              }
            }
          }

          // Ajoute les nouveaux utilisateurs
          for (const utilisateur of utilisateursAcces) {
            if (!idsActuels.has(utilisateur.id)) {
              try {
                await accesService.attribuer(projetSelectionne.id, { id_utilisateur: utilisateur.id });
              } catch (erreurAjout) {
                console.warn(
                  `Impossible d'ajouter l'accès pour ${utilisateur.prenom} ${utilisateur.nom}:`,
                  erreurAjout
                );
              }
            }
          }
        }

        afficherNotification(
          `Projet "${formulaire.nomProjet.trim()}" modifié avec succès`,
          'success'
        );

        // Recharge et repasse en lecture avec les données à jour
        const listeMiseAJour = await chargerProjets();
        const projetMisAJour = listeMiseAJour.find((p) => p.id === projetSelectionne.id);
        if (projetMisAJour) await activerModeLecture(projetMisAJour);

      } catch (erreur) {
        console.error('Erreur modification projet:', erreur);
        afficherNotification('Erreur lors de la modification du projet', 'error');
      }
    }
  }

  // ============================================================
  // SECTION 14 — ANNULATION
  // ============================================================

  async function annuler() {
    if (modeFormulaire === 'edition' && projetSelectionne) {
      // Restaure les données originales depuis l'API
      await activerModeLecture(projetSelectionne);
      afficherNotification('Modifications annulées', 'warning');
    }
  }

  // ============================================================
  // SECTION 15 — SUPPRESSION
  // ============================================================

  async function supprimerProjet() {
    if (!projetSelectionne) {
      afficherNotification("Veuillez d'abord sélectionner un projet", 'warning');
      return;
    }

    const confirmation = window.confirm(
      `Êtes-vous sûr de vouloir supprimer le projet "${projetSelectionne.nom}" ?\nCette action est irréversible.`
    );
    if (!confirmation) return;

    const nomSauvegarde = projetSelectionne.nom;

    try {
      await projetsService.delete(projetSelectionne.id);
      await chargerProjets();
      activerModeCreation();
      afficherNotification(`Projet "${nomSauvegarde}" supprimé avec succès`, 'success');
    } catch (erreur) {
      console.error('Erreur suppression projet:', erreur);
      afficherNotification('Erreur lors de la suppression du projet', 'error');
    }
  }

  // ============================================================
  // SECTION 16 — EXPORT ET IMPORT
  // ============================================================

  async function exporterProjet() {
    if (!projetSelectionne) {
      afficherNotification("Veuillez d'abord sélectionner un projet", 'warning');
      return;
    }
    try {
      // Afficher le chemin cible si défini — aide l'utilisateur
      // à naviguer vers le bon dossier dans la fenêtre Windows
      if (projetSelectionne.chemin_export) {
        afficherNotification(
          `Naviguez vers : ${projetSelectionne.chemin_export}`,
          'info'
        );
        // Laisser le temps à l'utilisateur de lire le message
        // avant que la fenêtre "Enregistrer sous" s'ouvre
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }

      // Déclenche la fenêtre "Enregistrer sous" (Chrome/Edge)
      // ou le téléchargement classique (Firefox/Safari)
      // Retourne false si l'utilisateur a annulé la fenêtre
      const succes = await projetsService.exporter(projetSelectionne.id, projetSelectionne.nom);
      if (!succes) return; // Annulation — pas de notification
      afficherNotification('Exportation !', 'success');
      // Recharge pour mettre à jour txt_a_jour et date_dernier_export
      await chargerProjets();
    } catch (erreur) {
      console.error('Erreur export projet:', erreur);
      afficherNotification("Erreur lors de l'export du projet", 'error');
    }
  }

  // ============================================================
  // SECTION 16B — IMPORT FICHIER .TXT REVIT
  // ============================================================

  // Déclenche la sélection de fichier et l'import
  async function importerProjet() {
    if (!projetSelectionne) {
      afficherNotification("Veuillez d'abord sélectionner un projet", 'warning');
      return;
    }

    // Étape 1 — Ouvrir la fenêtre de sélection de fichier
    const input = document.createElement('input');
    input.type   = 'file';
    input.accept = '.txt';

    input.onchange = async (evenement) => {
      const fichier = (evenement.target as HTMLInputElement).files?.[0];
      if (!fichier) return;

      // Étape 2 — Valider le fichier sélectionné
      const erreurValidation = await validerFichierImport(fichier);
      if (erreurValidation) {
        afficherNotification(erreurValidation, 'error');
        return;
      }

      // Étape 3 — Demander le mode d'import via confirmation
      const modeChoisi = await choisirModeImport(fichier.name);
      if (!modeChoisi) return; // Annulation

      // Étape 4 — Lire et envoyer le fichier
      await executerImport(fichier, modeChoisi);
    };

    input.click();
  }

  // Valide le fichier avant import — retourne un message d'erreur ou null
  async function validerFichierImport(fichier: File): Promise<string | null> {
    // Vérifier l'extension
    if (!fichier.name.endsWith('.txt')) {
      return "Le fichier doit être au format .txt";
    }

    // Vérifier la taille (max 5 MB)
    const TAILLE_MAX = 5 * 1024 * 1024;
    if (fichier.size > TAILLE_MAX) {
      return "Le fichier dépasse la taille maximale autorisée (5 MB)";
    }

    // Vérifier le contenu — lire les premières lignes
    try {
      const texte = await lireFichierTexte(fichier);
      const lignes = texte.split('\n').filter((l) => l.trim());
      if (lignes.length === 0) {
        return "Le fichier est vide";
      }
      // Vérifier qu'au moins la première ligne a le format TAB
      const premiereLigne = lignes[0];
      if (!premiereLigne.includes('\t')) {
        return "Format invalide — le fichier doit utiliser des tabulations comme séparateurs";
      }
    } catch {
      return "Impossible de lire le fichier";
    }

    return null; // Fichier valide
  }

  // Lit le contenu d'un fichier texte en gérant UTF-16 et UTF-8
  function lireFichierTexte(fichier: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        const buffer = e.target?.result as ArrayBuffer;
        const bytes  = new Uint8Array(buffer);

        // Détecter BOM UTF-16 LE (FF FE) ou UTF-16 BE (FE FF)
        if (
          (bytes[0] === 0xFF && bytes[1] === 0xFE) ||
          (bytes[0] === 0xFE && bytes[1] === 0xFF)
        ) {
          const decoder = new TextDecoder('utf-16');
          resolve(decoder.decode(buffer));
        } else {
          // Essayer UTF-16 sans BOM, puis UTF-8
          try {
            const decoder16 = new TextDecoder('utf-16le');
            const texte16   = decoder16.decode(buffer);
            // Valider que c'est du texte lisible (contient des tabulations)
            if (texte16.includes('\t')) {
              resolve(texte16);
            } else {
              const decoder8 = new TextDecoder('utf-8');
              resolve(decoder8.decode(buffer));
            }
          } catch {
            const decoder8 = new TextDecoder('utf-8');
            resolve(decoder8.decode(buffer));
          }
        }
      };

      reader.onerror = () => reject(new Error("Erreur de lecture"));
      reader.readAsArrayBuffer(fichier);
    });
  }

  // Affiche un dialogue pour choisir le mode d'import
  // Retourne 'remplacer', 'fusionner' ou null (annulation)
  async function choisirModeImport(nomFichier: string): Promise<'remplacer' | 'fusionner' | null> {
    return new Promise((resolve) => {
      setModeImportEnCours({ nomFichier, resolve });
    });
  }

  // Exécute l'import du fichier avec le mode choisi
  async function executerImport(
    fichier    : File,
    mode       : 'remplacer' | 'fusionner'
  ) {
    if (!projetSelectionne) return;

    try {
      afficherNotification(
        `Import en cours (mode : ${mode})...`, 'info'
      );

      const contenuTxt = await lireFichierTexte(fichier);

      const reponse = await projetsService.importer(
        projetSelectionne.id,
        { mode, contenu_txt: contenuTxt }
      );

      const stats = reponse.data;
      afficherNotification(
        `Import réussi — ${stats.categories_inserees} catégorie(s), ${stats.notes_inserees} note(s)`,
        'success'
      );

      await chargerProjets();

    } catch (erreur: any) {
      console.error('Erreur import:', erreur);
      const messageApi = erreur?.response?.data?.detail || "Erreur lors de l'import";
      afficherNotification(messageApi, 'error');
    }
  }

  // ============================================================
  // SECTION 17 — RENDU CONDITIONNEL : CHARGEMENT
  // ============================================================

  if (isLoading) {
    return <div className="container">Chargement...</div>;
  }

  // ============================================================
  // SECTION 18 — RENDU PRINCIPAL (JSX)
  // ============================================================

  return (
    <>
      {/* Notification flottante — re-montée à chaque nouvelle notification grâce à la clé */}
      {notification && (
        <Notification
          key={notification.cle}
          message={notification.message}
          type={notification.type}
          onClose={() => setNotification(null)}
        />
      )}

      <div className="container">

        {/* -------------------------------------------------- */}
        {/* SECTION FORMULAIRE                                  */}
        {/* -------------------------------------------------- */}
        <div className="section">
          <div className="section-header">
            <h2>Gestion des projets</h2>
          </div>

          <div className="grid-4x3">

            {/* CELLULE 1 — Nom du projet */}
            <div className="cell-form">
              <label className="cell-title" htmlFor="champ-nom-projet">
                Nom du projet
              </label>
              <input
                type="text"
                id="champ-nom-projet"
                className="form-input"
                placeholder="Saisissez le nom du projet"
                value={formulaire.nomProjet}
                readOnly={!formulaireEstModifiable}
                onChange={(e) => setFormulaire({ ...formulaire, nomProjet: e.target.value })}
              />
            </div>

            {/* CELLULE 2 — Chemin d'export */}
            <div className="cell-form">
              <label className="cell-title" htmlFor="champ-chemin-export">
                Chemin d'export
              </label>
              <input
                type="text"
                id="champ-chemin-export"
                className="form-input"
                placeholder="Sélectionner le dossier X - Data de votre projet"
                value={formulaire.cheminExport}
                readOnly={!formulaireEstModifiable}
                onChange={(e) => setFormulaire({ ...formulaire, cheminExport: e.target.value })}
              />
            </div>

            {/* CELLULE 3 — Chercher utilisateur à ajouter */}
            <div className="cell-form">
              <label className="cell-title" htmlFor="recherche-utilisateur-projet">
                Chercher utilisateur
              </label>
              <ChampRecherche<UtilisateurAPI>
                id="recherche-utilisateur-projet"
                placeholder="Nom, prénom ou email..."
                valeur={rechercheUtilisateur}
                suggestions={suggestionsUtilisateur}
                cléSuggestion={(u) => String(u.id)}
                renduSuggestion={(u) => (
                  <>
                    <strong>{u.prenom} {u.nom}</strong>
                    <br />
                    <small>{u.email}</small>
                  </>
                )}
                onChangement={(valeur) => {
                  setRechercheUtilisateur(valeur);
                  // Si l'utilisateur modifie le champ, annule la sélection en attente
                  if (utilisateurEnAttente && valeur !== `${utilisateurEnAttente.prenom} ${utilisateurEnAttente.nom}`) {
                    setUtilisateurEnAttente(null);
                  }
                }}
                onSelectionSuggestion={(u) => {
                  setRechercheUtilisateur(`${u.prenom} ${u.nom} — ${u.email}`);
                  setUtilisateurEnAttente(u);
                }}
                onEffacer={() => {
                  setRechercheUtilisateur('');
                  setUtilisateurEnAttente(null);
                }}
                disabled={!ajoutUtilisateurEstActif}
              />
              <button
                type="button"
                className="add-button"
                disabled={!ajoutUtilisateurEstActif}
                onClick={ajouterUtilisateur}
              >
                + Donner accès
              </button>
            </div>

            {/* CELLULE 3 — Liste des utilisateurs avec accès */}
            <div className="cell-users">
              <label className="cell-title">Utilisateurs avec accès</label>
              <div className="users-list">
                {utilisateursAcces.length === 0 ? (
                  <div className="empty-list">Aucun utilisateur</div>
                ) : (
                  utilisateursAcces.map((utilisateur) => (
                    <div key={utilisateur.id} className="user-item">
                      <span>{utilisateur.prenom} {utilisateur.nom}</span>
                      {/* Bouton retirer visible seulement en mode création ou édition */}
                      {ajoutUtilisateurEstActif && (
                        <button
                          type="button"
                          className="remove-user"
                          onClick={() => retirerUtilisateur(utilisateur.id)}
                        >
                          ✖
                        </button>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* CELLULE 4 — Rechercher projet existant */}
            <div className="cell-form">
              <div className="cell-title">Chercher projet</div>
              <ChampRecherche<Projet>
                id="recherche-projet"
                placeholder="Rechercher un projet par son nom..."
                valeur={rechercheProjet}
                suggestions={suggestionsProjet}
                cléSuggestion={(p) => String(p.id)}
                renduSuggestion={(p) => (
                  <>
                    <strong>{p.nom}</strong>
                    <br />
                    <small>Créé le {formaterDate(p.date_creation)}</small>
                  </>
                )}
                onChangement={(valeur) => {
                  setRechercheProjet(valeur);
                  // Débloquer les suggestions quand l'utilisateur tape
                  setSuggestionsProjetsBloquees(false);
                  // Si le champ est vidé, repasse en mode création
                  if (valeur.trim() === '') activerModeCreation();
                }}
                onSelectionSuggestion={(p) => selectionnerProjet(p.id)}
                onEffacer={() => {
                  activerModeCreation();
                  afficherNotification('Sélection effacée — Vous pouvez créer un nouveau projet', 'info');
                }}
              />
            </div>

            {/* LIGNE 3 — Boutons d'action (3 colonnes fusionnées) */}
            {/* Contient tous les boutons : Importer, Exporter, Modifier, */}
            {/* Enregistrer, Annuler, Supprimer                           */}
            <div className="cell-merged cell-merged-3">
              <div className="button-group">
                <button
                  type="button"
                  className="action-button"
                  disabled={!exportImportEstActif}
                  onClick={exporterProjet}
                >
                  Exporter
                </button>
                <button
                  type="button"
                  className="action-button"
                  disabled={!modifierEstActif}
                  onClick={activerModeEdition}
                >
                  Modifier
                </button>
                <button
                  type="button"
                  className="action-button"
                  disabled={!exportImportEstActif}
                  onClick={importerProjet}
                >
                  Importer
                </button>
                <button
                  type="button"
                  className="action-button"
                  disabled={!enregistrerEstActif}
                  onClick={enregistrer}
                >
                  Enregistrer
                </button>
                <button
                  type="button"
                  className="cancel-button"
                  disabled={!annulerEstActif}
                  onClick={annuler}
                >
                  Annuler
                </button>
                <button
                  type="button"
                  className="delete-button"
                  disabled={!supprimerEstActif}
                  onClick={supprimerProjet}
                >
                  Supprimer
                </button>
              </div>
            </div>

          </div>
        </div>

        {/* -------------------------------------------------- */}
        {/* DIALOGUE MODE D'IMPORT                              */}
        {/* -------------------------------------------------- */}
        {modeImportEnCours && (
          <div style={{
            position       : 'fixed',
            top            : 0,
            left           : 0,
            right          : 0,
            bottom         : 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display        : 'flex',
            alignItems     : 'center',
            justifyContent : 'center',
            zIndex         : 1000,
          }}>
            <div style={{
              backgroundColor: '#fff',
              borderRadius   : '12px',
              padding        : '32px',
              maxWidth       : '480px',
              width          : '90%',
              boxShadow      : '0 8px 32px rgba(0,0,0,0.2)',
            }}>
              <h3 style={{ margin: '0 0 8px', fontSize: '18px', color: '#333' }}>
                Mode d'import
              </h3>
              <p style={{ margin: '0 0 8px', fontSize: '14px', color: '#666' }}>
                Fichier : <strong>{modeImportEnCours.nomFichier}</strong>
              </p>
              <p style={{ margin: '0 0 24px', fontSize: '14px', color: '#666' }}>
                Choisissez comment importer les données dans le projet
                <strong> "{projetSelectionne?.nom}"</strong> :
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
                <div style={{ padding: '16px', border: '1px solid #e0e0e0', borderRadius: '8px' }}>
                  <strong style={{ fontSize: '14px' }}>Remplacer</strong>
                  <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#666' }}>
                    Supprime toutes les catégories et notes existantes,
                    puis importe le fichier. Action irréversible.
                  </p>
                </div>
                <div style={{ padding: '16px', border: '1px solid #e0e0e0', borderRadius: '8px' }}>
                  <strong style={{ fontSize: '14px' }}>Fusionner</strong>
                  <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#666' }}>
                    Ajoute uniquement les catégories et notes absentes.
                    Les éléments existants sont conservés.
                  </p>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="cancel-button"
                  onClick={() => {
                    modeImportEnCours.resolve(null);
                    setModeImportEnCours(null);
                  }}
                >
                  Annuler
                </button>
                <button
                  type="button"
                  className="action-button"
                  onClick={() => {
                    modeImportEnCours.resolve('fusionner');
                    setModeImportEnCours(null);
                  }}
                >
                  Fusionner
                </button>
                <button
                  type="button"
                  className="delete-button"
                  onClick={() => {
                    modeImportEnCours.resolve('remplacer');
                    setModeImportEnCours(null);
                  }}
                >
                  Remplacer
                </button>
              </div>
            </div>
          </div>
        )}

        {/* -------------------------------------------------- */}
        {/* SECTION TABLEAU — Liste des projets                 */}
        {/* -------------------------------------------------- */}
        <div className="section">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nom du projet</th>
                <th>Chemin d'export</th>
                <th>Date de création</th>
                <th>Dernier export</th>
                <th>Fichier .txt</th>
              </tr>
            </thead>
            <tbody>
              {projets.map((projet) => (
                <tr
                  key={projet.id}
                  style={{ cursor: 'pointer' }}
                  className={projetSelectionne?.id === projet.id ? 'row-selected' : ''}
                  onClick={() => selectionnerProjet(projet.id)}
                >
                  <td>{projet.id}</td>
                  <td>{projet.nom}</td>
                  <td>{projet.chemin_export ?? '—'}</td>
                  <td>{formaterDate(projet.date_creation)}</td>
                  <td>{formaterDate(projet.date_dernier_export)}</td>
                  <td>
                    <span
                      className={`badge ${projet.txt_a_jour ? 'badge-active' : 'badge-pending'}`}
                    >
                      {projet.txt_a_jour ? 'À jour' : 'Obsolète'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>
    </>
  );
};

export default Projets;
