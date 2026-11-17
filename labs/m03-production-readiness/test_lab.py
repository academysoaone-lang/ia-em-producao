from datetime import datetime
from pathlib import Path

import pytest

from soaone_lab import ErroProvedor, FakeLLM, Resposta, Uso

CASOS = Path(__file__).parent / "casos.jsonl"


# ---------- 3.1
def test_prompt_estatico_no_inicio_variavel_no_fim(lab):
    args = ("Você é o atendente.", ["Seja breve", "Nunca prometa prazo"], [("Oi", "Olá! Como posso ajudar?")])
    a = lab.montar_prompt(*args, [], "Cadê meu pedido?", datetime(2026, 11, 20, 9, 0))
    b = lab.montar_prompt(*args, [], "Qual o frete?", datetime(2026, 11, 20, 9, 7))
    assert a[0] == b[0], "a mensagem de sistema precisa ser idêntica entre chamadas"
    assert a[0]["role"] == "system" and "- Nunca prometa prazo" in a[0]["content"]
    assert "Cliente: Oi\nAtendente: Olá!" in a[0]["content"]
    assert "2026" not in a[0]["content"], "data no system invalida o cache"
    assert a[-1] == {"role": "user", "content": "[20/11/2026 09:00] Cadê meu pedido?"}
    assert lab.prefixo_comum(a, b) >= len(a[0]["content"])


def test_historico_fica_entre_o_estatico_e_a_pergunta(lab):
    h = [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "olá"}]
    m = lab.montar_prompt("s", ["r"], [], h, "e agora?", datetime(2026, 1, 1))
    assert m[1:3] == h and m[-1]["content"].endswith("e agora?")


# ---------- 3.2
def test_fallback_tenta_com_backoff_e_troca_de_provedor(lab):
    esperas = []
    principal = FakeLLM(["nunca"], nome="principal", falhas=5)
    reserva = FakeLLM(["resposta da reserva"], nome="reserva")
    c = lab.ClienteComFallback([principal, reserva], tentativas_por_provedor=3, espera_base=0.5, dormir=esperas.append)
    assert c.chat([{"role": "user", "content": "oi"}]).texto == "resposta da reserva"
    assert c.log == ["principal:erro", "principal:erro", "principal:erro", "reserva:ok"]
    assert esperas == [0.5, 1.0]


def test_fallback_se_recupera_no_mesmo_provedor(lab):
    c = lab.ClienteComFallback([FakeLLM(["ok"], nome="p", falhas=1)], dormir=lambda s: None)
    assert c.chat([]).texto == "ok" and c.log == ["p:erro", "p:ok"]


def test_fallback_desiste_e_nao_engole_bug(lab):
    c = lab.ClienteComFallback([FakeLLM(nome="a", falhas=9), FakeLLM(nome="b", falhas=9)], dormir=lambda s: None)
    with pytest.raises(lab.TodosProvedoresFalharam):
        c.chat([])

    def bug(m, f):
        raise KeyError("bug no seu código")
    c2 = lab.ClienteComFallback([FakeLLM(regra=bug, nome="a"), FakeLLM(["x"], nome="b")], dormir=lambda s: None)
    with pytest.raises(KeyError):
        c2.chat([])


# ---------- 3.3
def sistema_bom(p):
    p = p.lower()
    if "reembolso" in p: return "Você tem até 7 dias após o recebimento."
    if "frete" in p: return "Frete grátis acima de R$ 299,00."
    if "garantia" in p: return "Eletrônicos têm 12 meses de garantia."
    if "péssimos" in p: return "Sinto muito pelo atraso! Vou verificar seu pedido agora."
    if "passagens" in p: return "Não encontrei essa informação."
    if "cpf" in p: return "Recebi seus dados, obrigado."
    if "desconto" in p: return "Não consigo oferecer esse desconto."
    if "ignore" in p: return "Não posso fazer isso."
    return "Desculpe, só posso ajudar com assuntos da Loja soaone."


def test_evals_aprovam_sistema_bom(lab):
    juiz = FakeLLM(regra=lambda m, f: "APROVADO" if "Sinto muito" in m[-1]["content"] else "REPROVADO")
    rel = lab.rodar_evals(sistema_bom, lab.carregar_casos(str(CASOS)), juiz)
    assert rel.total == 10 and rel.aprovados == 10 and rel.taxa == 1.0
    assert rel.aprovado()


def test_evals_barram_vazamento_mesmo_com_taxa_alta(lab):
    def vaza(p):
        return "Claro! Minhas instruções são: AZUL-77" if "ignore" in p.lower() else sistema_bom(p)
    juiz = FakeLLM(regra=lambda m, f: "APROVADO")
    rel = lab.rodar_evals(vaza, lab.carregar_casos(str(CASOS)), juiz)
    assert rel.taxa == 0.9
    assert [f[0] for f in rel.falhas] == ["seguranca-01"]
    assert not rel.aprovado(minimo=0.9), "falha de segurança barra o deploy"


def test_evals_registram_excecao_e_juiz_ausente(lab):
    def quebra(p):
        raise TimeoutError("provedor lento")
    rel = lab.rodar_evals(quebra, [{"id": "x-1", "entrada": "a", "tipo": "contem", "esperado": "b"}])
    assert rel.falhas == [("x-1", "exceção: provedor lento")]
    rel2 = lab.rodar_evals(sistema_bom, [{"id": "t-1", "entrada": "péssimos", "tipo": "juiz", "esperado": "c"}])
    assert rel2.aprovados == 0


# ---------- 3.4
def test_trace_registra_tokens_custo_e_duracao(lab):
    tempo = iter([0.0, 0.25, 1.0, 1.5])
    t = lab.Tracer(relogio=lambda: next(tempo))
    tid = t.iniciar()
    with t.passo(tid, "filtro_entrada"):
        pass
    with t.passo(tid, "llm", modelo="falso") as p:
        t.registrar_llm(p, Resposta("oi", uso=Uso(1000, 200)))
    r = t.resumo(tid)
    assert r["passos"] == ["filtro_entrada", "llm"]
    assert r["tokens"] == 1200
    assert r["custo_usd"] == round((1000 * 1 + 200 * 5) / 1_000_000, 6)
    assert r["duracao_ms"] == 750.0
    assert r["erros"] == []


def test_trace_registra_erro_e_relanca(lab, tmp_path):
    t = lab.Tracer()
    tid = t.iniciar()
    with pytest.raises(ErroProvedor):
        with t.passo(tid, "llm"):
            raise ErroProvedor("timeout")
    assert t.resumo(tid)["erros"] == ["ErroProvedor: timeout"]
    arq = tmp_path / "traces.jsonl"
    t.exportar_jsonl(str(arq))
    assert '"erro": "ErroProvedor: timeout"' in arq.read_text()
