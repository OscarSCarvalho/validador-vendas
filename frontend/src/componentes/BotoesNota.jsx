/** Botões de nota de 1 a 5. Com `bloqueado`, só mostra a nota (ex.: margem automática). */
export default function BotoesNota({ rotulo, valor, aoMudar, bloqueado = false }) {
  return (
    <div className="btn-group w-100" role="group" aria-label={rotulo}>
      {[1, 2, 3, 4, 5].map((nota) => (
        <button key={nota} type="button" disabled={bloqueado}
                className={`btn ${valor === nota ? "btn-primary" : "btn-outline-primary"}`}
                aria-pressed={valor === nota} onClick={() => aoMudar(nota)}>
          {nota}
        </button>
      ))}
    </div>
  );
}
