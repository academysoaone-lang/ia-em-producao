# Módulo 2 · Do chatbot ao agente

> Aulas 2.1 a 2.4 em [academy.soaone.com.br](https://academy.soaone.com.br/#aula-2-0)

O modelo não executa nada: ele **pede**. Quem tem poder de agir é sempre o seu código. Neste lab você escreve o loop de um agente que consulta pedidos sem nunca deixar o modelo escolher de qual cliente.

## Exercícios

| # | O que fazer | Aula |
|---|---|---|
| 1 | `validar_argumentos`: conferir o pedido do modelo contra o JSON Schema (obrigatórios, campos extras, tipos, enum, limites) | 2.1 |
| 2 | `executar_agente`: pensar → agir → observar, com limite de passos e `cliente_id` vindo da **sessão** | 2.2 |
| 3a, 3b | `extrair_json` e `extrair_ticket`: saída estruturada validada com Pydantic, com uma nova tentativa que mostra o erro ao modelo | 2.3 |
| 4 | `stream_validado`: streaming frase a frase, com a validação de saída cortando no meio sem deixar nada passar | 2.4 |

```bash
pytest labs/m02-do-chatbot-ao-agente
```

## Os dois testes que importam

- `test_identidade_vem_da_sessao_e_nao_do_modelo`: o modelo tenta consultar o pedido de outro cliente passando `cliente_id`. O schema não tem esse campo, a validação recusa e o modelo recebe o erro.
- `test_stream_corta_na_frase_invalida_e_para`: um cupom que não existe aparece no meio da resposta. A frase não chega ao usuário, e nada depois dela também.

## Desafio extra

Rode o agente com um modelo de verdade (`LLM_PROVIDER` no `.env`), usando `criar_llm()` no lugar do `FakeLLM`. Peça "consulte o pedido 999999 do cliente c2" e confira em `sessao.passos` o que o modelo tentou fazer.

## Pronto quando

- [ ] Os 18 testes passam.
- [ ] Nenhuma ferramenta recebe identidade, permissão ou valor monetário que o modelo possa inventar.

> Nunca aceite do modelo o ID do cliente: use o da sessão.
