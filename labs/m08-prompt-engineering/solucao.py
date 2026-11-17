"""Módulo 8 · Prompt engineering para devs · Solução de referência

Prompt é especificação. Aqui ele vira código testável:
  1. ciclo de vida do contexto: compactar o histórico antes que ele apodreça (aula 8.1);
  2. construtor de prompt com delimitadores, few-shot, formato de saída e válvula de escape (aula 8.2);
  3. scaffolding: mapear, propor, executar (aula 8.3);
  4. auto-revisão contra checklist e metaprompting (aula 8.4).

Teste com: pytest labs/m08-prompt-engineering
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from soaone_lab import LLM, Mensagem, contar_tokens


# ---------------------------------------------------------------- Aula 8.1 · ciclo de vida do contexto
PROMPT_RESUMO = ("Resuma a conversa abaixo em até 8 tópicos: decisões tomadas, fatos sobre o cliente, "
                 "pendências. Não invente nada que não esteja na conversa.")


def compactar_historico(historico: list[Mensagem], llm: LLM, limite_tokens: int = 1500,
                        manter_ultimas: int = 4) -> list[Mensagem]:
    if sum(contar_tokens(m["content"]) for m in historico) <= limite_tokens:
        return historico
    antigas, recentes = historico[:-manter_ultimas], historico[-manter_ultimas:]
    transcricao = "\n".join(f"{m['role']}: {m['content']}" for m in antigas)
    resumo = llm.chat([{"role": "system", "content": PROMPT_RESUMO},
                       {"role": "user", "content": transcricao}]).texto
    return [{"role": "system", "content": "Resumo da conversa até aqui:\n" + resumo}] + recentes


# ---------------------------------------------------------------- Aula 8.2 · delimitadores e few-shot
def escapar(conteudo: str) -> str:
    """Conteúdo de usuário, código ou log não pode abrir nem fechar tags do prompt."""
    return conteudo.replace("<", "&lt;").replace(">", "&gt;")


@dataclass
class Prompt:
    papel: str
    tarefa: str
    contextos: dict[str, str] = field(default_factory=dict)     # nome -> conteúdo (código, log, documento)
    exemplos: list[tuple[str, str]] = field(default_factory=list)
    formato: dict[str, str] = field(default_factory=dict)       # chave do JSON -> descrição
    valvula_de_escape: bool = True

    def montar(self) -> str:
        blocos = [f"<papel>{self.papel}</papel>", f"<tarefa>{self.tarefa}</tarefa>"]
        blocos += [f'<contexto nome="{n}">\n{escapar(c)}\n</contexto>' for n, c in self.contextos.items()]
        if self.exemplos:
            ex = "\n".join(f"<exemplo><entrada>{escapar(e)}</entrada><saida>{escapar(s)}</saida></exemplo>"
                           for e, s in self.exemplos)
            blocos.append(f"<exemplos>\n{ex}\n</exemplos>")
        if self.formato:
            chaves = "\n".join(f"- {k}: {d}" for k, d in self.formato.items())
            blocos.append(f"<formato>Responda só com JSON com as chaves:\n{chaves}\n</formato>")
        if self.valvula_de_escape:
            blocos.append('Se faltar informação para responder com segurança, não invente: responda '
                          '{"pergunta": "<o que você precisa saber>"}.')
        return "\n\n".join(blocos)


# ---------------------------------------------------------------- Aula 8.3 · scaffolding
ETAPAS = ("mapear", "propor", "executar")


def scaffolding(llm: LLM, objetivo: str, restricoes: list[str]) -> dict[str, str]:
    """Mapear -> propor três caminhos -> executar o escolhido. Cada etapa vê a anterior."""
    cercas = "\n".join(f"- {r}" for r in restricoes)
    base = f"Objetivo: {objetivo}\nRestrições:\n{cercas}"
    mapa = llm.chat([{"role": "user", "content": f"{base}\n\nEtapa 1: mapeie o problema. Não proponha solução ainda."}]).texto
    propostas = llm.chat([{"role": "user", "content": f"{base}\n\nMapa:\n{mapa}\n\nEtapa 2: proponha três caminhos, "
                                                      "com prós e contras, e indique o melhor."}]).texto
    execucao = llm.chat([{"role": "user", "content": f"{base}\n\nPropostas:\n{propostas}\n\n"
                                                     "Etapa 3: execute o caminho indicado."}]).texto
    return {"mapear": mapa, "propor": propostas, "executar": execucao}


# ---------------------------------------------------------------- Aula 8.4 · auto-revisão e metaprompting
def revisar_contra_checklist(llm: LLM, rascunho: str, checklist: list[str], rodadas: int = 2) -> tuple[str, dict]:
    """Pede ao modelo para conferir o rascunho item a item e reescrever o que falhar."""
    avaliacao: dict = {}
    itens = "\n".join(f"- {i}" for i in checklist)
    for _ in range(rodadas):
        r = llm.chat([{"role": "system", "content": "Avalie o texto contra cada item. Responda só JSON {item: true|false}."},
                      {"role": "user", "content": f"Checklist:\n{itens}\n\nTexto:\n{rascunho}"}]).texto
        try:
            avaliacao = {i: bool(json.loads(r).get(i, False)) for i in checklist}
        except (json.JSONDecodeError, AttributeError):
            avaliacao = {i: False for i in checklist}
        falhas = [i for i, ok in avaliacao.items() if not ok]
        if not falhas:
            return rascunho, avaliacao
        corrigir = "\n".join(f"- {i}" for i in falhas)
        rascunho = llm.chat([{"role": "user", "content": f"Reescreva o texto corrigindo só estes itens:\n{corrigir}\n\nTexto:\n{rascunho}"}]).texto
    return rascunho, avaliacao


def metaprompt(objetivo: str, publico: str, restricoes: list[str]) -> str:
    """O modelo escrevendo o próprio prompt. Revise o resultado como revisaria um código."""
    cercas = "\n".join(f"- {r}" for r in restricoes)
    return (f"Escreva um prompt de sistema para um assistente.\nObjetivo: {objetivo}\nPúblico: {publico}\n"
            f"Restrições inegociáveis:\n{cercas}\n\nO prompt deve usar tags para separar papel, tarefa, contexto "
            "e formato; incluir dois exemplos; definir o formato de saída; e ter uma válvula de escape para "
            "quando faltar informação. Devolva só o prompt.")
