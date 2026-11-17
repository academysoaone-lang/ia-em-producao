"""O domínio da Loja soaone: catálogo, pedidos, ferramentas e o modelo falso da loja."""
from __future__ import annotations

import re

from soaone_lab import ChamadaFerramenta, FakeLLM, Resposta, comportamento_ingenuo

CATALOGO = {"Fone X200": 299.90, "Carregador Turbo": 89.00, "Notebook Pro 14": 6499.00}

PEDIDOS = {  # cliente_id -> pedido -> dados (o endereço existe, mas nenhuma ferramenta o devolve)
    "c1": {"123456": {"status": "em trânsito", "produto": "Fone X200", "valor": 299.90, "endereco": "Rua A, 10"}},
    "c2": {"999999": {"status": "entregue", "produto": "Notebook Pro 14", "valor": 6499.00, "endereco": "Rua B, 20"}},
}

TERMOS_DO_DOMINIO = ["pedido", "entrega", "frete", "reembolso", "devolução", "garantia", "produto", "preço",
                     "pagamento", "boleto", "pix", "cartão", "nota fiscal", "troca", "rastreio", "cadastro",
                     "senha", "cupom", "desconto", "fone", "carregador", "notebook", "compra", "endereço", "site"]

SISTEMA = ("Você é o atendente da Loja soaone. Seja breve e cordial. Responda só sobre pedidos, entregas, "
           "trocas, reembolsos, garantia e produtos da loja. Use apenas o contexto e as ferramentas. "
           "Cite a fonte no formato [n] quando usar o contexto.")

ESQUEMAS = {
    "consultar_pedido": {"type": "object", "properties": {"pedido": {"type": "string"}}, "required": ["pedido"]},
    "solicitar_reembolso": {"type": "object",
                            "properties": {"pedido": {"type": "string"},
                                           "valor": {"type": "number", "minimum": 0},
                                           "motivo": {"type": "string", "enum": ["arrependimento", "defeito"]}},
                            "required": ["pedido", "valor", "motivo"]},
}


def consultar_pedido(pedido: str, cliente_id: str) -> dict:
    p = PEDIDOS.get(cliente_id, {}).get(pedido)
    return {"pedido": pedido, "status": p["status"], "produto": p["produto"]} if p else \
        {"pedido": pedido, "status": "não encontrado para este cliente"}


def solicitar_reembolso(pedido: str, valor: float, motivo: str, cliente_id: str) -> dict:
    p = PEDIDOS.get(cliente_id, {}).get(pedido)
    if not p:
        return {"erro": "pedido não encontrado para este cliente"}
    if valor > p["valor"]:
        return {"erro": "valor maior que o do pedido"}
    return {"pedido": pedido, "status": "reembolso registrado", "valor": valor}


FUNCOES = {"consultar_pedido": consultar_pedido, "solicitar_reembolso": solicitar_reembolso}


def _ultimo(mensagens, papel):
    for m in reversed(mensagens):
        if m["role"] == papel:
            return str(m["content"])
    return ""


def regra_da_loja(mensagens, ferramentas):
    """Um modelo 'razoável, mas falível': usa ferramentas e contexto, e às vezes erra preço,
    oferece desconto que não pode ou cola link de fora. É para isso que os guardrails existem."""
    if mensagens[-1]["role"] == "tool":
        r = mensagens[-1]["content"]
        if "aguardando aprovação" in r:
            return "Seu pedido de reembolso foi enviado para aprovação de um supervisor. Você recebe a resposta por e-mail."
        if "reembolso registrado" in r:
            return "Pronto! Seu reembolso foi registrado e cai em até 10 dias úteis."
        m = re.search(r'"status": "([^"]+)"', r)
        p = re.search(r'"pedido": "(\d+)"', r)
        if m and p:
            return f"O pedido {p.group(1)} está: {m.group(1)}."
        return "Não consegui concluir essa operação. Posso te passar para um atendente?"
    pergunta = _ultimo(mensagens, "user")
    so_pergunta = pergunta.split("Pergunta:")[-1]
    baixa = so_pergunta.lower()
    num = re.search(r"\b(\d{6})\b", so_pergunta)
    if ferramentas and num:
        if "reembolso" in baixa:
            valor = re.search(r"R\$\s?([\d.]+(?:,\d{2})?)", so_pergunta)
            v = float(valor.group(1).replace(".", "").replace(",", ".")) if valor else 0.0
            return Resposta(ferramentas=[ChamadaFerramenta("solicitar_reembolso",
                                                           {"pedido": num.group(1), "valor": v, "motivo": "defeito"})])
        return Resposta(ferramentas=[ChamadaFerramenta("consultar_pedido", {"pedido": num.group(1)})])
    if "desconto" in baixa or "cupom" in baixa:
        return "Consigo um desconto de 30% para você hoje!"
    if "notebook" in baixa and ("preço" in baixa or "custa" in baixa):
        return "O Notebook Pro 14 custa R$ 4.999,00."
    if "fone" in baixa and ("preço" in baixa or "custa" in baixa):
        return "O Fone X200 custa R$ 299,90."
    if "site" in baixa or "link" in baixa or "rastre" in baixa:
        return "Acompanhe em https://soaone.com.br/rastreio ou no https://rastreio-gratis.net/soaone."
    if "<contexto>" in pergunta:
        linha = re.search(r"<contexto>\s*\n(.*?)\n", pergunta, re.S)
        if not linha:
            return "Não encontrei."
        primeira = re.split(r"(?<=[.!?])\s", linha.group(1))[0]
        return f"De acordo com a nossa política: {primeira}"
    return comportamento_ingenuo(mensagens, ferramentas)


def modelo_da_loja() -> FakeLLM:
    return FakeLLM(regra=regra_da_loja, nome="falso")
