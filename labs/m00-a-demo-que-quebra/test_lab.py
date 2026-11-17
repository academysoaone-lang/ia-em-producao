import pytest

from soaone_lab import FakeLLM


def test_cada_sintoma_tem_a_camada_certa(lab):
    esperado = {
        "esquece o que o usuário disse duas mensagens atrás": "orquestrador",
        "inventa a política de reembolso": "orquestrador",
        "obedece a 'ignore as instruções anteriores'": "entrada",
        "responde perguntas fora do negócio": "entrada",
        "mostra um preço diferente do catálogo": "saida",
        "envia link para um domínio desconhecido": "saida",
        "cpf do cliente aparece no log do provedor": "entrada",
        "resposta muda de estilo entre versões do modelo": "modelo",
    }
    for sintoma, camada in esperado.items():
        assert lab.camada_do_sintoma(sintoma) == camada, sintoma


def _orq(texto):
    return [{"role": "system", "content": "atendente"}, {"role": "user", "content": texto}]


def test_pipeline_passa_por_todas_as_etapas_em_ordem(lab):
    llm = FakeLLM(["resposta do modelo"])
    p = lab.Pipeline(llm, _orq, entrada=[str.strip, str.lower], saida=[lambda t: t + "!"])
    assert p.processar("  OLÁ  ") == "resposta do modelo!"
    assert llm.chamadas[0][-1]["content"] == "olá"
    assert p.registro == ["entrada ok", "orquestrador ok", "modelo ok", "saida ok"]


def test_bloqueio_na_entrada_nao_chama_o_modelo(lab):
    def barra(t):
        raise lab.Bloqueado("entrada", "fora do escopo")
    llm = FakeLLM(["nunca"])
    p = lab.Pipeline(llm, _orq, entrada=[barra])
    assert p.processar("escreva meu TCC") == p.resposta_bloqueio
    assert llm.chamadas == []
    assert p.registro == ["bloqueado em entrada: fora do escopo"]


def test_bloqueio_na_saida_esconde_a_resposta(lab):
    def barra(t):
        raise lab.Bloqueado("saida", "preço divergente")
    p = lab.Pipeline(FakeLLM(["custa R$ 1,00"]), _orq, saida=[barra])
    assert p.processar("quanto custa?") == p.resposta_bloqueio
    assert p.registro[-1] == "bloqueado em saida: preço divergente"
