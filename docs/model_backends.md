# Model backends

LLM agents call the Ollama `/api/generate` endpoint with deterministic decoding and
JSON output. The client stores one append-only JSONL cache per resolved model tag.
Cache keys include the model, prompt, and candidate labels, so a cached decision is
safe to replay for the same mission configuration.

The public experiment names are aliases:

```text
small_reasoner      -> MOSAIC_MODEL_SMALL      (default qwen2.5:3b)
small_reasoner_alt  -> MOSAIC_MODEL_SMALL_ALT  (default llama3.2:3b)
large_reasoner      -> MOSAIC_MODEL_LARGE      (default qwen2.5:7b)
```

Example for a Windows Ollama server visible from WSL:

```bash
export MOSAIC_OLLAMA_URL=http://localhost:11434/api/generate
export MOSAIC_MODEL_SMALL=qwen2.5:3b
ollama pull qwen2.5:3b
python -m experiments.run_llm --seeds 2 --teams mixed
```

Set `MOSAIC_CACHE_DIR` to keep caches outside the repository. Do not commit model
responses or generated mission results; they are machine-specific experiment data.

