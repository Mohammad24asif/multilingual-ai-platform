"""Test doubles. These live under tests/ on purpose: the shipped application never contains fake translators."""

from __future__ import annotations

import threading
import time

from app.domain.models import ModelSpec

SAMPLE_BY_CODE = {
    "tel_Telu": "తెలుగు పాఠం", "hin_Deva": "हिंदी पाठ", "tam_Taml": "தமிழ் உரை", "eng_Latn": "translated text",
    "te_IN": "తెలుగు పాఠం", "hi_IN": "हिंदी पाठ", "en_XX": "translated text", "urd_Arab": "اردو متن",
}


def default_transform(text: str, src: str, tgt: str) -> str:
    return f"{SAMPLE_BY_CODE.get(tgt, 'x')} {len(text)}"


class FakeBackend:
    supports_token_count = False

    def __init__(self, spec: ModelSpec, *, device="cpu", transform=None, fail_load=False, fail_with=None,
                 delay=0.0, gate: threading.Event | None = None, wrong_count=False):
        self.spec = spec
        self.device = device
        self.transform = transform or default_transform
        self.fail_load = fail_load
        self.fail_with = fail_with
        self.delay = delay
        self.gate = gate
        self.wrong_count = wrong_count
        self.loaded = False
        self.calls: list[tuple[list[str], str, str]] = []

    def load(self):
        if self.fail_load:
            raise RuntimeError("weights at C:/secret/path were corrupt: user text leaked here")
        self.loaded = True

    def unload(self):
        self.loaded = False

    def count_tokens(self, text, src_code):
        return len(text.split())

    def translate_batch(self, texts, src_code, tgt_code, params):
        self.calls.append((list(texts), src_code, tgt_code))
        if self.gate is not None:
            self.gate.wait(timeout=5)
        if self.delay:
            time.sleep(self.delay)
        if self.fail_with is not None:
            raise self.fail_with
        out = [self.transform(t, src_code, tgt_code) for t in texts]
        return out[:-1] if self.wrong_count and out else out


class FakeFactory:
    """Creates one FakeBackend per spec (cached by id) and remembers how often it was asked."""

    def __init__(self, **backend_kwargs):
        self.backend_kwargs = backend_kwargs
        self.created: list[FakeBackend] = []
        self.per_model: dict[str, dict] = {}

    def __call__(self, spec: ModelSpec) -> FakeBackend:
        kwargs = {**self.backend_kwargs, **self.per_model.get(spec.id, {})}
        backend = FakeBackend(spec, **kwargs)
        self.created.append(backend)
        return backend

    def backend_for(self, model_id: str) -> FakeBackend:
        return next(b for b in reversed(self.created) if b.spec.id == model_id)
