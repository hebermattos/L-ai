# L-ai — IA local com RAG

Assistente de IA **de propósito geral** com chat local e recuperação de conhecimento (**RAG**). Usa **Ollama + Qwen3 4B Instruct + Open WebUI** para pesquisar documentos e responder perguntas em diferentes áreas. Destinado a Linux com **CPU e 16 GB de RAM**, sem GPU obrigatória.

O RAG não treina nem altera os pesos do modelo: ele indexa documentos autorizados e recupera trechos relevantes durante a conversa. O assistente não é limitado a um tema específico.

## Instalação rápida

Pré-requisitos: Ubuntu/Debian, Docker Engine com Compose v2, Git e OpenSSL, acesso ao Docker e espaço livre para modelos e documentos. A primeira instalação baixa imagens e o modelo.

```bash
git clone https://github.com/hebermattos/L-ai.git
cd L-ai
bash scripts/setup.sh
docker compose ps
```

Abra **http://localhost:3000**, crie o administrador local e escolha o modelo **lai**. O script cria um segredo em `.env`, inicia Ollama/Open WebUI, baixa o Qwen e configura o perfil genérico `lai`. Não execute o script como `sudo bash`; configure o acesso ao Docker conforme a [documentação oficial](https://docs.docker.com/engine/install/linux-postinstall/).

**Teste inicial:** peça ao modelo que explique um conceito de programação ou resuma uma ideia geral. Isso testa apenas a inferência, não a recuperação RAG.

## Habilitar o RAG

1. No Open WebUI, entre em **Workspace → Knowledge** e crie uma base chamada `Biblioteca de Conhecimento`.
2. Importe um pequeno PDF com texto selecionável ou TXT/Markdown pela interface.
3. No chat com `lai`, vincule essa base usando o seletor de conhecimento (em versões compatíveis, digite `#`) ou configure a base no modelo personalizado.
4. Pergunte algo que só consta do documento; confira se a resposta indica a fonte correta. Uma resposta plausível sem referência **não comprova** que o RAG foi usado.

Para ingestão automatizada via API, crie uma chave no Open WebUI (área de conta) e obtenha o ID da base. Em um terminal local:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-ingest.txt
export OPEN_WEBUI_API_KEY='SUA_CHAVE'
export OPEN_WEBUI_KNOWLEDGE_ID='ID_DA_BASE'
```

Não adicione tokens a arquivos versionados. A instalação base do Docker não instala automaticamente as dependências Python de ingestão no host.

## Importar conteúdo

**Páginas individuais** (uma URL de um domínio explicitamente autorizado):

```bash
python -m ingest.cli --url https://example.org/artigo --allow-domain example.org --dry-run
```

**Crawler recursivo controlado**, limitado ao host e ao diretório inicial:

```bash
python -m ingest.cli --url https://example.org/library/index --allow-domain example.org --crawl --max-depth 2 --max-pages 25 --dry-run
```

**Sitemap** e **PDF remoto** (endereços HTTPS autorizados, explícitos):

```bash
python -m ingest.cli --sitemap https://example.org/sitemap.xml --allow-domain example.org --max-pages 25 --dry-run
python -m ingest.cli --remote-pdf https://example.org/obra.pdf --allow-domain example.org --dry-run
```

**Livros locais** (PDF/EPUB) e **OCR opcional** de PDFs escaneados:

```bash
python -m ingest.cli --directory ~/Livros --max-documents 50 --dry-run
python -m ingest.cli --file ~/Documentos/arquivo.pdf --ocr --dry-run
```

Substitua `example.org` por um domínio que permita a coleta. `--dry-run` extrai e apresenta resultados sem enviar à base; para indexar, remova essa opção após configurar a chave e o ID. O OCR requer Tesseract e pacotes de idioma instalados à parte.

O scraping só aceita HTTPS, hosts expressamente autorizados, regras `robots.txt`, não segue redirecionamentos e limita profundidade/tamanho. **Não faz scraping de sites arbitrários ou JavaScript dinâmico.** PDF remoto exige URL fornecida explicitamente; o crawler não baixa automaticamente cada PDF encontrado.

## Consultar e verificar

No Open WebUI, escolha `lai` e vincule a biblioteca importada. Perguntas de exemplo: “Quais são os requisitos descritos neste documento?” ou “Resuma o capítulo 2 e cite a fonte utilizada.”

Para testar upload, indexação e associação com uma **base descartável**, consulte [validação real do RAG](docs/reliability.md). Isso não substitui um teste de recuperação semântica no chat.

## Documentação por assunto

- [Coleta web e segurança](docs/web-ingestion.md) — URLs, sitemap, limites, permissão.
- [Crawler e documentos locais](docs/advanced-import.md) — navegação, PDF, EPUB e OCR.
- [Confiabilidade e testes](docs/reliability.md) — SQLite, atualização, recuperação de falhas.
- [Pipeline e avaliação](docs/knowledge-pipeline.md) — agenda, metadados, métricas e busca híbrida.

## Operação e limites

```bash
docker compose ps
docker compose logs --tail=100
docker compose stop
docker compose start
```

O chat fica em `127.0.0.1:3000`; Ollama permanece na rede interna Docker. Os volumes `ollama_data` e `open_webui_data` guardam modelos e dados. Faça backup antes de atualizar; **não use `docker compose down -v`** se quiser preservá-los. Não exponha a API ou o chat à internet sem controles adicionais. A coleta de sites usa rede externa; a inferência local não exige API paga.

Atualização: `docker compose pull && docker compose up -d`, preferencialmente com versões fixadas e backup. O desempenho depende da CPU; OCR e indexação de grandes bibliotecas podem ser lentos.

## Estrutura resumida

```text
.
├── compose.yaml
├── .env.example
├── config/Modelfile
├── biblioteca/                 # conteúdo e estado local, ignorados pelo Git
├── ingest/                     # CLI, crawler, extratores e integração Open WebUI
├── requirements-ingest.txt
├── docs/                       # guias de uso
├── scripts/setup.sh
├── scripts/check.sh
├── tests/
└── .github/workflows/ci.yml
```

Referências: [Ollama](https://ollama.com/library/qwen3:4b-instruct), [Open WebUI](https://docs.openwebui.com/) e [Docker](https://docs.docker.com/engine/install/ubuntu/).
