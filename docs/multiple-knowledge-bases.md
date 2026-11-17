# Multiple knowledge bases

Use separate Open WebUI knowledge bases for topics or projects. The same language
model can consult different bases without retraining. Importing content and
selecting context for a conversation are separate operations.

## Create and list bases

Install the host dependencies and set `OPEN_WEBUI_API_KEY` as described in the
[README](../README.md#enable-rag). These commands do not require
`OPEN_WEBUI_KNOWLEDGE_ID`:

```bash
python -m ingest.knowledge create --name "Programming" --description "Language and framework documentation"
python -m ingest.knowledge create --name "Security" --description "Security tool manuals"
python -m ingest.knowledge list
```

Commands print JSON containing IDs and names. Listing includes all bases visible
to the API user and follows pagination. Creation requires Open WebUI permission
to manage knowledge; it does not add sharing permissions. To use localhost
instead of the default 127.0.0.1 URL, put
`--webui-url http://localhost:3000` **before** `list` or `create`.

Alternatively, create bases in **Workspace → Knowledge** in Open WebUI.

## Choose the import destination

Each import targets exactly one base:

```bash
python -m ingest.cli --import-folder ./programming --knowledge-name "Programming"
python -m ingest.cli --import-folder ./security --knowledge-name "Security"
# An ID works even when several bases have the same name:
python -m ingest.cli --import-folder ./security --knowledge-id YOUR_SECURITY_BASE_ID
```

Add `--allow-domain` for web sources. All existing import limits and options
still apply; see [import content](advanced-import.md).

- `--knowledge-name` matches an exact, case-sensitive name. Missing or duplicate
  names stop the import before upload; use an ID to resolve ambiguity.
- `--knowledge-id` and `--knowledge-name` are mutually exclusive. Either explicit
  option overrides `OPEN_WEBUI_KNOWLEDGE_ID`; the environment variable remains
  the default when neither option is supplied.
- `--dry-run` extracts inputs without contacting Open WebUI, resolving names,
  creating bases, uploading, or saving state. It does not verify that a base exists.
- Bases are never created implicitly by an import. Renaming a base changes the
  name needed for future imports; its ID remains the stable selector.

The shared SQLite state tracks each source **per base ID**. Importing the same
source into another base does not skip it as already imported. Updates and
duplicate detection remain scoped to the target base. Run imports sequentially
when sharing a state database.

## Choose bases for a chat

1. Open a chat with `lai`.
2. Use Open WebUI's knowledge attachment selector to attach the desired bases.
   Depending on the installed version, the picker may be opened with `#` or
   another context shortcut.
3. Add more than one base when the question needs combined context.
4. Check the attached items and source citations to verify the intended material
   was retrieved.

For a reusable preset, attach knowledge to a custom model in
**Workspace → Models**. Also review knowledge inherited from a model or chat
folder when changing the conversation's sources. Removing an attachment does
not erase earlier messages or retrieved passages; start a new chat when you
need fresh context from a different selection.

Selection scopes document retrieval. It does not remove the model's general
knowledge or guarantee that every selected base contributes to every answer.
The L-ai CLI manages import destinations; conversation selection is handled by
Open WebUI. Interface details depend on the deployed version.
