import { useState } from 'react';
import { authService } from '../api/api';

function Inscription() {
  const [formData, setFormData] = useState({
    nom: '',
    prenom: '',
    email: '',
    mot_de_passe: '',
    confirmer_mot_de_passe: '',
  });

  const [message, setMessage] = useState('');
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
    setMessage('');
    setChargement(true);

    if (formData.mot_de_passe !== formData.confirmer_mot_de_passe) {
      setErreur('Les mots de passe ne correspondent pas');
      setChargement(false);
      return;
    }

    try {
      const response = await authService.inscription(formData);
      console.log('Réponse:', response.data);
      setMessage('✅ Inscription réussie ! Votre compte est en attente d\'approbation.');
      setFormData({
        nom: '',
        prenom: '',
        email: '',
        mot_de_passe: '',
        confirmer_mot_de_passe: '',
      });
    } catch (error: any) {
      console.error('Erreur:', error);
      const messageErreur = error.response?.data?.detail || 'Erreur lors de l\'inscription';
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
      backgroundColor: '#007bff',
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
    message: {
      marginTop: '15px',
      padding: '10px',
      borderRadius: '4px',
      textAlign: 'center' as const,
    },
    success: {
      backgroundColor: '#d4edda',
      color: '#155724',
      border: '1px solid #c3e6cb',
    },
    error: {
      backgroundColor: '#f8d7da',
      color: '#721c24',
      border: '1px solid #f5c6cb',
    },
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Inscription</h2>
      <form onSubmit={handleSubmit}>
        <div style={styles.formGroup}>
          <label style={styles.label}>Nom :</label>
          <input
            type="text"
            name="nom"
            value={formData.nom}
            onChange={handleChange}
            required
            style={styles.input}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Prénom :</label>
          <input
            type="text"
            name="prenom"
            value={formData.prenom}
            onChange={handleChange}
            required
            style={styles.input}
          />
        </div>

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

        <div style={styles.formGroup}>
          <label style={styles.label}>Confirmer le mot de passe :</label>
          <input
            type="password"
            name="confirmer_mot_de_passe"
            value={formData.confirmer_mot_de_passe}
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
          {chargement ? 'Inscription en cours...' : "S'inscrire"}
        </button>
      </form>

      {message && (
        <div style={{ ...styles.message, ...styles.success }}>
          {message}
        </div>
      )}

      {erreur && (
        <div style={{ ...styles.message, ...styles.error }}>
          {erreur}
        </div>
      )}
    </div>
  );
}

export default Inscription;