# OWASP Top 10 para aplicações com LLM (2025) × laboratórios

Cada risco da [lista oficial da OWASP](https://genai.owasp.org/llm-top-10/) tem defesa praticada em pelo menos um lab.

| Código | Risco | Onde este repositório trata |
|---|---|---|
| LLM01 | Prompt Injection | m04 (`pontuar_injecao`, injeção indireta), m07 (travas), projeto final g02 |
| LLM02 | Sensitive Information Disclosure | m01 (permissão no RAG), m04 (`MascaradorPII`), projeto final g03, g05 |
| LLM03 | Supply Chain | m03 (modelo reserva passa nos mesmos evals), m08 (válvula de escape contra pacotes inventados) |
| LLM04 | Data and Model Poisoning | m01 (metadados e grupos na base do RAG), m04 (conteúdo externo como dado) |
| LLM05 | Improper Output Handling | m05 (`sanitizar_saida`, `validar_valores`), m02 (validação com Pydantic) |
| LLM06 | Excessive Agency | m02 (identidade da sessão, limite de passos), m07 (menor privilégio, aprovação humana, `verificar_comando`) |
| LLM07 | System Prompt Leakage | m06 (canary token; nenhum segredo no prompt) |
| LLM08 | Vector and Embedding Weaknesses | m01 (filtro de permissão antes da busca) |
| LLM09 | Misinformation | m05 (`checar_grounding`), m01 (saída "não encontrei") |
| LLM10 | Unbounded Consumption | m06 (`TokenBucket`, `TetoDeGasto`), m02 (limite de passos), m03 (custo no trace) |
