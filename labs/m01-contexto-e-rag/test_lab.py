from pathlib import Path

import pytest

from soaone_lab import FakeLLM

DOCS = Path(__file__).parent / "docs"


@pytest.fixture
def indice(lab):
    ix = lab.Indice()
    for d in lab.carregar_documentos(DOCS):
        ix.adicionar(d)
    return ix


# ---------- 1.1 memória
def test_conversa_lembra_porque_reenvia_o_historico(lab):
    llm = FakeLLM()
    c = lab.Conversa(llm, "Você é o atendente.")
    c.perguntar("Oi, meu nome é Ana.")
    assert "Ana" in c.perguntar("Como eu me chamo?")
    ultima = llm.chamadas[-1]
    assert ultima[0] == {"role": "system", "content": "Você é o atendente."}
    assert [m["role"] for m in ultima] == ["system", "user", "assistant", "user"]
    assert len(c.historico) == 4


def test_janela_descarta_o_mais_antigo_e_mantem_o_sistema(lab):
    llm = FakeLLM()
    c = lab.Conversa(llm, "sistema", max_tokens_historico=30)
    for i in range(10):
        c.perguntar(f"mensagem número {i} " + "x" * 40)
    enviadas = llm.chamadas[-1]
    assert enviadas[0]["role"] == "system"
    assert enviadas[-1]["content"].startswith("mensagem número 9")
    assert not any("número 0" in m["content"] for m in enviadas)
    assert len(enviadas) < 21


# ---------- 1.4 chunking
def test_fatiar_com_sobreposicao(lab):
    texto = " ".join(f"p{i}" for i in range(100))
    t = lab.fatiar(texto, tamanho=30, sobreposicao=10)
    assert all(len(x.split()) <= 30 for x in t)
    assert t[0].split()[-10:] == t[1].split()[:10]
    assert t[-1].split()[-1] == "p99"
    assert len(t) == 5


def test_fatiar_casos_de_borda(lab):
    assert lab.fatiar("", 10, 2) == []
    assert lab.fatiar("uma frase curta", 10, 2) == ["uma frase curta"]
    with pytest.raises(ValueError):
        lab.fatiar("a b c", 5, 5)


# ---------- 1.3 / 1.4 busca
def test_busca_encontra_o_documento_certo(indice):
    assert indice.buscar("Qual o prazo para pedir reembolso?", ["publico"])[0][1].doc_id == "reembolso"
    assert indice.buscar("A garantia cobre queda do celular?", ["publico"])[0][1].doc_id == "garantia"
    assert indice.buscar("Como funciona o frete grátis?", ["publico"])[0][1].doc_id == "frete"


def test_busca_ordena_e_respeita_k(indice):
    r = indice.buscar("frete grátis", ["publico"], k=2)
    assert len(r) == 2 and r[0][0] >= r[1][0]


def test_filtro_de_permissao_vem_antes_da_busca(indice):
    publico = indice.buscar("faixa salarial atendente", ["publico"], k=20)
    assert all("rh" not in t.grupos for _, t in publico)
    rh = indice.buscar("faixa salarial atendente", ["publico", "rh"])
    assert rh[0][1].doc_id == "rh-faixas-salariais"


def test_palavra_chave(lab):
    assert lab.Indice._palavra_chave("frete grátis", "O frete é grátis acima de R$ 299") == 1.0
    assert lab.Indice._palavra_chave("frete garantia", "O frete é grátis") == 0.5
    assert lab.Indice._palavra_chave("o de a", "qualquer coisa") == 0.0


# ---------- 1.2 RAG
def test_rag_usa_o_contexto_e_cita_a_fonte(lab, indice):
    llm = FakeLLM()
    r = lab.responder(llm, indice, "Qual o prazo para pedir reembolso?", ["publico"])
    assert "reembolso" in r["fontes"] and r["fontes"] == sorted(r["fontes"])
    enviado = llm.chamadas[0]
    assert enviado[0]["role"] == "system" and "contexto" in enviado[0]["content"]
    assert "<contexto>" in enviado[1]["content"] and "[1]" in enviado[1]["content"]
    assert "7 dias" in r["texto"]


def test_rag_sem_trecho_diz_nao_encontrei_e_nao_chama_o_modelo(lab, indice):
    llm = FakeLLM()
    r = lab.responder(llm, indice, "Vocês vendem passagens aéreas?", ["publico"])
    assert r == {"texto": lab.NAO_ENCONTREI, "fontes": []}
    assert llm.chamadas == []


def test_rag_nao_vaza_documento_de_outro_grupo(lab, indice):
    llm = FakeLLM()
    r = lab.responder(llm, indice, "Qual a faixa salarial do atendente?", ["publico"])
    assert r["texto"] == lab.NAO_ENCONTREI
    assert all("2.400" not in str(m) for chamada in llm.chamadas for m in chamada)
