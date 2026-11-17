# Módulo 1 · O cérebro expandido: contexto, RAG e embeddings

> Aulas 1.1 a 1.4 em [academy.soaone.com.br](https://academy.soaone.com.br/#aula-1-0)

Memória e conhecimento são responsabilidade da aplicação, não do modelo. Neste lab você constrói um RAG completo sem nenhuma biblioteca de RAG, para entender cada peça antes de terceirizá-la.

## O que tem aqui

| Arquivo | Para quê |
|---|---|
| `docs/` | Base de conhecimento da Loja soaone: reembolso, frete e garantia (grupo `publico`) e faixas salariais (grupo `rh`, confidencial) |
| `exercicio.py` | Onde você trabalha |
| `solucao.py` | Referência. Olhe só depois de tentar |
| `test_lab.py` | Os critérios de pronto |

## Exercícios

| # | O que fazer | Aula |
|---|---|---|
| 1a, 1b | `Conversa`: guardar o histórico, reenviá-lo a cada chamada e cortar pela janela de tokens | 1.1 |
| 2 | `fatiar`: chunking com sobreposição | 1.4 |
| 3a, 3b | `Indice.buscar`: busca híbrida (vetor + palavra-chave) com **filtro de permissão antes da busca** | 1.3, 1.4 |
| 4 | `responder`: RAG com citação `[n]` e saída "não encontrei" sem chamar o modelo | 1.2 |

```bash
pytest labs/m01-contexto-e-rag
```

## Sobre o embedder

O `HashEmbedder` da `soaone_lab` transforma radicais e bigramas em um vetor de 512 posições. Ele roda offline e mostra o pipeline inteiro, mas **não entende sinônimos**: "devolver" não encontra "reembolso". Por isso a busca híbrida mistura vetor e palavra-chave.

Desafio extra: troque por embeddings de verdade (do seu provedor ou `sentence-transformers`). A interface é só `embed(texto) -> list[float]`. Depois compare os resultados com perguntas como "Quanto tempo tenho para devolver?".

## Pronto quando

- [ ] Os 11 testes passam.
- [ ] A pergunta sobre salário, feita por um usuário do grupo `publico`, nunca chega ao modelo com o trecho confidencial.
- [ ] Uma pergunta fora da base devolve "não encontrei", e o modelo não é chamado.

> Um RAG sem filtro de permissão é vazamento de dados com interface simpática.
