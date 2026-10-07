import { IconeCheck } from "./Icones.jsx";

const RECURSOS = [
  "Pontuação do produto em 5 critérios, com veredito",
  "Validação manual guiada em 8 etapas, com gerador de links UTM",
  "Teste de venda com funil, CTR, conversão, CPA e lucro",
  "Painel comparativo para ver qual produto dá mais lucro",
  "Importação de CSV e integração com Nuvemshop e Shopify",
];

/** Telas de login e cadastro: faixa azul com o nome e os recursos à esquerda, formulário à direita.
 *  No celular, a faixa vira um topo curto (sem a lista de recursos). */
export default function LayoutAutenticacao({ titulo, subtitulo, children }) {
  return (
    <main className="container-fluid p-0 bg-white">
      <div className="row g-0 min-vh-100 linha-login">
        <section className="col-12 col-lg-6 painel-login d-flex align-items-center">
          <div className="px-4 py-4 py-lg-5 px-lg-5 mx-auto" style={{ maxWidth: "34rem" }}>
            <h1 className="fw-bold mb-2 fs-2">Validador de Vendas</h1>
            <p className="mb-0 mb-lg-4 opacity-75">
              Descubra se um produto vale a pena antes de investir pesado: primeiro valide à mão, depois automatize.
            </p>
            <ul className="list-unstyled lista-recursos mb-0 d-none d-lg-block">
              {RECURSOS.map((recurso) => (
                <li key={recurso} className="d-flex align-items-start gap-2">
                  <IconeCheck tamanho={20} className="flex-shrink-0 mt-1" />
                  <span>{recurso}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="col-12 col-lg-6 bg-white d-flex align-items-center justify-content-center">
          <div className="formulario-login px-4 py-5">
            <h2 className="h3 fw-bold mb-1">{titulo}</h2>
            <p className="text-muted mb-4">{subtitulo}</p>
            {children}
          </div>
        </section>
      </div>
    </main>
  );
}
