import pytest


# ---------- 7.1
def test_regras_repetidas_no_fim(lab):
    m = lab.montar_com_reforco("Você é o atendente.", ["Nunca prometa prazo", "Não ofereça desconto"],
                               ["doc A " * 50, "doc B " * 50], "Chega amanhã?")
    assert [x["role"] for x in m] == ["system", "user"]
    assert "- Nunca prometa prazo" in m[0]["content"]
    assert m[1]["content"].endswith("Lembre-se: Nunca prometa prazo; Não ofereça desconto")
    assert m[1]["content"].index("Pergunta: Chega amanhã?") > m[1]["content"].index("doc B")


# ---------- 7.2

@pytest.fixture
def politica(lab):
    return lab.PoliticaFerramentas([
        lab.RegraFerramenta("consultar_pedido", "leitura", {"cliente", "atendente"}),
        lab.RegraFerramenta("reembolsar", "escrita", {"atendente"}, limite_valor=200),
        lab.RegraFerramenta("cancelar_conta", "irreversivel", {"atendente"}),
        lab.RegraFerramenta("rodar_migracao", "escrita", {"dev"}, so_desenvolvimento=True),
    ])


@pytest.mark.parametrize("nome,args,papel,amb,acao,motivo", [
    ("apagar_tudo", {}, "atendente", "producao", "negar", "ferramenta desconhecida"),
    ("reembolsar", {"valor": 50}, "cliente", "producao", "negar", "papel sem permissão"),
    ("rodar_migracao", {}, "dev", "producao", "negar", "bloqueada em produção"),
    ("rodar_migracao", {}, "dev", "desenvolvimento", "permitir", "ok"),
    ("cancelar_conta", {}, "atendente", "producao", "aprovar", "ação irreversível"),
    ("reembolsar", {"valor": 1500}, "atendente", "producao", "aprovar", "valor acima do limite"),
    ("reembolsar", {"valor": 200}, "atendente", "producao", "permitir", "ok"),
    ("consultar_pedido", {"pedido": "1"}, "cliente", "producao", "permitir", "ok"),
])
def test_politica_de_ferramentas(lab, politica, nome, args, papel, amb, acao, motivo):
    d = politica.autorizar(nome, args, lab.Contexto("u1", papel, amb))
    assert (d.acao, d.motivo) == (acao, motivo)


# ---------- 7.3 aprovação
def test_fluxo_de_aprovacao_com_quatro_olhos(lab):
    fila = lab.FilaAprovacao()
    pid = fila.solicitar("reembolsar", {"pedido": "123456", "valor": 1500}, lab.Contexto("ana", "atendente"))
    with pytest.raises(lab.AprovacaoNegada):
        fila.executar(pid, lambda **k: "pago")                       # ainda pendente
    with pytest.raises(lab.AprovacaoNegada):
        fila.decidir(pid, lab.Contexto("ana", "supervisor"), True)    # quem pede não aprova
    with pytest.raises(lab.AprovacaoNegada):
        fila.decidir(pid, lab.Contexto("bia", "atendente"), True)     # papel sem permissão
    p = fila.decidir(pid, lab.Contexto("carla", "supervisor"), True)
    assert p.status == "aprovado" and p.aprovador == "carla"
    assert fila.executar(pid, lambda pedido, valor: f"reembolso de {valor} no pedido {pedido}") == \
        "reembolso de 1500 no pedido 123456"
    with pytest.raises(lab.AprovacaoNegada):
        fila.executar(pid, lambda **k: "de novo")                    # não executa duas vezes


def test_pedido_rejeitado_nao_executa(lab):
    fila = lab.FilaAprovacao()
    pid = fila.solicitar("cancelar_conta", {}, lab.Contexto("ana", "atendente"))
    fila.decidir(pid, lab.Contexto("carla", "supervisor"), False)
    with pytest.raises(lab.AprovacaoNegada):
        fila.executar(pid, lambda: "cancelado")
    with pytest.raises(lab.AprovacaoNegada):
        fila.decidir(pid, lab.Contexto("davi", "supervisor"), True)


# ---------- 7.3 rede de segurança
@pytest.mark.parametrize("cmd", [
    "php artisan migrate:fresh --seed", "psql -c 'DROP DATABASE loja'", "rm -rf /", "rm -rf ~",
    "git push origin main --force", "git push -f", "terraform destroy -auto-approve",
    "kubectl delete namespace loja", "mysql -e 'delete from pedidos;'", "npm test && rm -rf *",
])
def test_destrutivos_bloqueados_ate_em_desenvolvimento(lab, cmd):
    with pytest.raises(lab.ComandoBloqueado):
        lab.verificar_comando(cmd, "desenvolvimento")


@pytest.mark.parametrize("cmd", ["npm test", "php artisan migrate", "git push origin feature/x",
                                 "rm -rf node_modules", "mysql -e 'delete from pedidos where id=3'"])
def test_comandos_normais_em_desenvolvimento(lab, cmd):
    assert lab.verificar_comando(cmd, "desenvolvimento") == cmd


def test_em_producao_o_agente_so_le(lab):
    assert lab.verificar_comando("kubectl get pods | grep api", "producao")
    assert lab.verificar_comando("git log --oneline", "producao")
    for cmd in ("php artisan migrate", "kubectl rollout restart deploy/api", "ls && npm install"):
        with pytest.raises(lab.ComandoBloqueado):
            lab.verificar_comando(cmd, "producao")
