import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Accueil from './pages/Accueil';
import Inscription from './pages/Inscription';
import Connexion from './pages/Connexion';
import Dashboard from './pages/Dashboard';

function App() {
  const styles = {
    nav: {
      padding: '10px 20px',
      backgroundColor: '#f8f9fa',
      borderBottom: '1px solid #ddd',
      display: 'flex',
      gap: '20px',
    },
    link: {
      textDecoration: 'none',
      color: '#007bff',
    },
  };

  return (
    <BrowserRouter>
      <nav style={styles.nav}>
        <Link to="/" style={styles.link}>Accueil</Link>
        <Link to="/inscription" style={styles.link}>Inscription</Link>
        <Link to="/connexion" style={styles.link}>Connexion</Link>
      </nav>

      <Routes>
        <Route path="/" element={<Accueil />} />
        <Route path="/inscription" element={<Inscription />} />
        <Route path="/connexion" element={<Connexion />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;