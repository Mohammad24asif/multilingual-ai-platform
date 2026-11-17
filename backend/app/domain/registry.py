"""Language and model registry: the single source of truth for what the platform claims to support.

Data lives in ``app/registry/*.json`` (hand-edited declarations) plus an optional machine-written
``models.lock.json`` (pinned revisions and licence checks produced by ``scripts/pin_models.py``).
Everything the router, API, UI and generated documentation say about support comes from here.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path
from typing import Any

from .models import (
    Language,
    Licence,
    LicenceClass,
    ModelSpec,
    ScriptInfo,
    UnlistedLanguage,
)

DEFAULT_REGISTRY_DIR = Path(__file__).resolve().parents[1] / "registry"


class RegistryError(ValueError):
    """Raised when registry data is inconsistent. The message lists every problem found."""


class Registry:
    def __init__(
        self,
        languages: Iterable[Language],
        models: Iterable[ModelSpec],
        unlisted: Iterable[UnlistedLanguage] = (),
        script_info: Iterable[ScriptInfo] = (),
    ) -> None:
        self._languages = {lang.code: lang for lang in languages}
        self._models = {m.id: m for m in models}
        self._unlisted = tuple(unlisted)
        self._script_info = {s.name: s for s in script_info}

    # -- languages ---------------------------------------------------------------------------
    def languages(self) -> list[Language]:
        return list(self._languages.values())

    def language(self, code: str) -> Language | None:
        return self._languages.get(code)

    def script_is_open(self, script: str) -> bool:
        info = self._script_info.get(script)
        return bool(info and info.open)

    def script_note(self, script: str) -> str:
        info = self._script_info.get(script)
        return info.note if info else ""

    def languages_for_script(self, script: str) -> list[tuple[str, str, bool]]:
        """(code, name, listed) for every known language that uses ``script``."""
        found = [(l.code, l.name, True) for l in self._languages.values() if script in l.scripts]
        found += [(u.code, u.name, False) for u in self._unlisted if script in u.scripts]
        return found

    # -- models ------------------------------------------------------------------------------
    def models(self, task: str | None = None) -> list[ModelSpec]:
        return [m for m in self._models.values() if task is None or m.task == task]

    def model(self, model_id: str) -> ModelSpec | None:
        return self._models.get(model_id)

    # -- loading -----------------------------------------------------------------------------
    @classmethod
    def from_dir(cls, directory: Path | str = DEFAULT_REGISTRY_DIR) -> Registry:
        directory = Path(directory)
        languages_doc = _read_json(directory / "languages.json")
        models_doc = _read_json(directory / "models.json")
        lock_path = directory / "models.lock.json"
        lock_doc = _read_json(lock_path) if lock_path.exists() else {"models": {}}
        return cls.from_documents(languages_doc, models_doc, lock_doc)

    @classmethod
    def from_documents(
        cls, languages_doc: dict[str, Any], models_doc: dict[str, Any], lock_doc: dict[str, Any] | None = None
    ) -> Registry:
        errors: list[str] = []
        languages = [
            Language(
                code=item["code"],
                name=item["name"],
                native_name=item.get("native_name", item["name"]),
                scripts=tuple(item["scripts"]),
                rtl=bool(item.get("rtl", False)),
            )
            for item in languages_doc.get("languages", [])
        ]
        codes = [l.code for l in languages]
        if len(codes) != len(set(codes)):
            errors.append("duplicate language codes in languages.json")
        unlisted = [
            UnlistedLanguage(item["code"], item["name"], tuple(item["scripts"]))
            for item in languages_doc.get("known_unlisted", [])
        ]
        script_info = [
            ScriptInfo(name, bool(info.get("open", False)), info.get("note", ""))
            for name, info in languages_doc.get("script_info", {}).items()
        ]
        language_codes = set(codes)
        locks = (lock_doc or {}).get("models", {})
        models: list[ModelSpec] = []
        seen_ids: set[str] = set()
        for item in models_doc.get("models", []):
            mid = item.get("id", "<missing id>")
            if mid in seen_ids:
                errors.append(f"duplicate model id {mid}")
            seen_ids.add(mid)
            code_set_name = item.get("code_set")
            code_set = models_doc.get("code_sets", {}).get(code_set_name)
            if code_set is None:
                errors.append(f"{mid}: unknown code_set {code_set_name!r}")
                continue
            unknown = set(code_set) - language_codes
            if unknown:
                errors.append(f"{mid}: code set {code_set_name} uses languages missing from languages.json: {sorted(unknown)}")
            sources = _resolve_languages(item.get("sources", "all"), code_set, errors, mid, "sources")
            targets = _resolve_languages(item.get("targets", "all"), code_set, errors, mid, "targets")
            lic = item["licence"]
            try:
                klass = LicenceClass(lic["class"])
            except ValueError:
                errors.append(f"{mid}: unknown licence class {lic.get('class')!r}")
                klass = LicenceClass.UNKNOWN
            licence = Licence(lic["spdx"], klass, bool(lic.get("verified", False)), lic.get("note", ""))
            revision = item.get("revision")
            lock = locks.get(mid)
            if lock:
                revision = lock.get("revision") or revision
                hub_licence = lock.get("hub_licence")
                if hub_licence is not None:
                    if hub_licence.lower() == licence.spdx.lower():
                        licence = replace(licence, verified=True)
                    else:
                        licence = Licence(
                            hub_licence, LicenceClass.UNKNOWN, False,
                            f"Hub reports '{hub_licence}' but registry declares '{licence.spdx}'; review before use.",
                        )
            models.append(
                ModelSpec(
                    id=mid,
                    display_name=item.get("display_name", mid),
                    family=item["family"],
                    task=item.get("task", "translate"),
                    hf_repo=item["hf_repo"],
                    revision=revision,
                    licence=licence,
                    requires_remote_code=bool(item.get("requires_remote_code", False)),
                    params_millions=item.get("params_millions"),
                    language_codes=dict(code_set),
                    sources=frozenset(sources),
                    targets=frozenset(targets),
                    priority=int(item.get("priority", 0)),
                    enabled_by_default=bool(item.get("enabled_by_default", False)),
                    segment_token_limit=int(item.get("segment_token_limit", 200)),
                    evidence=dict(item.get("evidence", {})),
                    notes=item.get("notes", ""),
                )
            )
        if errors:
            raise RegistryError("; ".join(errors))
        return cls(languages, models, unlisted, script_info)


def _resolve_languages(spec: Any, code_set: dict[str, str], errors: list[str], mid: str, label: str) -> set[str]:
    if spec == "all":
        return set(code_set)
    if spec == "non_english":
        return {c for c in code_set if c != "en"}
    if isinstance(spec, list):
        missing = [c for c in spec if c not in code_set]
        if missing:
            errors.append(f"{mid}: {label} not in its code set: {missing}")
        return {c for c in spec if c in code_set}
    errors.append(f"{mid}: bad {label} specification {spec!r}")
    return set()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
