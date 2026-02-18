# Model Optimization Analysis — AI Presentation Agent

## 1) Current Model Usage

**Status:** A single model is used for all tasks. `LLMClient` is instantiated once with `config.openai_model` (default `gpt-5`) and passed to every component. There is no per-task model selection.

| Step | Component | Calls per run | Input size | Output size | Current model |
|------|-----------|----------------|------------|-------------|----------------|
| Outline | OutlineGenerator | 1 (or 2 on retry) | Small (topic, duration, audience) | Small (sections + points) | gpt-5 |
| Manuscript | ScriptGenerator | 1 | Medium (outline) | **Large** (full prose) | gpt-5 |
| Review evaluate | ScriptReviewer | 1 | **Large** (full manuscript) | Small (score + lists) | gpt-5 |
| Review rewrite | ScriptReviewer | 0–1 (if score < 8) | Large (manuscript + feedback) | **Large** (full prose) | gpt-5 |
| Slides | SlideGenerator | 1 | **Large** (manuscript) | Medium (slides + image_query per slide) | gpt-5 |
| Notes | NotesGenerator | 1 | Large (manuscript + slides) | Medium (notes per slide) | gpt-5 |
| Image vision | ImageService | **N × 3** (N = slides with image_query) | Small (URL + topic) | Tiny (score, reason, bool) | gpt-5 |

**Note:** Image query generation is not a separate step; it is produced in the same SlideGenerator call as titles and bullets.

**Total LLM calls (example: 10 slides, 7 with image_query):**  
1 + 1 + 1 + (0 or 1) + 1 + 1 + 7×3 = **25–26 calls**. Vision dominates call count.

---

## 2) Optimized Model Assignment per Task

| Task | Recommended model | Reasoning |
|------|-------------------|-----------|
| **outline_generation** | `gpt-4o` or `gpt-5-mini` | Structured output, clear schema. Speed and cost matter; quality is high enough with a strong fast model. |
| **manuscript_generation** | `gpt-5` | Long-form creative writing; quality and coherence matter most. Keep best model here. |
| **script_review (evaluate)** | `gpt-5-mini` or `gpt-4o-mini` | Classification/evaluation with fixed schema. Lightweight model is sufficient. |
| **script_review (rewrite)** | `gpt-5` | Same as manuscript; only used when improving. |
| **slide_generation** | `gpt-4o` | Extraction + image query generation. Needs good instruction-following; no need for top reasoning. |
| **notes_generation** | `gpt-5-mini` or `gpt-4o-mini` | Repetitive, per-slide notes. Highly structured; smaller model is enough. |
| **image_vision_evaluation** | `gpt-4o` or `gpt-4o-mini` | Vision required. Many small calls; cheaper/faster vision model reduces cost and latency. |
| **other_tasks** | — | No other LLM tasks in pipeline. |

### Streaming

- **Beneficial:** Manuscript generation (and review rewrite if used). Streaming would improve perceived latency; implementation would require non-JSON streaming + post-process or structured streaming if supported.
- **Not helpful:** All other steps expect a single JSON object; streaming does not reduce time-to-complete.

### Lightweight-friendly tasks

- Outline, script review (evaluate), notes, image vision: all can use a smaller or faster model without sacrificing MVP quality.

---

## 3) Key Performance Bottlenecks

1. **Manuscript generation (1 call)**  
   - Longest single response; drives latency and token cost.  
   - No way to “half-skip”; quality is central.

2. **Image vision (N × 3 calls)**  
   - Largest number of API calls.  
   - Per slide: 3 vision calls are **sequential** (loop with `await`).  
   - Slides are parallel (`asyncio.gather`), but within each slide the three evaluations are not parallelized.

3. **Script review**  
   - One full pass over the manuscript (evaluate); optional second full pass (rewrite).  
   - Both are heavy in input tokens.

4. **Single-model usage**  
   - All steps use the same (expensive) model, so cost and latency are higher than necessary for classification and extraction.

---

## 4) Concrete Recommendations to Improve Speed

- **Use a model map**  
  - Assign the recommended model per task (see Section 5).  
  - Implement via multiple `LLMClient` instances (e.g. `llm_fast`, `llm_vision`, `llm_best`) or a single client with an optional `model` argument per request.

- **Parallelize vision evaluations per slide**  
  - For each slide, run the 3 candidate evaluations with `asyncio.gather` instead of a sequential loop.  
  - Reduces image step latency by up to ~3× for that phase.

- **Keep vision model smaller**  
  - Use `gpt-4o` or `gpt-4o-mini` for `evaluate_image_vision` to cut cost and speed up the many vision calls.

- **Lighter models for evaluate + notes**  
  - Use `gpt-5-mini` or `gpt-4o-mini` for script evaluation and notes generation to reduce cost and improve speed with minimal quality impact.

- **Optional: limit review rewrite**  
  - For MVP, consider a single review pass (evaluate only) and skip rewrite, or only rewrite when score &lt; 6 to save one heavy call when quality is borderline.

- **Caching**  
  - Not applied today. Same (topic, duration, audience) could reuse outline; same outline could reuse manuscript. Only worth adding if you see repeated identical runs.

- **Prompt size**  
  - Script review and notes send the full manuscript. For notes, a short summary or section headers + slide list might be enough to reduce tokens; would require a small prompt redesign.

---

## 5) Recommended Model Map (MVP)

```json
{
  "outline_generation": "gpt-4o",
  "manuscript_generation": "gpt-5",
  "script_review_evaluate": "gpt-5-mini",
  "script_review_rewrite": "gpt-5",
  "slide_generation": "gpt-4o",
  "notes_generation": "gpt-5-mini",
  "image_vision_evaluation": "gpt-4o",
  "other_tasks": "gpt-4o"
}
```

**Rationale (short):**

- **gpt-5:** Manuscript and rewrite only (quality-critical, long-form).
- **gpt-4o:** Outline, slides, vision — good balance of speed, cost, and quality; vision-capable.
- **gpt-5-mini:** Review evaluation and notes — structured, repetitive; minimize cost and latency.

If `gpt-4o-mini` is available and supports vision, use it for `image_vision_evaluation` to further reduce cost and speed up the image step.

**Implementation:** The codebase uses a per-task model map in `Config`. You can override via environment variables:

- `OPENAI_MODEL_OUTLINE` (default: gpt-4o)
- `OPENAI_MODEL_MANUSCRIPT` (default: gpt-5)
- `OPENAI_MODEL_SCRIPT_REVIEW_EVALUATE` (default: gpt-5-mini)
- `OPENAI_MODEL_SCRIPT_REVIEW_REWRITE` (default: gpt-5)
- `OPENAI_MODEL_SLIDES` (default: gpt-4o)
- `OPENAI_MODEL_NOTES` (default: gpt-5-mini)
- `OPENAI_MODEL_IMAGE_VISION` (default: gpt-4o)

If a task-specific variable is not set, `OPENAI_MODEL` is used as fallback, then the default above.

---

## 6) Optional Architectural Improvements

- **Single client, optional model override**  
  - Add `generate_structured(..., model: str | None = None)` and `evaluate_image_vision(..., model: str | None = None)` to `LLMClient`.  
  - If `model` is set, use it for that call; otherwise use the client default.  
  - Config holds a model map (e.g. `outline_model`, `manuscript_model`, …); each generator receives the same client and the config, and passes the appropriate model key when calling.

- **Parallel vision per slide**  
  - In `ImageService.fetch_image_for_query`, replace the loop over candidates with `asyncio.gather(*[self._evaluate_candidate(c, ...) for c in candidates])` (with proper handling of None and selection logic).  
  - No change to the rest of the pipeline.

- **Combine steps**  
  - Theoretically, slides + notes could be one call (slides + notes per slide). Would reduce one round-trip but increase prompt/response size and coupling; only consider if you later optimize for minimal call count over clarity.

---

## Summary

- **Current:** One model (gpt-5) for all steps; vision is N×3 calls, sequential per slide.
- **Target:** Per-task model map (gpt-5 for manuscript/rewrite, gpt-4o for outline/slides/vision, gpt-5-mini for review-evaluate and notes).
- **Quick wins:** Parallelize the 3 vision calls per slide; use a smaller/vision-capable model for image evaluation; use lighter models for script evaluation and notes.
- **Code:** Add optional `model` override to `LLMClient` and a small model map in config; pass model key from each component. In `image_service`, evaluate the 3 candidates in parallel with `asyncio.gather`.
