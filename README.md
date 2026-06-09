# askllm

A small Mojo CLI for asking questions through local no-key LLMs or the free-tier/trial-tier APIs of major LLM clouds.

The CLI is intentionally simple: Mojo provides the command entrypoint, and Mojo's Python interop calls a local standard-library Python module for HTTP and JSON handling. No provider SDKs are required.

## Supported providers

| Provider | Environment variable | Default model |
| --- | --- | --- |
| Ollama | none | `llama3.2` |
| Local OpenAI-compatible server | none | `local-model` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-3-5-haiku-latest` |
| Google Gemini | `GOOGLE_API_KEY` | `gemini-2.0-flash` |
| Groq | `GROQ_API_KEY` | `llama-3.1-8b-instant` |
| Mistral | `MISTRAL_API_KEY` | `mistral-small-latest` |
| Cohere | `COHERE_API_KEY` | `command-r` |
| Together AI | `TOGETHER_API_KEY` | `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo` |
| Cerebras | `CEREBRAS_API_KEY` | `llama3.1-8b` |

Free tiers, trial credits, model names, and rate limits change. This tool does not bundle API keys or bypass billing; it uses local no-key providers by default, or whichever provider keys you set in your environment.

## Install

Install Pixi first:

```sh
curl -fsSL https://pixi.sh/install.sh | sh
```

Restart your shell, or source your shell config so `pixi` is on your `PATH`:

```sh
source ~/.zshrc
```

Clone this repository and enter it:

```sh
git clone https://github.com/notredamedelinternet/askllm.git
cd askllm
```

Install Mojo and Python into the project environment:

```sh
pixi install
```

Check that Mojo is available:

```sh
pixi run mojo --version
```

## Usage

By default, `askllm` uses local Ollama with no API key. Install Ollama separately, pull a model, and ask a question:

```sh
ollama pull llama3.2
pixi run askllm "Explain DNS in one paragraph"
```

Use another local OpenAI-compatible server, such as LM Studio or llama.cpp:

```sh
export ASKLLM_LOCAL_OPENAI_BASE_URL="http://localhost:1234/v1"
pixi run askllm --provider local-openai --model local-model "Write a haiku"
```

For cloud providers, set at least one provider key:

```sh
export GOOGLE_API_KEY="..."
```

Ask a question:

```sh
pixi run askllm --provider google "Explain DNS in one paragraph"
```

Let the CLI use the default local Ollama provider:

```sh
pixi run askllm "What is a vector database?"
```

Pipe input:

```sh
echo "Summarize HTTP caching" | pixi run askllm --provider ollama
```

Use a different model:

```sh
pixi run askllm --provider mistral --model mistral-large-latest "Draft a concise release note"
```

Check setup:

```sh
pixi run askllm --list-providers
```

Run tests:

```sh
pixi run test
```

## How it chooses a provider

If you pass `--provider`, cloud providers must have their API key set. Local providers do not need keys. Without `--provider`, the CLI uses the first available provider in this order:

`ollama`, `local-openai`, `openai`, `anthropic`, `google`, `groq`, `mistral`, `cohere`, `together`, `cerebras`.

`ollama` uses `OLLAMA_HOST` when set, otherwise `http://localhost:11434`.

`local-openai` uses `ASKLLM_LOCAL_OPENAI_BASE_URL` when set, otherwise `http://localhost:1234/v1`.

## License

MIT
