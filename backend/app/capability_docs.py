"""Render docs/CAPABILITIES.md from the registry so the documentation cannot drift from the data.

CI (and tests/unit/test_capability_docs.py) fails when the committed file differs from this output.
"""

from __future__ import annotations

from .domain.models import ModelSpec
from .domain.registry import Registry


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _pair_count(spec: ModelSpec) -> int:
    return sum(1 for s in spec.sources for t in spec.targets if s != t)


def render_capabilities(registry: Registry) -> str:
    languages = registry.languages()
    codes = [lang.code for lang in languages]
    out: list[str] = []
    add = out.append
    add("# Language and model capabilities")
    add("")
    add("> Generated from `backend/app/registry/*.json` by `scripts/generate_capability_docs.py`. Do not edit by hand.")
    add("")
    add("## How to read this page")
    add("")
    add("- **Declared** coverage comes from a model card or paper. It has not been tested by this project unless a verification report says so.")
    add("- Language codes are mapped per model (for example Telugu is `tel_Telu` for NLLB and IndicTrans2, `te_IN` for mBART-50). "
        "`codes_verified: false` means the code has not yet been checked against the model's tokenizer on a real installation.")
    add("- **Licence verified** means the licence was confirmed against the model's public page or Hub metadata. In commercial mode only verified permissive licences are allowed.")
    add("- RAM figures are estimates from the declared parameter count, not measurements.")
    add("")
    add("## Languages")
    add("")
    add("| Code | Name | Native name | Script | Direction |")
    add("|---|---|---|---|---|")
    for lang in languages:
        add(f"| `{lang.code}` | {lang.name} | {lang.native_name} | {', '.join(lang.scripts)} | {'right-to-left' if lang.rtl else 'left-to-right'} |")
    add("")
    add("## Models")
    add("")
    add("| Model | Family | Licence | Verified | Params (M) | Est. RAM (MB) | Directed pairs | On by default | Remote code |")
    add("|---|---|---|---|---|---|---|---|---|")
    for spec in registry.models():
        add(
            f"| `{spec.id}` | {spec.family} | {spec.licence.spdx} ({spec.licence.klass.value}) | {_yes_no(spec.licence.verified)} | "
            f"{spec.params_millions:g} | {spec.estimated_ram_mb} | {_pair_count(spec)} | {_yes_no(spec.enabled_by_default)} | {_yes_no(spec.requires_remote_code)} |"
        )
    add("")
    add("## Coverage and evidence per model")
    for spec in registry.models():
        add("")
        add(f"### {spec.display_name}")
        add("")
        add(f"- Hugging Face repository: `{spec.hf_repo}`")
        add(f"- Licence: {spec.licence.spdx} ({spec.licence.klass.value}). {spec.licence.note}")
        add(f"- Source languages: {', '.join(sorted(spec.sources))}")
        add(f"- Target languages: {', '.join(sorted(spec.targets))}")
        add(f"- Evidence ({spec.evidence.get('checked', 'unknown date')}): {spec.evidence.get('coverage', '')}")
        for url in spec.evidence.get("urls", []):
            add(f"- Source: <{url}>")
        if spec.notes:
            add(f"- Notes: {spec.notes}")
    add("")
    add("## Direct translation pairs per model")
    add("")
    add("Rows are the source language, columns the target. A tick means the model declares support for that direction.")
    for spec in registry.models():
        add("")
        add(f"### {spec.display_name}")
        add("")
        add("| src \\ tgt | " + " | ".join(codes) + " |")
        add("|---|" + "---|" * len(codes))
        for src in codes:
            cells = ["✓" if spec.supports(src, tgt) else "·" for tgt in codes]
            add(f"| **{src}** | " + " | ".join(cells) + " |")
    add("")
    return "\n".join(out)
