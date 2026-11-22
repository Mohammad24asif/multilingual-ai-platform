# Viva and interview questions

Answers are written in plain English and tied to what is actually implemented. Milestone 1 topics; more are added each milestone.

## Concepts

**1. How does a Transformer translate a sentence?**
The encoder turns the source sentence into contextual vectors using self-attention, where every token looks at every other token. The decoder then writes the target one token at a time:
masked self-attention over what it has written so far, and cross-attention over the encoder's output to decide what to say next. Beam search keeps several partial translations alive and picks the best.

**2. How does one multilingual model know which language to produce?**
The tokenizer has special language-code tokens. For NLLB and mBART-50 the source code is set on the tokenizer (`src_lang`) and the target code is forced as the first generated token (`forced_bos_token_id`).
Our backends check that the tokenizer really knows a code; an unknown code would silently become `<unk>`, so we raise an error instead.

**3. mBART-50, NLLB-200 and IndicTrans2: what is the difference?**
mBART-50 many-to-many covers 50 languages (including Telugu, Hindi, Tamil but not Kannada or Punjabi). NLLB-200 covers 200 languages but its weights are CC-BY-NC-4.0, so research use only.
IndicTrans2 targets the 22 scheduled Indian languages with English-to-Indic, Indic-to-English and Indic-to-Indic models under MIT; it needs custom code and is gated, so we enable it only after a compatibility check.

**4. Why can't a raw mT5 checkpoint translate?**
mT5 is pretrained with a span-filling objective only. It has not been trained on translation pairs, so it must be fine-tuned first. That is why it is an experiment track, not a router default.

**5. Why is detection "script-based", and why does it sometimes ask the user?**
A script identifies a writing system, not a language. Telugu script means Telugu, but Devanagari is used by Hindi, Marathi, Nepali and others. Guessing would mislabel text, so we return the candidates and ask.
We also never show a confidence percentage because we have nothing calibrated to base one on.

**6. Why NFC and not NFKC? What are ZWJ and ZWNJ?**
NFKC rewrites characters and can change meaning. NFC only composes equivalent sequences. ZWJ and ZWNJ are invisible joiners that decide how conjunct consonants and half-forms are drawn in Telugu, Hindi, Malayalam and others, so stripping them would damage the text.

## Design

**7. Why a framework-free core?**
The trust-critical logic (routing, segmentation, validation, queueing) should be testable without web frameworks or multi-gigabyte ML libraries, and should outlive framework changes. Adapters (FastAPI, SQLAlchemy, Transformers) stay thin.

**8. What is the capability registry and why does it matter?**
It is JSON data stating which languages each model supports, the model-specific codes, licences and evidence. The router, API, UI and the generated Capabilities page all read it, so support claims cannot drift or be exaggerated.

**9. How does the router choose a model?**
It evaluates every translation model and records reasons: disabled, language not covered, licence not allowed in the current mode, remote code not reviewed, over the memory budget, weights not downloaded.
Among accepted models it takes the highest priority. Today priority is an editorial prior; when the Evaluation Lab exists it will use measured scores.

**10. What is pivot translation and why is it not automatic?**
Translating te to hi through English means two translations, so errors compound. The router offers it only when the caller sets `allow_pivot=true`, and the result lists both legs.

**11. Why research mode and commercial mode?**
Some licences forbid commercial use. In commercial mode only licences that are permissive and verified are accepted; NLLB is blocked. Every response states the model and licence.

**12. How are long texts handled without losing content?**
We split into sentences while remembering the exact whitespace after each one, translate in length-sorted batches, and re-join with the original separators. Sentences longer than the model limit are split at clauses, then words, and the split is disclosed.
Fuzz tests check that an identity "translation" reproduces the input exactly.

## Reliability and security

**13. Why a single inference worker and a bounded queue?**
Inference blocks, so it must not run on the event loop, and several workers would load several copies of a model into RAM. One worker owns the models; when the queue is full the API answers 503 with Retry-After instead of letting latency grow forever.

**14. What happens on timeout or when the user closes the tab?**
A job still waiting is dropped and never runs. A running job checks a cancel token between batches, so the worst case is finishing one batch.

**15. How do you stop the server running out of memory?**
The model manager loads lazily, caches, evicts the least recently used model, honours a memory budget and a maximum number of loaded models, and the router refuses models that exceed the budget. Memory figures are estimates until measured.

**16. What are the model supply-chain risks and your controls?**
Remote code can run anything, and pickle weight files execute code when loaded. Controls: pinned commit hashes, a human code review step and an allowlist for remote code, safetensors preferred, offline loading by default, and explicit sized downloads.

**17. How do you protect privacy?**
Logs redact content fields and drop exception messages, validation errors never echo input, responses are not cacheable, and history stores metadata only unless a request opts in to storing text.

## Testing and evaluation

**18. How do you test a system that needs gigabytes of models?**
The core is tested with fake backends that exist only under `tests/`; fuzz tests guard invariants; real-model checks are scripts you run after downloading. We state clearly which results were produced where.

**19. How will translation quality be evaluated?**
With chrF++ and spBLEU (SacreBLEU's flores200 tokenizer, which suits Indic scripts better than default BLEU tokenization), COMET where its licence allows, on documented datasets such as FLORES+,
with SacreBLEU signatures stored for reproducibility. BLEU is never presented as a percentage of correctness. Human review complements the metrics.

**20. How could it run faster on a CPU?**
Distilled models, batching, and CTranslate2 with int8 quantisation. We would adopt it only if the measured chrF++ loss stays under a threshold decided in advance.

## Honesty

**21. What are the main limitations today?**
No quality measurements yet; sentence-level translation loses context; detection abstains on shared scripts; IndicTrans2 is unverified with current Transformers; NLLB is research-only; no authentication; many features (NLP tasks, documents, evaluation, history UI) are planned, not built.

**22. A language you want is missing from mBART-50. What do you do?**
Not claim it. Kannada and Punjabi are not in mBART-50's language list, so the registry marks them unsupported for that model and the router uses NLLB (or IndicTrans2 once enabled).
Extending a model's vocabulary would be a research project, not a configuration change.
