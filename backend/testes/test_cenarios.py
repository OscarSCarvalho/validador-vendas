"""Cenários BDD da Etapa 1, executados contra a API com um banco temporário."""
import io
import json
import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from app import ChaveSecretaAusente, criar_app

PRODUTO_PADRAO = {"nome": "Leitor de código de barras", "plataforma": "Nuvemshop",
                  "url_produto": "https://athos.exemplo.com/leitor",
                  "preco_venda": "200", "custo_unitario": "110"}


class CenarioBase(unittest.TestCase):

    def setUp(self):
        descritor, self.caminho_banco = tempfile.mkstemp(suffix=".db")
        os.close(descritor)
        self.app = criar_app({"TESTING": True, "CAMINHO_BANCO": self.caminho_banco})
        self.cliente = self.app.test_client()

    def tearDown(self):
        os.remove(self.caminho_banco)

    def cadastrar(self, email="oscar@exemplo.com", senha="segredo123", nome="Oscar"):
        return self.cliente.post("/api/auth/cadastro",
                                 json={"nome": nome, "email": email, "senha": senha})

    def cadastrar_produto(self, **campos):
        return self.cliente.post("/api/produtos", json=dict(PRODUTO_PADRAO, **campos))


class TestAutenticacao(CenarioBase):

    def test_cadastro_ja_entra_logado(self):
        """Dado que não tenho conta, Quando me cadastro,
        Então já fico logado com meu nome."""
        resposta = self.cadastrar()
        self.assertEqual(resposta.status_code, 201)
        eu = self.cliente.get("/api/auth/eu")
        self.assertEqual(eu.status_code, 200)
        self.assertEqual(eu.get_json()["nome"], "Oscar")

    def test_cadastro_com_dados_invalidos(self):
        """Dado que não tenho conta, Quando me cadastro sem nome e com senha curta,
        Então vejo os dois erros."""
        resposta = self.cadastrar(nome="", senha="123")
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.get_json()["erros"], [
            "Informe seu nome.", "A senha precisa ter pelo menos 6 caracteres."])

    def test_email_duplicado(self):
        """Dado que já existe conta com um e-mail, Quando tento cadastrar o mesmo e-mail,
        Então vejo 'Este e-mail já está cadastrado'."""
        self.cadastrar()
        resposta = self.cadastrar(nome="Outro")
        self.assertEqual(resposta.status_code, 409)
        self.assertIn("Este e-mail já está cadastrado.", resposta.get_json()["erros"])

    def test_login_e_logout(self):
        """Dado que tenho conta, Quando entro e depois saio,
        Então deixo de ter acesso aos produtos."""
        self.cadastrar()
        self.cliente.post("/api/auth/logout")
        resposta = self.cliente.post("/api/auth/login",
                                     json={"email": "OSCAR@exemplo.com", "senha": "segredo123"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.cliente.get("/api/produtos").status_code, 200)
        self.assertEqual(self.cliente.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.cliente.get("/api/produtos").status_code, 401)

    def test_senha_errada_nao_loga(self):
        """Dado que tenho conta, Quando entro com a senha errada,
        Então vejo 'E-mail ou senha incorretos'."""
        self.cadastrar()
        self.cliente.post("/api/auth/logout")
        resposta = self.cliente.post("/api/auth/login",
                                     json={"email": "oscar@exemplo.com", "senha": "errada"})
        self.assertEqual(resposta.status_code, 401)
        self.assertIn("E-mail ou senha incorretos.", resposta.get_json()["erros"])

    def test_sem_login_recebe_401(self):
        """Dado que não estou logado, Quando peço a lista de produtos,
        Então recebo 401 (o React leva para o Login)."""
        self.assertEqual(self.cliente.get("/api/produtos").status_code, 401)
        self.assertEqual(self.cliente.get("/api/auth/eu").status_code, 401)


class TestProdutos(CenarioBase):

    def setUp(self):
        super().setUp()
        self.cadastrar()

    def test_cadastro_de_produto_mostra_margem(self):
        """Dado que estou logado,
        Quando cadastro um produto com preço 200 e custo 110,
        Então vejo a margem de R$ 90,00 (45%)."""
        resposta = self.cadastrar_produto()
        self.assertEqual(resposta.status_code, 201)
        produto = self.cliente.get("/api/produtos").get_json()[0]
        self.assertEqual(produto["margem_unitaria"], 90)
        self.assertAlmostEqual(produto["margem_percentual"], 0.45)
        self.assertEqual(produto["status"], "ideia")

    def test_preco_com_virgula_e_aceito(self):
        """Dado que estou logado, Quando informo preço '199,90' e custo '100,00',
        Então a margem é R$ 99,90."""
        produto = self.cadastrar_produto(preco_venda="199,90", custo_unitario="100,00").get_json()
        self.assertEqual(produto["margem_unitaria"], 99.9)

    def test_preco_invalido_nao_grava(self):
        """Dado que estou logado, Quando informo preço 0,
        Então vejo um erro e nenhum produto é gravado."""
        resposta = self.cadastrar_produto(preco_venda="0")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("O preço de venda deve ser um número maior que zero.",
                      resposta.get_json()["erros"])
        self.assertEqual(self.cliente.get("/api/produtos").get_json(), [])

    def test_editar_produto_atualiza_margem(self):
        """Dado um produto com preço 200 e custo 110, Quando altero o custo para 150,
        Então a margem passa a R$ 50,00 (25%)."""
        produto_id = self.cadastrar_produto().get_json()["id"]
        resposta = self.cliente.put(f"/api/produtos/{produto_id}",
                                    json=dict(PRODUTO_PADRAO, custo_unitario="150,00"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json()["margem_unitaria"], 50)
        self.assertAlmostEqual(resposta.get_json()["margem_percentual"], 0.25)

    def test_excluir_produto(self):
        """Dado um produto cadastrado, Quando o excluo, Então ele some da lista."""
        produto_id = self.cadastrar_produto().get_json()["id"]
        self.assertEqual(self.cliente.delete(f"/api/produtos/{produto_id}").status_code, 204)
        self.assertEqual(self.cliente.get("/api/produtos").get_json(), [])

    def test_nao_acessa_produto_de_outro_usuario(self):
        """Dado que outro usuário tem um produto, Quando tento vê-lo, editá-lo ou excluí-lo,
        Então recebo 404."""
        produto_id = self.cadastrar_produto().get_json()["id"]
        self.cliente.post("/api/auth/logout")
        self.cadastrar(email="b@exemplo.com")
        url = f"/api/produtos/{produto_id}"
        self.assertEqual(self.cliente.get(url).status_code, 404)
        self.assertEqual(self.cliente.put(url, json=PRODUTO_PADRAO).status_code, 404)
        self.assertEqual(self.cliente.delete(url).status_code, 404)
        self.assertEqual(self.cliente.get("/api/produtos").get_json(), [])

    def test_rota_inexistente_da_api_responde_json(self):
        resposta = self.cliente.get("/api/nao-existe")
        self.assertEqual(resposta.status_code, 404)
        self.assertIn("erros", resposta.get_json())


class TestPontuacao(CenarioBase):

    NOTAS = {"demanda": 4, "concorrencia": 3, "frete": 5, "facilidade_explicar": 4}

    def setUp(self):
        super().setUp()
        self.cadastrar()
        self.produto_id = self.cadastrar_produto().get_json()["id"]  # preço 200, custo 110 (45%)

    def pontuar(self, **notas):
        return self.cliente.post(f"/api/pontuacao/{self.produto_id}", json=dict(self.NOTAS, **notas))

    def test_pontuar_calcula_margem_total_e_veredito(self):
        """Dado o leitor com margem de 45% (nota 4),
        Quando dou demanda 4, concorrência 3, frete 5 e facilidade 4,
        Então o total é 20 de 25 e o veredito é 'Vale testar'."""
        resposta = self.pontuar()
        self.assertEqual(resposta.status_code, 201)
        pontuacao = resposta.get_json()
        self.assertEqual(pontuacao["margem"], 4)
        self.assertEqual(pontuacao["total"], 20)
        self.assertEqual(pontuacao["veredito"], "vale_testar")

    def test_pontuar_muda_status_para_pontuado(self):
        """Dado um produto com status 'ideia', Quando o pontuo, Então o status vira 'pontuado'."""
        self.pontuar()
        produto = self.cliente.get(f"/api/produtos/{self.produto_id}").get_json()
        self.assertEqual(produto["status"], "pontuado")

    def test_margem_enviada_pelo_formulario_e_ignorada(self):
        """Dado um produto com margem de 45% (nota 4), Quando alguém envia margem 1,
        Então o backend usa a nota 4 calculada."""
        self.assertEqual(self.pontuar(margem=1).get_json()["margem"], 4)

    def test_tela_traz_nota_da_margem_antes_de_pontuar(self):
        """Dado um produto ainda sem pontuação, Quando abro a pontuação,
        Então vejo a nota da margem 4 e nenhuma pontuação anterior."""
        dados = self.cliente.get(f"/api/pontuacao/{self.produto_id}").get_json()
        self.assertEqual(dados["nota_margem"], 4)
        self.assertIsNone(dados["ultima"])
        self.assertEqual(dados["historico"], [])

    def test_historico_guarda_todas_as_pontuacoes(self):
        """Dado um produto pontuado com 20, Quando o pontuo de novo com notas 1,
        Então a última é 8 ('Descartar') e o histórico tem as duas."""
        self.pontuar()
        self.pontuar(demanda=1, concorrencia=1, frete=1, facilidade_explicar=1)
        dados = self.cliente.get(f"/api/pontuacao/{self.produto_id}").get_json()
        self.assertEqual(dados["ultima"]["total"], 8)
        self.assertEqual(dados["ultima"]["veredito"], "descartar")
        self.assertEqual([p["total"] for p in dados["historico"]], [8, 20])

    def test_nota_invalida_nao_grava(self):
        """Dado um produto, Quando envio demanda 9 e não envio frete,
        Então vejo os erros e nada é gravado."""
        resposta = self.cliente.post(f"/api/pontuacao/{self.produto_id}",
                                     json={"demanda": 9, "concorrencia": 3, "facilidade_explicar": 4})
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.get_json()["erros"], [
            "Escolha uma nota de 1 a 5 para Demanda.", "Escolha uma nota de 1 a 5 para Frete."])
        self.assertEqual(self.cliente.get(f"/api/pontuacao/{self.produto_id}").get_json()["historico"], [])

    def test_mudar_preco_nao_altera_historico(self):
        """Dado um produto pontuado com margem nota 4, Quando o custo sobe para 190 (5%),
        Então o histórico mantém a nota 4 e a próxima pontuação usa nota 1."""
        self.pontuar()
        self.cliente.put(f"/api/produtos/{self.produto_id}",
                         json=dict(PRODUTO_PADRAO, custo_unitario="190"))
        dados = self.cliente.get(f"/api/pontuacao/{self.produto_id}").get_json()
        self.assertEqual(dados["ultima"]["margem"], 4)
        self.assertEqual(dados["nota_margem"], 1)
        self.assertEqual(self.pontuar().get_json()["margem"], 1)

    def test_excluir_produto_pontuado(self):
        """Dado um produto pontuado, Quando o excluo, Então ele e suas pontuações somem."""
        self.pontuar()
        self.assertEqual(self.cliente.delete(f"/api/produtos/{self.produto_id}").status_code, 204)
        self.assertEqual(self.cliente.get("/api/produtos").get_json(), [])

    def test_nao_pontua_produto_de_outro_usuario(self):
        """Dado que outro usuário tem um produto, Quando tento ver ou pontuar, Então recebo 404."""
        self.cliente.post("/api/auth/logout")
        self.cadastrar(email="b@exemplo.com")
        url = f"/api/pontuacao/{self.produto_id}"
        self.assertEqual(self.cliente.get(url).status_code, 404)
        self.assertEqual(self.cliente.post(url, json=self.NOTAS).status_code, 404)

    def test_sem_login_recebe_401(self):
        self.cliente.post("/api/auth/logout")
        self.assertEqual(self.cliente.get(f"/api/pontuacao/{self.produto_id}").status_code, 401)


class TestValidacaoManual(CenarioBase):

    def setUp(self):
        super().setUp()
        self.cadastrar()
        self.produto_id = self.cadastrar_produto().get_json()["id"]

    def salvar_etapa(self, etapa, **campos):
        dados = {"concluida": True, "observacao": "", "link_evidencia": ""}
        dados.update(campos)
        return self.cliente.put(f"/api/validacao/{self.produto_id}/{etapa}", json=dados)

    def checklist(self):
        return self.cliente.get(f"/api/validacao/{self.produto_id}").get_json()

    def status_do_produto(self):
        return self.cliente.get(f"/api/produtos/{self.produto_id}").get_json()["status"]

    def test_checklist_novo_tem_8_etapas_pendentes(self):
        """Dado um produto novo, Quando abro a validação,
        Então vejo as 8 etapas não concluídas e o progresso 0 de 8."""
        dados = self.checklist()
        self.assertEqual(len(dados["etapas"]), 8)
        self.assertEqual(dados["etapas"][0]["titulo"], "Escolher 1 produto e 1 público")
        self.assertFalse(any(etapa["concluida"] for etapa in dados["etapas"]))
        self.assertEqual(dados["progresso"], {"concluidas": 0, "total": 8})

    def test_concluir_etapa_com_observacao_e_link(self):
        """Dado um produto, Quando concluo a etapa 2 com observação e link de evidência,
        Então o progresso vira 1 de 8 e a etapa guarda o que escrevi."""
        resposta = self.salvar_etapa(2, observacao="Aparece no top 10 do Mercado Livre",
                                     link_evidencia="https://trends.google.com/exemplo")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json()["progresso"], {"concluidas": 1, "total": 8})
        etapa = self.checklist()["etapas"][1]
        self.assertTrue(etapa["concluida"])
        self.assertEqual(etapa["observacao"], "Aparece no top 10 do Mercado Livre")
        self.assertEqual(etapa["link_evidencia"], "https://trends.google.com/exemplo")
        self.assertIsNotNone(etapa["atualizado_em"])

    def test_primeira_etapa_concluida_muda_status_para_em_validacao(self):
        """Dado um produto com status 'ideia', Quando concluo uma etapa,
        Então o status vira 'em_validacao'."""
        self.assertEqual(self.salvar_etapa(1).get_json()["status"], "em_validacao")
        self.assertEqual(self.status_do_produto(), "em_validacao")

    def test_produto_pontuado_tambem_vai_para_em_validacao(self):
        """Dado um produto 'pontuado', Quando concluo uma etapa, Então o status vira 'em_validacao'."""
        self.cliente.post(f"/api/pontuacao/{self.produto_id}",
                          json={"demanda": 4, "concorrencia": 3, "frete": 5, "facilidade_explicar": 4})
        self.assertEqual(self.status_do_produto(), "pontuado")
        self.salvar_etapa(1)
        self.assertEqual(self.status_do_produto(), "em_validacao")

    def test_salvar_observacao_sem_concluir_nao_muda_status(self):
        """Dado um produto 'ideia', Quando salvo só uma observação, Então o status continua 'ideia'."""
        self.salvar_etapa(1, concluida=False, observacao="Ainda pensando no público")
        self.assertEqual(self.status_do_produto(), "ideia")
        self.assertEqual(self.checklist()["progresso"]["concluidas"], 0)

    def test_desmarcar_etapa_nao_volta_status(self):
        """Dado uma etapa concluída, Quando a desmarco,
        Então o progresso volta para 0 e o status continua 'em_validacao'."""
        self.salvar_etapa(1)
        resposta = self.salvar_etapa(1, concluida=False).get_json()
        self.assertEqual(resposta["progresso"]["concluidas"], 0)
        self.assertEqual(resposta["status"], "em_validacao")

    def test_nao_rebaixa_produto_em_etapa_mais_avancada(self):
        """Dado um produto 'em_teste', Quando concluo uma etapa, Então ele continua 'em_teste'."""
        conexao = sqlite3.connect(self.caminho_banco)
        conexao.execute("UPDATE produtos SET status = 'em_teste' WHERE id = ?", (self.produto_id,))
        conexao.commit()
        conexao.close()
        self.salvar_etapa(3)
        self.assertEqual(self.status_do_produto(), "em_teste")

    def test_salvar_de_novo_atualiza_sem_duplicar(self):
        """Dado a etapa 4 salva, Quando a salvo de novo com outra observação,
        Então vale a nova e o progresso continua 1 de 8."""
        self.salvar_etapa(4, observacao="primeira versão")
        resposta = self.salvar_etapa(4, observacao="landing pronta").get_json()
        self.assertEqual(resposta["etapa"]["observacao"], "landing pronta")
        self.assertEqual(resposta["progresso"]["concluidas"], 1)

    def test_link_invalido_nao_grava(self):
        """Dado um produto, Quando informo o link 'meusite.com', Então vejo um erro e nada é gravado."""
        resposta = self.salvar_etapa(2, link_evidencia="meusite.com")
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("O link de evidência deve começar com http:// ou https://.",
                      resposta.get_json()["erros"])
        self.assertFalse(self.checklist()["etapas"][1]["concluida"])

    def test_etapa_inexistente(self):
        self.assertEqual(self.salvar_etapa(9).status_code, 404)
        self.assertEqual(self.salvar_etapa(0).status_code, 404)

    def test_excluir_produto_com_validacao(self):
        """Dado um produto com etapas salvas, Quando o excluo, Então ele some da lista."""
        self.salvar_etapa(1)
        self.assertEqual(self.cliente.delete(f"/api/produtos/{self.produto_id}").status_code, 204)
        self.assertEqual(self.cliente.get("/api/produtos").get_json(), [])

    def test_nao_acessa_validacao_de_outro_usuario(self):
        """Dado que outro usuário tem um produto, Quando tento ver ou salvar a validação,
        Então recebo 404."""
        self.cliente.post("/api/auth/logout")
        self.cadastrar(email="b@exemplo.com")
        self.assertEqual(self.cliente.get(f"/api/validacao/{self.produto_id}").status_code, 404)
        self.assertEqual(self.salvar_etapa(1).status_code, 404)

    def test_sem_login_recebe_401(self):
        self.cliente.post("/api/auth/logout")
        self.assertEqual(self.cliente.get(f"/api/validacao/{self.produto_id}").status_code, 401)


TESTE_PADRAO = {"canal": "Facebook Ads", "utm_campanha": "Leitor-Codigo", "verba_diaria": "30",
                "data_inicio": "2026-10-01", "data_fim": "2026-10-07"}


class TestTesteDeVenda(CenarioBase):
    """Produto: preço 200, custo 110 -> margem unitária R$ 90."""

    def setUp(self):
        super().setUp()
        self.cadastrar()
        self.produto_id = self.cadastrar_produto().get_json()["id"]

    def criar_teste(self, **campos):
        dados = dict(TESTE_PADRAO, produto_id=self.produto_id, **campos)
        return self.cliente.post("/api/testes", json=dados)

    def lancar_dia(self, teste_id, data, **metricas):
        return self.cliente.put(f"/api/testes/{teste_id}/metricas/{data}", json=metricas)

    def status_do_produto(self):
        return self.cliente.get(f"/api/produtos/{self.produto_id}").get_json()["status"]

    def test_criar_teste_coloca_produto_em_teste(self):
        """Dado um produto, Quando crio um teste,
        Então o teste fica 'em_andamento', sem dados, e o produto fica 'em_teste'."""
        resposta = self.criar_teste()
        self.assertEqual(resposta.status_code, 201)
        resumo = resposta.get_json()
        self.assertEqual(resumo["teste"]["status"], "em_andamento")
        self.assertEqual(resumo["teste"]["utm_campanha"], "leitor-codigo")
        self.assertEqual(resumo["veredito"]["codigo"], "continue_testando")
        self.assertIsNone(resumo["indicadores"]["cpa"])
        self.assertEqual(self.status_do_produto(), "em_teste")

    def test_lancar_metricas_calcula_funil_indicadores_e_veredito(self):
        """Dado um teste, Quando lanço 2 dias com R$ 210 investidos e 3 vendas no total,
        Então o CPA é R$ 70 (77,8% da margem), o veredito é 'Ajustar' e o produto fica 'ajustar'."""
        teste_id = self.criar_teste().get_json()["teste"]["id"]
        self.lancar_dia(teste_id, "2026-10-01", investimento="100,00", impressoes="5.000", cliques=100,
                        visitas=80, carrinhos=6, vendas=1, receita="200")
        resumo = self.lancar_dia(teste_id, "2026-10-02", investimento=110, impressoes=5000, cliques=100,
                                 visitas=70, carrinhos=6, vendas=2, receita=400).get_json()
        self.assertEqual(resumo["totais"]["impressoes"], 10000)
        self.assertEqual(resumo["totais"]["vendas"], 3)
        self.assertAlmostEqual(resumo["indicadores"]["cpa"], 70)
        self.assertEqual(resumo["indicadores"]["lucro"], 60)
        self.assertEqual(resumo["funil"][4]["valor"], 3)
        self.assertEqual(resumo["veredito"]["codigo"], "ajustar")
        self.assertEqual(self.status_do_produto(), "ajustar")

    def test_cpa_baixo_escala(self):
        """Dado um teste, Quando invisto R$ 60 e vendo 1 (CPA = 66,7% da margem),
        Então o veredito é 'Escalar' e o produto fica 'escalar'."""
        teste_id = self.criar_teste().get_json()["teste"]["id"]
        resumo = self.lancar_dia(teste_id, "2026-10-01", investimento=60, vendas=1).get_json()
        self.assertEqual(resumo["veredito"]["codigo"], "escalar")
        self.assertEqual(self.status_do_produto(), "escalar")

    def test_sem_vendas_e_investimento_alto_descarta(self):
        """Dado um teste, Quando invisto R$ 100 sem vendas (mais que a margem de R$ 90),
        Então o veredito é 'Trocar' e o produto fica 'descartado'."""
        teste_id = self.criar_teste().get_json()["teste"]["id"]
        resumo = self.lancar_dia(teste_id, "2026-10-01", investimento=100).get_json()
        self.assertEqual(resumo["veredito"]["codigo"], "trocar")
        self.assertEqual(self.status_do_produto(), "descartado")

    def test_lancar_mesmo_dia_corrige_sem_duplicar(self):
        """Dado o dia 01/10 lançado com 1 venda, Quando lanço o mesmo dia com 2 vendas,
        Então o teste tem 1 dia e 2 vendas."""
        teste_id = self.criar_teste().get_json()["teste"]["id"]
        self.lancar_dia(teste_id, "2026-10-01", investimento=30, vendas=1)
        resumo = self.lancar_dia(teste_id, "2026-10-01", investimento=30, vendas=2).get_json()
        self.assertEqual(len(resumo["metricas"]), 1)
        self.assertEqual(resumo["totais"]["vendas"], 2)
        self.assertEqual(resumo["metricas"][0]["origem"], "manual")

    def test_campos_vazios_valem_zero(self):
        teste_id = self.criar_teste().get_json()["teste"]["id"]
        resposta = self.lancar_dia(teste_id, "2026-10-01", investimento="30", cliques="", vendas=None)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json()["metricas"][0]["cliques"], 0)

    def test_metricas_invalidas_nao_gravam(self):
        """Dado um teste, Quando lanço vendas -1 e investimento 'abc', Então vejo os erros."""
        teste_id = self.criar_teste().get_json()["teste"]["id"]
        resposta = self.lancar_dia(teste_id, "2026-10-01", investimento="abc", vendas=-1)
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.get_json()["erros"], [
            "Investimento deve ser um valor igual ou maior que zero.",
            "Vendas deve ser um número inteiro igual ou maior que zero."])
        self.assertEqual(self.lancar_dia(teste_id, "01-10-2026", investimento=1).status_code, 400)

    def test_excluir_dia_recalcula(self):
        """Dado 2 dias lançados, Quando excluo um, Então os totais são recalculados."""
        teste_id = self.criar_teste().get_json()["teste"]["id"]
        self.lancar_dia(teste_id, "2026-10-01", investimento=60, vendas=1)
        self.lancar_dia(teste_id, "2026-10-02", investimento=200)
        resposta = self.cliente.delete(f"/api/testes/{teste_id}/metricas/2026-10-02")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json()["totais"]["investimento"], 60)
        self.assertEqual(resposta.get_json()["veredito"]["codigo"], "escalar")
        self.assertEqual(self.cliente.delete(f"/api/testes/{teste_id}/metricas/2026-10-09").status_code, 404)

    def test_encerrar_e_editar_teste(self):
        """Dado um teste em andamento, Quando o encerro, Então ele fica 'encerrado'."""
        teste_id = self.criar_teste().get_json()["teste"]["id"]
        resposta = self.cliente.put(f"/api/testes/{teste_id}", json=dict(TESTE_PADRAO, status="encerrado",
                                                                         verba_diaria="50"))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json()["teste"]["status"], "encerrado")
        self.assertEqual(resposta.get_json()["teste"]["verba_diaria"], 50)

    def test_dados_do_teste_invalidos(self):
        """Dado um produto, Quando crio um teste sem canal e com fim antes do início, Então vejo os erros."""
        resposta = self.criar_teste(canal="", data_fim="2026-09-30")
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.get_json()["erros"], [
            "Informe o canal.", "A data de fim não pode ser antes da data de início."])

    def test_listar_testes_do_produto(self):
        teste_id = self.criar_teste().get_json()["teste"]["id"]
        self.lancar_dia(teste_id, "2026-10-01", investimento=60, vendas=1)
        lista = self.cliente.get(f"/api/testes?produto_id={self.produto_id}").get_json()
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["veredito"]["codigo"], "escalar")
        self.assertEqual(lista[0]["totais"]["vendas"], 1)

    def test_excluir_teste_e_produto(self):
        """Dado um produto com teste e métricas, Quando excluo o teste e depois o produto, Então tudo some."""
        teste_id = self.criar_teste().get_json()["teste"]["id"]
        self.lancar_dia(teste_id, "2026-10-01", investimento=30)
        self.assertEqual(self.cliente.delete(f"/api/testes/{teste_id}").status_code, 204)
        self.assertEqual(self.cliente.get(f"/api/testes/{teste_id}").status_code, 404)
        self.criar_teste()
        self.assertEqual(self.cliente.delete(f"/api/produtos/{self.produto_id}").status_code, 204)

    def test_nao_acessa_teste_de_outro_usuario(self):
        """Dado que outro usuário tem um teste, Quando tento ver, lançar ou criar teste no produto dele,
        Então recebo 404."""
        teste_id = self.criar_teste().get_json()["teste"]["id"]
        self.cliente.post("/api/auth/logout")
        self.cadastrar(email="b@exemplo.com")
        self.assertEqual(self.cliente.get(f"/api/testes/{teste_id}").status_code, 404)
        self.assertEqual(self.lancar_dia(teste_id, "2026-10-01", vendas=1).status_code, 404)
        self.assertEqual(self.criar_teste().status_code, 404)
        self.assertEqual(self.cliente.get(f"/api/testes?produto_id={self.produto_id}").status_code, 404)


class TestPainel(CenarioBase):
    """Leitor: preço 200, custo 110 -> margem R$ 90."""

    def setUp(self):
        super().setUp()
        self.cadastrar()

    def painel(self):
        return self.cliente.get("/api/painel").get_json()

    def criar_teste(self, produto_id, data_inicio, data_fim, canal="Facebook Ads"):
        return self.cliente.post("/api/testes", json=dict(
            TESTE_PADRAO, produto_id=produto_id, canal=canal,
            data_inicio=data_inicio, data_fim=data_fim)).get_json()["teste"]["id"]

    def test_painel_vazio(self):
        self.assertEqual(self.painel(), {"produtos": [], "testes": []})

    def test_produto_sem_pontuacao_nem_teste(self):
        """Dado um produto só cadastrado, Quando abro o painel,
        Então ele aparece como 'ideia', sem pontuação e sem teste."""
        self.cadastrar_produto()
        produto = self.painel()["produtos"][0]
        self.assertEqual(produto["status"], "ideia")
        self.assertIsNone(produto["pontuacao"])
        self.assertIsNone(produto["teste"])
        self.assertEqual(produto["quantidade_testes"], 0)

    def test_mostra_ultima_pontuacao_e_teste_mais_recente(self):
        """Dado um produto pontuado duas vezes e com dois testes,
        Quando abro o painel,
        Então vejo a última pontuação e o CPA, lucro e veredito do teste com início mais recente."""
        produto_id = self.cadastrar_produto().get_json()["id"]
        url_pontuacao = f"/api/pontuacao/{produto_id}"
        self.cliente.post(url_pontuacao, json={"demanda": 1, "concorrencia": 1, "frete": 1, "facilidade_explicar": 1})
        self.cliente.post(url_pontuacao, json={"demanda": 4, "concorrencia": 3, "frete": 5, "facilidade_explicar": 4})

        recente = self.criar_teste(produto_id, "2026-10-08", "2026-10-14", canal="Instagram Ads")
        antigo = self.criar_teste(produto_id, "2026-10-01", "2026-10-07")
        self.cliente.put(f"/api/testes/{antigo}/metricas/2026-10-01", json={"investimento": 300})
        self.cliente.put(f"/api/testes/{recente}/metricas/2026-10-08",
                         json={"investimento": 120, "vendas": 2, "receita": 400})

        produto = self.painel()["produtos"][0]
        self.assertEqual(produto["pontuacao"]["total"], 20)
        self.assertEqual(produto["pontuacao"]["veredito"], "vale_testar")
        self.assertEqual(produto["teste"]["id"], recente)
        self.assertEqual(produto["teste"]["canal"], "Instagram Ads")
        self.assertAlmostEqual(produto["teste"]["cpa"], 60)          # 120 / 2
        self.assertEqual(produto["teste"]["lucro"], 60)              # 2 × 90 − 120
        self.assertEqual(produto["teste"]["veredito"]["codigo"], "escalar")
        self.assertEqual(produto["quantidade_testes"], 2)

    def test_lista_de_testes_para_o_grafico(self):
        """Dado dois produtos com testes, Então o seletor traz todos, do mais recente ao mais antigo."""
        primeiro = self.cadastrar_produto().get_json()["id"]
        segundo = self.cadastrar_produto(nome="Impressora térmica").get_json()["id"]
        self.criar_teste(primeiro, "2026-10-01", "2026-10-07")
        self.criar_teste(segundo, "2026-10-05", "2026-10-11")
        testes = self.painel()["testes"]
        self.assertEqual([t["produto_nome"] for t in testes], ["Impressora térmica", "Leitor de código de barras"])

    def test_nao_mostra_produtos_de_outro_usuario(self):
        """Dado que outro usuário tem produtos e testes, Quando abro meu painel, Então não vejo os dele."""
        produto_id = self.cadastrar_produto().get_json()["id"]
        self.criar_teste(produto_id, "2026-10-01", "2026-10-07")
        self.cliente.post("/api/auth/logout")
        self.cadastrar(email="b@exemplo.com")
        self.assertEqual(self.painel(), {"produtos": [], "testes": []})

    def test_sem_login_recebe_401(self):
        self.cliente.post("/api/auth/logout")
        self.assertEqual(self.cliente.get("/api/painel").status_code, 401)


CSV_ANUNCIOS = (
    "Início dos relatórios;Valor usado (BRL);Impressões;Cliques no link\n"
    "2026-10-01;30,00;5.000;100\n"
    "2026-10-02;40,00;6.000;120\n"
    "2026-10-20;10,00;1.000;10\n"
    ";80,00;12.000;230\n"
)
CSV_PEDIDOS = "Pedido;Data;Total\n1;01/10/2026 10:00;200,00\n2;02/10/2026 11:00;200,00\n3;02/10/2026 18:00;200,00\n"


class TestImportacaoCsv(CenarioBase):
    """Teste de 01/10 a 07/10 de um produto com margem R$ 90."""

    def setUp(self):
        super().setUp()
        self.cadastrar()
        produto_id = self.cadastrar_produto().get_json()["id"]
        self.teste_id = self.cliente.post("/api/testes", json=dict(TESTE_PADRAO, produto_id=produto_id)
                                          ).get_json()["teste"]["id"]

    def enviar(self, acao, conteudo, mapeamento=None, nome="relatorio.csv"):
        dados = {"arquivo": (io.BytesIO(conteudo.encode("utf-8")), nome)}
        if mapeamento is not None:
            dados["mapeamento"] = json.dumps(mapeamento)
        return self.cliente.post(f"/api/testes/{self.teste_id}/csv/{acao}", data=dados,
                                 content_type="multipart/form-data")

    def test_previa_sugere_colunas_e_mostra_dias(self):
        """Dado um CSV do Meta, Quando peço a prévia,
        Então vejo as colunas sugeridas, 3 dias (um fora do período) e a linha de total ignorada."""
        resposta = self.enviar("previa", CSV_ANUNCIOS)
        self.assertEqual(resposta.status_code, 200)
        previa = resposta.get_json()
        self.assertEqual(previa["mapeamento"]["investimento"], "Valor usado (BRL)")
        self.assertEqual([d["data"] for d in previa["dias"]], ["2026-10-01", "2026-10-02", "2026-10-20"])
        self.assertEqual([d["fora_do_periodo"] for d in previa["dias"]], [False, False, True])
        self.assertEqual(previa["dias"][0]["situacao"], "novo")
        self.assertEqual(len(previa["ignoradas"]), 1)
        # A prévia não grava nada.
        self.assertEqual(self.cliente.get(f"/api/testes/{self.teste_id}").get_json()["metricas"], [])

    def test_importar_grava_com_origem_csv(self):
        """Dado um CSV do Meta, Quando importo, Então os dias são gravados com origem 'csv'."""
        resposta = self.enviar("importar", CSV_ANUNCIOS)
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.get_json()
        self.assertEqual((corpo["importados"], corpo["novos"], corpo["atualizados"]), (3, 3, 0))
        metricas = corpo["resumo"]["metricas"]
        self.assertEqual(metricas[0]["impressoes"], 5000)
        self.assertEqual({m["origem"] for m in metricas}, {"csv"})
        self.assertEqual(corpo["resumo"]["totais"]["investimento"], 80)

    def test_juntar_anuncios_e_pedidos_sem_apagar(self):
        """Dado o CSV de anúncios importado e um dia lançado à mão com 9 carrinhos,
        Quando importo a planilha de pedidos (vendas = 1 por linha, receita = Total),
        Então o dia mantém investimento, cliques e carrinhos e ganha as vendas e a receita."""
        self.enviar("importar", CSV_ANUNCIOS)
        self.cliente.put(f"/api/testes/{self.teste_id}/metricas/2026-10-03", json={"carrinhos": 9})
        mapeamento = {"data": "Data", "vendas": "__contar_linhas__", "receita": "Total"}
        previa = self.enviar("previa", CSV_PEDIDOS, mapeamento).get_json()
        self.assertEqual([d["situacao"] for d in previa["dias"]], ["atualiza", "atualiza"])

        resumo = self.enviar("importar", CSV_PEDIDOS, mapeamento).get_json()["resumo"]
        dia2 = next(m for m in resumo["metricas"] if m["data"] == "2026-10-02")
        self.assertEqual((dia2["investimento"], dia2["cliques"], dia2["vendas"], dia2["receita"]),
                         (40, 120, 2, 400))
        dia3 = next(m for m in resumo["metricas"] if m["data"] == "2026-10-03")
        self.assertEqual((dia3["carrinhos"], dia3["origem"]), (9, "manual"))
        # 80 investidos, 3 vendas -> CPA 26,67 (29,6% da margem) -> Escalar; o produto acompanha.
        self.assertEqual(resumo["veredito"]["codigo"], "escalar")
        self.assertEqual(resumo["produto"]["status"], "escalar")

    def test_sem_coluna_de_data_pede_para_escolher(self):
        """Dado um CSV sem coluna parecida com data, Quando peço a prévia,
        Então vejo as colunas e o aviso para escolher, e importar sem escolher dá erro."""
        conteudo = "Quando;Vendas\n2026-10-01;2\n"
        previa = self.enviar("previa", conteudo).get_json()
        self.assertEqual(previa["colunas"], ["Quando", "Vendas"])
        self.assertEqual(previa["aviso"], "Escolha a coluna da data.")
        self.assertEqual(self.enviar("importar", conteudo).status_code, 400)
        ok = self.enviar("importar", conteudo, {"data": "Quando", "vendas": "Vendas"})
        self.assertEqual(ok.get_json()["importados"], 1)

    def test_erros_de_envio(self):
        sem_arquivo = self.cliente.post(f"/api/testes/{self.teste_id}/csv/previa", data={},
                                        content_type="multipart/form-data")
        self.assertEqual(sem_arquivo.get_json()["erros"], ["Envie um arquivo CSV."])
        coluna_errada = self.enviar("previa", CSV_ANUNCIOS, {"data": "Nao existe", "vendas": "Impressões"})
        self.assertEqual(coluna_errada.status_code, 400)
        so_total = self.enviar("importar", "Data;Vendas\nTotal;5\n", {"data": "Data", "vendas": "Vendas"})
        self.assertEqual(so_total.get_json()["erros"], ["Nenhum dia válido para importar."])

    def test_arquivo_grande_demais(self):
        grande = "Data;Vendas\n" + "2026-10-01;1\n" * 300000
        resposta = self.enviar("previa", grande)
        self.assertIn(resposta.status_code, (400, 413))
        self.assertIn("Arquivo grande demais", resposta.get_json()["erros"][0])

    def test_nao_importa_em_teste_de_outro_usuario(self):
        self.cliente.post("/api/auth/logout")
        self.cadastrar(email="b@exemplo.com")
        self.assertEqual(self.enviar("previa", CSV_ANUNCIOS).status_code, 404)
        self.assertEqual(self.enviar("importar", CSV_ANUNCIOS).status_code, 404)


PRODUTO_AFILIADO = {"modelo": "afiliado", "nome": "Camiseta UV masculina", "plataforma": "Shopee",
                    "url_produto": "https://s.shopee.com.br/exemplo", "preco_venda": "34,95",
                    "taxa_comissao": "10"}


class TestModoAfiliado(CenarioBase):

    def setUp(self):
        super().setUp()
        self.cadastrar()

    def test_cadastro_de_produto_de_afiliado(self):
        """Dado que sou afiliado, Quando cadastro um produto de R$ 34,95 com 10% de comissão,
        Então a margem mostrada é a comissão: R$ 3,50 (10%), sem custo."""
        resposta = self.cliente.post("/api/produtos", json=PRODUTO_AFILIADO)
        self.assertEqual(resposta.status_code, 201)
        produto = resposta.get_json()
        self.assertEqual((produto["modelo"], produto["taxa_comissao"], produto["custo_unitario"]),
                         ("afiliado", 10, 0))
        self.assertEqual(produto["margem_unitaria"], 3.5)
        self.assertAlmostEqual(produto["margem_percentual"], 0.10)

    def test_afiliado_sem_comissao_valida(self):
        resposta = self.cliente.post("/api/produtos", json=dict(PRODUTO_AFILIADO, taxa_comissao="0"))
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("A comissão deve ser um percentual maior que 0 e até 100.", resposta.get_json()["erros"])

    def test_produto_sem_modelo_continua_vendedor(self):
        """Dado um cadastro antigo (sem o campo modelo), Então o produto é de vendedor, como antes."""
        produto = self.cadastrar_produto().get_json()
        self.assertEqual((produto["modelo"], produto["margem_unitaria"]), ("vendedor", 90))

    def test_trocar_vendedor_para_afiliado(self):
        """Dado um produto cadastrado como vendedor (preço 34,95 e custo 30),
        Quando o edito para afiliado com 3% de comissão, Então a margem vira R$ 1,05."""
        produto_id = self.cadastrar_produto(preco_venda="34,95", custo_unitario="30").get_json()["id"]
        resposta = self.cliente.put(f"/api/produtos/{produto_id}", json=dict(PRODUTO_AFILIADO, taxa_comissao="3"))
        self.assertEqual(resposta.get_json()["margem_unitaria"], 1.05)
        self.assertEqual(resposta.get_json()["custo_unitario"], 0)

    def test_pontuacao_do_afiliado_usa_nota_da_comissao(self):
        """Dado um produto de afiliado com comissão de R$ 3,50, Então a nota da margem é 2."""
        produto_id = self.cliente.post("/api/produtos", json=PRODUTO_AFILIADO).get_json()["id"]
        self.assertEqual(self.cliente.get(f"/api/pontuacao/{produto_id}").get_json()["nota_margem"], 2)

    def criar_teste_afiliado(self):
        produto_id = self.cliente.post("/api/produtos", json=PRODUTO_AFILIADO).get_json()["id"]
        return self.cliente.post("/api/testes", json=dict(TESTE_PADRAO, produto_id=produto_id,
                                                           utm_campanha="camisetainsta")).get_json()["teste"]["id"]

    def lancar_dia(self, teste_id, data, **metricas):
        return self.cliente.put(f"/api/testes/{teste_id}/metricas/{data}", json=metricas).get_json()

    def status_do_produto(self):
        return self.cliente.get("/api/produtos").get_json()[0]["status"]

    def test_teste_de_venda_do_afiliado(self):
        """Dado um produto de afiliado com comissão de R$ 3,50 e um teste com Sub_id,
        Quando lanço R$ 30 investidos, 200 cliques no link, 2 pedidos e R$ 8,20 de comissão recebida,
        Então o lucro é −R$ 21,80, aparece o alerta de prejuízo e, no 1º dia, o veredito é Continue testando."""
        teste_id = self.criar_teste_afiliado()
        resumo = self.lancar_dia(teste_id, "2026-10-01", investimento=30, impressoes=8000, cliques=250,
                                 visitas=200, vendas=2, receita="8,20")
        self.assertEqual(resumo["indicadores"]["lucro"], -21.8)
        self.assertEqual(resumo["indicadores"]["cpa"], 15)
        self.assertEqual(resumo["veredito"]["codigo"], "continue_testando")
        self.assertEqual([e["etapa"] for e in resumo["funil"]], ["impressoes", "cliques", "visitas", "vendas"])
        self.assertEqual(resumo["alertas"][0]["codigo"], "investimento_acima_da_comissao")
        self.assertEqual(self.cliente.get("/api/painel").get_json()["produtos"][0]["modelo"], "afiliado")

    def test_primeiro_dia_sem_pedido_nao_descarta(self):
        """Dado um produto de afiliado com comissão de R$ 3,50,
        Quando lanço o 1º dia com R$ 30 investidos e nenhum pedido,
        Então o veredito é Continue testando e o produto continua Em teste (não Descartado)."""
        teste_id = self.criar_teste_afiliado()
        resumo = self.lancar_dia(teste_id, "2026-10-01", investimento=30, cliques=120, visitas=80)
        self.assertEqual(resumo["veredito"]["codigo"], "continue_testando")
        self.assertEqual(self.status_do_produto(), "em_teste")

    def test_tres_dias_sem_comissao_trocar(self):
        """Dado 3 dias com R$ 30 investidos por dia e nenhuma comissão,
        Então o veredito é Trocar de produto e o produto vira Descartado."""
        teste_id = self.criar_teste_afiliado()
        for data in ("2026-10-01", "2026-10-02", "2026-10-03"):
            resumo = self.lancar_dia(teste_id, data, investimento=30, visitas=80)
        self.assertEqual(resumo["veredito"]["codigo"], "trocar")
        self.assertEqual(self.status_do_produto(), "descartado")

    def test_lucro_positivo_escalar(self):
        """Dado 3 dias com R$ 30 investidos por dia (R$ 90) e R$ 135 de comissão recebida,
        Então o lucro é R$ 45, a razão é 66,7% e o veredito é Escalar, mesmo com o CPA acima da comissão estimada."""
        teste_id = self.criar_teste_afiliado()
        for data in ("2026-10-01", "2026-10-02", "2026-10-03"):
            resumo = self.lancar_dia(teste_id, data, investimento=30, visitas=100, vendas=5, receita=45)
        self.assertEqual(resumo["indicadores"]["lucro"], 45)
        self.assertEqual(resumo["indicadores"]["cpa"], 6)  # acima dos R$ 3,50 estimados
        self.assertAlmostEqual(resumo["veredito"]["razao_cpa_margem"], 90 / 135, places=5)
        self.assertEqual(resumo["veredito"]["codigo"], "escalar")
        self.assertEqual(resumo["alertas"], [])
        self.assertEqual(self.status_do_produto(), "escalar")


class TestChaveSecreta(unittest.TestCase):
    """Item G: sem SECRET_KEY de verdade, o sistema não sobe (antes usava a chave de exemplo sem avisar)."""

    def test_sem_chave_ou_com_a_de_exemplo_nao_sobe(self):
        for chave in ("", "troque-esta-chave"):
            with self.subTest(chave=chave), mock.patch.dict(os.environ, {"SECRET_KEY": chave}):
                with self.assertRaises(ChaveSecretaAusente):
                    criar_app({"CAMINHO_BANCO": os.devnull})

    def test_com_chave_de_verdade_sobe(self):
        descritor, caminho = tempfile.mkstemp(suffix=".db")
        os.close(descritor)
        try:
            with mock.patch.dict(os.environ, {"SECRET_KEY": "a1b2c3" * 8}):
                self.assertEqual(criar_app({"CAMINHO_BANCO": caminho}).config["SECRET_KEY"], "a1b2c3" * 8)
        finally:
            os.remove(caminho)


if __name__ == "__main__":
    unittest.main()
