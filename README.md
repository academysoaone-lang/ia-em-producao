# IA em Produção: Arquitetura e Segurança · Laboratórios

[![testes](https://github.com/academysoaone-lang/ia-em-producao/actions/workflows/testes.yml/badge.svg)](https://github.com/academysoaone-lang/ia-em-producao/actions/workflows/testes.yml)

Os laboratórios do curso gratuito **IA em Produção** da [soaone Academy](https://academy.soaone.com.br). Os vídeos e as aulas interativas ficam no portal. Aqui ficam o código, os exercícios e o projeto final.

> Um LLM sozinho não é um produto. O que transforma esse motor probabilístico em um sistema confiável é a engenharia de software em volta dele.

## Roda sem chave de API e sem custo

Todos os labs usam, por padrão, um **modelo falso, local e determinístico** (`soaone_lab.FakeLLM`). Com ele você não precisa de cartão de crédito, os testes dão sempre o mesmo resultado e os defeitos clássicos de um LLM cru aparecem de propósito: ele esquece, inventa política e obedece a quem escreve "ignore as instruções".

Quando quiser, troque para um modelo de verdade no `.env` (Anthropic, OpenAI ou Ollama local). O código dos labs não muda.

## Começando

Requisitos: Python 3.10 ou mais novo e git.

```bash
git clone https://github.com/academysoaone-lang/ia-em-producao.git
cd ia-em-producao
python -m venv .venv && source .venv/bin/activate   # no Windows: .venv\Scripts\activate
pip install -e .

python labs/m00-a-demo-que-quebra/demo.py   # os sintomas de um LLM cru
python scripts/progresso.py                  # o seu progresso em todos os labs
```

## Como cada lab funciona

```
labs/m04-defesa-inbound/
├── README.md       o objetivo, a tabela de exercícios e o "pronto quando"
├── exercicio.py    onde você trabalha: cada TODO diz o que fazer e em qual aula
├── solucao.py      a referência (tente antes de olhar)
└── test_lab.py     os critérios de pronto
```

```bash
pytest labs/m04-defesa-inbound             # testa o SEU exercicio.py
pytest labs/m04-defesa-inbound --solucao   # testa a solução de referência
pytest                                     # tudo
```

Os testes começam falhando com `NotImplementedError: TODO ...`. O lab termina quando todos passam.

## Os laboratórios

| Módulo | Lab | Você constrói | Testes |
|---|---|---|---|
| 0 | [A demo que quebra](labs/m00-a-demo-que-quebra) | o esqueleto entrada → orquestrador → modelo → saída | 4 |
| 1 | [Contexto e RAG](labs/m01-contexto-e-rag) | memória com janela, chunking, busca híbrida com permissão, "não encontrei" | 11 |
| 2 | [Do chatbot ao agente](labs/m02-do-chatbot-ao-agente) | validação de tool calling, loop do agente, Pydantic, streaming validado | 18 |
| 3 | [Production readiness](labs/m03-production-readiness) | prompt para cache, fallback com backoff, evals que barram deploy, trace com custo | 10 |
| 4 | [Defesa inbound](labs/m04-defesa-inbound) | escopo, detector de injection, máscara de PII, injeção indireta | 30 |
| 5 | [Defesa outbound](labs/m05-defesa-outbound) | validação de preços, moderação, grounding, sanitização de links | 18 |
| 6 | [Proteção sistêmica](labs/m06-protecao-sistemica) | canary token, rate limit, teto de gasto, red team automatizado | 15 |
| 7 | [Regra vs. trava](labs/m07-regra-vs-trava) | política de ferramentas, aprovação humana, bloqueio de comandos destrutivos | 27 |
| 8 | [Prompt engineering](labs/m08-prompt-engineering) | compactação de contexto, prompt com tags, scaffolding, auto-revisão | 9 |
| 9 | [Projeto final](projeto-final) | o atendente da Loja soaone com os 13 guardrails, evals, red team e custo por conversa | 18 |

O projeto final importa o **seu** código dos labs 1 a 7. Se um lab não estiver pronto, o projeto mostra exatamente qual peça falta.

## Material de apoio

- [Checklist de deploy em produção](docs/checklist-deploy.md): os 10 portões de go-live
- [OWASP Top 10 para LLMs × labs](docs/owasp-llm-top10.md)
- E-book gratuito e aulas em vídeo: [academy.soaone.com.br](https://academy.soaone.com.br)

## A biblioteca `soaone_lab`

| Módulo | O que tem |
|---|---|
| `llm.py` | `FakeLLM` (modelo falso programável), `criar_llm()` e os clientes Anthropic, OpenAI e Ollama com a mesma interface `chat(mensagens, ferramentas) -> Resposta` |
| `texto.py` | `normalizar`, `radicais` e o `HashEmbedder`, um embedding offline para ver o pipeline do RAG sem baixar modelo |
| `tokens.py` | contagem aproximada de tokens e custo por tabela de preço |

## Contribuindo

Achou um ataque que fura o detector do lab 4? Abra uma issue com o ataque. Os melhores entram em `labs/m06-protecao-sistemica/ataques.jsonl`, com crédito.

## Licença

Código sob a [licença MIT](LICENSE). Feito por [Claudecir Miranda](https://soaone.com.br) · soaone, Solutions of Architecture #1.
