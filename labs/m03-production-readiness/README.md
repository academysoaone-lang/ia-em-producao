# Módulo 3 · Production readiness

> Aulas 3.1 a 3.4 em [academy.soaone.com.br](https://academy.soaone.com.br/#aula-3-0)

O que separa uma demo de um serviço: custo previsível, disponibilidade quando o provedor cai, um teste que barra o deploy e um trace que reproduz qualquer reclamação em minutos.

## Exercícios

| # | O que fazer | Aula |
|---|---|---|
| 1 | `montar_prompt`: estático no começo (sistema, regras, exemplos), variável no fim (histórico, data e pergunta) | 3.1 |
| 2 | `ClienteComFallback.chat`: retry com backoff exponencial, troca de provedor e sem engolir bug | 3.2 |
| 3 | `rodar_evals`: casos `contem`, `nao_contem`, `regex` e `juiz`, mais o portão que barra o deploy com qualquer falha de segurança | 3.3 |
| 4a, 4b | `Tracer.passo` e `Tracer.resumo`: duração, tokens, custo e erro por passo | 3.4 |

```bash
pytest labs/m03-production-readiness
```

## `casos.jsonl`

São 10 casos de exemplo, em quatro categorias: política, fora do escopo, segurança e tom. A regra do curso é que **todo incidente vira um caso de teste**. Comece o seu produto com 30 a 50 casos tirados de conversas reais.

Repare no teste `test_evals_barram_vazamento_mesmo_com_taxa_alta`: 90% de acerto parece ótimo, mas a falha que sobrou é o vazamento do prompt. Taxa média não substitui portão por categoria.

## Desafio extra

- Escreva `ClienteComFallback` com um disjuntor (circuit breaker): depois de N falhas seguidas, pule o provedor principal por 60 segundos.
- Exporte o trace com `exportar_jsonl` e abra no seu visualizador favorito. Ou mande para o OpenTelemetry: o formato de passo já é um *span*.

## Pronto quando

- [ ] Os 10 testes passam.
- [ ] Você sabe dizer quanto custou, em dólar, a última conversa do seu sistema.

> Fallback sem eval troca indisponibilidade por resposta errada.
