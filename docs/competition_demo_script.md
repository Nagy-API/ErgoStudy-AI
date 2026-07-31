# Competition demo script

Use this five-to-seven-minute flow:

1. State the boundary: this repository is a personalized one-day study planner. Physical sensors exist but are owned by hardware and Flutter teams and are never sent to the AI backend. All users receive the same AI features.
2. Show a school request with custom topics and explain strict input validation.
3. Show a university request using `CS` and `Stats` aliases and point to canonical retrieval.
4. Show a 30-minute request where one subject cannot fit and appears explicitly as unscheduled.
5. Show an unknown subject and the visible knowledge fallback instead of invented evidence.
6. Show normal timer-based breaks and the unchanged deterministic score/allocation rules.
7. Request an optional Ollama explanation. If Ollama is unavailable or slow, show the deterministic fallback as the designed success path.
8. Open `/openapi.json` and show the six active endpoints and absence of hardware-specific schemas.

Before the demo, run dataset validation, Chroma verification, `scripts/final_validation.py`, and the full test suite. Prewarm Ollama only if the model is already installed; never download it during preparation. Keep the generated JSON demo artifacts available as a backup.
