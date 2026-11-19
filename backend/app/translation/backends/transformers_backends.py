"""Real translation engines built on Hugging Face Transformers.

STATUS: written against the documented APIs but NOT executed in the build sandbox (no network, no PyTorch).
Verify on your machine with ``python scripts/smoke_translate.py`` (see docs/INSTALLATION.md).

Design notes
* Only ``Auto*`` classes are used, so the code does not depend on class names that changed between
  Transformers 4.x and 5.x. The ``translation`` pipeline is NOT used (removed in v5).
* Language-token handling is verified rather than assumed: at load time we check that setting
  ``tokenizer.src_lang`` really inserts the source-language token, and per request we refuse a target
  code the tokenizer does not know instead of letting it map silently to <unk>.
* Weights load from local files only unless downloads were explicitly allowed.
"""

from __future__ import annotations

import gc
import logging
from collections.abc import Callable, Sequence
from typing import Any

from ...core.errors import InferenceError, ModelLoadError, RemoteCodeNotAllowedError
from ...domain.models import ModelSpec
from .base import BackendContext, GenerationParams, TranslationBackend

logger = logging.getLogger(__name__)


class _Seq2SeqBackend:
    supports_token_count = True
    remote_code = False

    def __init__(self, spec: ModelSpec, ctx: BackendContext) -> None:
        self.spec = spec
        self.ctx = ctx
        self.device = ctx.device
        self._tokenizer: Any = None
        self._model: Any = None

    # -- loading -----------------------------------------------------------------------------
    def _common_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"local_files_only": not self.ctx.allow_download}
        if self.spec.revision:
            kwargs["revision"] = self.spec.revision
        if self.remote_code:
            kwargs["trust_remote_code"] = True  # only reachable for a pinned, human-reviewed revision
        return kwargs

    def load(self) -> None:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        if self.ctx.torch_threads:
            torch.set_num_threads(self.ctx.torch_threads)
        common = self._common_kwargs()
        model_kwargs = dict(common)
        if self.ctx.require_safetensors:
            model_kwargs["use_safetensors"] = True
        self._tokenizer = AutoTokenizer.from_pretrained(self.spec.hf_repo, **common)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(self.spec.hf_repo, **model_kwargs)
        self._model.eval()
        self._model.to(self.device)
        self._self_check()

    def _self_check(self) -> None:  # overridden where there is something cheap to verify
        return None

    def unload(self) -> None:
        self._model = None
        self._tokenizer = None
        gc.collect()
        if self.device == "cuda":
            try:
                import torch

                torch.cuda.empty_cache()
            except ImportError:
                pass

    # -- inference helpers -------------------------------------------------------------------
    def count_tokens(self, text: str, src_code: str) -> int:
        return len(self._tokenizer(text)["input_ids"])

    def _generate(self, encoded: Any, params: GenerationParams, *, forced_bos_token_id: int | None = None, **extra: Any) -> Any:
        import torch

        encoded = {key: value.to(self.device) for key, value in encoded.items()}
        longest = int(encoded["input_ids"].shape[1])
        kwargs: dict[str, Any] = {
            "num_beams": params.num_beams,
            "max_new_tokens": min(params.max_new_tokens, longest * 3 + 16),
            "length_penalty": params.length_penalty,
        }
        if forced_bos_token_id is not None:
            kwargs["forced_bos_token_id"] = forced_bos_token_id
        kwargs.update(extra)
        with torch.inference_mode():
            return self._model.generate(**encoded, **kwargs)

    def translate_batch(self, texts: Sequence[str], src_code: str, tgt_code: str, params: GenerationParams) -> list[str]:
        raise NotImplementedError


class _LanguageTokenBackend(_Seq2SeqBackend):
    """NLLB and mBART-50: the source language is set on the tokenizer, the target via forced_bos_token_id."""

    def _language_token_id(self, code: str) -> int:
        token_id = self._tokenizer.convert_tokens_to_ids(code)
        if token_id is None or token_id == self._tokenizer.unk_token_id:
            raise InferenceError(f"The tokenizer has no language token '{code}'.", code="language_token_missing", extra={"model_id": self.spec.id})
        return int(token_id)

    def _self_check(self) -> None:
        code = self.spec.model_code("en")
        self._tokenizer.src_lang = code
        ids = self._tokenizer("hello")["input_ids"]
        if self._language_token_id(code) not in ids:
            raise RuntimeError("tokenizer did not insert the source-language token; language handling cannot be trusted")

    def translate_batch(self, texts: Sequence[str], src_code: str, tgt_code: str, params: GenerationParams) -> list[str]:
        forced = self._language_token_id(tgt_code)
        self._tokenizer.src_lang = src_code
        encoded = self._tokenizer(list(texts), return_tensors="pt", padding=True, truncation=True, max_length=512)
        generated = self._generate(encoded, params, forced_bos_token_id=forced)
        return list(self._tokenizer.batch_decode(generated, skip_special_tokens=True))


class NllbBackend(_LanguageTokenBackend):
    """facebook/nllb-200-distilled-600M (CC-BY-NC-4.0: research use only)."""


class MBart50Backend(_LanguageTokenBackend):
    """facebook/mbart-large-50-many-to-many-mmt (50 languages; no Kannada or Punjabi)."""


def _make_indic_processor() -> Any:
    last_error: Exception | None = None
    for module_name in ("IndicTransToolkit.processor", "IndicTransToolkit", "IndicTransTokenizer"):
        try:
            module = __import__(module_name, fromlist=["IndicProcessor"])
            processor_cls = module.IndicProcessor
        except (ImportError, AttributeError) as exc:
            last_error = exc
            continue
        try:
            return processor_cls(inference=True)
        except TypeError:
            return processor_cls()
    raise ModelLoadError(
        "IndicTrans2 needs the IndicTransToolkit package (pip install IndicTransToolkit; it may need a C++ build tool on Windows).",
        code="indictranstoolkit_missing",
        extra={"error_type": type(last_error).__name__ if last_error else None},
    )


class IndicTrans2Backend(_Seq2SeqBackend):
    """ai4bharat/indictrans2-* (MIT). Uses custom modelling code, so it only loads for a pinned, reviewed revision."""

    remote_code = True

    def __init__(self, spec: ModelSpec, ctx: BackendContext) -> None:
        super().__init__(spec, ctx)
        self._processor: Any = None

    def load(self) -> None:
        super().load()
        self._processor = _make_indic_processor()

    def unload(self) -> None:
        self._processor = None
        super().unload()

    def translate_batch(self, texts: Sequence[str], src_code: str, tgt_code: str, params: GenerationParams) -> list[str]:
        batch = self._processor.preprocess_batch(list(texts), src_lang=src_code, tgt_lang=tgt_code)
        encoded = self._tokenizer(batch, truncation=True, padding="longest", return_tensors="pt", return_attention_mask=True)
        try:
            generated = self._generate(encoded, params, use_cache=True)
        except (TypeError, AttributeError, RuntimeError) as exc:
            if "cache" not in str(exc).lower():
                raise
            logger.warning("indictrans2 generate failed with use_cache=True; retrying without the cache")
            generated = self._generate(encoded, params, use_cache=False)
        decoded = self._tokenizer.batch_decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        return list(self._processor.postprocess_batch(decoded, lang=tgt_code))


FAMILIES: dict[str, type[_Seq2SeqBackend]] = {
    "nllb": NllbBackend,
    "mbart50": MBart50Backend,
    "indictrans2": IndicTrans2Backend,
}


def make_backend_factory(
    ctx: BackendContext, remote_code_allowlist: frozenset[str] = frozenset()
) -> Callable[[ModelSpec], TranslationBackend]:
    """Build the factory the ModelManager uses. Enforces the remote-code policy a second time (defence in depth)."""

    def factory(spec: ModelSpec) -> TranslationBackend:
        backend_cls = FAMILIES.get(spec.family)
        if backend_cls is None:
            raise ModelLoadError(f"No backend implementation for model family '{spec.family}'.", code="unknown_family")
        if spec.requires_remote_code and not (spec.revision_pinned and f"{spec.hf_repo}@{spec.revision}" in remote_code_allowlist):
            raise RemoteCodeNotAllowedError(
                f"'{spec.id}' runs code from its model repository. Pin its revision (scripts/pin_models.py), review the code "
                "(scripts/review_remote_code.py) and add 'repo@commit' to MLAI_REMOTE_CODE_ALLOWLIST.",
                extra={"model_id": spec.id},
            )
        return backend_cls(spec, ctx)  # type: ignore[return-value]

    return factory
