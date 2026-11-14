# Coleta web para o RAG

Este guia descreve **recursos atuais**. A CLI oferece URLs individuais, listas `urls.txt`, crawler recursivo autorizado, descoberta por sitemap e PDFs remotos fornecidos explicitamente. Extração HTML usa Trafilatura; resultados podem ser enviados à Knowledge Base do Open WebUI.

## Pré-requisitos

Instale dependências e configure a API conforme o [README](../README.md#habilitar-o-rag). Crie `urls.txt` com uma URL HTTPS por linha e comentários iniciados por `#`:

```text
https://example.org/artigo-a
https://example.org/artigo-b
```

```bash
python -m ingest.cli --urls-file urls.txt --allow-domain example.org --dry-run
python -m ingest.cli --url https://example.org/artigo-a --allow-domain example.org --dry-run
```

Para coletar e indexar, remova `--dry-run` depois de definir `OPEN_WEBUI_API_KEY` e `OPEN_WEBUI_KNOWLEDGE_ID`. URLs são deduplicadas; páginas alteradas são reprocessadas usando hash do texto. O estado fica em `biblioteca/.web-ingest.sqlite3`.

## Descoberta de páginas

```bash
python -m ingest.cli --url https://example.org/library/index --allow-domain example.org --crawl --max-depth 2 --max-pages 25 --dry-run
python -m ingest.cli --sitemap https://example.org/sitemap.xml --allow-domain example.org --max-pages 25 --dry-run
```

O crawler só segue links internos dentro do diretório da URL inicial, com profundidade de 0 a 3 e até 100 páginas tentadas por execução. A busca por sitemap aceita índices XML limitados, não segue links arbitrários e também requer um domínio autorizado. `--crawl` sozinho exige uma URL inicial `--url` ou `--urls-file`; usar apenas `--sitemap` não habilita crawling adicional.

A opção `--remote-pdf` importa **somente o PDF explicitamente indicado**, não todos os PDFs linkados pelo site:

```bash
python -m ingest.cli --remote-pdf https://example.org/obra.pdf --allow-domain example.org --dry-run
```

## Proteções e limites

- **HTTPS/443 e allowlist exata:** o host da URL precisa corresponder ao parâmetro `--allow-domain`; subdomínios exigem autorização separada.
- **Sem redirecionamentos:** forneça a URL final explicitamente; resoluções de IP não globais são recusadas e o TLS confere o nome do host.
- **Robots e ritmo:** o coletor consulta `robots.txt`, não ignora bloqueios e usa pausas entre requisições.
- **Limites de volume:** HTML até 2 MiB, PDFs remotos até 30 MiB, lista de URLs até 100 entradas; crawler até 100 páginas, profundidade máxima 3.
- **Não inclui:** login em sites, execução JavaScript, `sitemap.xml.gz`, descoberta automática de PDFs ou contorno de bloqueios.

Respeite licenças, autorização e termos de uso. `robots.txt` não equivale a licença de reprodução. `example.org` é apenas ilustrativo: substitua por fonte autorizada. Consulte [documentos e OCR](advanced-import.md) e [detalhes de confiabilidade](reliability.md).
