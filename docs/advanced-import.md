# P1 — Crawler de sites e importação de PDF/EPUB

Esta etapa amplia o coletor P0 e mantém o uso de **Ollama + Open WebUI**, sem adicionar outros bancos, serviços ou modelos. Compatível com CPU e 16 GB de RAM.

## Preparação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-ingest.txt
export OPEN_WEBUI_API_KEY='SUA_CHAVE'
export OPEN_WEBUI_KNOWLEDGE_ID='ID_DA_BASE'
```

## Crawler autorizado

```bash
# Faça primeiro uma extração de teste, sem indexar:
python -m ingest.cli --url https://example.org/library/index \
  --allow-domain example.org --crawl --max-depth 2 --max-pages 25 --dry-run

# Depois remova --dry-run para atualizar a base Knowledge.
```

O crawler utiliza busca em largura, visita **somente o domínio exato e o diretório da URL inicial**, ignora links externos, recursos binários e `nofollow`; não executa JavaScript. Respeita o `robots.txt`, bloqueia redirecionamentos e IPs privados pelo `SafeFetcher` existente. Profundidade máxima: 3; páginas tentadas: no máximo 100. A configuração padrão é profundidade 2, até 25 páginas.

Um seed como `https://example.org/library/index` permite explorar `/library/`, mas não `/other/`. Para explorar o site inteiro, use uma URL inicial no diretório `/` e certifique-se de ter autorização. Os limites são globais por execução.

A lista `urls.txt` também funciona com `--crawl`, respeitando os limites de entrada existentes.

## Documentos locais

```bash
python -m ingest.cli --file ~/Livros/obra.pdf --dry-run
python -m ingest.cli --file ~/Livros/obra.pdf --file ~/Livros/obra.epub
python -m ingest.cli --directory ~/Livros --max-documents 50
```

A importação de documentos é local e **não exige `--allow-domain`**. O diretório é percorrido recursivamente, mas links simbólicos são rejeitados. São aceitos PDFs com texto selecionável e EPUBs sem criptografia. PDFs são segmentados por número de página, e o título/autor são extraídos quando disponíveis.

Limites por arquivo: PDF até 30 MiB e 500 páginas; EPUB até 20 MiB, 80 MiB descompactados e 500 entradas ZIP; texto extraído até 2 milhões de caracteres; 50 arquivos por operação (configurável até 100). Não há OCR nesta etapa: PDFs compostos apenas por imagens falham explicitamente.

Para bibliotecas de domínio público ou materiais licenciados, preserve metadados bibliográficos e verifique os direitos de uso antes de importar.

## Estado e privacidade

As novas fontes reutilizam o banco SQLite `biblioteca/.web-ingest.sqlite3` e o pipeline retomável do P0; documentos são identificados pela URI de seu caminho local, porém **o caminho absoluto não é incluído no texto indexado**. O estado continua no computador.

Consulte [confiabilidade](reliability.md) e [segurança do scraping](web-ingestion.md).

## Limitações

- Sem OCR, recorte por seções, importação de PDF remoto, crawling JS ou execução agendada.
- Para EPUBs com capítulos em ordem complexa, a ordem de extração é a ordem dos itens da biblioteca e pode diferir da ordem de leitura do `spine`.
- Os testes CI validam parsing, extração, limites e fluxo simulado. A indexação com Open WebUI em execução requer o teste de integração opcional da documentação do P0.
