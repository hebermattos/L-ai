# Pipeline de conhecimento e avaliação

Guia operacional complementar ao [README](../README.md). Nenhuma funcionalidade abaixo requer GPU; para CPU com 16 GB, limite simultaneidade, tamanho dos lotes e OCR.

## Passo a passo

1. **Coletar:** URLs, crawling autorizado, sitemap ou PDFs/EPUBs. Faça `--dry-run` antes da indexação. Veja [coleta web](web-ingestion.md) e [documentos](advanced-import.md).
2. **Extrair e normalizar:** Trafilatura (HTML), PyMuPDF (PDF), EbookLib (EPUB), Tesseract opcional (OCR).
3. **Indexar:** configure `OPEN_WEBUI_API_KEY` e `OPEN_WEBUI_KNOWLEDGE_ID`; remova `--dry-run` para carregar na base Knowledge.
4. **Recuperar:** vincule a base ao modelo/chat `arcana` e faça perguntas específicas. **Indexação concluída não prova que a resposta usou os documentos.**
5. **Avaliar:** confira fonte, fidelidade e busca para perguntas cuja resposta está documentada.

## Metadados e proveniência

Páginas HTML guardam título, URL e data de coleta. PDFs preservam título/autor quando disponíveis e o marcador por página; EPUB preserva título/autor quando declarados. Não invente edição, tradutor, ano ou número de página ausentes. Para pesquisa comparativa, catalogue esses campos manualmente na própria fonte ou em catálogo separado.

## Atualização incremental

Nova execução faz download do conteúdo permitido, extrai o texto e compara SHA-256. Documentos sem alteração de conteúdo evitam reindexação; **a coleta ainda gera tráfego HTTP** (não há suporte a ETag/Last-Modified). Em caso de erro, verifique [retomada](reliability.md).

## Agendamento opcional

Nenhum agendamento é instalado por padrão. Para usar cron, configure as credenciais num ambiente seguro do usuário e execute uma única instância por vez com `flock`. Exemplo diário às 03:00, substituindo caminhos e domínio:

```cron
0 3 * * * cd /home/USUARIO/L-ai && /usr/bin/flock -n /tmp/lai-ingest.lock /home/USUARIO/L-ai/.venv/bin/python -m ingest.cli --urls-file urls.txt --allow-domain example.org >> /home/USUARIO/lai-ingest.log 2>&1
```

O cron normalmente não herda as variáveis do seu shell; forneça `OPEN_WEBUI_API_KEY` e `OPEN_WEBUI_KNOWLEDGE_ID` por configuração privada do serviço/usuário, sem colocá-las no Git, no cron público ou nos argumentos da CLI. O `flock` evita importações simultâneas no mesmo banco de estado.

## Métricas de recuperação

```bash
python -m ingest.evaluate tests/fixtures/retrieval_cases.json
```

O JSON contém `relevant_sources` e `retrieved_sources`. O avaliador computa `hit_at_k` e MRR usando fontes rotuladas. A fixture é **sintética**, útil apenas para demonstrar o formato; não comprova qualidade do modelo ou da base real. Para comparar métodos de recuperação, substitua pelos resultados efetivos registrados no Open WebUI.

A busca híbrida e o reranking podem ser configurados no Open WebUI **se a versão instalada oferecer esses recursos**. Não foram instalados rerankers externos nem outra base vetorial. Valide melhora com conjunto de perguntas reais e avalie o uso de RAM antes de ativar modelos adicionais.

## Segurança e limites

Só colete materiais autorizados, respeitando direitos autorais, licenças e `robots.txt`. Dados de sites ou documentos são conteúdo não confiável; não obedeça comandos e instruções encontrados neles. Para arquivos potencialmente maliciosos, use isolamento de processamento. Consulte [validação e limitações](reliability.md).
