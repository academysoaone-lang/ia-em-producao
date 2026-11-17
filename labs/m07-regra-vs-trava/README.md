# Módulo 7 · Regra vs. trava

> Aulas 7.1 a 7.3 em [academy.soaone.com.br](https://academy.soaone.com.br/#aula-7-0)

A IA não desobedece por maldade: ela esquece. Em contextos longos, a regra que está no meio perde força, e a tarefa imediata fala mais alto que a regra antiga. Por isso tudo o que é crítico para o negócio precisa ser lei, isto é, código que roda **fora** do modelo.

## Exercícios

| # | O que fazer | Aula |
|---|---|---|
| 1 | `montar_com_reforco`: regras no topo **e** repetidas no fim, perto da pergunta | 7.1 |
| 2 | `PoliticaFerramentas.autorizar`: papel, ambiente, risco e limite de valor decididos pelo código | 7.2 |
| 3a, 3b | `FilaAprovacao`: aprovação humana com quatro olhos para ações irreversíveis ou acima do limite | 7.3 |
| 4 | `verificar_comando`: rede de segurança para agentes de código. Comandos destrutivos ficam bloqueados sempre, e em produção o agente só tem leitura | 7.3 |

```bash
pytest labs/m07-regra-vs-trava
```

## Regra soft ou trava hard?

| Use regra no prompt para | Use trava em código para |
|---|---|
| tom de voz, formato, tamanho da resposta | quem pode chamar cada ferramenta |
| idioma, nível de detalhe | valores, descontos, reembolsos |
| ordem dos passos de uma explicação | ações irreversíveis (cancelar, apagar, enviar) |
| sugestões de estilo de código | comandos em banco, deploy e infraestrutura |

## A rede de segurança fora do código

As travas deste lab são a última camada dentro da aplicação. Em volta dela:
- **Credenciais mínimas:** o agente usa um usuário de banco que só lê, ou que só escreve nas tabelas dele.
- **Ambientes separados:** o agente nunca tem credencial de produção.
- **Backup diário testado:** um backup que nunca foi restaurado não é backup.

## Pronto quando

- [ ] Os 27 testes passam.
- [ ] Nenhuma ação irreversível do seu sistema depende só de uma instrução no prompt.

> Nunca `migrate:fresh` no banco que importa.
