# Web scraping para a base RAG

Este módulo coleta **apenas páginas HTTPS explicitamente escolhidas**, extrai texto principal via Trafilatura e faz upload para **Knowledge** do Open WebUI, aguardando o processamento antes de vincular o arquivo. Não faz crawling nem descoberta automática de links (P1).

## Configuração

```bash
cd L-ai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-ingest.txt
```

1. No Open WebUI, crie uma base em **Workspace → Knowledge** e copie seu ID da URL ou da API.
2. Crie uma **API Key** em **Settings → Account**.
3. Exporte localmente, sem colocar tokens nos arquivos do Git:

```bash
export OPEN_WEBUI_API_KEY='sua-chave'
export OPEN_WEBUI_KNOWLEDGE_ID='id-da-base'
```

Defina os endereços em `urls.txt`, um por linha:

```text
# Lista de páginas para pesquisa; substitua pelos domínios com permissão
https://example.org/artigo1
https://example.org/artigo2
```

Primeiro teste somente a extração, sem enviar nada ao Open WebUI:

```bash
python -m ingest.cli --urls-file urls.txt --allow-domain example.org --dry-run
```

Depois execute a importação:

```bash
python -m ingest.cli --urls-file urls.txt --allow-domain example.org
```

Também é possível passar `--url https://example.org/artigo1` várias vezes; para vários hosts, repita `--allow-domain HOST`. A lista de domínios autorizados é **obrigatória** e cada subdomínio precisa ser autorizado separadamente.

O estado de hashes e IDs é mantido em `biblioteca/.web-ingest.sqlite3` (não versionado). URLs com conteúdo idêntico não são importadas duas vezes; quando uma URL muda, o documento já associado a ela tem o texto indexado atualizado via API. Não exclua o arquivo de estado sem planejar a reconciliação com o Open WebUI, pois isso pode provocar reimportações.

## Segurança e limites

- Somente **HTTPS**, porta 443 e **hosts explicitamente permitidos**; nenhuma URL com credenciais embutidas.
- Resolução DNS validada antes de cada conexão. Se houver qualquer IP privado, loopback ou não global, a conexão é rejeitada; conexão e TLS usam um **IP fixado**, com SNI e verificação de certificado do domínio original.
- **Sem seguir redirecionamentos**, inclusive redirecionamentos de `robots.txt`.
- Respeita `robots.txt`; falha fechada se indisponível (HTTP 404 significa regras ausentes).
- Máximo de 2 MiB de conteúdo por resposta, 25 URLs por execução por padrão, 100 máximo configurável; pausa de pelo menos dois segundos entre requisições do coletor.
- Interface administrativa Open WebUI disponível somente em localhost; a integração não envia a chave para os sites externos.
- Sem execução de scripts das páginas, sem Playwright e sem acessos recursivos.
- Confira direitos autorais, licenças, termos de uso e autorização de acesso antes da coleta. `robots.txt` não é licença de reprodução.

## Limitações de P0

- Apenas páginas com HTML ou texto sem autenticação. Não há importação automática de PDF remoto, JavaScript dinâmico, páginas paginadas ou descoberta recursiva.
- A verificação de `robots.txt` depende da disponibilidade do site. Páginas que impedem automação serão ignoradas.
- O banco de estado é local; alterações feitas diretamente no Open WebUI podem exigir reconciliação manual.
- A atualização de conteúdo depende da versão da API do Open WebUI.
- Para ambiente com alta exigência de segurança, execute o coletor em container ou VM isolada e restrinja também o tráfego de saída no firewall.

**Referência:** [API de arquivos e Knowledge do Open WebUI](https://docs.openwebui.com/reference/api-endpoints/).
