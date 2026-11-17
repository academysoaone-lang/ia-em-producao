"""Módulo 8 · Prompt engineering para devs · Exercício

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
    # TODO 1: se a soma de tokens do histórico couber no limite, devolva-o sem mudar.
    #   Senão, peça ao llm um resumo das mensagens ANTIGAS (todas menos as `manter_ultimas`):
    #   system = PROMPT_RESUMO; user = transcrição "papel: conteúdo" uma por linha.
    #   Devolva [{"role": "system", "content": "Resumo da conversa até aqui:\n" + resumo}]
    #   seguido das `manter_ultimas` mensagens mais recentes, intactas.
    raise NotImplementedError("TODO 1")


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
        # TODO 2: monte o texto com estas tags, nesta ordem, uma seção por bloco
        #   (separe blocos com linha em branco; pule seções vazias):
        #   <papel>...</papel>
        #   <tarefa>...</tarefa>
        #   <contexto nome="NOME">...</contexto>      (um por item; conteúdo passa por escapar())
        #   <exemplos>
        #   <exemplo><entrada>...</entrada><saida>...</saida></exemplo>   (um por linha)
        #   </exemplos>
        #   <formato>Responda só com JSON com as chaves:
        #   - chave: descrição            (uma por linha)
        #   </formato>
        #   Com valvula_de_escape, o último bloco é:
        #   "Se faltar informação para responder com segurança, não invente: responda
        #   {\"pergunta\": \"<o que você precisa saber>\"}."
        raise NotImplementedError("TODO 2")


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
    # TODO 3: repita até `rodadas` vezes:
    #   a) peça a avaliação: system "Avalie o texto contra cada item. Responda só JSON {item: true|false}.",
    #   user = "Checklist:\n- item...\n\nTexto:\n" + rascunho. Faça json.loads da resposta.
    #   (Se o JSON vier quebrado, trate todos os itens como false.)
    #   b) se todos os itens forem true, devolva (rascunho, avaliacao).
    #   c) senão, peça a reescrita: user = "Reescreva o texto corrigindo só estes itens:\n- ...\n\nTexto:\n" + rascunho
    #   e use a resposta como novo rascunho.
    #   Ao fim das rodadas, devolva (rascunho, última avaliação).
    raise NotImplementedError("TODO 3")


def metaprompt(objetivo: str, publico: str, restricoes: list[str]) -> str:
    """O modelo escrevendo o próprio prompt. Revise o resultado como revisaria um código."""
    cercas = "\n".join(f"- {r}" for r in restricoes)
    return (f"Escreva um prompt de sistema para um assistente.\nObjetivo: {objetivo}\nPúblico: {publico}\n"
            f"Restrições inegociáveis:\n{cercas}\n\nO prompt deve usar tags para separar papel, tarefa, contexto "
            "e formato; incluir dois exemplos; definir o formato de saída; e ter uma válvula de escape para "
            "quando faltar informação. Devolva só o prompt.")
