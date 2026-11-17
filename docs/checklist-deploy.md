# Checklist de deploy em produção

Use esta lista como portão de go-live. Se algum item ficar sem marcar, o agente ainda é uma demo.

| | Portão | Pergunta | Onde praticar |
|---|---|---|---|
| [ ] | Contexto | O ciclo de vida do contexto é gerenciado e a sessão é limpa regularmente? | m01 (`Conversa.janela`), m08 (`compactar_historico`) |
| [ ] | Conhecimento | O RAG filtra por permissão antes da busca e tem saída "não sei"? | m01 (`Indice.buscar`, `responder`) |
| [ ] | Defesas de entrada | Filtro de escopo, detector de injection e mascaramento de PII estão ativos? | m04 |
| [ ] | Defesas de saída | Validação de regras de negócio, moderação, grounding e allowlist de links estão ativos? | m05 |
| [ ] | Travas | Permissões críticas estão garantidas no código (lei) e não dependem do prompt (pedido)? | m02 (identidade da sessão), m07 (`PoliticaFerramentas`) |
| [ ] | Ações irreversíveis | Exigem aprovação humana implementada no despachante? | m07 (`FilaAprovacao`) |
| [ ] | Observabilidade | Cada passo gera trace com tokens, custo e resultado dos guardrails? | m03 (`Tracer`) |
| [ ] | Resiliência | Há retry, fallback para modelo testado e rate limiting por usuário? | m03 (`ClienteComFallback`), m06 (`TokenBucket`, `TetoDeGasto`) |
| [ ] | Testes | Evals e suíte de red teaming rodam a cada mudança de prompt, modelo ou ferramenta? | m03 (`rodar_evals`), m06 (`rodar_red_team`), CI deste repositório |
| [ ] | Raciocínio | Tarefas complexas usam scaffolding (mapear, propor, executar) antes da execução? | m08 (`scaffolding`) |

> Construa sistemas, não apenas prompts.
