# Project Instructions

These rules apply to the entire repository.

## Language and communication

- Use English for source code, comments, notebooks, documentation, API fields, test names, and generated responses.
- Prefer clear, natural explanations that a student can confidently discuss.
- Keep names descriptive and avoid unnecessary abstractions.

## Code and notebooks

- Write readable, discussion-friendly Python with small functions and explicit control flow.
- Keep the project Windows-friendly. Use `pathlib` for filesystem paths and avoid shell-specific assumptions.
- Keep notebooks focused: use short Markdown explanations, deterministic cells, and graceful checks for optional tools.
- Put reusable production logic in Python modules rather than notebook-only code.
- Run relevant tests and compilation checks after implementation changes.

## Data and sources

- Preserve source, citation, license, and retrieval metadata for factual educational or health-related knowledge.
- Validate source-backed records before any synthetic expansion.
- Never present synthetic content as source-verified evidence.
- Do not fabricate hardware details, research findings, or dataset sources.

## Services, security, and scope

- Do not use paid services or paid APIs.
- Never commit secrets, tokens, credentials, private keys, or local environment files.
- Keep local configuration out of version control when it can contain machine-specific or sensitive values.
- Do not make unrelated edits.
- Ask before downloading models, datasets, or other large files.
- Ask before destructive actions, including deleting data, rewriting history, or replacing substantial user work.
