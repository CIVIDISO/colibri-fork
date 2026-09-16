# TypeSafe AI and Colibri

TypeSafe AI's public product is Jev, a System One Model for typed probabilistic decisions. It is not a local inference engine, GPU offload layer, or faster replacement for Colibri's code generation.

## Where it fits

Use Jev as an optional fast decision specialist for:

- deciding which local model or agent role should handle a task;
- classifying a task as inspect, plan, patch, test, browser, sandbox, or media;
- scoring whether an agent result is confident enough for review;
- routing low-risk decisions without spending a long autoregressive coding turn;
- coordinating agent handoffs with typed outcomes and confidence thresholds.

Keep Colibri/Ollama for:

- code and patch generation;
- repository reasoning;
- long-form explanations;
- tool-call planning that needs strings;
- image/video prompt construction.

## Current integration status

Jev is early access and the public pages do not expose a stable endpoint/schema suitable for a hard-coded client. The provider is therefore represented as an optional decision provider, but disabled until TypeSafe access credentials and the official request contract are available.

Do not put a TypeSafe key in the repository or browser storage. The eventual adapter should read a machine-local `TYPESAFE_API_KEY` and a documented `TYPESAFE_BASE_URL`, then normalize Jev's typed response into:

```json
{
  "decision": "plan|patch|test|browser|sandbox|media",
  "confidence": 0.0,
  "reason": "short machine-readable explanation",
  "nextAgent": "role-name"
}
```

The surrounding Colibri approval policy must still win: confidence can recommend an action, never silently authorize a host write, command, browser action, or media job.

## Speed reality

Jev can reduce latency for narrow classification and routing calls because its outputs are typed decisions rather than token-by-token prose. It cannot accelerate the local Qwen3.6/Colibri decode path. The current fast path remains Ollama `qwen2.5-coder:7b` on the RTX 2000 Ada; Colibri's larger model remains the deep path.

Reference: https://typesafe.ai/ and https://github.com/typesafe-ai/system-one-adapter-python
