"""Projeto final · Atendente da Loja soaone com os 13 guardrails · Solução de referência

Você vai ligar as peças que construiu nos labs 1 a 7 num único atendente. O método
`responder` (já pronto) mostra o caminho da mensagem; você implementa as quatro etapas:

    _entrada  ->  _contexto  ->  _agente  ->  _saida

Por padrão o projeto usa o SEU código dos labs (componentes("exercicio")).
Teste com: pytest projeto-final
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from componentes import componentes  # noqa: E402
from loja import CATALOGO, ESQUEMAS, FUNCOES, SISTEMA, TERMOS_DO_DOMINIO, modelo_da_loja  # noqa: E402

from soaone_lab import LLM, Mensagem  # noqa: E402

FONTE = "solucao"

RESPOSTAS = {
    "escopo": "Desculpe, só posso ajudar com pedidos, entregas, trocas, reembolsos e produtos da Loja soaone.",
    "injecao": "Não posso fazer isso. Posso ajudar com algo sobre o seu pedido?",
    "rate_limit": "Você enviou muitas mensagens seguidas. Aguarde um minuto e tente de novo.",
    "teto_gasto": "Você atingiu o limite de atendimento automático de hoje. Um atendente humano vai continuar.",
    "saida": "Não consegui montar uma resposta segura para isso. Vou te passar para um atendente humano.",
}
DOMINIOS_PERMITIDOS = ["soaone.com.br"]


class Bloqueio(Exception):
    def __init__(self, guardrail: str, detalhe: str = "", resposta: str | None = None):
        super().__init__(f"{guardrail}: {detalhe}")
        self.guardrail, self.detalhe = guardrail, detalhe
        self.resposta = resposta or RESPOSTAS.get(guardrail, RESPOSTAS["saida"])


@dataclass
class SessaoCliente:
    """Identidade e permissões vêm daqui (do login), nunca do modelo."""
    cliente_id: str
    papel: str = "cliente"
    grupos: list[str] = field(default_factory=lambda: ["publico"])
    historico: list[Mensagem] = field(default_factory=list)
    mascarador: object = None


@dataclass
class Resultado:
    texto: str
    bloqueado_por: str | None
    trace_id: str
    fontes: list[str] = field(default_factory=list)


class Atendente:
    def __init__(self, llm: LLM | None = None, fonte: str = FONTE, limite_usd_dia: float = 0.05,
                 rajada: int = 10, relogio=None, hoje=None):
        c = self.c = componentes(fonte)
        self.llm = c.producao.ClienteComFallback([llm or modelo_da_loja()], dormir=lambda s: None)
        self.tracer = c.producao.Tracer()
        self.escopo = c.entrada.FiltroEscopo(TERMOS_DO_DOMINIO)
        self.indice = c.rag.Indice()
        for d in c.rag.carregar_documentos(c.docs):
            self.indice.adicionar(d)
        kw = {"relogio": relogio} if relogio else {}
        self.limite = c.sistemico.TokenBucket(capacidade=rajada, por_segundo=rajada / 60, **kw)
        self.teto = c.sistemico.TetoDeGasto(limite_usd_dia, **({"hoje": hoje} if hoje else {}))
        self.canary = c.sistemico.gerar_canary()
        self.politica = c.travas.PoliticaFerramentas([
            c.travas.RegraFerramenta("consultar_pedido", "leitura", {"cliente", "atendente"}),
            c.travas.RegraFerramenta("solicitar_reembolso", "escrita", {"cliente", "atendente"}, limite_valor=200),
        ])
        self.aprovacoes = c.travas.FilaAprovacao()
        self.ferramentas = [{"name": n, "description": n.replace("_", " "), "parameters": s} for n, s in ESQUEMAS.items()]

    # ------------------------------------------------------------ caminho de uma mensagem (pronto)
    def responder(self, sessao: SessaoCliente, mensagem: str) -> Resultado:
        if sessao.mascarador is None:
            sessao.mascarador = self.c.entrada.MascaradorPII()
        tid = self.tracer.iniciar()
        try:
            with self.tracer.passo(tid, "entrada"):
                texto = self._entrada(sessao, mensagem)
            with self.tracer.passo(tid, "contexto"):
                mensagens, trechos, fontes = self._contexto(sessao, texto)
            resposta, usou_ferramentas = self._agente(sessao, mensagens, tid)
            with self.tracer.passo(tid, "saida"):
                # resposta que veio de ferramenta não se apoia nos trechos: o grounding vale para o RAG
                final = self._saida(sessao, resposta, [] if usou_ferramentas else trechos)
        except Bloqueio as b:
            self.tracer.traces[tid].append(self.c.producao.Passo("bloqueio", {"guardrail": b.guardrail, "detalhe": b.detalhe}))
            return Resultado(b.resposta, b.guardrail, tid)
        sessao.historico += [{"role": "user", "content": texto}, {"role": "assistant", "content": resposta}]
        return Resultado(final, None, tid, fontes)

    # ------------------------------------------------------------ etapa 1 · entrada
    def _entrada(self, sessao: SessaoCliente, mensagem: str) -> str:
        """Guardrails 1 a 4: rate limit, teto de gasto, escopo, injeção e PII."""
        e = self.c.entrada
        if not self.limite.permitir(sessao.cliente_id):
            raise Bloqueio("rate_limit")
        if self.teto.restante(sessao.cliente_id) <= 0:
            raise Bloqueio("teto_gasto")
        if not self.escopo.eh_do_escopo(mensagem):
            raise Bloqueio("escopo", mensagem[:60])
        try:
            e.verificar_entrada(mensagem)
        except e.TentativaDeInjecao as x:
            raise Bloqueio("injecao", str(x)) from x
        return sessao.mascarador.mascarar(mensagem)

    # ------------------------------------------------------------ etapa 2 · contexto
    def _contexto(self, sessao: SessaoCliente, texto: str) -> tuple[list[Mensagem], list[str], list[str]]:
        """Guardrails 5 e 12: RAG com permissão e canary no prompt."""
        achados = [(s, t) for s, t in self.indice.buscar(texto, sessao.grupos) if s >= 0.2]
        trechos = [t.texto for _, t in achados]
        system = {"role": "system", "content": self.c.sistemico.inserir_canary(SISTEMA, self.canary)}
        if trechos:
            ctx = "\n".join(f"[{i}] {t}" for i, t in enumerate(trechos, 1))
            user = f"<contexto>\n{ctx}\n</contexto>\n\nPergunta: {texto}"
        else:
            user = texto
        mensagens = [system] + sessao.historico[-6:] + [{"role": "user", "content": user}]
        return mensagens, trechos, sorted({t.doc_id for _, t in achados})

    # ------------------------------------------------------------ etapa 3 · agente
    def _executar_ferramenta(self, sessao: SessaoCliente, nome: str, argumentos: dict) -> dict:
        """Guardrails 6 e 7: argumentos validados, identidade da sessão, política e aprovação humana."""
        a, t = self.c.agente, self.c.travas
        if nome not in ESQUEMAS:
            return {"erro": "ferramenta desconhecida"}
        try:
            args = dict(a.validar_argumentos(ESQUEMAS[nome], argumentos))
        except a.ArgumentosInvalidos as e:
            return {"erro": str(e)}
        args = {k: sessao.mascarador.revelar(v) if isinstance(v, str) else v for k, v in args.items()}
        ctx = t.Contexto(sessao.cliente_id, sessao.papel, "producao")
        d = self.politica.autorizar(nome, args, ctx)
        if d.acao == "negar":
            return {"erro": f"não autorizado: {d.motivo}"}
        if d.acao == "aprovar":
            return {"status": "aguardando aprovação humana", "protocolo": self.aprovacoes.solicitar(nome, args, ctx)}
        return FUNCOES[nome](**args, cliente_id=sessao.cliente_id)

    def _agente(self, sessao: SessaoCliente, mensagens: list[Mensagem], tid: str,
                max_passos: int = 4) -> tuple[str, bool]:
        """Loop do agente com trace e custo por passo (lab 3). Devolve (texto, usou_ferramentas)."""
        mensagens = list(mensagens)
        for n in range(max_passos):
            with self.tracer.passo(tid, f"llm_{n + 1}") as p:
                r = self.llm.chat(mensagens, self.ferramentas)
                self.tracer.registrar_llm(p, r)
            try:
                self.teto.registrar(sessao.cliente_id, p.custo_usd)
            except self.c.sistemico.GastoExcedido as e:
                raise Bloqueio("teto_gasto", str(e)) from e
            if not r.ferramentas:
                return r.texto, n > 0
            for ch in r.ferramentas:
                with self.tracer.passo(tid, f"ferramenta:{ch.nome}", argumentos=ch.argumentos):
                    resultado = self._executar_ferramenta(sessao, ch.nome, ch.argumentos)
                mensagens += [{"role": "assistant", "content": "", "tool_call": ch.nome},
                              {"role": "tool", "name": ch.nome, "content": json.dumps(resultado, ensure_ascii=False)}]
        raise Bloqueio("limite_de_passos", f"mais de {max_passos} passos")

    # ------------------------------------------------------------ etapa 4 · saída
    def _saida(self, sessao: SessaoCliente, resposta: str, trechos: list[str]) -> str:
        """Guardrails 8 a 12: canary, moderação, valores, grounding e sanitização."""
        s, sis = self.c.saida, self.c.sistemico
        if sis.verificar_vazamento(resposta, self.canary):
            raise Bloqueio("canary", "o prompt vazou na resposta")
        cats = s.moderar(resposta)
        if cats:
            raise Bloqueio("moderacao", ", ".join(cats))
        problemas = s.validar_valores(resposta, CATALOGO)
        if problemas:
            raise Bloqueio("validacao", "; ".join(problemas))
        if trechos:
            sem_apoio = s.checar_grounding(resposta, trechos)
            if sem_apoio:
                raise Bloqueio("grounding", " | ".join(sem_apoio))
        return sessao.mascarador.revelar(s.sanitizar_saida(resposta, DOMINIOS_PERMITIDOS))


def custo_da_conversa(atendente: Atendente, trace_ids: list[str]) -> dict:
    """Painel de custo por conversa: some os resumos dos traces de cada mensagem."""
    resumos = [atendente.tracer.resumo(t) for t in trace_ids]
    return {"mensagens": len(resumos), "tokens": sum(r["tokens"] for r in resumos),
            "custo_usd": round(sum(r["custo_usd"] for r in resumos), 6)}


if __name__ == "__main__":
    at = Atendente()
    s = SessaoCliente("c1")
    print("Atendente da Loja soaone. Você é o cliente c1 (pedido 123456). Ctrl+C para sair.\n")
    ids = []
    try:
        while True:
            r = at.responder(s, input("você > "))
            ids.append(r.trace_id)
            marca = f"   [bloqueado por: {r.bloqueado_por}]" if r.bloqueado_por else ""
            print(f"loja > {r.texto}{marca}\n")
    except (KeyboardInterrupt, EOFError):
        print("\n", custo_da_conversa(at, ids))
