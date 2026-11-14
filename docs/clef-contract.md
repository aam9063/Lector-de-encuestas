# Clef API contract (captured from the live API, 2026-11-14)

Verification item 1 of the design doc ("the JSON response format is not documented")
is now resolved. Everything below was observed against `POST /v1/systemone` with
`model: "clef"` and a real key. The captured responses live in
[`server/tests/fixtures/clef/`](../server/tests/fixtures/clef/).

## Request

```json
{
  "model": "clef",
  "state": "<string, up to ~16k tokens>",
  "questions": {
    "<id>": { "type": "noul", "instructions": "..." }
  }
}
```

`instructions` is optional per question in practice, but we always send it.

## Question types

| Type | Fields | Response fields |
|---|---|---|
| `noul` | `instructions` | `noul`, `probabilities {yes, no}`, `confidence` |
| `choice` | `instructions`, `criteria` (**object**: label → short description) | `choice` (label), `probabilities {label: p}`, `confidence` |
| `score` | `instructions`, `criteria` (**ordered list** of levels, low → high) | `score` (continuous position), `legend {index: level}`, `probabilities {index: p}`, `confidence` |

Two field names the design doc guessed wrong:

- `choice` uses **`criteria`**, not `options`. Unknown fields are rejected with
  `400 unknown field(s) [...]`.
- `score` uses **`criteria`** as an *ordered list* of levels, not `levels`.
  An object there fails with
  `400 score criteria must be an ordered list of levels`.

## Response envelope

```json
{
  "id": "decision-9086c6bd9ccc8be4",
  "object": "structured_decision",
  "created": 1794648116,
  "model": "clef",
  "answers": { "<id>": { "type": "...", "...": "..." } },
  "usage": { "input_tokens": 286, "output_tokens": 0 },
  "diagnostics": { "<id>": { "label_mass": 1.0, "argmax_is_label": true } },
  "joint": null
}
```

`diagnostics.label_mass` below 1.0 means probability mass fell outside the declared
labels: a signal that the criteria need review, not that the model is wrong.

## Error shape

```json
{ "error": { "message": "...", "type": "BadRequestError", "param": null, "code": 400 } }
```

## Observed latency and cost

Single small state with 2 questions: 286 input tokens, `output_tokens: 0`,
roughly 0.3-0.5 s as the design doc expected. The `score` question on a 5-level
scale returned `confidence` equal to the top label probability (0.26), which is
expected for a flat distribution and confirms `confidence` is not a measure of
label certainty for `score` types.
