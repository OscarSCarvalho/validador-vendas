import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useUsuario } from "../contexto/UsuarioContexto.jsx";

/** Sem login, leva para /login e volta para a página pedida depois de entrar. */
export default function RotaProtegida() {
  const { usuario, carregando } = useUsuario();
  const local = useLocation();

  if (carregando) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-secondary" role="status">
          <span className="visually-hidden">Carregando...</span>
        </div>
      </div>
    );
  }
  if (!usuario) {
    return <Navigate to="/login" replace state={{ voltarPara: local.pathname }} />;
  }
  return <Outlet />;
}
