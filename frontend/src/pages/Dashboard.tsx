import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/api';

function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState<any>(null);
  const [projets, setProjets] = useState<any[]>([]);
  const [utilisateurs, setUtilisateurs] = useState<any[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [nouveauProjet, setNouveauProjet] = useState('');
  const [creationEnCours, setCreationEnCours] = useState(false);
  const [ongletActif, setOngletActif] = useState<'projets' | 'utilisateurs'>('projets');

  useEffect(() => {
    // Vérifier si l'utilisateur est connecté
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');

    if (!token) {
      navigate('/connexion');
      return;
    }

    // Récupérer et parser les données utilisateur
    if (userData) {
      try {
        const parsedUser = JSON.parse(userData);
        console.log('👤 Utilisateur chargé:', parsedUser);
        setUser(parsedUser);
      } catch (error) {
        console.error('Erreur de parsing userData:', error);
        setUser(null);
      }
    }

    chargerProjets();
    chargerUtilisateurs();
  }, [navigate]);

  // Charger les projets
  const chargerProjets = async () => {
    try {
      console.log('📁 Chargement des projets...');
      const response = await api.get('/projets');
      console.log('Projets chargés:', response.data);

      if (Array.isArray(response.data)) {
        setProjets(response.data);
      } else if (response.data.data && Array.isArray(response.data.data)) {
        setProjets(response.data.data);
      } else {
        setProjets([]);
      }
    } catch (error: any) {
      console.error('Erreur lors du chargement des projets:', error);
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        navigate('/connexion');
      } else {
        setErreur('Impossible de charger les projets');
      }
    } finally {
      setChargement(false);
    }
  };

  // Charger les demandes d'inscription en attente
  const chargerUtilisateurs = async () => {
    try {
      console.log('👥 Chargement des demandes d\'inscription...');
      const response = await api.get('/utilisateurs/demandes');
      console.log('Demandes chargées:', response.data);

      if (Array.isArray(response.data)) {
        setUtilisateurs(response.data);
      } else if (response.data.data && Array.isArray(response.data.data)) {
        setUtilisateurs(response.data.data);
      } else {
        setUtilisateurs([]);
      }
    } catch (error: any) {
      console.error('Erreur lors du chargement des demandes:', error);
      // Si l'endpoint demandes n'existe pas, essayer tous les utilisateurs
      if (error.response?.status === 404) {
        try {
          const response2 = await api.get('/utilisateurs');
          const users = Array.isArray(response2.data) ? response2.data : (response2.data.data || []);
          const demandes = users.filter((u: any) => u.statut === 'en_attente');
          setUtilisateurs(demandes);
        } catch (e) {
          console.error('Erreur fallback:', e);
        }
      }
    }
  };

  const handleDeconnexion = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/connexion');
  };

  const handleCreerProjet = async () => {
    if (!nouveauProjet.trim()) {
      setErreur('Le nom du projet ne peut pas être vide');
      return;
    }

    setCreationEnCours(true);
    setErreur('');

    try {
      const response = await api.post('/projets', { nom_projet: nouveauProjet });
      console.log('✅ Projet créé:', response.data);

      setProjets([...projets, response.data]);
      setShowModal(false);
      setNouveauProjet('');
    } catch (error: any) {
      console.error('Erreur lors de la création:', error);
      const messageErreur = error.response?.data?.detail || 'Erreur lors de la création du projet';
      setErreur(messageErreur);
    } finally {
      setCreationEnCours(false);
    }
  };

  const handleApprouverUtilisateur = async (id: number) => {
    try {
      const response = await api.put(`/utilisateurs/${id}/approuver`);
      console.log('✅ Utilisateur approuvé:', response.data);
      chargerUtilisateurs();
      setErreur('');
    } catch (error: any) {
      console.error('Erreur lors de l\'approbation:', error);
      setErreur(error.response?.data?.detail || 'Erreur lors de l\'approbation');
    }
  };

  const handleRefuserUtilisateur = async (id: number) => {
    if (window.confirm('Êtes-vous sûr de vouloir refuser et supprimer définitivement cet utilisateur ? Cette action est irréversible.')) {
      try {
        const response = await api.put(`/utilisateurs/${id}/refuser`);
        console.log('❌ Utilisateur refusé:', response.data);
        chargerUtilisateurs();
        setErreur('');
      } catch (error: any) {
        console.error('Erreur lors du refus:', error);
        setErreur(error.response?.data?.detail || 'Erreur lors du refus');
      }
    }
  };

  // Fonction pour afficher le nom complet correctement
  const getNomComplet = () => {
    if (!user) return '';
    if (user.prenom && user.nom) {
      return `${user.prenom} ${user.nom}`;
    } else if (user.nom) {
      return user.nom;
    } else if (user.prenom) {
      return user.prenom;
    } else if (user.email) {
      return user.email.split('@')[0];
    }
    return 'Utilisateur';
  };

  // Fonction pour afficher le rôle en français
  const getRoleFrancais = (role: string) => {
    if (role === 'super_admin') return '👑 BIM Manager (Super Admin)';
    if (role === 'utilisateur') return '📝 utilisateur';
    return role || 'Utilisateur';
  };

  // Fonction pour afficher le statut en français
  const getStatutFrancais = (statut: string) => {
    if (statut === 'en_attente') return '⏳ En attente';
    if (statut === 'approuve') return '✅ Approuvé';
    if (statut === 'refuse') return '❌ Refusé';
    return statut;
  };

  const styles = {
    container: {
      maxWidth: '900px',
      margin: '0 auto',
      padding: '20px',
      fontFamily: 'Arial, sans-serif',
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      borderBottom: '1px solid #ddd',
      paddingBottom: '10px',
      marginBottom: '20px',
    },
    title: {
      margin: 0,
    },
    logoutBtn: {
      padding: '8px 16px',
      backgroundColor: '#dc3545',
      color: 'white',
      border: 'none',
      borderRadius: '4px',
      cursor: 'pointer',
    },
    tabs: {
      display: 'flex',
      gap: '10px',
      marginBottom: '20px',
      borderBottom: '1px solid #ddd',
    },
    tab: {
      padding: '10px 20px',
      cursor: 'pointer',
      border: 'none',
      background: 'none',
      fontSize: '16px',
      color: '#666',
    },
    tabActif: {
      color: '#007bff',
      borderBottom: '2px solid #007bff',
    },
    createBtn: {
      padding: '8px 16px',
      backgroundColor: '#007bff',
      color: 'white',
      border: 'none',
      borderRadius: '4px',
      cursor: 'pointer',
      marginBottom: '20px',
    },
    card: {
      border: '1px solid #ddd',
      borderRadius: '8px',
      padding: '15px',
      marginBottom: '15px',
      backgroundColor: '#f9f9f9',
    },
    userCard: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      border: '1px solid #ddd',
      borderRadius: '8px',
      padding: '15px',
      marginBottom: '15px',
      backgroundColor: '#f9f9f9',
      flexWrap: 'wrap' as const,
    },
    userInfo: {
      flex: 1,
    },
    userActions: {
      display: 'flex',
      gap: '10px',
      marginTop: '10px',
    },
    approveBtn: {
      padding: '6px 12px',
      backgroundColor: '#28a745',
      color: 'white',
      border: 'none',
      borderRadius: '4px',
      cursor: 'pointer',
    },
    rejectBtn: {
      padding: '6px 12px',
      backgroundColor: '#dc3545',
      color: 'white',
      border: 'none',
      borderRadius: '4px',
      cursor: 'pointer',
    },
    loading: {
      textAlign: 'center' as const,
      padding: '50px',
    },
    welcome: {
      marginBottom: '20px',
      padding: '15px',
      backgroundColor: '#e8f4fd',
      borderRadius: '8px',
      color: '#666',
    },
    error: {
      marginTop: '15px',
      padding: '10px',
      borderRadius: '4px',
      textAlign: 'center' as const,
      backgroundColor: '#f8d7da',
      color: '#721c24',
      border: '1px solid #f5c6cb',
    },
    modal: {
      overlay: {
        position: 'fixed' as const,
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
      },
      content: {
        backgroundColor: 'white',
        padding: '20px',
        borderRadius: '8px',
        width: '400px',
        maxWidth: '90%',
      },
      input: {
        width: '100%',
        padding: '8px',
        margin: '10px 0',
        border: '1px solid #ccc',
        borderRadius: '4px',
        fontSize: '16px',
      },
      button: {
        padding: '8px 16px',
        margin: '5px',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
      },
      confirmBtn: {
        backgroundColor: '#007bff',
        color: 'white',
      },
      cancelBtn: {
        backgroundColor: '#6c757d',
        color: 'white',
      },
    },
  };

  if (chargement) {
    return <div style={styles.loading}>Chargement...</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>📊 Dashboard</h1>
        <button onClick={handleDeconnexion} style={styles.logoutBtn}>
          Se déconnecter
        </button>
      </div>

      {user && (
        <div style={styles.welcome}>
          <p>Bonjour, <strong>{getNomComplet()}</strong> !</p>
          <p>Email: {user.email}</p>
          <p>Rôle: {getRoleFrancais(user.role)}</p>
        </div>
      )}

      {/* Onglets */}
      <div style={styles.tabs}>
        <button
          style={{ ...styles.tab, ...(ongletActif === 'projets' ? styles.tabActif : {}) }}
          onClick={() => setOngletActif('projets')}
        >
          📁 Projets
        </button>
        <button
          style={{ ...styles.tab, ...(ongletActif === 'utilisateurs' ? styles.tabActif : {}) }}
          onClick={() => setOngletActif('utilisateurs')}
        >
          👥 Utilisateurs
        </button>
      </div>

      {erreur && (
        <div style={styles.error}>
          {erreur}
        </div>
      )}

      {/* Contenu de l'onglet Projets */}
      {ongletActif === 'projets' && (
        <>
          <button onClick={() => setShowModal(true)} style={styles.createBtn}>
            + Créer un projet
          </button>

          {projets.length === 0 ? (
            <p>Aucun projet pour le moment. Cliquez sur "Créer un projet" pour commencer.</p>
          ) : (
            projets.map((projet) => (
              <div key={projet.id} style={styles.card}>
                <h3>{projet.nom}</h3>
                <p>ID: {projet.id}</p>
                <p>Créé le: {projet.date_creation ? new Date(projet.date_creation).toLocaleDateString() : 'Date inconnue'}</p>
              </div>
            ))
          )}
        </>
      )}

      {/* Contenu de l'onglet Utilisateurs */}
      {ongletActif === 'utilisateurs' && (
        <>
          <h3>📋 Demandes d'inscription</h3>
          {utilisateurs.length === 0 ? (
            <p>Aucune demande en attente.</p>
          ) : (
            utilisateurs.map((utilisateur) => (
              <div key={utilisateur.id} style={styles.userCard}>
                <div style={styles.userInfo}>
                  <strong>{utilisateur.prenom} {utilisateur.nom}</strong>
                  <p>Email: {utilisateur.email}</p>
                  <p>Rôle: {getRoleFrancais(utilisateur.role)}</p>
                  <p>Statut: {getStatutFrancais(utilisateur.statut)}</p>
                  <p>Inscrit le: {new Date(utilisateur.date_creation).toLocaleDateString()}</p>
                </div>
                {utilisateur.statut === 'en_attente' && (
                  <div style={styles.userActions}>
                    <button
                      onClick={() => handleApprouverUtilisateur(utilisateur.id)}
                      style={styles.approveBtn}
                    >
                      ✅ Approuver
                    </button>
                    <button
                      onClick={() => handleRefuserUtilisateur(utilisateur.id)}
                      style={styles.rejectBtn}
                    >
                      ❌ Refuser
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </>
      )}

      {/* Modal de création de projet */}
      {showModal && (
        <div style={styles.modal.overlay}>
          <div style={styles.modal.content}>
            <h3>Créer un nouveau projet</h3>
            <input
              type="text"
              placeholder="Nom du projet"
              value={nouveauProjet}
              onChange={(e) => setNouveauProjet(e.target.value)}
              style={styles.modal.input}
            />
            <div style={{ textAlign: 'right', marginTop: '15px' }}>
              <button
                onClick={() => setShowModal(false)}
                style={{ ...styles.modal.button, ...styles.modal.cancelBtn }}
              >
                Annuler
              </button>
              <button
                onClick={handleCreerProjet}
                disabled={creationEnCours}
                style={{ ...styles.modal.button, ...styles.modal.confirmBtn }}
              >
                {creationEnCours ? 'Création...' : 'Créer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;