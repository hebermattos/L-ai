# P0 — Confiabilidade de ingestão

## O que foi corrigido

- O SQLite usa `PRIMARY KEY (url, knowledge_id)`, permitindo a mesma URL em mais de uma base sem sobrescrever os IDs de arquivos.
- A migração da tabela anterior ocorre automaticamente em transação. Faça um backup de `biblioteca/.web-ingest.sqlite3` antes da primeira execução.
- Estados persistidos: `uploaded` (upload realizado, link pendente), `updating` (reindexação pendente), `ready` (confirmado). Reexecutar o mesmo comando retoma o processamento, sem repetir o upload quando seu ID já foi salvo.
- Uma URL inalterada só é ignorada se seu arquivo ainda estiver associado à Knowledge Base.
- Atualizações usam `POST /api/v1/files/{id}/data/content/update`, que nas versões atuais do Open WebUI reprocessa as bases vinculadas. O resultado é conferido com uma leitura `GET /api/v1/files/{id}/data/content` e com a listagem de arquivos da Knowledge Base.
- Respostas de erro, divergências e falta de associação mantêm o estado pendente para nova tentativa.

## Testes

Os testes unitários não exigem servidor, GPU ou modelos baixados:

```bash
python -m unittest discover -s tests -v
```

Para testar **contra Open WebUI real**, crie uma **base de teste descartável** e configure:

```bash
export OPEN_WEBUI_API_KEY='...'
export OPEN_WEBUI_KNOWLEDGE_ID='id-de-uma-base-descartavel'
L_AI_INTEGRATION=1 python -m unittest tests.test_webui_integration -v
```

Este teste envia e altera um arquivo na base de teste, mas **não o exclui**. Não use uma base de produção.

## Limitações conhecidas

- O endpoint de leitura confirma conteúdo persistido e associação, mas **não garante matematicamente** que todos os vetores estejam disponíveis. Testes de busca e recall com documentos reais são recomendados antes de produção.
- Se o processo terminar exatamente entre o sucesso do upload HTTP e a gravação local do ID, é possível criar um arquivo órfão. Reconciliação remota de órfãos fica para melhoria futura.
- **Não execute duas instâncias de importação simultaneamente usando o mesmo banco de estado.** O controle atual cobre retomadas sequenciais.
- O código mantém o fluxo legado de upload e associação para preservar compatibilidade. Alguns formatos de paginação da API podem variar conforme a versão do Open WebUI.
- Evite usar imagens Docker `latest`/ `main` em produção; fixe versões testadas para atualizações previsíveis.

Referência: https://docs.openwebui.com/features/workspace/knowledge/
