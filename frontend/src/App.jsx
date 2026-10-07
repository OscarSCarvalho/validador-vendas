import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./componentes/Layout.jsx";
import RotaProtegida from "./componentes/RotaProtegida.jsx";
import Cadastro from "./paginas/Cadastro.jsx";
import ImportarCsv from "./paginas/ImportarCsv.jsx";
import ListaProdutos from "./paginas/ListaProdutos.jsx";
import Login from "./paginas/Login.jsx";
import Painel from "./paginas/Painel.jsx";
import Pontuacao from "./paginas/Pontuacao.jsx";
import Produto from "./paginas/Produto.jsx";
import TestesProduto from "./paginas/TestesProduto.jsx";
import TesteVenda from "./paginas/TesteVenda.jsx";
import Validacao from "./paginas/Validacao.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/cadastro" element={<Cadastro />} />
      <Route element={<RotaProtegida />}>
        <Route element={<Layout />}>
          <Route path="/produtos" element={<ListaProdutos />} />
          <Route path="/produtos/novo" element={<Produto />} />
          <Route path="/produtos/:id/editar" element={<Produto />} />
          <Route path="/produtos/:id/pontuacao" element={<Pontuacao />} />
          <Route path="/produtos/:id/validacao" element={<Validacao />} />
          <Route path="/produtos/:id/testes" element={<TestesProduto />} />
          <Route path="/testes/:id" element={<TesteVenda />} />
          <Route path="/testes/:id/importar" element={<ImportarCsv />} />
          <Route path="/painel" element={<Painel />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/produtos" replace />} />
    </Routes>
  );
}
