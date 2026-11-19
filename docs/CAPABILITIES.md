# Language and model capabilities

> Generated from `backend/app/registry/*.json` by `scripts/generate_capability_docs.py`. Do not edit by hand.

## How to read this page

- **Declared** coverage comes from a model card or paper. It has not been tested by this project unless a verification report says so.
- Language codes are mapped per model (for example Telugu is `tel_Telu` for NLLB and IndicTrans2, `te_IN` for mBART-50). `codes_verified: false` means the code has not yet been checked against the model's tokenizer on a real installation.
- **Licence verified** means the licence was confirmed against the model's public page or Hub metadata. In commercial mode only verified permissive licences are allowed.
- RAM figures are estimates from the declared parameter count, not measurements.

## Languages

| Code | Name | Native name | Script | Direction |
|---|---|---|---|---|
| `en` | English | English | Latin | left-to-right |
| `te` | Telugu | తెలుగు | Telugu | left-to-right |
| `hi` | Hindi | हिन्दी | Devanagari | left-to-right |
| `ta` | Tamil | தமிழ் | Tamil | left-to-right |
| `kn` | Kannada | ಕನ್ನಡ | Kannada | left-to-right |
| `ml` | Malayalam | മലയാളം | Malayalam | left-to-right |
| `bn` | Bengali | বাংলা | Bengali | left-to-right |
| `mr` | Marathi | मराठी | Devanagari | left-to-right |
| `gu` | Gujarati | ગુજરાતી | Gujarati | left-to-right |
| `ur` | Urdu | اردو | Arabic | right-to-left |
| `pa` | Punjabi (Gurmukhi) | ਪੰਜਾਬੀ | Gurmukhi | left-to-right |

## Models

| Model | Family | Licence | Verified | Params (M) | Est. RAM (MB) | Directed pairs | On by default | Remote code |
|---|---|---|---|---|---|---|---|---|
| `nllb-200-distilled-600m` | nllb | CC-BY-NC-4.0 (non_commercial) | yes | 600 | 3000 | 110 | yes | no |
| `mbart50-many-to-many` | mbart50 | MIT (permissive) | no | 611 | 3055 | 72 | yes | no |
| `indictrans2-en-indic-1b` | indictrans2 | MIT (permissive) | no | 1000 | 5000 | 10 | no | yes |
| `indictrans2-indic-en-1b` | indictrans2 | MIT (permissive) | no | 1000 | 5000 | 10 | no | yes |
| `indictrans2-indic-indic-1b` | indictrans2 | MIT (permissive) | yes | 1000 | 5000 | 90 | no | yes |
| `indictrans2-en-indic-dist-200m` | indictrans2 | MIT (permissive) | no | 200 | 1000 | 10 | no | yes |
| `indictrans2-indic-en-dist-200m` | indictrans2 | MIT (permissive) | no | 200 | 1000 | 10 | no | yes |
| `indictrans2-indic-indic-dist-320m` | indictrans2 | MIT (permissive) | no | 320 | 1600 | 90 | no | yes |

## Coverage and evidence per model

### NLLB-200 distilled (600M)

- Hugging Face repository: `facebook/nllb-200-distilled-600M`
- Licence: CC-BY-NC-4.0 (non_commercial). Research use only. The model card lists production deployment and document translation as out of scope.
- Source languages: bn, en, gu, hi, kn, ml, mr, pa, ta, te, ur
- Target languages: bn, en, gu, hi, kn, ml, mr, pa, ta, te, ur
- Evidence (2026-11-16): Model card: 200 languages. Codes follow FLORES-200 names and are not yet verified against the tokenizer.
- Source: <https://huggingface.co/facebook/nllb-200-distilled-600M>
- Notes: Trained on inputs up to 512 tokens, so long text is translated sentence by sentence.

### mBART-50 many-to-many

- Hugging Face repository: `facebook/mbart-large-50-many-to-many-mmt`
- Licence: MIT (permissive). Expected licence for this checkpoint family; run scripts/pin_models.py to confirm against Hub metadata. Unverified models are excluded in commercial mode.
- Source languages: bn, en, gu, hi, ml, mr, ta, te, ur
- Target languages: bn, en, gu, hi, ml, mr, ta, te, ur
- Evidence (2026-11-16): Model card language list (50 languages). It includes Telugu, Hindi, Tamil, Malayalam, Marathi, Gujarati, Bengali and Urdu, but not Kannada or Punjabi.
- Source: <https://huggingface.co/facebook/mbart-large-50-many-to-many-mmt>
- Notes: Multilingual baseline.

### IndicTrans2 English to Indic (1B)

- Hugging Face repository: `ai4bharat/indictrans2-en-indic-1B`
- Licence: MIT (permissive). MIT per the IndicTrans2 GitHub repository and the sibling indic-indic-1B model page; this repository's own model card was not opened. scripts/pin_models.py verifies it against Hub metadata.
- Source languages: en
- Target languages: bn, gu, hi, kn, ml, mr, pa, ta, te, ur
- Evidence (2026-11-16): Paper and model card: all 22 scheduled Indian languages plus English. Codes follow FLORES-style names and are not yet verified against the tokenizer.
- Source: <https://huggingface.co/ai4bharat/indictrans2-en-indic-1B>
- Source: <https://arxiv.org/abs/2305.16307>
- Notes: Uses custom modelling code (trust_remote_code) and the IndicTransToolkit pre/post-processor. Disabled until the compatibility check passes on your machine.

### IndicTrans2 Indic to English (1B)

- Hugging Face repository: `ai4bharat/indictrans2-indic-en-1B`
- Licence: MIT (permissive). MIT per the IndicTrans2 GitHub repository and the sibling indic-indic-1B model page; this repository's own model card was not opened. scripts/pin_models.py verifies it against Hub metadata.
- Source languages: bn, gu, hi, kn, ml, mr, pa, ta, te, ur
- Target languages: en
- Evidence (2026-11-16): Paper and model card: all 22 scheduled Indian languages plus English. Codes follow FLORES-style names and are not yet verified against the tokenizer.
- Source: <https://huggingface.co/ai4bharat/indictrans2-indic-en-1B>
- Source: <https://arxiv.org/abs/2305.16307>
- Notes: Uses custom modelling code (trust_remote_code) and the IndicTransToolkit pre/post-processor. Disabled until the compatibility check passes on your machine.

### IndicTrans2 Indic to Indic (1B)

- Hugging Face repository: `ai4bharat/indictrans2-indic-indic-1B`
- Licence: MIT (permissive). MIT: shown on the Hub model page and the GitHub repository (checked 2026-11-16).
- Source languages: bn, gu, hi, kn, ml, mr, pa, ta, te, ur
- Target languages: bn, gu, hi, kn, ml, mr, pa, ta, te, ur
- Evidence (2026-11-16): Paper and model card: direct translation between the 22 scheduled Indian languages. Codes follow FLORES-style names and are not yet verified against the tokenizer.
- Source: <https://huggingface.co/ai4bharat/indictrans2-indic-indic-1B>
- Source: <https://arxiv.org/abs/2305.16307>
- Notes: Uses custom modelling code (trust_remote_code) and the IndicTransToolkit pre/post-processor. Disabled until the compatibility check passes on your machine.

### IndicTrans2 English to Indic (distilled 200M)

- Hugging Face repository: `ai4bharat/indictrans2-en-indic-dist-200M`
- Licence: MIT (permissive). MIT per the IndicTrans2 GitHub repository and the sibling indic-indic-1B model page; this repository's own model card was not opened. scripts/pin_models.py verifies it against Hub metadata.
- Source languages: en
- Target languages: bn, gu, hi, kn, ml, mr, pa, ta, te, ur
- Evidence (2026-11-16): Distilled variant of the 1B model; same language coverage. Codes not yet verified against the tokenizer.
- Source: <https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M>
- Notes: Laptop-friendly variant. Uses custom modelling code; disabled until the compatibility check passes.

### IndicTrans2 Indic to English (distilled 200M)

- Hugging Face repository: `ai4bharat/indictrans2-indic-en-dist-200M`
- Licence: MIT (permissive). MIT per the IndicTrans2 GitHub repository and the sibling indic-indic-1B model page; this repository's own model card was not opened. scripts/pin_models.py verifies it against Hub metadata.
- Source languages: bn, gu, hi, kn, ml, mr, pa, ta, te, ur
- Target languages: en
- Evidence (2026-11-16): Distilled variant of the 1B model; same language coverage. Codes not yet verified against the tokenizer.
- Source: <https://huggingface.co/ai4bharat/indictrans2-indic-en-dist-200M>
- Notes: Laptop-friendly variant. Uses custom modelling code; disabled until the compatibility check passes.

### IndicTrans2 Indic to Indic (distilled 320M)

- Hugging Face repository: `ai4bharat/indictrans2-indic-indic-dist-320M`
- Licence: MIT (permissive). MIT per the IndicTrans2 GitHub repository and the sibling indic-indic-1B model page; this repository's own model card was not opened. scripts/pin_models.py verifies it against Hub metadata.
- Source languages: bn, gu, hi, kn, ml, mr, pa, ta, te, ur
- Target languages: bn, gu, hi, kn, ml, mr, pa, ta, te, ur
- Evidence (2026-11-16): Distilled variant of the 1B model; same language coverage. Codes not yet verified against the tokenizer.
- Source: <https://huggingface.co/ai4bharat/indictrans2-indic-indic-dist-320M>
- Notes: Laptop-friendly variant. Uses custom modelling code; disabled until the compatibility check passes.

## Direct translation pairs per model

Rows are the source language, columns the target. A tick means the model declares support for that direction.

### NLLB-200 distilled (600M)

| src \ tgt | en | te | hi | ta | kn | ml | bn | mr | gu | ur | pa |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **en** | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **te** | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **hi** | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **ta** | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **kn** | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **ml** | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ |
| **bn** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ |
| **mr** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ |
| **gu** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ |
| **ur** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ |
| **pa** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · |

### mBART-50 many-to-many

| src \ tgt | en | te | hi | ta | kn | ml | bn | mr | gu | ur | pa |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **en** | · | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | · |
| **te** | ✓ | · | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | · |
| **hi** | ✓ | ✓ | · | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | · |
| **ta** | ✓ | ✓ | ✓ | · | · | ✓ | ✓ | ✓ | ✓ | ✓ | · |
| **kn** | · | · | · | · | · | · | · | · | · | · | · |
| **ml** | ✓ | ✓ | ✓ | ✓ | · | · | ✓ | ✓ | ✓ | ✓ | · |
| **bn** | ✓ | ✓ | ✓ | ✓ | · | ✓ | · | ✓ | ✓ | ✓ | · |
| **mr** | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | · | ✓ | ✓ | · |
| **gu** | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | · | ✓ | · |
| **ur** | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | · | · |
| **pa** | · | · | · | · | · | · | · | · | · | · | · |

### IndicTrans2 English to Indic (1B)

| src \ tgt | en | te | hi | ta | kn | ml | bn | mr | gu | ur | pa |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **en** | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **te** | · | · | · | · | · | · | · | · | · | · | · |
| **hi** | · | · | · | · | · | · | · | · | · | · | · |
| **ta** | · | · | · | · | · | · | · | · | · | · | · |
| **kn** | · | · | · | · | · | · | · | · | · | · | · |
| **ml** | · | · | · | · | · | · | · | · | · | · | · |
| **bn** | · | · | · | · | · | · | · | · | · | · | · |
| **mr** | · | · | · | · | · | · | · | · | · | · | · |
| **gu** | · | · | · | · | · | · | · | · | · | · | · |
| **ur** | · | · | · | · | · | · | · | · | · | · | · |
| **pa** | · | · | · | · | · | · | · | · | · | · | · |

### IndicTrans2 Indic to English (1B)

| src \ tgt | en | te | hi | ta | kn | ml | bn | mr | gu | ur | pa |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **en** | · | · | · | · | · | · | · | · | · | · | · |
| **te** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **hi** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **ta** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **kn** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **ml** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **bn** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **mr** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **gu** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **ur** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **pa** | ✓ | · | · | · | · | · | · | · | · | · | · |

### IndicTrans2 Indic to Indic (1B)

| src \ tgt | en | te | hi | ta | kn | ml | bn | mr | gu | ur | pa |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **en** | · | · | · | · | · | · | · | · | · | · | · |
| **te** | · | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **hi** | · | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **ta** | · | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **kn** | · | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **ml** | · | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ |
| **bn** | · | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ |
| **mr** | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ |
| **gu** | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ |
| **ur** | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ |
| **pa** | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · |

### IndicTrans2 English to Indic (distilled 200M)

| src \ tgt | en | te | hi | ta | kn | ml | bn | mr | gu | ur | pa |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **en** | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **te** | · | · | · | · | · | · | · | · | · | · | · |
| **hi** | · | · | · | · | · | · | · | · | · | · | · |
| **ta** | · | · | · | · | · | · | · | · | · | · | · |
| **kn** | · | · | · | · | · | · | · | · | · | · | · |
| **ml** | · | · | · | · | · | · | · | · | · | · | · |
| **bn** | · | · | · | · | · | · | · | · | · | · | · |
| **mr** | · | · | · | · | · | · | · | · | · | · | · |
| **gu** | · | · | · | · | · | · | · | · | · | · | · |
| **ur** | · | · | · | · | · | · | · | · | · | · | · |
| **pa** | · | · | · | · | · | · | · | · | · | · | · |

### IndicTrans2 Indic to English (distilled 200M)

| src \ tgt | en | te | hi | ta | kn | ml | bn | mr | gu | ur | pa |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **en** | · | · | · | · | · | · | · | · | · | · | · |
| **te** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **hi** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **ta** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **kn** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **ml** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **bn** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **mr** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **gu** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **ur** | ✓ | · | · | · | · | · | · | · | · | · | · |
| **pa** | ✓ | · | · | · | · | · | · | · | · | · | · |

### IndicTrans2 Indic to Indic (distilled 320M)

| src \ tgt | en | te | hi | ta | kn | ml | bn | mr | gu | ur | pa |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **en** | · | · | · | · | · | · | · | · | · | · | · |
| **te** | · | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **hi** | · | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **ta** | · | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **kn** | · | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **ml** | · | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ | ✓ |
| **bn** | · | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ | ✓ |
| **mr** | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ | ✓ |
| **gu** | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | ✓ |
| **ur** | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ |
| **pa** | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · |
