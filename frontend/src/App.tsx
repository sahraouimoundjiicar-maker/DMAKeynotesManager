import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Connexion    from './pages/Connexion';
import Projets      from './pages/Projets';
import Utilisateurs from './pages/Utilisateurs';
import Keynotes     from './pages/Keynotes';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"             element={<Connexion />} />
        <Route path="/connexion"    element={<Connexion />} />
        <Route path="/projets"      element={<Projets />} />
        <Route path="/utilisateurs" element={<Utilisateurs />} />
        <Route path="/keynotes"     element={<Keynotes />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
