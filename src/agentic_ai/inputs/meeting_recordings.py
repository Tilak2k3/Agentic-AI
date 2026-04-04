"""Meeting recordings: plain text files or audio transcribed via Hugging Face ASR."""

from __future__ import annotations

from pathlib import Path

from agentic_ai.config import get_hf_asr_config

AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus", ".webm", ".aac"})
TEXT_EXTENSIONS = frozenset({".txt", ".md", ".markdown", ".log"})


def _read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def transcribe_audio_file(
    audio_path: str | Path,
    *,
    model: str | None = None,
    api_key: str | None = None,
    provider: str | None = None,
) -> str:
    """Transcribe audio using Hugging Face InferenceClient (Whisper or compatible model)."""
    from huggingface_hub import InferenceClient

    cfg = get_hf_asr_config()
    key = api_key if api_key is not None else cfg.api_key
    if not key:
        raise ValueError(
            "Missing Hugging Face API token. Set HUGGINGFACE_API_KEY or HF_TOKEN in the environment."
        )
    use_model = model or cfg.model
    use_provider = provider if provider is not None else cfg.provider

    kwargs = {"api_key": key}
    if use_provider is not None:
        kwargs["provider"] = use_provider
    client = InferenceClient(**kwargs)
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    result = client.automatic_speech_recognition(str(path), model=use_model)
    if isinstance(result, str):
        return result
    if hasattr(result, "text"):
        return getattr(result, "text") or ""
    if isinstance(result, dict) and "text" in result:
        return str(result["text"])
    return str(result)


def extract_meeting_text(
    path: str | Path,
    *,
    asr_model: str | None = None,
    hf_api_key: str | None = None,
    hf_provider: str | None = None,
) -> str:
    """
    Load meeting content from a file.

    - Text-like extensions (.txt, .md, …): read as UTF-8.
    - Audio extensions: transcribe via Hugging Face ASR.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    suffix = p.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return _read_utf8(p)
    if suffix in AUDIO_EXTENSIONS:
        return transcribe_audio_file(
            p,
            model=asr_model,
            api_key=hf_api_key,
            provider=hf_provider,
        )
    raise ValueError(
        f"Unsupported meeting file type {suffix!r}. "
        f"Use one of {sorted(TEXT_EXTENSIONS | AUDIO_EXTENSIONS)}."
    )
