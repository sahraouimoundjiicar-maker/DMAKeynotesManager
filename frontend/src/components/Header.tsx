import { useNavigate, useLocation } from 'react-router-dom';

// ============================================================
// SECTION 1 — COMPOSANT HEADER
// Navigation minimaliste commune aux pages protégées.
// Affiche : logo | navigation | utilisateur + déconnexion
// ============================================================

export default function Header() {
  const navigate  = useNavigate();
  const location  = useLocation();

  // Récupérer les infos de l'utilisateur connecté
  const userRole  = localStorage.getItem('user_role') ?? '';
  const userEmail = localStorage.getItem('user_email') ?? '';
  const estSuperAdmin = userRole === 'super_admin';

  // Déconnexion — vider le localStorage et rediriger
  function seDeconnecter() {
    localStorage.removeItem('token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_email');
    navigate('/connexion');
  }

  // Vérifier si un lien est actif
  function estActif(chemin: string): boolean {
    return location.pathname === chemin;
  }

  return (
    <header style={styles.header}>

      {/* Logo / Nom de l'application */}
      <div style={styles.logo}>
        DMA<span style={styles.logoAccent}>Keynotes</span>
      </div>

      {/* Navigation centrale */}
      <nav style={styles.nav}>
        <button
          style={{
            ...styles.navLink,
            ...(estActif('/projets') ? styles.navLinkActif : {}),
          }}
          onClick={() => navigate('/projets')}
        >
          Projets
        </button>

        {/* Keynotes — visible par tous */}
        <button
          style={{
            ...styles.navLink,
            ...(estActif('/keynotes') ? styles.navLinkActif : {}),
          }}
          onClick={() => navigate('/keynotes')}
        >
          Keynotes
        </button>

        {/* Utilisateurs — visible uniquement par le super_admin */}
        {estSuperAdmin && (
          <button
            style={{
              ...styles.navLink,
              ...(estActif('/utilisateurs') ? styles.navLinkActif : {}),
            }}
            onClick={() => navigate('/utilisateurs')}
          >
            Utilisateurs
          </button>
        )}
      </nav>

      {/* Utilisateur connecté + Déconnexion */}
      <div style={styles.userZone}>
        <span style={styles.userEmail}>{userEmail}</span>
        <button style={styles.btnDeconnexion} onClick={seDeconnecter}>
          Déconnexion
        </button>
      </div>

    </header>
  );
}

// ============================================================
// SECTION 2 — STYLES
// ============================================================

const styles: Record<string, React.CSSProperties> = {

  header: {
    display        : 'flex',
    alignItems     : 'center',
    justifyContent : 'space-between',
    height         : '54px',
    padding        : '0 24px',
    backgroundColor: '#fff',
    borderBottom   : '1px solid #e0e0e0',
    boxShadow      : '0 1px 3px rgba(0,0,0,0.08)',
    position       : 'sticky',
    top            : 0,
    zIndex         : 100,
  },

  logo: {
    fontSize  : '18px',
    fontWeight: 700,
    color     : '#333',
    letterSpacing: '0.3px',
  },

  logoAccent: {
    color: '#090ea0',
  },

  nav: {
    display: 'flex',
    gap    : '4px',
  },

  navLink: {
    padding         : '6px 16px',
    fontSize        : '14px',
    fontWeight      : 500,
    color           : '#555',
    background      : 'none',
    border          : 'none',
    borderRadius    : '6px',
    cursor          : 'pointer',
    transition      : 'background 0.15s, color 0.15s',
  },

  navLinkActif: {
    color          : '#090ea0',
    backgroundColor: '#e8f0fe',
    fontWeight     : 600,
  },

  userZone: {
    display   : 'flex',
    alignItems: 'center',
    gap       : '12px',
  },

  userEmail: {
    fontSize : '13px',
    color    : '#777',
    maxWidth : '200px',
    overflow : 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace  : 'nowrap',
  },

  btnDeconnexion: {
    padding         : '6px 14px',
    fontSize        : '13px',
    fontWeight      : 500,
    color           : '#d93025',
    background      : 'none',
    border          : '1px solid #d93025',
    borderRadius    : '6px',
    cursor          : 'pointer',
    transition      : 'background 0.15s, color 0.15s',
  },

};
