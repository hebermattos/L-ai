# Confiabilidade, recuperação de falhas e testes

O L-ai usa SQLite local em `biblioteca/.web-ingest.sqlite3`, com chave composta `(url, knowledge_id)`. Isso permite utilizar a mesma fonte em bases distintas. A migração do esquema legado é transacional; **faça backup do SQLite antes de atualizar**.

## Fluxo de estados

- `uploaded`: arquivo enviado; processamento/associação à base ainda podem estar pendentes.
- `updating`: atualização de conteúdo remoto pendente ou em validação.
- `ready`: a API confirmou conteúdo/associação; **não comprova recuperação semântica**.

Reexecutar o mesmo comando pode retomar operações pendentes. Há riscos conhecidos: queda entre upload remoto e registro local pode deixar arquivo órfão; o estado não deve ser usado simultaneamente por duas instâncias. A validação de conteúdo usa endpoints da versão instalada do Open WebUI — comportamento pode mudar entre versões.

## Testes isolados

```bash
python -m unittest discover -s tests -v
```

O CI verifica o Compose, sintaxe Shell e testes Python. Os testes de API simulados **não iniciam** Ollama nem Open WebUI.

## Teste real opcional (somente base descartável)

No Open WebUI local, crie uma base vazia descartável e uma chave API com acesso. Execute no terminal onde a instância está disponível:

```bash
export OPEN_WEBUI_API_KEY='SUA_CHAVE'
export OPEN_WEBUI_KNOWLEDGE_ID='ID_DE_BASE_DESCARTAVEL'
L_AI_INTEGRATION=1 python -m unittest discover -s tests -p 'test_webui_integration.py' -v
```

O teste envia e altera um documento. **Não o remove automaticamente**; exclua-o depois pela interface. Não execute contra bases reais de produção.

Para verificar o **RAG de ponta a ponta**, vincule a base ao chat, faça uma pergunta sobre uma frase exclusiva do documento de teste e compare com a resposta/citação. Repita após atualizar o conteúdo e confira que a passagem antiga deixou de ser recuperada. A CI não valida esse fluxo de recuperação.

## Diagnóstico

Se `docker compose ps` indicar serviço parado, consulte `docker compose logs --tail=100`. Se o upload falhar, confira chave, ID e versão da API. Se a consulta responder sem referências, verifique se a base está vinculada ao chat e teste a recuperação de um trecho literal. Em caso de diferenças de comportamento entre releases, fixe versões de imagens Docker testadas antes de mudar o código.

Consulte [pipeline e avaliação](knowledge-pipeline.md) e [instalação](../README.md).
