# Módulo 6 · Proteção sistêmica

> Aulas 6.1 a 6.3 em [academy.soaone.com.br](https://academy.soaone.com.br/#aula-6-0)

Defesas que olham para o sistema inteiro: um alarme que dispara quando o prompt vaza, limites que impedem o seu bot de virar IA gratuita e uma bateria de ataques que roda antes de cada deploy.

## Exercícios

| # | O que fazer | Aula |
|---|---|---|
| 1 | `verificar_vazamento`: achar o canary na saída mesmo disfarçado (espaçado, invertido, em base64) | 6.1 |
| 2a | `TokenBucket.permitir`: limite de requisições ou de tokens por chave, com reposição no tempo | 6.2 |
| 2b | `TetoDeGasto.registrar`: teto diário em dólar por usuário | 6.2 |
| 3 | `rodar_red_team`: rodar a biblioteca `ataques.jsonl` e reprovar com qualquer falha crítica | 6.3 |

```bash
pytest labs/m06-protecao-sistemica
```

## `ataques.jsonl`

A biblioteca tem 10 ataques, em 5 categorias e 3 níveis de severidade. Cada ataque declara os **sinais de falha**, ou seja, o texto que só aparece se o ataque funcionou. Acrescente um ataque novo:
- toda vez que alguém achar um furo;
- toda vez que você ler sobre uma técnica nova.

A biblioteca roda a cada mudança de prompt, de modelo ou de ferramenta. Antes de grandes lançamentos, faça também uma sessão humana: pessoas acham o que a lista não tem.

## Lembrete sobre o canary

O canary **avisa** que o prompt vazou; ele não impede o vazamento. A regra continua: nunca coloque no prompt o que seria um problema se vazasse. Chaves, senhas e regras de desconto ficam no código.

## Pronto quando

- [ ] Os 15 testes passam.
- [ ] Nenhum usuário consegue gastar mais que o teto diário, mesmo abrindo várias sessões.
- [ ] O red team roda no seu CI e barra o deploy com qualquer falha crítica.

> Ataque o seu sistema antes que vire print nas redes.
