# Ollama TypeScript debugger (local)

Use a **custom Ollama model** based on `llama3.2` plus a Python helper that gathers `tsconfig` JSON, runs `tsc -b`, and sends diagnostics + source to the model. The script is **advisory-only**: it prints suggested diffs or full-file replacements; it does not modify your tree.

## Prerequisites

- [Ollama](https://ollama.com/) installed and running (default API: `http://127.0.0.1:11434`).
- Node.js and npm; in this repo, install web deps once:

  ```powershell
  npm --prefix web install
  ```

## 1. Pull base model and create the custom model

From the repository root:

```powershell
ollama pull llama3.2
ollama create ts-debugger -f ollama/typescript-debugger.Modelfile
```

This defines the `ts-debugger` tag with a fixed system prompt and `temperature 0` in the Modelfile (API `--temperature` is optional).

## 2. Run the helper

**Recommended (single path from repo root):**

```powershell
python docs/typescript-debug.py web/src/lib/api.ts --repo .
```

**Alternative (explicit TS package root + file under `web/`):**

```powershell
python docs/typescript-debug.py web src/lib/api.ts --repo .
```

**If Ollama is not on localhost:**

```powershell
python docs/typescript-debug.py web/src/types.ts --ollama-url http://127.0.0.1:11434
```

**Skip `tsc` (e.g. you only have pasted errors):**

```powershell
python docs/typescript-debug.py web/src/lib/api.ts --no-tsc --extra-errors "src/foo.ts(1,1): error TS2304: Cannot find name 'x'."
```

**Different model name:**

```powershell
python docs/typescript-debug.py web/src/lib/api.ts --model my-other-model
```

## 3. What the script does

1. Resolves `--repo` (default `.`) and the target `.ts` / `.tsx` file; rejects paths that escape the repo.
2. Finds the nearest `tsconfig.json` walking up from the file (for this repo, that is [`web/tsconfig.json`](../web/tsconfig.json)).
3. In that directory, runs `npx tsc -b --pretty false` and captures stdout/stderr (unless `--no-tsc`).
4. POSTs to Ollama `/api/chat` with system + user content including tsconfig bundle and source.

## 4. Quick validation (no file writes)

```powershell
python docs/typescript-debug.py --help
python -m py_compile docs/typescript-debug.py
```

To smoke-test the model (requires `ts-debugger` running locally):

```powershell
python docs/typescript-debug.py web/src/types.ts --repo .
```

## Files

| File | Role |
|------|------|
| [`ollama/typescript-debugger.Modelfile`](../ollama/typescript-debugger.Modelfile) | `FROM llama3.2` + system prompt |
| [`docs/typescript-debug.py`](../docs/typescript-debug.py) | CLI: `tsc` + Ollama chat |

## Notes

- The old Anthropic-based script in the same path has been **replaced** by this Ollama flow; no `ANTHROPIC_API_KEY` is required.
- For best results, keep the target file path under [`web/`](../web/) so the helper uses the Vite/TypeScript project config.
