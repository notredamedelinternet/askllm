# free-llm-mojo

A small Mojo CLI for asking questions through the free-tier or trial-tier APIs of major LLM clouds.

The CLI is intentionally simple: Mojo provides the command entrypoint, and Mojo's Python interop calls a local standard-library Python module for HTTP and JSON handling. No provider SDKs are required.

## Supported providers

| Provider | Environment variable | Default model |
| --- | --- | --- |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-3-5-haiku-latest` |
| Google Gemini | `GOOGLE_API_KEY` | `gemini-2.0-flash` |
| Groq | `GROQ_API_KEY` | `llama-3.1-8b-instant` |
| Mistral | `MISTRAL_API_KEY` | `mistral-small-latest` |
| Cohere | `COHERE_API_KEY` | `command-r` |
| Together AI | `TOGETHER_API_KEY` | `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo` |
| Cerebras | `CEREBRAS_API_KEY` | `llama3.1-8b` |

Free tiers, trial credits, model names, and rate limits change. This tool does not bundle API keys or bypass billing; it uses whichever provider keys you set in your environment.

## Install

Install Mojo with `pixi`:

```sh
pixi install
```

Or follow the current Mojo install instructions from Modular, then run the `.mojo` file directly.

## Usage

Set at least one provider key:

```sh
export GOOGLE_API_KEY="..."
```

Ask a question:

```sh
pixi run ask --provider google "Explain DNS in one paragraph"
```

Let the CLI choose the first configured provider:

```sh
pixi run ask "What is a vector database?"
```

Pipe input:

```sh
echo "Summarize HTTP caching" | pixi run ask --provider groq
```

Use a different model:

```sh
pixi run ask --provider mistral --model mistral-large-latest "Draft a concise release note"
```

Check setup:

```sh
pixi run ask --list-providers
```

Run tests:

```sh
pixi run test
```

## How it chooses a provider

If you pass `--provider`, that provider must have its API key set. Without `--provider`, the CLI uses the first configured provider in this order:

`openai`, `anthropic`, `google`, `groq`, `mistral`, `cohere`, `together`, `cerebras`.

## License

MIT
