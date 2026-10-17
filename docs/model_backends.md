# Model backends

LLM agents call the Ollama `/api/generate` endpoint with deterministic decoding and
JSON output. The client stores one append-only JSONL cache per resolved model tag.
Cache keys include the model, prompt, and candidate labels, so a cached decision is
safe to replay for the same mission configuration.

The public experiment names are aliases:

```text
small_reasoner      -> MICA_MODEL_SMALL      (default qwen2.5:3b)
small_reasoner_alt  -> MICA_MODEL_SMALL_ALT  (default llama3.2:3b)
large_reasoner      -> MICA_MODEL_LARGE      (default qwen2.5:7b)
```

Example for a Windows Ollama server visible from WSL:

```bash
export MICA_OLLAMA_URL=http://127.0.0.1:11434/api/generate
export MICA_MODEL_SMALL=llama3.1:8b
python -m experiments.run_llm --seeds 2 --teams mixed
```

Use a model already installed on the server. The example URL works when the
server is accessible at that address from the simulation host. For Windows
Ollama bound to Windows localhost and WSL simulation, see the bridge supported
by the [LLM calibration runner](llm_behavior_calibration.md).

Set `MICA_CACHE_DIR` to keep caches outside the repository. Do not commit model
responses or generated mission results; they are machine-specific experiment data.

