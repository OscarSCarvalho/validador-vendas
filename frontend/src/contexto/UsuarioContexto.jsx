import { createContext, useContext, useEffect, useState } from "react";
import { buscarUsuarioLogado, definirAoPerderSessao } from "../api.js";

const UsuarioContexto = createContext(null);

export function UsuarioProvedor({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    definirAoPerderSessao(() => setUsuario(null));
    buscarUsuarioLogado()
      .then(setUsuario)
      .catch(() => setUsuario(null))
      .finally(() => setCarregando(false));
  }, []);

  return (
    <UsuarioContexto.Provider value={{ usuario, setUsuario, carregando }}>
      {children}
    </UsuarioContexto.Provider>
  );
}

export function useUsuario() {
  return useContext(UsuarioContexto);
}
