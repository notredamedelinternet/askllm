"""Provider-agnostic CLI logic for the Mojo entrypoint."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


Json = dict[str, Any]
ENV_FILE = ".env"


@dataclass(frozen=True)
class Provider:
    name: str
    key_env: str | None
    default_model: str
    make_request: Callable[[str | None, str, str], tuple[str, Json, dict[str, str]]]
    parse_response: Callable[[Json], str]
    note: str


def _chat_completions_request(
    api_key: str | None,
    model: str,
    prompt: str,
    *,
    base_url: str,
    auth_header: str = "Authorization",
    auth_prefix: str = "Bearer ",
) -> tuple[str, Json, dict[str, str]]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers[auth_header] = f"{auth_prefix}{api_key}"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    return base_url.rstrip("/") + "/chat/completions", body, headers


def _parse_chat_completions(data: Json) -> str:
    return data["choices"][0]["message"]["content"].strip()


def _ollama_request(_api_key: str | None, model: str, prompt: str) -> tuple[str, Json, dict[str, str]]:
    base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    return (
        base_url.rstrip("/") + "/api/generate",
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        {"Content-Type": "application/json"},
    )


def _parse_ollama(data: Json) -> str:
    return str(data.get("response", "")).strip()


def _local_openai_request(
    _api_key: str | None, model: str, prompt: str
) -> tuple[str, Json, dict[str, str]]:
    base_url = os.getenv("ASKLLM_LOCAL_OPENAI_BASE_URL", "http://localhost:1234/v1")
    return _chat_completions_request(None, model, prompt, base_url=base_url)


def _anthropic_request(api_key: str, model: str, prompt: str) -> tuple[str, Json, dict[str, str]]:
    return (
        "https://api.anthropic.com/v1/messages",
        {
            "model": model,
            "max_tokens": 1024,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        },
        {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )


def _parse_anthropic(data: Json) -> str:
    chunks = []
    for item in data.get("content", []):
        if item.get("type") == "text":
            chunks.append(item.get("text", ""))
    return "\n".join(chunks).strip()


def _gemini_request(api_key: str, model: str, prompt: str) -> tuple[str, Json, dict[str, str]]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    return (
        url,
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        },
        {"Content-Type": "application/json"},
    )


def _parse_gemini(data: Json) -> str:
    parts = data["candidates"][0]["content"]["parts"]
    return "\n".join(part.get("text", "") for part in parts).strip()


def _quote_env_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    value = value.replace('\\"', '"').replace("\\\\", "\\")
    return key, value


def read_env_file(path: str = ENV_FILE) -> dict[str, str]:
    values: dict[str, str] = {}
    if not os.path.exists(path):
        return values
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            parsed = _parse_env_line(line)
            if parsed:
                key, value = parsed
                values[key] = value
    return values


def write_env_file(values: dict[str, str], path: str = ENV_FILE) -> None:
    lines = [
        "# askllm local configuration",
        "# This file may contain API keys. Do not commit it.",
    ]
    for key in sorted(values):
        lines.append(f"{key}={_quote_env_value(values[key])}")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_env_file(path: str = ENV_FILE) -> None:
    for key, value in read_env_file(path).items():
        os.environ.setdefault(key, value)


PROVIDERS: dict[str, Provider] = {
    "ollama": Provider(
        name="ollama",
        key_env=None,
        default_model="llama3.2",
        make_request=_ollama_request,
        parse_response=_parse_ollama,
        note="Local Ollama API. No API key required.",
    ),
    "local-openai": Provider(
        name="local-openai",
        key_env=None,
        default_model="local-model",
        make_request=_local_openai_request,
        parse_response=_parse_chat_completions,
        note="Local OpenAI-compatible API, such as LM Studio or llama.cpp. No API key required.",
    ),
    "openai": Provider(
        name="openai",
        key_env="OPENAI_API_KEY",
        default_model="gpt-4o-mini",
        make_request=lambda key, model, prompt: _chat_completions_request(
            key, model, prompt, base_url="https://api.openai.com/v1"
        ),
        parse_response=_parse_chat_completions,
        note="OpenAI Chat Completions API.",
    ),
    "anthropic": Provider(
        name="anthropic",
        key_env="ANTHROPIC_API_KEY",
        default_model="claude-3-5-haiku-latest",
        make_request=_anthropic_request,
        parse_response=_parse_anthropic,
        note="Anthropic Messages API.",
    ),
    "google": Provider(
        name="google",
        key_env="GOOGLE_API_KEY",
        default_model="gemini-2.0-flash",
        make_request=_gemini_request,
        parse_response=_parse_gemini,
        note="Google Gemini API.",
    ),
    "groq": Provider(
        name="groq",
        key_env="GROQ_API_KEY",
        default_model="llama-3.1-8b-instant",
        make_request=lambda key, model, prompt: _chat_completions_request(
            key, model, prompt, base_url="https://api.groq.com/openai/v1"
        ),
        parse_response=_parse_chat_completions,
        note="Groq OpenAI-compatible API.",
    ),
    "mistral": Provider(
        name="mistral",
        key_env="MISTRAL_API_KEY",
        default_model="mistral-small-latest",
        make_request=lambda key, model, prompt: _chat_completions_request(
            key, model, prompt, base_url="https://api.mistral.ai/v1"
        ),
        parse_response=_parse_chat_completions,
        note="Mistral Chat Completions API.",
    ),
    "cohere": Provider(
        name="cohere",
        key_env="COHERE_API_KEY",
        default_model="command-r",
        make_request=lambda key, model, prompt: _chat_completions_request(
            key,
            model,
            prompt,
            base_url="https://api.cohere.com/compatibility/v1",
            auth_header="Authorization",
        ),
        parse_response=_parse_chat_completions,
        note="Cohere OpenAI-compatible Chat API.",
    ),
    "together": Provider(
        name="together",
        key_env="TOGETHER_API_KEY",
        default_model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        make_request=lambda key, model, prompt: _chat_completions_request(
            key, model, prompt, base_url="https://api.together.xyz/v1"
        ),
        parse_response=_parse_chat_completions,
        note="Together AI OpenAI-compatible API.",
    ),
    "cerebras": Provider(
        name="cerebras",
        key_env="CEREBRAS_API_KEY",
        default_model="llama3.1-8b",
        make_request=lambda key, model, prompt: _chat_completions_request(
            key, model, prompt, base_url="https://api.cerebras.ai/v1"
        ),
        parse_response=_parse_chat_completions,
        note="Cerebras OpenAI-compatible API.",
    ),
}


def available_providers() -> list[str]:
    return [
        name
        for name, provider in PROVIDERS.items()
        if provider.key_env is None or os.getenv(provider.key_env)
    ]


def choose_provider(requested: str | None) -> Provider:
    if requested:
        if requested not in PROVIDERS:
            raise SystemExit(f"Unknown provider '{requested}'. Try --list-providers.")
        provider = PROVIDERS[requested]
        if provider.key_env and not os.getenv(provider.key_env):
            raise SystemExit(f"Set {provider.key_env} to use {requested}.")
        return provider

    names = available_providers()
    if not names:
        raise SystemExit("No provider available. Try --provider ollama with Ollama running locally.")
    return PROVIDERS[names[0]]


def ask(provider: Provider, prompt: str, model: str | None = None, timeout: int = 60) -> str:
    api_key = os.environ[provider.key_env] if provider.key_env else None
    selected_model = model or provider.default_model
    url, body, headers = provider.make_request(api_key, selected_model, prompt)
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{provider.name} returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {provider.name}: {exc.reason}") from exc

    data = json.loads(payload)
    answer = provider.parse_response(data)
    if not answer:
        raise RuntimeError(f"{provider.name} returned an empty answer: {payload}")
    return answer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="askllm",
        description="Ask a question using a local no-key LLM or a configured LLM cloud key.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Examples:
              pixi run askllm setup
              pixi run askllm "Explain DNS in one paragraph"
              pixi run askllm --provider local-openai --model qwen2.5-7b-instruct "Write a haiku"
              pixi run askllm --provider google "Explain DNS in one paragraph"
              echo "Summarize this" | pixi run askllm --provider ollama
            """
        ),
    )
    parser.add_argument("question", nargs="*", help="Question to ask. Reads stdin if omitted.")
    parser.add_argument("-p", "--provider", choices=sorted(PROVIDERS), help="Provider to use.")
    parser.add_argument("-m", "--model", help="Override the provider's default model.")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds.")
    parser.add_argument("--list-providers", action="store_true", help="Show provider setup status.")
    return parser


def print_provider_status() -> None:
    for name in sorted(PROVIDERS):
        provider = PROVIDERS[name]
        if provider.key_env is None:
            status = "no key"
            env = "-"
        else:
            status = "configured" if os.getenv(provider.key_env) else "missing key"
            env = provider.key_env
        print(f"{name:12} {status:12} env={env} default={provider.default_model}")
    sys.stdout.flush()


def cloud_key_envs() -> list[tuple[str, str]]:
    return [
        (name, provider.key_env)
        for name, provider in PROVIDERS.items()
        if provider.key_env is not None
    ]


def run_setup(path: str = ENV_FILE) -> int:
    existing = read_env_file(path)
    updated = dict(existing)
    print(f"askllm setup writes local configuration to {path}.")
    print("Press Enter to keep an existing value or skip a provider.")
    print("Local providers like ollama do not need API keys.")
    print()
    sys.stdout.flush()

    for name, key_env in cloud_key_envs():
        current = "configured" if os.getenv(key_env) or existing.get(key_env) else "empty"
        prompt = f"{name} ({key_env}, {current}): "
        if sys.stdin.isatty():
            value = getpass.getpass(prompt).strip()
        else:
            value = input(prompt).strip()
        if value:
            updated[key_env] = value

    local_base_url = input(
        "local-openai base URL "
        f"(ASKLLM_LOCAL_OPENAI_BASE_URL, current: {existing.get('ASKLLM_LOCAL_OPENAI_BASE_URL', 'default')}): "
    ).strip()
    if local_base_url:
        updated["ASKLLM_LOCAL_OPENAI_BASE_URL"] = local_base_url

    ollama_host = input(
        f"ollama host (OLLAMA_HOST, current: {existing.get('OLLAMA_HOST', 'default')}): "
    ).strip()
    if ollama_host:
        updated["OLLAMA_HOST"] = ollama_host

    write_env_file(updated, path)
    load_env_file(path)
    print()
    print(f"Saved {path}. Run `pixi run askllm --list-providers` to check setup.")
    sys.stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    load_env_file()

    if argv and argv[0] == "setup":
        return run_setup()

    parser = build_parser()
    if "-h" in argv or "--help" in argv:
        print(parser.format_help())
        sys.stdout.flush()
        return 0

    args = parser.parse_args(argv)

    if args.list_providers:
        print_provider_status()
        return 0

    prompt = " ".join(args.question).strip()
    if not prompt and not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    if not prompt:
        print("askllm: error: provide a question or pipe text on stdin", file=sys.stderr)
        sys.stderr.flush()
        return 2

    try:
        provider = choose_provider(args.provider)
        print(ask(provider, prompt, model=args.model, timeout=args.timeout))
    except SystemExit as exc:
        if exc.code:
            print(exc.code, file=sys.stderr)
            sys.stderr.flush()
            return 1
        return 0
    except RuntimeError as exc:
        print(f"askllm: error: {exc}", file=sys.stderr)
        sys.stderr.flush()
        return 1

    sys.stdout.flush()
    return 0


def run(argv: list[str] | None = None) -> None:
    code = main(argv)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


if __name__ == "__main__":
    raise SystemExit(main())
