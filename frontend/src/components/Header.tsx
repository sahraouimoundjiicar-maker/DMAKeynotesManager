import { NavLink } from 'react-router-dom';

// ============================================================
// SECTION 1 — COMPOSANT HEADER
// Navigation minimaliste — même largeur que .container
// ============================================================

export default function Header() {

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

        {/* Logo */}
        <span style={styles.logo}>
          DMA Keynote Manager
        </span>

        {/* Navigation */}
        <nav style={styles.nav}>
          <NavLink
            to="/projets"
            style={({ isActive }) => ({
              ...styles.lien,
              ...(isActive ? styles.lienActif : {}),
            })}
          >
            Projets
          </NavLink>

          <NavLink
            to="/keynotes"
            style={({ isActive }) => ({
              ...styles.lien,
              ...(isActive ? styles.lienActif : {}),
            })}
          >
            Keynotes
          </NavLink>

          {estSuperAdmin && (
            <NavLink
              to="/utilisateurs"
              style={({ isActive }) => ({
                ...styles.lien,
                ...(isActive ? styles.lienActif : {}),
              })}
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
    gap       : '4px',
    alignItems: 'center',
  },

  lien: {
    padding       : '6px 16px',
    fontSize      : '14px',
    fontWeight    : 500,
    color         : '#555',
    textDecoration: 'none',
    borderRadius  : '6px',
    transition    : 'background 0.15s, color 0.15s',
  },

  lienActif: {
    color          : '#090ea0',
    backgroundColor: '#e8eaf6',
    fontWeight     : 600,
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
