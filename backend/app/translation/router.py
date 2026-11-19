"""Capability-, licence- and resource-aware translation routing.

The router never picks a model just to return *something*. For every request it evaluates every
registered translation model, records why each was accepted or rejected, and either returns the best
accepted one or raises a precise error. Pivot translation (through English) happens only when the
caller explicitly allows it, and is always disclosed in the plan.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ..core.errors import (
    ModelNotDownloadedError,
    SameLanguageError,
    UnknownModelError,
    UnsupportedLanguageError,
    UnsupportedPairError,
)
from ..domain.models import LicenceClass, ModelSpec
from ..domain.registry import Registry

LICENCE_MODES = ("research", "commercial")


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    licence_mode: str = "research"  # "research" allows research-only licences; "commercial" requires verified permissive ones
    enabled_models: frozenset[str] | None = None  # None => every model with enabled_by_default
    ram_budget_mb: int | None = None  # None => no memory limit
    remote_code_allowlist: frozenset[str] = frozenset()  # "repo@40-hex-commit" entries a human has reviewed
    pivot_languages: tuple[str, ...] = ("en",)

    def __post_init__(self) -> None:
        if self.licence_mode not in LICENCE_MODES:
            raise ValueError(f"licence_mode must be one of {LICENCE_MODES}")


@dataclass(frozen=True, slots=True)
class Candidate:
    spec: ModelSpec
    reasons: tuple[str, ...]  # empty => accepted

    @property
    def accepted(self) -> bool:
        return not self.reasons


@dataclass(frozen=True, slots=True)
class Route:
    spec: ModelSpec
    source: str
    target: str
    considered: tuple[Candidate, ...] = field(default=(), compare=False)


@dataclass(frozen=True, slots=True)
class RoutePlan:
    legs: tuple[Route, ...]
    pivot_via: str | None = None

    @property
    def is_pivot(self) -> bool:
        return self.pivot_via is not None


class TranslationRouter:
    def __init__(
        self,
        registry: Registry,
        policy: RoutingPolicy,
        *,
        is_available: Callable[[ModelSpec], bool] | None = None,
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._is_available = is_available

    @property
    def policy(self) -> RoutingPolicy:
        return self._policy

    # -- evaluation --------------------------------------------------------------------------
    def is_enabled(self, spec: ModelSpec) -> bool:
        enabled = self._policy.enabled_models
        return spec.enabled_by_default if enabled is None else spec.id in enabled

    def remote_code_allowed(self, spec: ModelSpec) -> bool:
        return spec.revision_pinned and f"{spec.hf_repo}@{spec.revision}" in self._policy.remote_code_allowlist

    def policy_reasons(self, spec: ModelSpec, *, check_availability: bool = True) -> list[str]:
        """Reasons unrelated to which languages the model covers (switches, licence, safety, resources)."""
        reasons: list[str] = []
        if not self.is_enabled(spec):
            reasons.append("disabled")
        if self._policy.licence_mode == "commercial":
            if spec.licence.klass is not LicenceClass.PERMISSIVE:
                reasons.append(f"licence_not_allowed:{spec.licence.klass.value}")
            elif not spec.licence.verified:
                reasons.append("licence_unverified")
        elif spec.licence.klass is LicenceClass.UNKNOWN:
            reasons.append("licence_unknown")
        if spec.requires_remote_code and not self.remote_code_allowed(spec):
            reasons.append("remote_code_not_reviewed")
        budget = self._policy.ram_budget_mb
        if budget is not None and spec.estimated_ram_mb is not None and spec.estimated_ram_mb > budget:
            reasons.append("exceeds_ram_budget")
        if check_availability and self._is_available is not None and not self._is_available(spec):
            reasons.append("not_downloaded")
        return reasons

    def _reasons(self, spec: ModelSpec, src: str, tgt: str, *, check_availability: bool = True) -> list[str]:
        reasons = self.policy_reasons(spec, check_availability=check_availability)
        if src not in spec.sources:
            reasons.append("source_language_not_supported")
        if tgt not in spec.targets:
            reasons.append("target_language_not_supported")
        return reasons

    def usable_models(self, *, check_availability: bool = True) -> list[ModelSpec]:
        """Translation models that pass every policy check (switches, licence, safety, resources, availability)."""
        return [s for s in self._registry.models("translate") if not self.policy_reasons(s, check_availability=check_availability)]

    def evaluate(self, src: str, tgt: str, *, check_availability: bool = True) -> list[Candidate]:
        """Every translation model with the reasons (if any) it cannot serve this pair, best first."""
        candidates = [
            Candidate(spec, tuple(self._reasons(spec, src, tgt, check_availability=check_availability)))
            for spec in self._registry.models("translate")
        ]
        accepted = sorted((c for c in candidates if c.accepted), key=lambda c: (-c.spec.priority, c.spec.estimated_ram_mb or 0, c.spec.id))
        rejected = [c for c in candidates if not c.accepted]
        return accepted + rejected

    # -- routing -----------------------------------------------------------------------------
    def route(self, src: str, tgt: str, *, model_id: str | None = None) -> Route:
        for code in (src, tgt):
            if self._registry.language(code) is None:
                raise UnsupportedLanguageError(f"Language '{code}' is not in the registry.", extra={"language": code})
        if src == tgt:
            raise SameLanguageError("Choose two different languages.")
        candidates = self.evaluate(src, tgt)
        if model_id is not None:
            spec = self._registry.model(model_id)
            if spec is None or spec.task != "translate":
                raise UnknownModelError(f"'{model_id}' is not a registered translation model.", extra={"model_id": model_id})
            chosen = next(c for c in candidates if c.spec.id == model_id)
            if not chosen.accepted:
                self._raise_for_rejected([chosen], src, tgt, requested=True)
            return Route(chosen.spec, src, tgt, tuple(candidates))
        accepted = [c for c in candidates if c.accepted]
        if accepted:
            return Route(accepted[0].spec, src, tgt, tuple(candidates))
        self._raise_for_rejected(candidates, src, tgt, requested=False)
        raise AssertionError("unreachable")  # pragma: no cover

    def _raise_for_rejected(self, candidates: list[Candidate], src: str, tgt: str, *, requested: bool) -> None:
        only_download = [c for c in candidates if c.reasons == ("not_downloaded",)]
        if only_download:
            ids = [c.spec.id for c in only_download]
            raise ModelNotDownloadedError(
                f"A suitable model exists but its weights are not downloaded: {', '.join(ids)}.",
                extra={"model_ids": ids, "hint": "Run: python scripts/download_models.py --model " + ids[0]},
            )
        reasons = {c.spec.id: list(c.reasons) for c in candidates}
        who = "The requested model cannot translate" if requested else "No enabled model can translate"
        raise UnsupportedPairError(f"{who} {src} to {tgt}.", extra={"source": src, "target": tgt, "reasons": reasons})

    def plan(self, src: str, tgt: str, *, model_id: str | None = None, allow_pivot: bool = False) -> RoutePlan:
        try:
            return RoutePlan(legs=(self.route(src, tgt, model_id=model_id),))
        except (UnsupportedPairError, ModelNotDownloadedError) as direct_error:
            if model_id is not None:
                raise
            pivot = self._find_pivot(src, tgt)
            if pivot is None:
                raise
            if not allow_pivot:
                direct_error.extra["pivot_available_via"] = pivot.pivot_via
                direct_error.detail += f" A two-step translation via {pivot.pivot_via} is possible; retry with allow_pivot=true."
                raise
            return pivot

    def _find_pivot(self, src: str, tgt: str) -> RoutePlan | None:
        for via in self._policy.pivot_languages:
            if via in (src, tgt) or self._registry.language(via) is None:
                continue
            try:
                first = self.route(src, via)
                second = self.route(via, tgt)
            except (UnsupportedPairError, ModelNotDownloadedError):
                continue
            return RoutePlan(legs=(first, second), pivot_via=via)
        return None

    # -- reporting ---------------------------------------------------------------------------
    def supported_languages(self) -> dict[str, dict[str, bool]]:
        """For each registry language: can it be a source / target under the current policy (ignoring downloads)?"""
        usable = [s for s in self._registry.models("translate") if not self.policy_reasons(s, check_availability=False)]
        result: dict[str, dict[str, bool]] = {}
        for lang in self._registry.languages():
            code = lang.code
            result[code] = {
                "source": any(code in s.sources and (s.targets - {code}) for s in usable),
                "target": any(code in s.targets and (s.sources - {code}) for s in usable),
            }
        return result
