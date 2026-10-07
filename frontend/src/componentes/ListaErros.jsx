/** Mostra a lista de erros devolvida pela API. */
export default function ListaErros({ erros }) {
  if (!erros.length) return null;
  return (
    <div className="alert alert-danger" role="alert">
      {erros.length === 1 ? erros[0] : (
        <ul className="mb-0 ps-3">{erros.map((erro) => <li key={erro}>{erro}</li>)}</ul>
      )}
    </div>
  );
}
