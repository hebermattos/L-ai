# Crawler e importação de documentos

O L-ai pode explorar links HTML internos de sites autorizados e importar **PDF/EPUB locais**, além de **PDFs remotos explicitamente indicados**. Para usar a CLI, siga a instalação de dependências e credenciais do [README](../README.md#habilitar-o-rag).

## Crawler recursivo

```bash
python -m ingest.cli --url https://example.org/library/index --allow-domain example.org --crawl --max-depth 2 --max-pages 25 --dry-run
```

Busca em largura no domínio e diretório da URL inicial; ignora links externos, `nofollow`, recursos não HTML e URLs repetidas. Não executa JavaScript. Os limites de profundidade (0 a 3) e páginas (1 a 100) valem por execução. A descoberta por `sitemap.xml` está descrita em [coleta web](web-ingestion.md).

## PDF e EPUB locais

```bash
python -m ingest.cli --file ~/Livros/obra.pdf --file ~/Livros/obra.epub --dry-run
python -m ingest.cli --directory ~/Livros --max-documents 50 --dry-run
```

O diretório é percorrido recursivamente; links simbólicos são rejeitados. PDFs precisam conter texto selecionável ou utilizar OCR opcional. EPUB não requer OCR e conteúdo criptografado não é suportado. O extrator preserva título e autor quando presentes; PDFs incluem marcadores de página.

Limites: PDF de até 30 MiB, 500 páginas e 2 milhões de caracteres extraídos; EPUB até 20 MiB, 80 MiB descompactados e 500 entradas ZIP. Processa até 100 documentos por execução (`--max-documents`, padrão 50).

## OCR opcional para PDFs digitalizados

Instale o Tesseract e os idiomas português/inglês no host:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por tesseract-ocr-eng
python -m ingest.cli --file ~/Livros/digitalizado.pdf --ocr --dry-run
```

O OCR roda **somente nas páginas sem texto selecionável**, com 120 DPI, timeout de 45 s por página e limite de 100 páginas para OCR. Execute inicialmente com `--dry-run`. O processamento pode ser lento em CPU.

## PDF remoto

```bash
python -m ingest.cli --remote-pdf https://example.org/obra.pdf --allow-domain example.org --dry-run
```

Exige HTTPS, `robots.txt`, domínio autorizado, extensão `.pdf` e assinatura PDF. Não há OCR remoto; para escaneados, obtenha uma cópia local autorizada. A segurança da coleta é detalhada em [coleta web](web-ingestion.md).

## Indexação

A remoção de `--dry-run` envia os trechos para o Open WebUI, após configuração da API e base. O estado local evita reindexar conteúdos idênticos por hash. Arquivos são identificados por URI local no estado, mas o caminho absoluto não é incluído no documento indexado. Confirme a busca no chat usando fontes conhecidas; veja [confiabilidade](reliability.md).
