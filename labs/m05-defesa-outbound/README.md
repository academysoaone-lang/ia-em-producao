# Módulo 5 · Defesa outbound

> Aulas 5.1 a 5.4 em [academy.soaone.com.br](https://academy.soaone.com.br/#aula-5-0)

O modelo redige; o sistema garante o número. A resposta só chega ao usuário depois de quatro conferências feitas pelo seu código.

## Exercícios

| # | O que fazer | Aula |
|---|---|---|
| 1a, 1b | `ler_reais` e `validar_valores`: preço citado conferido contra o catálogo, desconto acima do limite barrado | 5.1 |
| 2 | `moderar`: categorias proibidas, com palavra inteira ("burro" não casa com "burrocracia") | 5.2 |
| 3 | `checar_grounding`: cada afirmação cita `[n]` e se apoia no trecho citado | 5.3 |
| 4a, 4b | `dominio_permitido` e `sanitizar_saida`: HTML escapado e links só de domínios aprovados, inclusive contra `soaone.com.br.golpe.com` e `soaone.com.br@golpe.com` | 5.4 |

```bash
pytest labs/m05-defesa-outbound
```

## Por que no seu código, e não no prompt

"Nunca invente preços" no prompt é um pedido. `validar_valores` é uma trava: mesmo que o modelo erre, a resposta com o preço errado não sai. A mesma lógica vale para links. O modelo pode ter lido um link de phishing num e-mail (injeção indireta, módulo 4), mas `sanitizar_saida` não o deixa chegar ao usuário.

## Desafio extra

Ligue o `checar_grounding` à saída do RAG do módulo 1. Para as frases que ele marcar, chame um segundo modelo que classifique cada uma como *apoiada*, *contradita* ou *sem apoio*, usando os trechos como referência.

## Pronto quando

- [ ] Os 18 testes passam.
- [ ] Nenhum preço, desconto ou link da resposta depende só da boa vontade do modelo.

> A saída do modelo é input não confiável.
