"""Integrações (Etapa 7): funções puras dos webhooks e cenários com a Nuvemshop simulada."""
import base64
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

from app import criar_app
from rotas.integracoes import (assinatura_valida_base64, assinatura_valida_hex, data_do_pedido,
                               extrair_utm_campanha)

SEGREDO = "segredo-de-teste"
CONFIG_NUVEMSHOP = {"NUVEMSHOP_SEGREDO_APP": SEGREDO, "NUVEMSHOP_TOKEN_ACESSO": "token-teste",
                    "NUVEMSHOP_EMAIL_USUARIO": "oscar@exemplo.com"}
CONFIG_SHOPIFY = {"SHOPIFY_SEGREDO_WEBHOOK": SEGREDO, "SHOPIFY_EMAIL_USUARIO": "oscar@exemplo.com"}


def pedido_nuvemshop(numero, total="200.00", landing_url="https://loja.com/leitor?utm_source=facebook&utm_campaign=leitor",
                     paid_at="2026-10-02T15:00:00+0000"):
    return {"id": numero, "total": total, "paid_at": paid_at, "created_at": paid_at, "landing_url": landing_url}


class TestFuncoesDoWebhook(unittest.TestCase):

    def test_assinaturas(self):
        corpo = b'{"id": 1}'
        hexa = hmac.new(SEGREDO.encode(), corpo, hashlib.sha256).hexdigest()
        b64 = base64.b64encode(hmac.new(SEGREDO.encode(), corpo, hashlib.sha256).digest()).decode()
        self.assertTrue(assinatura_valida_hex(SEGREDO, corpo, hexa))
        self.assertTrue(assinatura_valida_hex(SEGREDO, corpo, hexa.upper()))
        self.assertFalse(assinatura_valida_hex(SEGREDO, corpo + b" ", hexa))
        self.assertFalse(assinatura_valida_hex(SEGREDO, corpo, None))
        self.assertTrue(assinatura_valida_base64(SEGREDO, corpo, b64))
        self.assertFalse(assinatura_valida_base64("outro", corpo, b64))

    def test_utm_na_url_de_entrada(self):
        pedido = {"landing_url": "https://loja.com/p?utm_source=fb&utm_campaign=Leitor-Codigo&x=1"}
        self.assertEqual(extrair_utm_campanha(pedido, ("landing_url",)), "leitor-codigo")

    def test_utm_em_qualquer_lugar_do_pedido_e_codificada(self):
        pedido = {"extra": {"origem": [{"url": "/p?utm_campaign=black%20friday"}]}, "landing_url": None}
        self.assertEqual(extrair_utm_campanha(pedido, ("landing_url",)), "black friday")
        self.assertEqual(extrair_utm_campanha({"landing_site": "/p?utm_campaign=promo+leitor"}), "promo leitor")

    def test_pedido_sem_utm(self):
        self.assertIsNone(extrair_utm_campanha({"landing_url": "https://loja.com/", "total": "10"}))

    def test_data_do_pedido_no_fuso_local(self):
        utc = datetime(2026, 10, 6, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(data_do_pedido("2026-10-06T23:30:00+0000"), utc.astimezone().date().isoformat())
        self.assertEqual(data_do_pedido("2026-10-06T14:33:00-03:00"),
                         datetime(2026, 10, 6, 17, 33, tzinfo=timezone.utc).astimezone().date().isoformat())
        self.assertEqual(data_do_pedido(None), datetime.now().date().isoformat())


class CenarioWebhook(unittest.TestCase):
    """Usuário oscar@exemplo.com com o leitor (margem R$ 90) e um teste 'leitor' de 01/10 a 07/10."""

    def setUp(self):
        descritor, self.caminho_banco = tempfile.mkstemp(suffix=".db")
        os.close(descritor)
        self.app = criar_app({"TESTING": True, "CAMINHO_BANCO": self.caminho_banco})
        self.cliente = self.app.test_client()
        self.cliente.post("/api/auth/cadastro", json={"nome": "Oscar", "email": "oscar@exemplo.com",
                                                      "senha": "segredo123"})
        produto_id = self.cliente.post("/api/produtos", json={
            "nome": "Leitor", "plataforma": "Nuvemshop", "preco_venda": "200", "custo_unitario": "110"}
        ).get_json()["id"]
        self.teste_id = self.cliente.post("/api/testes", json={
            "produto_id": produto_id, "canal": "Facebook Ads", "utm_campanha": "leitor", "verba_diaria": "30",
            "data_inicio": "2026-10-01", "data_fim": "2026-10-07"}).get_json()["teste"]["id"]
        self.cliente.put(f"/api/testes/{self.teste_id}/metricas/2026-10-02", json={"investimento": 30, "visitas": 50})
        self.ambiente = mock.patch.dict(os.environ, {**CONFIG_NUVEMSHOP, **CONFIG_SHOPIFY})
        self.ambiente.start()

    def tearDown(self):
        self.ambiente.stop()
        os.remove(self.caminho_banco)

    def avisar_nuvemshop(self, numero, pedido=None, evento="order/paid", assinatura=None):
        corpo = json.dumps({"store_id": 123, "event": evento, "id": numero}).encode()
        assinatura = assinatura or hmac.new(SEGREDO.encode(), corpo, hashlib.sha256).hexdigest()
        with mock.patch("rotas.integracoes.buscar_pedido_nuvemshop",
                        return_value=pedido or pedido_nuvemshop(numero)) as buscar:
            resposta = self.cliente.post("/api/integracoes/nuvemshop/webhook", data=corpo,
                                         headers={"x-linkedstore-hmac-sha256": assinatura,
                                                  "Content-Type": "application/json"})
        return resposta, buscar

    def dia(self, data):
        metricas = self.cliente.get(f"/api/testes/{self.teste_id}").get_json()["metricas"]
        return next((m for m in metricas if m["data"] == data), None)

    def test_pedido_pago_soma_venda_no_dia_do_teste(self):
        """Dado o teste 'leitor' com R$ 30 investidos em 02/10,
        Quando a Nuvemshop avisa um pedido pago de R$ 200 com utm_campaign=leitor,
        Então o dia 02/10 ganha 1 venda e R$ 200, mantém o investimento, e o produto vai para 'escalar'."""
        resposta, buscar = self.avisar_nuvemshop(1001)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), {"situacao": "registrado", "teste_id": self.teste_id})
        buscar.assert_called_once_with(123, 1001)
        dia = self.dia(data_do_pedido("2026-10-02T15:00:00+0000"))
        self.assertEqual((dia["vendas"], dia["receita"], dia["investimento"]), (1, 200, 30))
        produto = self.cliente.get("/api/produtos").get_json()[0]
        self.assertEqual(produto["status"], "escalar")  # CPA 30 = 33% da margem

    def test_pedido_repetido_nao_conta_duas_vezes(self):
        """Dado um pedido já recebido, Quando a Nuvemshop reenvia o mesmo aviso, Então a venda não duplica."""
        self.avisar_nuvemshop(1001)
        resposta, _ = self.avisar_nuvemshop(1001)
        self.assertEqual(resposta.get_json(), {"situacao": "repetido"})
        self.assertEqual(self.dia(data_do_pedido("2026-10-02T15:00:00+0000"))["vendas"], 1)

    def test_dia_sem_metricas_e_criado_com_origem_webhook(self):
        pedido = pedido_nuvemshop(1002, total="199.90", paid_at="2026-10-04T15:00:00+0000")
        self.avisar_nuvemshop(1002, pedido)
        dia = self.dia(data_do_pedido("2026-10-04T15:00:00+0000"))
        self.assertEqual((dia["vendas"], dia["receita"], dia["origem"]), (1, 199.9, "webhook"))

    def test_pedido_sem_campanha_fica_registrado(self):
        """Dado um pedido sem UTM, Quando ele chega, Então fica como 'sem campanha' na lista de pedidos."""
        resposta, _ = self.avisar_nuvemshop(1003, pedido_nuvemshop(1003, landing_url="https://loja.com/"))
        self.assertEqual(resposta.get_json(), {"situacao": "registrado", "teste_id": None})
        pedidos = self.cliente.get("/api/integracoes/pedidos").get_json()
        self.assertEqual(len(pedidos), 1)
        self.assertIsNone(pedidos[0]["teste_id"])
        self.assertIsNone(pedidos[0]["utm_campanha"])
        self.assertEqual(self.dia(data_do_pedido("2026-10-02T15:00:00+0000"))["vendas"], 0)

    def test_assinatura_invalida_recusa(self):
        resposta, buscar = self.avisar_nuvemshop(1004, assinatura="0" * 64)
        self.assertEqual(resposta.status_code, 401)
        buscar.assert_not_called()
        self.assertEqual(self.cliente.get("/api/integracoes/pedidos").get_json(), [])

    def test_evento_que_nao_e_pagamento_e_ignorado(self):
        resposta, buscar = self.avisar_nuvemshop(1005, evento="order/created")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("ignorado", resposta.get_json())
        buscar.assert_not_called()

    def test_sem_configuracao_responde_503(self):
        with mock.patch.dict(os.environ, {"NUVEMSHOP_SEGREDO_APP": ""}):
            resposta, _ = self.avisar_nuvemshop(1006)
        self.assertEqual(resposta.status_code, 503)

    def test_falha_ao_buscar_pedido_pede_nova_tentativa(self):
        """Dado que a API da Nuvemshop está fora, Quando chega um aviso,
        Então respondo 502 (a Nuvemshop tenta de novo) e nada é gravado."""
        import urllib.error
        corpo = json.dumps({"store_id": 123, "event": "order/paid", "id": 1007}).encode()
        assinatura = hmac.new(SEGREDO.encode(), corpo, hashlib.sha256).hexdigest()
        with mock.patch("rotas.integracoes.buscar_pedido_nuvemshop", side_effect=urllib.error.URLError("fora do ar")):
            resposta = self.cliente.post("/api/integracoes/nuvemshop/webhook", data=corpo,
                                         headers={"x-linkedstore-hmac-sha256": assinatura})
        self.assertEqual(resposta.status_code, 502)
        self.assertEqual(self.cliente.get("/api/integracoes/pedidos").get_json(), [])

    def test_webhook_da_shopify(self):
        """Dado a Shopify configurada, Quando chega um pedido pago com landing_site com a campanha,
        Então soma a venda no teste."""
        pedido = {"id": 555, "total_price": "200.00", "processed_at": "2026-10-03T10:00:00-03:00",
                  "landing_site": "/products/leitor?utm_source=instagram&utm_campaign=leitor"}
        corpo = json.dumps(pedido).encode()
        assinatura = base64.b64encode(hmac.new(SEGREDO.encode(), corpo, hashlib.sha256).digest()).decode()
        resposta = self.cliente.post("/api/integracoes/shopify/webhook", data=corpo, headers={
            "X-Shopify-Hmac-Sha256": assinatura, "X-Shopify-Topic": "orders/paid"})
        self.assertEqual(resposta.get_json(), {"situacao": "registrado", "teste_id": self.teste_id})
        self.assertEqual(self.dia(data_do_pedido("2026-10-03T10:00:00-03:00"))["vendas"], 1)
        errada = self.cliente.post("/api/integracoes/shopify/webhook", data=corpo,
                                   headers={"X-Shopify-Hmac-Sha256": "invalida"})
        self.assertEqual(errada.status_code, 401)

    def test_lista_de_pedidos_exige_login_e_mostra_so_os_meus(self):
        self.avisar_nuvemshop(1008)
        self.cliente.post("/api/auth/logout")
        self.assertEqual(self.cliente.get("/api/integracoes/pedidos").status_code, 401)
        self.cliente.post("/api/auth/cadastro", json={"nome": "B", "email": "b@exemplo.com", "senha": "segredo123"})
        self.assertEqual(self.cliente.get("/api/integracoes/pedidos").get_json(), [])

    def test_alertas_no_resumo_do_teste(self):
        """Dado 02/10 com conversão de 10% e 03/10 com 2%, Então aparece o alerta de queda de conversão;
        e com CPA acima da margem, o alerta de CPA."""
        self.cliente.put(f"/api/testes/{self.teste_id}/metricas/2026-10-02",
                         json={"investimento": 30, "visitas": 50, "vendas": 5})
        self.cliente.put(f"/api/testes/{self.teste_id}/metricas/2026-10-03",
                         json={"investimento": 600, "visitas": 50, "vendas": 1})  # 630 / 6 = CPA 105 > 90
        alertas = self.cliente.get(f"/api/testes/{self.teste_id}").get_json()["alertas"]
        self.assertEqual([a["codigo"] for a in alertas], ["cpa_acima_da_margem", "conversao_caiu"])
        painel = self.cliente.get("/api/painel").get_json()
        self.assertEqual(len(painel["produtos"][0]["teste"]["alertas"]), 2)


if __name__ == "__main__":
    unittest.main()
