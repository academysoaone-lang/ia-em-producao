import json

import pytest

from soaone_lab import ChamadaFerramenta, FakeLLM, Resposta

SCHEMA = {
    "type": "object",
    "properties": {
        "pedido": {"type": "string"},
        "motivo": {"type": "string", "enum": ["arrependimento", "defeito"]},
        "valor": {"type": "number", "minimum": 0, "maximum": 500},
        "urgente": {"type": "boolean"},
    },
    "required": ["pedido", "motivo"],
}


# ---------- 2.1
def test_argumentos_validos_passam(lab):
    args = {"pedido": "123456", "motivo": "defeito", "valor": 99.9, "urgente": False}
    assert lab.validar_argumentos(SCHEMA, args) == args


@pytest.mark.parametrize("args", [
    {"pedido": "123456"},                                         # falta motivo
    {"pedido": "123456", "motivo": "defeito", "cliente_id": "c9"},  # campo extra
    {"pedido": 123456, "motivo": "defeito"},                      # tipo errado
    {"pedido": "1", "motivo": "porque sim"},                      # fora do enum
    {"pedido": "1", "motivo": "defeito", "valor": 9999},          # acima do máximo
    {"pedido": "1", "motivo": "defeito", "valor": True},          # bool não é número
])
def test_argumentos_invalidos_sao_recusados(lab, args):
    with pytest.raises(lab.ArgumentosInvalidos):
        lab.validar_argumentos(SCHEMA, args)


# ---------- 2.2
PEDIDOS = {"c1": {"123456": "em trânsito"}, "c2": {"999999": "entregue"}}


def _ferramentas(lab):
    def status(pedido, cliente_id):
        return {"status": PEDIDOS.get(cliente_id, {}).get(pedido, "pedido não encontrado")}
    return [lab.Ferramenta("status_pedido", "Consulta o status de um pedido do cliente logado",
                           {"type": "object", "properties": {"pedido": {"type": "string"}}, "required": ["pedido"]},
                           status, usa_cliente_da_sessao=True)]


def _pede(nome, **args):
    return Resposta(ferramentas=[ChamadaFerramenta(nome, args)])


def test_loop_executa_a_ferramenta_e_devolve_a_resposta_final(lab):
    llm = FakeLLM([_pede("status_pedido", pedido="123456"), "Seu pedido está em trânsito."])
    s = lab.Sessao("c1")
    assert lab.executar_agente(llm, "Cadê meu pedido 123456?", _ferramentas(lab), s) == "Seu pedido está em trânsito."
    tool = llm.chamadas[1][-1]
    assert tool["role"] == "tool" and json.loads(tool["content"]) == {"status": "em trânsito"}
    assert s.passos == ["status_pedido({'pedido': '123456'})"]


def test_identidade_vem_da_sessao_e_nao_do_modelo(lab):
    # o modelo tenta consultar o pedido de outro cliente passando cliente_id
    llm = FakeLLM([_pede("status_pedido", pedido="999999", cliente_id="c2"), "ok"])
    lab.executar_agente(llm, "pedido 999999", _ferramentas(lab), lab.Sessao("c1"))
    resultado = json.loads(llm.chamadas[1][-1]["content"])
    assert "erro" in resultado and "cliente_id" in resultado["erro"]


def test_sem_cliente_id_ainda_usa_o_da_sessao(lab):
    llm = FakeLLM([_pede("status_pedido", pedido="999999"), "ok"])
    lab.executar_agente(llm, "pedido 999999", _ferramentas(lab), lab.Sessao("c1"))
    assert json.loads(llm.chamadas[1][-1]["content"]) == {"status": "pedido não encontrado"}


def test_ferramenta_desconhecida_vira_erro_para_o_modelo(lab):
    llm = FakeLLM([_pede("apagar_banco"), "desculpe"])
    assert lab.executar_agente(llm, "x", _ferramentas(lab), lab.Sessao("c1")) == "desculpe"
    assert "desconhecida" in llm.chamadas[1][-1]["content"]


def test_limite_de_passos(lab):
    llm = FakeLLM(regra=lambda m, f: _pede("status_pedido", pedido="123456"))
    with pytest.raises(lab.LimiteDePassos):
        lab.executar_agente(llm, "x", _ferramentas(lab), lab.Sessao("c1"), max_passos=3)
    assert len(llm.chamadas) == 3


# ---------- 2.3
def test_extrair_json_tira_as_cercas(lab):
    assert lab.extrair_json('Aqui está:\n```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(lab.SaidaInvalida):
        lab.extrair_json("não sei")


def test_ticket_valido_de_primeira(lab):
    llm = FakeLLM(['{"categoria": "entrega", "prioridade": 3, "resumo": "Pedido atrasado", "pedido": "123456"}'])
    t = lab.extrair_ticket(llm, "meu pedido 123456 não chegou")
    assert t.categoria == "entrega" and t.pedido == "123456"


def test_ticket_invalido_gera_nova_tentativa_com_o_erro(lab):
    llm = FakeLLM(['{"categoria": "urgente", "prioridade": 9, "resumo": "x"}',
                   '```json\n{"categoria": "defeito", "prioridade": 4, "resumo": "Tela quebrada na entrega"}\n```'])
    t = lab.extrair_ticket(llm, "chegou quebrado")
    assert t.categoria == "defeito"
    assert "validação" in llm.chamadas[1][-1]["content"]


def test_ticket_desiste_depois_das_tentativas(lab):
    llm = FakeLLM(["não sei", "também não"])
    with pytest.raises(lab.SaidaInvalida):
        lab.extrair_ticket(llm, "??", tentativas=2)


# ---------- 2.4
def test_stream_entrega_frase_por_frase(lab):
    frags = ["Olá", "! Seu pe", "dido saiu. Chega ", "amanhã."]
    assert list(lab.stream_validado(frags, lambda f: True)) == ["Olá! ", "Seu pedido saiu. ", "Chega amanhã."]


def test_stream_corta_na_frase_invalida_e_para(lab):
    frags = ["O produto custa ", "R$ 10. ", "Use o cupom ", "GRATIS100. ", "Obrigado."]
    saida = list(lab.stream_validado(frags, lambda f: "GRATIS" not in f))
    assert saida[0] == "O produto custa R$ 10. "
    assert "GRATIS" not in "".join(saida) and "Obrigado" not in "".join(saida)
    assert saida[-1].strip().startswith("[resposta interrompida")
