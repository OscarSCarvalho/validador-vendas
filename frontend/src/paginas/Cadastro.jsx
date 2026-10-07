import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { cadastrar } from "../api.js";
import CampoSenha from "../componentes/CampoSenha.jsx";
import { IconeEnvelope, IconePessoa } from "../componentes/Icones.jsx";
import LayoutAutenticacao from "../componentes/LayoutAutenticacao.jsx";
import ListaErros from "../componentes/ListaErros.jsx";
import { useUsuario } from "../contexto/UsuarioContexto.jsx";

export default function Cadastro() {
  const { usuario, setUsuario } = useUsuario();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erros, setErros] = useState([]);
  const [enviando, setEnviando] = useState(false);

  // Depois do cadastro o backend já inicia a sessão; com o usuário definido, vai para Produtos.
  if (usuario) return <Navigate to="/produtos" replace />;

  async function aoEnviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    try {
      setUsuario(await cadastrar(nome, email, senha));
    } catch (erro) {
      setErros(erro.erros);
      setEnviando(false);
    }
  }

  return (
    <LayoutAutenticacao titulo="Criar conta" subtitulo="Comece a validar seus produtos.">
      <ListaErros erros={erros} />
      <form onSubmit={aoEnviar}>
        <div className="mb-3">
          <label htmlFor="nome" className="form-label">Nome</label>
          <div className="campo-com-icone">
            <IconePessoa className="icone-campo" />
            <input type="text" className="form-control form-control-lg com-icone-esquerda" id="nome"
                   value={nome} onChange={(e) => setNome(e.target.value)}
                   placeholder="Seu nome" required autoFocus autoComplete="name" />
          </div>
        </div>
        <div className="mb-3">
          <label htmlFor="email" className="form-label">E-mail</label>
          <div className="campo-com-icone">
            <IconeEnvelope className="icone-campo" />
            <input type="email" className="form-control form-control-lg com-icone-esquerda" id="email"
                   value={email} onChange={(e) => setEmail(e.target.value)}
                   placeholder="seu@email.com" required autoComplete="email" />
          </div>
        </div>
        <div className="mb-4">
          <label htmlFor="senha" className="form-label">Senha</label>
          <CampoSenha id="senha" valor={senha} aoMudar={setSenha} minLength={6} required
                      autoComplete="new-password" aria-describedby="ajuda-senha" />
          <div id="ajuda-senha" className="form-text">Mínimo de 6 caracteres.</div>
        </div>
        <button type="submit" className="btn btn-primary btn-lg w-100" disabled={enviando}>
          {enviando ? "Cadastrando..." : "Cadastrar"}
        </button>
      </form>
      <p className="mt-4 mb-0 text-center">
        Já tem conta? <Link to="/login">Entrar</Link>
      </p>
    </LayoutAutenticacao>
  );
}
