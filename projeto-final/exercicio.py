"""Projeto final · Atendente da Loja soaone com os 13 guardrails · Exercício

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

FONTE = "exercicio"   # troque para "solucao" para ver o atendente de referência funcionando

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
        # TODO 1: nesta ordem, levantando Bloqueio(nome_do_guardrail, detalhe):
        #   1. self.limite.permitir(sessao.cliente_id) falso         -> Bloqueio("rate_limit")
        #   2. self.teto.restante(sessao.cliente_id) <= 0             -> Bloqueio("teto_gasto")
        #   3. self.escopo.eh_do_escopo(mensagem) falso               -> Bloqueio("escopo")
        #   4. verificar_entrada (lab 4) levantar TentativaDeInjecao -> Bloqueio("injecao", str(e))
        #   5. devolva a mensagem mascarada por sessao.mascarador (o provedor nunca vê o CPF).
        raise NotImplementedError("TODO 1")

    # ------------------------------------------------------------ etapa 2 · contexto
    def _contexto(self, sessao: SessaoCliente, texto: str) -> tuple[list[Mensagem], list[str], list[str]]:
        """Guardrails 5 e 12: RAG com permissão e canary no prompt."""
        # TODO 2: monte as mensagens para o modelo.
        #   - Busque no self.indice com os grupos DA SESSÃO e fique com pontuação >= 0.2.
        #   - system = inserir_canary(SISTEMA, self.canary)  (lab 6).
        #   - Depois, as últimas 6 mensagens de sessao.historico (memória, lab 1).
        #   - user: se houver trechos, "<contexto>\n[1] ...\n[2] ...\n</contexto>\n\nPergunta: " + texto;
        #   senão, só o texto.
        #   Devolva (mensagens, lista de textos dos trechos, lista ordenada dos doc_id usados).
        raise NotImplementedError("TODO 2")

    # ------------------------------------------------------------ etapa 3 · agente
    def _executar_ferramenta(self, sessao: SessaoCliente, nome: str, argumentos: dict) -> dict:
        """Guardrails 6 e 7: argumentos validados, identidade da sessão, política e aprovação humana."""
        # TODO 3a: devolva o resultado (dict) que vai para o modelo:
        #   - ferramenta fora de ESQUEMAS -> {"erro": "ferramenta desconhecida"};
        #   - validar_argumentos (lab 2) falhou -> {"erro": str(e)};
        #   - revele PII nos argumentos de texto (sessao.mascarador.revelar), porque a ferramenta precisa do valor real;
        #   - política (lab 7) com Contexto(sessao.cliente_id, sessao.papel, "producao"):
        #   negar   -> {"erro": f"não autorizado: {motivo}"}
        #   aprovar -> crie o pedido na self.aprovacoes e devolva
        #   {"status": "aguardando aprovação humana", "protocolo": id}
        #   permitir-> FUNCOES[nome](**argumentos, cliente_id=sessao.cliente_id)
        raise NotImplementedError("TODO 3a")

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
        # TODO 4: nesta ordem, levantando Bloqueio(nome, detalhe):
        #   1. verificar_vazamento(resposta, self.canary)          -> Bloqueio("canary")
        #   2. moderar(resposta) com alguma categoria               -> Bloqueio("moderacao", categorias)
        #   3. validar_valores(resposta, CATALOGO) com problemas    -> Bloqueio("validacao", problemas)
        #   4. se houver trechos e checar_grounding achar frase sem apoio -> Bloqueio("grounding", frases)
        #   5. sanitizar_saida(resposta, DOMINIOS_PERMITIDOS)
        #   6. revele a PII (o cliente pode ver o próprio CPF; o provedor e o log, não) e devolva.
        raise NotImplementedError("TODO 4")


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
