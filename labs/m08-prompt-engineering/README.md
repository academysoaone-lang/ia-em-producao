# Módulo 8 · Prompt engineering para devs

> Aulas 8.1 a 8.4 em [academy.soaone.com.br](https://academy.soaone.com.br/#aula-8-0)

Prompt é especificação, e especificação se versiona e se testa. Este lab transforma as técnicas do módulo em funções com testes, para usar tanto no seu produto quanto no seu dia a dia com assistentes de código.

## Exercícios

| # | O que fazer | Aula |
|---|---|---|
| 1 | `compactar_historico`: quando passar do limite, resumir o antigo e manter as últimas mensagens intactas | 8.1 |
| 2 | `Prompt.montar`: tags delimitadoras, conteúdo escapado, few-shot, formato de saída e válvula de escape | 8.2 |
| — | `scaffolding` (já implementado): mapear, propor três caminhos e executar. Leia o código e rode o teste | 8.3 |
| 3 | `revisar_contra_checklist`: o modelo confere o próprio texto item a item e reescreve só o que falhou | 8.4 |

```bash
pytest labs/m08-prompt-engineering
```

## Para usar no seu dia a dia

- **Uma conversa por tarefa.** Depois de horas, o contexto apodrece. Peça um resumo, feche a conversa e comece uma nova com o resumo.
- **Delimite tudo.** Código, log e documento entram em tags. O teste `test_prompt_com_tags_exemplos_e_formato` mostra um log tentando fechar a tag e dar uma ordem nova.
- **Dê o destino e as cercas, não o roteiro.** Com modelos de raciocínio, bastam o objetivo e as restrições. O `scaffolding` serve para tarefas grandes, em que você quer ver o mapa antes do código.
- **Válvula de escape.** "Se não tiver certeza absoluta, pergunte antes de codificar."

## Pronto quando

- [ ] Os 9 testes passam.
- [ ] Você tem, no seu projeto, um prompt montado por código e coberto por teste, em vez de um texto colado num arquivo.

> Contexto limpo vale mais que prompt longo.
