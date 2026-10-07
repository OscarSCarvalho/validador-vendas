import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { sair } from "../api.js";
import { useUsuario } from "../contexto/UsuarioContexto.jsx";

export default function Layout() {
  const { usuario, setUsuario } = useUsuario();
  const [menuAberto, setMenuAberto] = useState(false);
  const navegar = useNavigate();

  async function aoSair() {
    await sair().catch(() => {});
    setUsuario(null);
    navegar("/login", { replace: true });
  }

  const classeLink = ({ isActive }) => `nav-link${isActive ? " active" : ""}`;

  return (
    <>
      <nav className="navbar navbar-expand-md navbar-dark bg-dark">
        <div className="container">
          <Link className="navbar-brand" to="/produtos">Validador de Vendas</Link>
          <button className="navbar-toggler" type="button" aria-controls="menu"
                  aria-expanded={menuAberto} aria-label="Abrir menu"
                  onClick={() => setMenuAberto(!menuAberto)}>
            <span className="navbar-toggler-icon"></span>
          </button>
          <div className={`collapse navbar-collapse${menuAberto ? " show" : ""}`} id="menu">
            <ul className="navbar-nav me-auto" onClick={() => setMenuAberto(false)}>
              <li className="nav-item"><NavLink className={classeLink} to="/produtos">Produtos</NavLink></li>
              <li className="nav-item"><NavLink className={classeLink} to="/painel">Painel</NavLink></li>
            </ul>
            <div className="d-flex align-items-center gap-2 py-2 py-md-0">
              <span className="navbar-text small">Olá, {usuario.nome}</span>
              <button className="btn btn-outline-light btn-sm" type="button" onClick={aoSair}>Sair</button>
            </div>
          </div>
        </div>
      </nav>
      <main className="container py-4">
        <Outlet />
      </main>
    </>
  );
}
