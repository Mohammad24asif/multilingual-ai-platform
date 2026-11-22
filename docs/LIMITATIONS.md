# Limitations

Written to be read before you rely on anything. Items marked *by design* are choices; the rest are gaps.

## Translation quality

- **No quality has been measured yet.** There are no BLEU, chrF++ or COMET numbers for any model in this project. Results shown in the UI are model outputs, not evaluated claims.
- Translation is **sentence by sentence**, so context across sentences (pronouns, names, tone) is lost. Long documents will read less well than a human or document-level translation.
- Named entities, numbers and dates are not protected; a model may transliterate or alter them.
- Low-resource directions can be poor. Telugu quality depends on the model; compare models in the UI before trusting one.
- The validation warnings (wrong script, copied sentences, length outliers) are heuristics. Their absence does not mean the translation is correct.

## Languages and detection

- Eleven languages are registered. NLLB and IndicTrans2 cover more, but they are not added until their codes are verified against a tokenizer.
- mBART-50 does not cover Kannada or Punjabi. Any "50 languages" claim applies to mBART-50 translation only.
- **Detection is script-based.** Telugu, Tamil, Kannada, Malayalam, Gujarati and Gurmukhi resolve by script. Devanagari (Hindi, Marathi, others), Arabic script (Urdu and others), Bengali script (Bengali and Assamese) and Latin text need your choice. Kannada script is also used for Tulu; text is assumed to be Kannada.
- Romanised Indian-language text (for example Telugu in English letters) is not recognised; it will be reported as ambiguous at best.
- The English check uses function-word evidence and abstains on short text, so "Hello" alone asks you to confirm.
- Code-mixed text is handled only by dominant script share (60%).

## Segmentation

- Rule-based and documented: a newline always ends a sentence, so hard-wrapped text (copied from a PDF) is translated line by line. Document de-wrapping arrives with Milestone 5.
- Abbreviation handling is a short English list; other abbreviations can cause a wrong split.

## Models and licences

- NLLB-200 is **research use only** (CC-BY-NC-4.0). Commercial mode blocks it.
- IndicTrans2 is disabled until its remote code is shown to work with your Transformers version and you have reviewed it. It is also gated on Hugging Face.
- Memory figures are estimates from parameter counts, not measurements. The first request after start-up loads the model and can take a minute on a CPU.
- Only one model is kept in memory by default (`MLAI_MAX_LOADED_MODELS=1`); switching models reloads weights.
- Inference is serial by design (one worker). A busy server answers 503 rather than queueing without limit.

## Security and operations

- No authentication or rate limiting: local use only (see SECURITY.md).
- Requests without a Content-Length header are not size-limited by the middleware yet.
- Docker files, GitHub Actions workflows and the Alembic migration were written offline and have not been executed.

## Features not built yet

Summarisation, sentiment, named-entity recognition, classification, question answering, keyword extraction, document upload and translation, the evaluation lab,
translation history in the UI, glossary and translation memory, semantic search and RAG, UI localisation, model comparison view. See PROJECT_STATUS.md for the plan.
