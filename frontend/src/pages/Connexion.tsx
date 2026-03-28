import { useState } from 'react';
import { authService } from '../api/api';
import { useNavigate } from 'react-router-dom';

function Connexion() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    mot_de_passe: '',
  });
  const [erreur, setErreur] = useState('');
  const [chargement, setChargement] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErreur('');
    setChargement(true);

    try {
      const response = await authService.connexion(formData);
      console.log('✅ Connexion réussie:', response.data);

      // Stocker le token JWT
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
        console.log('🔐 Token stocké');
      }

      // Construire et stocker les informations utilisateur
      // Le backend retourne: { access_token, token_type, role }
      const userData = {
        email: formData.email,
        role: response.data.role || 'utilisateur',
        // Nom temporaire à partir de l'email (avant le @)
        nom: formData.email.split('@')[0],
        prenom: '',
      };

      localStorage.setItem('user', JSON.stringify(userData));
      console.log('👤 Utilisateur stocké:', userData);

      // Rediriger vers le dashboard
      navigate('/dashboard');
    } catch (error: any) {
      console.error('❌ Erreur de connexion:', error);
      const messageErreur = error.response?.data?.detail ||
                            error.response?.data?.message ||
                            'Email ou mot de passe incorrect';
      setErreur(`❌ ${messageErreur}`);
    } finally {
      setChargement(false);
    }
  };

  const styles = {
    container: {
      maxWidth: '400px',
      margin: '50px auto',
      padding: '20px',
      border: '1px solid #ddd',
      borderRadius: '8px',
      fontFamily: 'Arial, sans-serif',
    },
    title: {
      textAlign: 'center' as const,
      marginBottom: '20px',
    },
    formGroup: {
      marginBottom: '15px',
    },
    label: {
      display: 'block',
      marginBottom: '5px',
      fontWeight: 'bold' as const,
    },
    input: {
      width: '100%',
      padding: '8px',
      border: '1px solid #ccc',
      borderRadius: '4px',
      fontSize: '16px',
    },
    button: {
      width: '100%',
      padding: '10px',
      backgroundColor: '#28a745',
      color: 'white',
      border: 'none',
      borderRadius: '4px',
      fontSize: '16px',
      cursor: 'pointer',
    },
    buttonDisabled: {
      backgroundColor: '#ccc',
      cursor: 'not-allowed',
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
    link: {
      textAlign: 'center' as const,
      marginTop: '15px',
    },
    linkText: {
      color: '#007bff',
      textDecoration: 'none',
    },
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Connexion</h2>
      <form onSubmit={handleSubmit}>
        <div style={styles.formGroup}>
          <label style={styles.label}>Email :</label>
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
            style={styles.input}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Mot de passe :</label>
          <input
            type="password"
            name="mot_de_passe"
            value={formData.mot_de_passe}
            onChange={handleChange}
            required
            style={styles.input}
          />
        </div>

        <button
          type="submit"
          disabled={chargement}
          style={{
            ...styles.button,
            ...(chargement ? styles.buttonDisabled : {}),
          }}
        >
          {chargement ? 'Connexion en cours...' : 'Se connecter'}
        </button>
      </form>

      {erreur && (
        <div style={styles.error}>
          {erreur}
        </div>
      )}

      <div style={styles.link}>
        <a href="/inscription" style={styles.linkText}>
          Pas encore de compte ? S'inscrire
        </a>
      </div>
    </div>
  );
}

export default Connexion;