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
  useEffect(() => {
    const minuterie = setTimeout(onClose, 3000);
    return () => clearTimeout(minuterie);
  }, [onClose]);

  return <div className={`notification ${type}`}>{message}</div>;
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
  const [rechercheUtilisateur, setRechercheUtilisateur] = useState('');

  // Utilisateur sélectionné dans le champ recherche (avant ajout)
  const [utilisateurEnAttente, setUtilisateurEnAttente] = useState<UtilisateurAPI | null>(null);

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
    rechercheProjet.trim().length >= 2
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
      afficherNotification(`Export du projet "${projetSelectionne.nom}" en cours...`, 'info');
      await projetsService.exporter(projetSelectionne.id);
      afficherNotification(`Projet "${projetSelectionne.nom}" exporté avec succès`, 'success');
      // Recharge pour mettre à jour txt_a_jour et date_dernier_export
      await chargerProjets();
    } catch (erreur) {
      console.error('Erreur export projet:', erreur);
      afficherNotification("Erreur lors de l'export du projet", 'error');
    }
  }

  function importerProjet() {
    // Fonctionnalité à implémenter — ouverture d'un dialogue de fichier
    afficherNotification("Import — Veuillez sélectionner un fichier .txt Revit", 'info');
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

            {/* CELLULE TITRE — Création / Édition / Lecture */}
            <div className="cell-merged cell-merged-3">
              <h2 style={{ margin: 0, fontSize: '20px', color: '#333' }}>
                {modeFormulaire === 'creation' && 'Nouveau projet'}
                {modeFormulaire === 'lecture' && `Projet : ${projetSelectionne?.nom}`}
                {modeFormulaire === 'edition' && `Modifier : ${projetSelectionne?.nom}`}
              </h2>
            </div>

            {/* CELLULE BOUTONS PRINCIPAUX */}
            <div className="cell cell-no-left-padding">
              <div className="button-group">
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
              </div>
            </div>

            {/* CELLULE 1 — Nom du projet */}
            <div className="cell-form">
              <label className="cell-title" htmlFor="champ-nom-projet">
                Nom du projet *
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
                placeholder='ex: I:\\26\\2026-017 Dream Industrial\\X - Data'  
                value={formulaire.cheminExport}
                readOnly={!formulaireEstModifiable}
                onChange={(e) => setFormulaire({ ...formulaire, cheminExport: e.target.value })}
              />
            </div>

            {/* CELLULE 3 — Chercher utilisateur à ajouter */}
            <div className="cell-form">
              <label className="form-label" htmlFor="recherche-utilisateur-projet">
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
              <div className="users-title">Utilisateurs avec accès</div>
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

            {/* CELLULE 4+5 — Rechercher projet existant */}
            <div className="cell-merged cell-merged-2">
              <div className="search-row">
                <div className="cell-title">Chercher projet existant</div>
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
            </div>

            {/* CELLULE 6+7 — Boutons d'action sur projet sélectionné */}
            <div className="cell-merged cell-merged-2">
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
