import { Link } from 'react-router-dom';

function Accueil() {
  const styles = {
    container: {
      textAlign: 'center' as const,
      padding: '50px',
      fontFamily: 'Arial, sans-serif',
    },
    title: {
      fontSize: '2.5rem',
      marginBottom: '20px',
    },
    description: {
      fontSize: '1.2rem',
      marginBottom: '30px',
      color: '#666',
    },
    links: {
      display: 'flex',
      gap: '20px',
      justifyContent: 'center',
    },
    link: {
      padding: '10px 20px',
      backgroundColor: '#007bff',
      color: 'white',
      textDecoration: 'none',
      borderRadius: '5px',
      fontSize: '1rem',
    },
    linkSecondary: {
      backgroundColor: '#28a745',
    },
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>🏠 DMA Keynotes Manager</h1>
      <p style={styles.description}>
        Bienvenue sur l'application de gestion de keynotes pour Revit
      </p>
      <div style={styles.links}>
        <Link to="/inscription" style={styles.link}>
          S'inscrire
        </Link>
        <Link to="/connexion" style={{ ...styles.link, ...styles.linkSecondary }}>
          Se connecter
        </Link>
      </div>
    </div>
  );
}

export default Accueil;