# Pipeline de conhecimento — L-ai

A instalação padrão continua **Ollama + Open WebUI**, compatível com CPU/16 GB. Estes recursos são opt-in: só use web scraping com autorização e observe direitos autorais, `robots.txt` e termos de uso.

## 1. Validar o fluxo RAG real (manual, base descartável)

1. Crie uma base de teste em Open WebUI e uma chave API local.
2. Execute `L_AI_INTEGRATION=1 python -m unittest tests.test_webui_integration -v`.
3. Vincule o documento ao chat e pergunte uma frase específica da amostra.
4. Confirme conteúdo, origem e a ausência de falsos positivos em perguntas de controle.
5. Confira manualmente que uma atualização substitui a passagem recuperada, e exclua o arquivo de teste pela UI.

O teste de API valida upload, processamento e vínculo; **não é um teste de recuperação semântica**. A métrica offline em `ingest.evaluate` mede ranking apenas se você fornecer resultados recuperados reais.

## 2. Descoberta por sitemap.xml

```bash
python -m ingest.cli \
  --sitemap https://example.org/sitemap.xml \
  --allow-domain example.org --max-pages 25 --dry-run
```

Índices aninhados até cinco mapas, no máximo 100 URLs e 2 MiB por sitemap. Apenas HTTPS autorizado, sem redirecionamentos, DNS/IP privado e com `robots.txt` obrigatório. Para XMLs com DTD/entidades externas a análise falha com segurança; arquivos `.xml.gz` ainda não são suportados. Páginas de um sitemap são coletadas individualmente, sem recursão; combine com `--crawl` quando também tiver URLs iniciais explícitas.

## 3. Importar PDF remoto

```bash
python -m ingest.cli --remote-pdf https://example.org/documento.pdf \
  --allow-domain example.org --dry-run
```

Somente PDFs explicitamente passados, em HTTPS 443, permitidos por `robots.txt`; não há coleta automática de arquivos apontados pelas páginas nesta entrega. Máximo de 30 MiB, 500 páginas e 2 milhões de caracteres extraídos. A assinatura do arquivo é verificada. O texto é enviado para a base Knowledge quando removido `--dry-run`.

## 4. OCR local

Instale os pacotes de idioma do Tesseract no Linux:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por tesseract-ocr-eng
python -m ingest.cli --file ~/Livros/escaneado.pdf --ocr --dry-run
```

OCR é executado somente em páginas sem texto selecionável, em resolução de 120 DPI, com timeout de 45 segundos por página e limite de 100 páginas processadas. Sem `--ocr` o comportamento anterior é mantido. EPUB não exige OCR.

## 5. Atualização incremental e agenda

Uma nova execução busca as páginas autorizadas e calcula SHA-256 do texto. **Se o hash não mudou, a API não reindexa aquele arquivo.** Mudanças são reprocessadas pelo fluxo retomável. Este é um mecanismo incremental de indexação, *não* de economia de tráfego HTTP por ETag.

Para executar diariamente às 03:00 no cron do próprio computador:

```cron
0 3 * * * cd /home/USUARIO/L-ai && /usr/bin/flock -n /tmp/lai-ingest.lock /home/USUARIO/L-ai/.venv/bin/python -m ingest.cli --urls-file urls.txt --allow-domain example.org >> /home/USUARIO/lai-ingest.log 2>&1
```

Mude o diretório, domínio, parâmetros e caminhos para sua instalação. Configure `OPEN_WEBUI_API_KEY` e `OPEN_WEBUI_KNOWLEDGE_ID` em um ambiente restrito do serviço, **sem adicionar credenciais ao Git nem à linha de comando**. A agenda é opcional e não é criada automaticamente. O `flock` impede duas execuções concorrentes, condição não suportada pelo SQLite atual.

## 6. Metadados bibliográficos

Para PDF são preservados título, autor e cabeçalhos por página; para EPUB, título e autor quando declarados pelo arquivo. Nas páginas web preserva-se URL, título e data de coleta. Para citar edição, tradutor ou ano com segurança, acrescente esses metadados à fonte original ou a um catálogo bibliográfico curado: o pipeline **não deve inventá-los**.

## 7. Métricas e busca híbrida

```bash
python -m ingest.evaluate tests/fixtures/retrieval_cases.json
```

Arquivo JSON: objetos com `relevant_sources` (lista de identificadores de origem verdadeiros) e `retrieved_sources` (ordem de recuperação registrada do Open WebUI). Retorna `hit_at_k` e `mrr`. A fixture contém apenas dados sintéticos e demonstra a ferramenta, **não mede o desempenho real do L-ai**.

O Open WebUI tem configurações de busca híbrida e reranking que podem ser habilitadas na interface, dependendo da versão; ajuste e compare métricas antes de fixar configuração. Nenhum serviço vetorial ou reranker adicional é instalado automaticamente para preservar 16 GB de RAM.

## Limites

- Conteúdo malformado e PDFs não confiáveis devem preferencialmente ser processados em ambiente isolado.
- Nem a validação de HTTP da API nem um teste de ranking sintético prova recuperação vetorial no chat.
- Coleta de site não implica permissão para redistribuir material protegido.
