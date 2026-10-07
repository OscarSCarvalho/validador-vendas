import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import "./estilo.css";
import App from "./App.jsx";
import { UsuarioProvedor } from "./contexto/UsuarioContexto.jsx";

createRoot(document.getElementById("raiz")).render(
  <StrictMode>
    <BrowserRouter>
      <UsuarioProvedor>
        <App />
      </UsuarioProvedor>
    </BrowserRouter>
  </StrictMode>
);
