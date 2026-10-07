# ai/ — centralized AI assistant guidance

Single source of truth for instructions and memories shared across AI coding
tools (Kiro, GitHub Copilot in VS Code, and any `AGENTS.md`-aware tool).

## Layout
- `memory/` — durable rules and lessons the assistant must follow. Each file is
  one topic. Edit these files; they are the canonical content.

## How each tool loads this
The content lives here once. Each tool has a thin pointer file in its own
auto-loaded location so you only maintain the text in `ai/`:

- **Kiro** reads `.kiro/steering/*.md`. The steering files use Kiro's
  `#[[file:...]]` include to pull in files from `ai/memory/`.
- **GitHub Copilot (VS Code)** reads `.github/copilot-instructions.md`, which
  references the files in `ai/memory/`.

## Adding a new memory
1. Create `ai/memory/<topic>.md` with the actual content.
2. Add a `#[[file:../../ai/memory/<topic>.md]]` line to a Kiro steering file
   (or create a new one in `.kiro/steering/`).
3. Add a bullet linking the new file in `.github/copilot-instructions.md`.
