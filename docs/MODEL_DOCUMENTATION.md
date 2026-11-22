# Model documentation

Facts below were read from public pages on **2026-11-16**. "Declared" means the model authors say so; this project has not yet measured any
translation quality, speed or memory use. Those measurements arrive with the Evaluation Lab (Milestone 3) and `scripts/measure_models.py`.

## Models registered in Milestone 1

| Model | Role | Licence | Declared coverage | Status |
|---|---|---|---|---|
| NLLB-200 distilled 600M | Broad fallback; the default first model | CC-BY-NC-4.0 (research use only) | 200 languages, includes all eleven in the registry | Enabled by default |
| mBART-50 many-to-many | Multilingual baseline | MIT expected, **not yet verified** | 50 languages; includes Telugu, Hindi, Tamil, Malayalam, Marathi, Gujarati, Bengali, Urdu; **not Kannada or Punjabi** | Enabled by default |
| IndicTrans2 (en-indic, indic-en, indic-indic; 1B and distilled) | Intended primary engine for Indian languages | MIT | 22 scheduled Indian languages plus English | Disabled until its compatibility check passes on your machine |

Per-direction tables and the evidence for every model are in the generated page [Capabilities](CAPABILITIES.md).

## What was verified, and where

| Subject | Fact | Source |
|---|---|---|
| NLLB-200 | Licence CC-BY-NC-4.0. The card calls it a research model, not released for production deployment, and says document translation is out of scope. Trained with inputs up to 512 tokens. 200 languages. | <https://huggingface.co/facebook/nllb-200-distilled-600M> |
| mBART-50 | The card's language list contains te_IN, hi_IN, ta_IN, ml_IN, mr_IN, gu_IN, bn_IN, ur_PK and does not contain Kannada or Punjabi. About 611M parameters (third-party catalogue). | <https://huggingface.co/facebook/mbart-large-50-many-to-many-mmt> |
| IndicTrans2 | The paper presents it as the first model to support all 22 scheduled Indian languages; the authors report it outperforming other open-source models on their multi-domain benchmarks, with exceptions (for example English to Tamil on one test set against NLLB 1.2B). | <https://arxiv.org/abs/2305.16307> |
| IndicTrans2 | The indic-indic-1B model page shows the MIT licence, requires `trust_remote_code=True`, and asks you to log in and accept terms (gated). The GitHub repository is MIT, documents CTranslate2 inference, and its last code push was 2024-05-23 (as indexed on the check date). | <https://huggingface.co/ai4bharat/indictrans2-indic-indic-1B>, <https://github.com/AI4Bharat/IndicTrans2> |
| Transformers 5 | v5.19.0 was published 2026-10-06 (release feed). Tokenizers were overhauled (one tokenizer file per model) and the `translation` pipeline is no longer supported, so this project loads models with `AutoModelForSeq2SeqLM` directly. | <https://releases.sh/hugging-face/transformers-releases.md>, NLLB model page notice |
| CTranslate2 | Version 4.8.1 published 2026-07-03, Windows wheels for Python 3.10-3.14, supports encoder-decoder models including NLLB, mBART-50 and M2M-100. A community NLLB conversion reports identical converter output under Transformers 4.57 and 5.5. | <https://pypi.org/project/ctranslate2> |
| TranslateGemma | Released 2026-01-15, 4B/12B/27B, 55 languages, built on Gemma 3, open weights under terms with restrictions. | <https://blog.google/innovation-and-ai/technology/developers-tools/translategemma/> |
| Sarvam-Translate | Fine-tuned from Gemma3-4B-IT, 22 Indian languages including Telugu, long-form context up to 8k tokens; the open checkpoint translates English to and from Indian languages. | <https://huggingface.co/sarvamai/sarvam-translate> |
| Gemma 4 | Released 2026-04-02 under Apache 2.0 in four sizes, trained on 140+ languages. | <https://www.theregister.com/2026/04/02/googles_gemma_4_open_weights/> |
| BGE-M3 | MIT, 100+ languages, up to 8192 tokens, dense, sparse and multi-vector retrieval in one model. | <https://huggingface.co/BAAI/bge-m3>, <https://arxiv.org/abs/2402.03216> |
| IndicLID | Language identification for 22 Indian languages in native and romanised script; MIT per the AIKosh listing. | <https://arxiv.org/abs/2305.15814> |

Background knowledge (not re-checked in this session): mT5 is pretrained on mC4 with a span-corruption objective only, so a raw mT5 checkpoint does not translate
until it is fine-tuned on parallel text. That is why it is not a router default.

## Candidates for later milestones (not integrated)

| Purpose | Candidate | Why it is only a candidate |
|---|---|---|
| Faster CPU inference | CTranslate2 with int8 | Keep only if its speed gain costs less chrF++ than a threshold set beforehand |
| Embeddings, semantic search, RAG | BGE-M3 | Not needed until Milestone 4 |
| Language identification | IndicLID, others | Chosen by accuracy on a labelled set, not by reputation |
| Document-level translation | Sarvam-Translate, TranslateGemma | Need GPU or quantisation; TranslateGemma terms carry restrictions |
| Local LLM for question answering and post-editing | Gemma 4 small variants | Telugu quality must be measured before use |

## Still unverified

- Language codes against each tokenizer (`scripts/verify_language_codes.py`).
- IndicTrans2 with the pinned Transformers version (remote code written for older versions).
- The licence of the exact mBART-50 checkpoint (`scripts/pin_models.py` compares Hub metadata).
- Measured RAM, load time and speed on a student laptop.
- Translation quality for any language pair.
