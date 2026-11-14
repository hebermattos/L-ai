# L-ai — Arcana

Chat de IA **100% local para inferência** especializado no estudo de ocultismo, hermetismo, alquimia, cabala, história da magia e grimórios. Executa em **Linux, CPU e 16 GB de RAM**, com **Ollama + Qwen3 4B Instruct + Open WebUI**. O conhecimento é ampliado por **RAG**, sem precisar ajustar os pesos do modelo.

> Os documentos são interpretados como fontes históricas, literárias ou de crenças; alegações sobrenaturais não são tratadas como evidência científica. O projeto não inclui livros ou bases protegidas por direitos autorais.

## Pré-requisitos

- Ubuntu/Debian com Docker Engine e plugin Docker Compose v2 instalados
- CPU x86-64 ou ARM64, **16 GB RAM recomendados**, aproximadamente 10 GB livres inicialmente (mais espaço para documentos)
- Internet **na primeira instalação** para baixar imagens e modelos
- `openssl`, `bash`, `curl` opcionais para testes de saúde

Instale o Docker via [documentação oficial](https://docs.docker.com/engine/install/ubuntu/). Para verificar: `docker compose version`.

## Início rápido

```bash
git clone https://github.com/hebermattos/L-ai.git
cd L-ai
bash scripts/setup.sh
```

O script gera um segredo aleatório em `.env`, inicia os containers, baixa o modelo `qwen3:4b-instruct` (Q4_K_M) e cria o modelo especializado `arcana`. **Não execute com `sudo bash`**; se seu usuário não tem acesso ao Docker, ajuste as permissões seguindo a documentação oficial ou use `sudo docker compose` para os comandos manuais.

Abra **http://localhost:3000**, cadastre o primeiro administrador local, selecione o modelo **arcana** e converse. O modelo pode responder com seu conhecimento prévio, mas **os livros só serão consultados depois que você os importar e vincular a uma base RAG**.

### Instalação manual

```bash
cp .env.example .env
# Edite .env e defina WEBUI_SECRET_KEY para um valor aleatório.
docker compose up -d
docker compose exec -T ollama ollama pull qwen3:4b-instruct
docker compose exec -T ollama ollama create arcana -f /config/Modelfile
docker compose ps
```

Crie o segredo com: `openssl rand -hex 32`. Nunca publique o `.env`.

## Importar seu conhecimento (RAG)

1. Organize os documentos em `biblioteca/hermetismo/`, `biblioteca/grimorios/`, `biblioteca/cabala/` etc. Essa pasta é **local** e ignorada pelo Git. Você também pode manter os arquivos em qualquer pasta.
2. No Open WebUI, entre em **Workspace → Knowledge → Create** e crie a base `Biblioteca de Ocultismo`.
3. Importe documentos PDF **com texto selecionável**, TXT, Markdown ou outros formatos suportados pela sua versão do Open WebUI. A importação é **pela interface**; adicionar arquivos em `biblioteca/` não indexa automaticamente.
4. Para PDF digitalizado como imagem, aplique OCR **antes** da importação; confira o resultado. Preserve metadados de título, autor, tradução, edição e páginas.
5. No chat, selecione o modelo `arcana` e anexe a base de conhecimento pelo seletor `#`, ou configure em **Workspace → Models** um modelo personalizado com a base vinculada.
6. Faça perguntas sobre os textos e confira as referências apresentadas. Se a consulta à base não ocorrer, revise as configurações de recuperação de conhecimento do Open WebUI.

Recomendação inicial para a busca: fragmentos ~800 tokens, sobreposição ~120, 4 resultados, com teste de qualidade em perguntas reais. O mecanismo de fragmentação e as unidades variam por versão/configuração. A mudança de modelo de embeddings pode exigir **reindexação**. Em computadores com 16 GB, comece com o embedding padrão local antes de adicionar modelos maiores.

**Atenção:** RAG não treina o modelo; ele recupera passagens de documentos e as disponibiliza durante a resposta. Já um fine-tuning modifica pesos e não faz parte deste MVP.

## Exemplos de consultas

- "Compare os temas centrais do *Corpus Hermeticum* e da *Tábua de Esmeralda*."
- "Segundo as fontes importadas, quais diferenças existem entre *Ars Goetia* e *Ars Theurgia-Goetia*?"
- "Como o conceito de correspondência aparece em diferentes obras? Cite autor e edição quando disponível."
- "Quais afirmações são históricas e quais pertencem à tradição esotérica neste documento?"

## Operação

```bash
docker compose ps
docker compose logs --tail=100
docker compose stop
docker compose start
docker compose pull && docker compose up -d  # faça backup antes
```

- **Chat:** http://127.0.0.1:3000; a porta está ligada apenas ao loopback.
- **Ollama:** acessível **somente na rede interna do Docker**, não exposto ao host.
- **Dados persistentes:** volumes Docker `ollama_data` e `open_webui_data`. Use backups antes de atualizar e **não execute `docker compose down -v`**.
- **Privacidade:** após os downloads, inferência e busca podem operar localmente, mas recursos opcionais de rede, atualizações e integrações externas devem permanecer desligados se precisar de isolamento estrito. Sem garantia de air gap por padrão.
- **Hardware:** o Qwen3 4B quantizado ocupa ~2,5 GB em disco para o modelo; memória total inclui KV cache, Open WebUI e embeddings. O desempenho depende da CPU.

## Estrutura

```text
.
├── compose.yaml
├── .env.example
├── config/Modelfile
├── biblioteca/            # seus arquivos: ignorados pelo Git
├── scripts/setup.sh
├── scripts/check.sh
├── tests/test_project.py
└── .github/workflows/ci.yml
```

## Documentação externa

- [Ollama Qwen3 4B Instruct](https://ollama.com/library/qwen3:4b-instruct)
- [Open WebUI](https://docs.openwebui.com/)
- [Docker Engine](https://docs.docker.com/engine/install/ubuntu/)

O modelo e as imagens são obtidos de seus distribuidores; confira as licenças e versões antes de usar em ambientes regulados.
