import { NavLink } from 'react-router-dom';

// ============================================================
// SECTION 1 — COMPOSANT HEADER
// Style sobre et léger — dashboard SaaS minimaliste
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
        <span style={styles.logo}>{titre}</span>

        {/* Navigation centrale */}
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
          <span style={styles.separateur}>·</span>
          <span
            style={styles.lienDeconnexion}
            onClick={seDeconnecter}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#333')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#999')}
          >
            Déconnexion
          </span>
        </div>

      </header>
    </div>
  );
}

// ============================================================
// SECTION 2 — STYLES INLINE
// ============================================================

const styles: Record<string, React.CSSProperties> = {

  wrapper: {
    width          : '100%',
    backgroundColor: '#fff',
    borderBottom   : '1px solid #f0f0f0',
    marginBottom   : '16px',
  },

  header: {
    maxWidth      : '1400px',
    width         : '100%',
    margin        : '0 auto',
    padding       : '0 32px',
    height        : '48px',
    display       : 'flex',
    alignItems    : 'center',
    justifyContent: 'space-between',
  },

  logo: {
    fontSize     : '15px',
    fontWeight   : 600,
    color        : '#222',
    letterSpacing: '0.2px',
    whiteSpace   : 'nowrap',
  },

  nav: {
    display   : 'flex',
    gap       : '32px',
    alignItems: 'center',
  },

  userZone: {
    display   : 'flex',
    alignItems: 'center',
    gap       : '8px',
  },

  userEmail: {
    fontSize    : '12px',
    color       : '#aaa',
    maxWidth    : '180px',
    overflow    : 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace  : 'nowrap',
  },

  separateur: {
    fontSize: '12px',
    color   : '#ddd',
  },

  lienDeconnexion: {
    fontSize      : '12px',
    color         : '#999',
    cursor        : 'pointer',
    textDecoration: 'none',
    transition    : 'color 0.15s',
  },

};
