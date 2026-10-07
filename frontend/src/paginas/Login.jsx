import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { entrar } from "../api.js";
import CampoSenha from "../componentes/CampoSenha.jsx";
import { IconeEnvelope } from "../componentes/Icones.jsx";
import LayoutAutenticacao from "../componentes/LayoutAutenticacao.jsx";
import ListaErros from "../componentes/ListaErros.jsx";
import { useUsuario } from "../contexto/UsuarioContexto.jsx";

export default function Login() {
  const { usuario, setUsuario } = useUsuario();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erros, setErros] = useState([]);
  const [enviando, setEnviando] = useState(false);
  const navegar = useNavigate();
  const voltarPara = useLocation().state?.voltarPara ?? "/produtos";

  if (usuario) return <Navigate to={voltarPara} replace />;

  async function aoEnviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    try {
      setUsuario(await entrar(email, senha));
      navegar(voltarPara, { replace: true });
    } catch (erro) {
      setErros(erro.erros);
      setEnviando(false);
    }
  }

  return (
    <LayoutAutenticacao titulo="Entrar" subtitulo="Acesse sua conta para continuar.">
      <ListaErros erros={erros} />
      <form onSubmit={aoEnviar}>
        <div className="mb-3">
          <label htmlFor="email" className="form-label">E-mail</label>
          <div className="campo-com-icone">
            <IconeEnvelope className="icone-campo" />
            <input type="email" className="form-control form-control-lg com-icone-esquerda" id="email"
                   value={email} onChange={(e) => setEmail(e.target.value)}
                   placeholder="seu@email.com" required autoFocus autoComplete="email" />
          </div>
        </div>
        <div className="mb-4">
          <label htmlFor="senha" className="form-label">Senha</label>
          <CampoSenha id="senha" valor={senha} aoMudar={setSenha} required autoComplete="current-password" />
        </div>
        <button type="submit" className="btn btn-primary btn-lg w-100" disabled={enviando}>
          {enviando ? "Entrando..." : "Entrar"}
        </button>
      </form>
      <p className="mt-4 mb-0 text-center">
        Ainda não tem conta? <Link to="/cadastro">Cadastre-se</Link>
      </p>
    </LayoutAutenticacao>
  );
}
