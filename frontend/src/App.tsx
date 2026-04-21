import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import Connexion    from './pages/Connexion';
import Projets      from './pages/Projets';
import Utilisateurs from './pages/Utilisateurs';
import Keynotes     from './pages/Keynotes';
import Header       from './components/Header';

// Pages qui affichent le header
const PAGES_AVEC_HEADER = ['/projets', '/utilisateurs', '/keynotes'];

function Layout() {
  const location        = useLocation();
  const afficherHeader  = PAGES_AVEC_HEADER.includes(location.pathname);

  return (
    <>
      {afficherHeader && <Header />}
      <Routes>
        <Route path="/"             element={<Connexion />} />
        <Route path="/connexion"    element={<Connexion />} />
        <Route path="/projets"      element={<Projets />} />
        <Route path="/utilisateurs" element={<Utilisateurs />} />
        <Route path="/keynotes"     element={<Keynotes />} />
      </Routes>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Layout />
    </BrowserRouter>
  );
}

export default App;