# Módulo 0 · A demo que quebra

> Aulas 0.1 e 0.2 em [academy.soaone.com.br](https://academy.soaone.com.br/#aula-0-0)

Um LLM sozinho não é um produto. Ele esquece o contexto, inventa dados, obedece a quem escreve o texto mais convincente e fica mais caro a cada turno. Este lab mostra os quatro sintomas e monta o esqueleto que o curso inteiro vai preencher.

## 1. Veja os sintomas

```bash
python labs/m00-a-demo-que-quebra/demo.py
```

Rode também com um modelo de verdade (veja `.env.example`). Os sintomas continuam lá: o modelo falso só os deixa previsíveis.

## 2. Exercícios (`exercicio.py`)

| # | O que fazer | Aula |
|---|---|---|
| 1 | Diga qual camada evita cada sintoma em `SINTOMAS` | 0.2 |
| 2 | Implemente `Pipeline.processar`: entrada → orquestrador → modelo → saída, parando no primeiro bloqueio | 0.2 |

```bash
pytest labs/m00-a-demo-que-quebra            # testa o seu código
pytest labs/m00-a-demo-que-quebra --solucao  # compara com a referência
```

## Pronto quando

- [ ] Os 4 testes passam.
- [ ] Você consegue explicar por que "obedece a 'ignore as instruções'" é problema da **entrada**, e não do modelo.

> Regra no texto é pedido. Trava em código é lei.
