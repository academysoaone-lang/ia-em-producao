import pytest

CATALOGO = {"Fone X200": 299.90, "Carregador Turbo": 89.00, "Notebook Pro 14": 6499.00}


# ---------- 5.1
def test_ler_reais(lab):
    assert lab.ler_reais("de R$ 1.299,90 por R$899 ou R$ 6.499,00") == [1299.9, 899.0, 6499.0]


def test_preco_certo_passa(lab):
    r = "O Fone X200 custa R$ 299,90. O Carregador Turbo sai por R$ 89,00."
    assert lab.validar_valores(r, CATALOGO) == []
    assert lab.garantir_valores(r, CATALOGO) == r


def test_preco_inventado_e_barrado(lab):
    r = "Ótima escolha! O Notebook Pro 14 está por R$ 4.999,00 hoje."
    assert lab.validar_valores(r, CATALOGO) == ["preço errado: R$ 4999.00 para Notebook Pro 14"]
    with pytest.raises(lab.SaidaBloqueada):
        lab.garantir_valores(r, CATALOGO)


def test_desconto_acima_do_limite(lab):
    assert lab.validar_valores("Consigo um desconto de 40% para você!", CATALOGO) == ["desconto acima do permitido: 40%"]
    assert lab.validar_valores("Temos desconto de 10% no Pix.", CATALOGO) == []
    assert lab.validar_valores("A bateria dura 95% do dia.", CATALOGO) == []


def test_valor_sem_produto_nao_e_julgado(lab):
    assert lab.validar_valores("O frete é grátis acima de R$ 299,00.", CATALOGO) == []


# ---------- 5.2
def test_moderacao(lab):
    assert lab.moderar("Você é um idiota") == ["ofensa"]
    assert lab.moderar("Garantimos que nunca vai quebrar, seu IDIOTA") == ["ofensa", "promessa_indevida"]
    assert lab.moderar("A burrocracia do banco atrasou o reembolso") == []
    assert lab.moderar("Em quem votar na eleição?") == ["assunto_proibido"]


# ---------- 5.3
TRECHOS = ["O cliente pode pedir reembolso em até 7 dias corridos após o recebimento do produto.",
           "Todos os eletrônicos têm garantia de 12 meses."]


def test_resposta_fundamentada(lab):
    r = "Você pode pedir reembolso em até 7 dias após o recebimento [1]. Eletrônicos têm garantia de 12 meses [2]. Posso ajudar em algo mais?"
    assert lab.checar_grounding(r, TRECHOS) == []


def test_afirmacao_sem_citacao_ou_inventada(lab):
    r = ("Você pode pedir reembolso em até 7 dias [1]. "
         "Clientes premium têm reembolso em dobro sem análise [1]. "
         "O frete de devolução é sempre grátis para todo o Brasil.")
    assert lab.checar_grounding(r, TRECHOS) == [
        "Clientes premium têm reembolso em dobro sem análise [1].",
        "O frete de devolução é sempre grátis para todo o Brasil.",
    ]


def test_citacao_para_trecho_que_nao_existe(lab):
    assert lab.checar_grounding("A garantia cobre quedas acidentais do aparelho [7].", TRECHOS) != []


# ---------- 5.4
OK = ["soaone.com.br", "academy.soaone.com.br"]


@pytest.mark.parametrize("url,esperado", [
    ("https://soaone.com.br/politicas", True),
    ("https://loja.soaone.com.br/pedido/1", True),
    ("http://academy.soaone.com.br", True),
    ("https://soaone.com.br.golpe.com/login", False),
    ("https://golpe.com/soaone.com.br", False),
    ("https://soaone.com.br@golpe.com", False),
    ("javascript:alert(1)", False),
    ("ftp://soaone.com.br/arquivo", False),
])
def test_dominio_permitido(lab, url, esperado):
    assert lab.dominio_permitido(url, OK) is esperado


def test_sanitizar_escapa_html_e_remove_links(lab):
    t = ('Veja <b>aqui</b>: [nossa política](https://soaone.com.br/politicas) ou '
         '[clique](https://soaone.com.br.golpe.com/pix). Também https://golpe.com/x. '
         '<script>alert(1)</script> e https://academy.soaone.com.br.')
    s = lab.sanitizar_saida(t, OK)
    assert "&lt;b&gt;aqui&lt;/b&gt;" in s and "<script>" not in s
    assert "[nossa política](https://soaone.com.br/politicas)" in s
    assert "clique [link removido]" in s and "golpe.com" not in s
    assert "Também [link removido]." in s
    assert s.endswith("e https://academy.soaone.com.br.")
