# Módulo 4 · Defesa inbound

> Aulas 4.1 a 4.4 em [academy.soaone.com.br](https://academy.soaone.com.br/#aula-4-0)

Tudo o que entra no sistema é suspeito até prova em contrário: a mensagem do usuário, o PDF que ele anexou e a página que o agente buscou. Este lab constrói as quatro barreiras que ficam antes do modelo.

## Exercícios

| # | O que fazer | Aula |
|---|---|---|
| 1 | `FiltroEscopo.eh_do_escopo`: rejeitar cedo o que não é do negócio | 4.1 |
| 2a, 2b | `pontuar_injecao` e `verificar_entrada`: sinais ponderados, desofuscação e limiar | 4.2 |
| 3a–3c | `validar_cpf` e `MascaradorPII`: token estável por valor, mapa só na sua aplicação, `revelar` para as ferramentas | 4.3 |
| 4a–4c | `envolver_externo`, `ler_conteudo_externo` e `ferramentas_disponiveis`: conteúdo externo como dado, com perda de privilégios | 4.4 |

```bash
pytest labs/m04-defesa-inbound
```

## Sobre o detector

Regex pega o ataque preguiçoso e ensina o formato do problema, mas **não existe filtro perfeito**. Os testes trazem 7 ataques e 5 mensagens legítimas parecidas ("Quero *ignorar* o frete expresso"). Depois de passar em todos, tente escrever um ataque que fure o seu detector. Você vai conseguir. É por isso que a aula 4.4 importa mais que a 4.2: a arquitetura precisa aguentar o dia em que o filtro falhar.

Em produção, combine três coisas:
- estas heurísticas, que são baratas e rodam em microssegundos;
- um classificador dedicado, que é um modelo pequeno treinado para detectar injeção;
- o desenho de menor privilégio, que é o tema do módulo 7.

## Pronto quando

- [ ] Os 30 testes passam.
- [ ] Nenhum CPF, e-mail ou telefone chega ao provedor ou ao log em texto claro.
- [ ] Depois de ler um documento externo, o agente não consegue mais chamar ferramentas que escrevem.

> Não existe filtro perfeito; existe arquitetura que aguenta a falha.
