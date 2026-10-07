import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { buscarValidacao, salvarEtapaValidacao } from "../api.js";
import GeradorUtm from "../componentes/GeradorUtm.jsx";
import OrientacaoSubId from "../componentes/OrientacaoSubId.jsx";
import ListaErros from "../componentes/ListaErros.jsx";
import { formatarDataHora } from "../formatar.js";

/** Um cartão do checklist: marcar/desmarcar salva na hora; observação e link salvam no botão. */
function CartaoEtapa({ produtoId, etapa, aoSalvar }) {
  const [observacao, setObservacao] = useState(etapa.observacao);
  const [link, setLink] = useState(etapa.link_evidencia);
  const [salvando, setSalvando] = useState(false);
  const [erros, setErros] = useState([]);
  const [salvo, setSalvo] = useState(false);

  const alterado = observacao !== etapa.observacao || link !== etapa.link_evidencia;

  async function salvar(concluida) {
    setSalvando(true);
    setSalvo(false);
    try {
      const resposta = await salvarEtapaValidacao(produtoId, etapa.etapa, {
        concluida, observacao, link_evidencia: link,
      });
      setErros([]);
      setObservacao(resposta.etapa.observacao);
      setLink(resposta.etapa.link_evidencia);
      setSalvo(true);
      aoSalvar(resposta);
    } catch (erro) {
      setErros(erro.erros);
    } finally {
      setSalvando(false);
    }
  }

  const idBase = `etapa-${etapa.etapa}`;
  return (
    <div className={`card mb-3 ${etapa.concluida ? "border-success" : ""}`}>
      <div className="card-body">
        <div className="form-check mb-1">
          <input className="form-check-input" type="checkbox" id={`${idBase}-concluida`}
                 checked={etapa.concluida} disabled={salvando}
                 onChange={() => salvar(!etapa.concluida)} />
          <label className="form-check-label fw-semibold" htmlFor={`${idBase}-concluida`}>
            {etapa.etapa}. {etapa.titulo}
          </label>
        </div>
        <p className="small text-muted mb-2">{etapa.dica}</p>
        <ListaErros erros={erros} />
        <div className="mb-2">
          <label htmlFor={`${idBase}-observacao`} className="form-label small mb-1">Observação</label>
          <textarea id={`${idBase}-observacao`} className="form-control form-control-sm" rows={2}
                    value={observacao} onChange={(e) => setObservacao(e.target.value)} />
        </div>
        <div className="mb-2">
          <label htmlFor={`${idBase}-link`} className="form-label small mb-1">Link de evidência</label>
          <input id={`${idBase}-link`} type="url" className="form-control form-control-sm"
                 placeholder="https://..." value={link} onChange={(e) => setLink(e.target.value)} />
        </div>
        <div className="d-flex align-items-center gap-2 flex-wrap">
          <button type="button" className="btn btn-sm btn-outline-primary"
                  disabled={salvando || !alterado} onClick={() => salvar(etapa.concluida)}>
            {salvando ? "Salvando..." : "Salvar"}
          </button>
          {etapa.link_evidencia && (
            <a href={etapa.link_evidencia} target="_blank" rel="noopener noreferrer" className="small">
              Abrir evidência
            </a>
          )}
          <span className="small text-muted ms-auto">
            {salvo && !alterado ? "Salvo · " : ""}
            {etapa.atualizado_em ? `Atualizado em ${formatarDataHora(etapa.atualizado_em)}` : ""}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function Validacao() {
  const { id } = useParams();
  const [dados, setDados] = useState(null);
  const [erros, setErros] = useState([]);

  useEffect(() => {
    buscarValidacao(id).then(setDados).catch((erro) => setErros(erro.erros));
  }, [id]);

  function aoSalvarEtapa({ etapa, progresso }) {
    setDados((atual) => ({
      ...atual,
      progresso,
      etapas: atual.etapas.map((e) => (e.etapa === etapa.etapa ? etapa : e)),
    }));
  }

  if (!dados) {
    return (
      <>
        <ListaErros erros={erros} />
        {erros.length ? <Link to="/produtos">Voltar para a lista de produtos</Link>
                      : <p className="text-muted">Carregando...</p>}
      </>
    );
  }

  const { produto, etapas, progresso } = dados;
  const percentual = Math.round((progresso.concluidas / progresso.total) * 100);

  return (
    <>
      <div className="d-flex justify-content-between align-items-start gap-2 mb-3">
        <div>
          <h1 className="h3 mb-1">Validação manual</h1>
          <p className="text-muted mb-0">{produto.nome} · {produto.plataforma}</p>
        </div>
        <Link to="/produtos" className="btn btn-outline-secondary btn-sm">Voltar</Link>
      </div>

      <div className="card card-body shadow-sm mb-4">
        <div className="d-flex justify-content-between small mb-1">
          <span className="fw-semibold">Progresso</span>
          <span>{progresso.concluidas} de {progresso.total} concluídas</span>
        </div>
        <div className="progress" role="progressbar" aria-label="Progresso da validação"
             aria-valuenow={progresso.concluidas} aria-valuemin={0} aria-valuemax={progresso.total}>
          <div className={`progress-bar ${progresso.concluidas === progresso.total ? "bg-success" : ""}`}
               style={{ width: `${percentual}%` }} />
        </div>
      </div>

      <div className="row g-4">
        <div className="col-12 col-lg-7">
          {etapas.map((etapa) => (
            <CartaoEtapa key={etapa.etapa} produtoId={produto.id} etapa={etapa} aoSalvar={aoSalvarEtapa} />
          ))}
        </div>
        <div className="col-12 col-lg-5">
          <div className="card shadow-sm">
            <div className="card-body">
              {produto.modelo === "afiliado" ? (
                <>
                  <h2 className="h5 mb-2">Link de afiliado com Sub_id</h2>
                  <OrientacaoSubId nomeProduto={produto.nome} />
                </>
              ) : (
                <>
                  <h2 className="h5 mb-1">Gerador de link UTM</h2>
                  <p className="small text-muted">
                    Um link para cada canal, para saber de onde vieram as visitas e as vendas.
                  </p>
                  <GeradorUtm urlProduto={produto.url_produto} nomeProduto={produto.nome} />
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
