import { NavLink } from 'react-router-dom';

// ============================================================
// SECTION 1 — COMPOSANT HEADER
// Navigation minimaliste — même largeur que .container
// ============================================================

interface PropsHeader {
  titre: string;
}

export default function Header({ titre }: PropsHeader) {

  const userRole      = localStorage.getItem('user_role') ?? '';
  const userEmail     = localStorage.getItem('user_email') ?? '';
  const estSuperAdmin = userRole === 'super_admin';

  function seDeconnecter() {
    localStorage.removeItem('token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_email');
    window.location.href = '/connexion';
  }

  return (
    <div style={styles.wrapper}>
      <header style={styles.header}>

        {/* Titre de la page */}
        <span style={styles.logo}>
          {titre}
        </span>

        {/* Navigation */}
        <nav style={styles.nav}>
          <NavLink
            to="/projets"
            className={({ isActive }: { isActive: boolean }) =>
              isActive ? 'nav-lien nav-lien-actif' : 'nav-lien'
            }
          >
            Projets
          </NavLink>

          <NavLink
            to="/keynotes"
            className={({ isActive }: { isActive: boolean }) =>
              isActive ? 'nav-lien nav-lien-actif' : 'nav-lien'
            }
          >
            Keynotes
          </NavLink>

          {estSuperAdmin && (
            <NavLink
              to="/utilisateurs"
              className={({ isActive }: { isActive: boolean }) =>
                isActive ? 'nav-lien nav-lien-actif' : 'nav-lien'
              }
            >
              Utilisateurs
            </NavLink>
          )}
        </nav>

        {/* Utilisateur + Déconnexion */}
        <div style={styles.userZone}>
          <span style={styles.userEmail}>{userEmail}</span>
          <span
            style={styles.lienDeconnexion}
            onClick={seDeconnecter}
          >
            Déconnexion
          </span>
        </div>

      </header>
    </div>
  );
}

// ============================================================
// SECTION 2 — STYLES
// Même contraintes que .container : max-width 1400px, centré
// ============================================================

const styles: Record<string, React.CSSProperties> = {

  wrapper: {
    width          : '100%',
    backgroundColor: '#fff',
    borderBottom   : '1px solid #e0e0e0',
    boxShadow      : '0 1px 3px rgba(0,0,0,0.08)',
    marginBottom   : '16px',
  },

  header: {
    maxWidth      : '1400px',
    width         : '100%',
    margin        : '0 auto',
    padding       : '0 32px',
    height        : '54px',
    display       : 'flex',
    alignItems    : 'center',
    justifyContent: 'space-between',
  },

  logo: {
    fontSize     : '18px',
    fontWeight   : 700,
    color        : '#090ea0',
    letterSpacing: '0.3px',
    whiteSpace   : 'nowrap',
  },

  nav: {
    display   : 'flex',
    gap       : '24px',
    alignItems: 'center',
  },

  userZone: {
    display   : 'flex',
    alignItems: 'center',
    gap       : '16px',
  },

  userEmail: {
    fontSize    : '13px',
    color       : '#777',
    maxWidth    : '200px',
    overflow    : 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace  : 'nowrap',
  },

  lienDeconnexion: {
    fontSize      : '13px',
    fontWeight    : 500,
    color         : '#d93025',
    cursor        : 'pointer',
    textDecoration: 'underline',
  },

};
