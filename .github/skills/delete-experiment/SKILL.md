---
name: delete-experiment
description: "Use when the user asks to delete, remove, clean up, purge, or reset an experiment folder — either locally (WSL) or remotely from Azure Files. Stops any running trainer first. Asks whether the experiment is local or remote before proceeding."
---

# Delete Experiment

Use this skill to safely remove an experiment. Always confirm game + experiment
name with the user before any destructive action.

---

## Step 0 — Detect Current Game and Confirm

```bash
ls -d rl_coding_game/games/*/
ls -d rl_coding_game/experiments/*/ 2>/dev/null || echo "(none)"
```

Ask the user:
> The game is **`<GAME>`**, experiment to delete: **`<EXPERIMENT_NAME>`**. Confirm?

**Do not proceed until the user confirms.**

---

## Step 1 — Ask: LOCAL or REMOTE?

> Is this experiment stored **locally** (`rl_coding_game/experiments/`) or **remotely** (Azure Files)?

---

## ── LOCAL ──────────────────────────────────────────────────────────────────

### A) Check the experiment exists

```bash
test -d "rl_coding_game/experiments/<GAME>/<EXPERIMENT_NAME>" \
    && echo "exists" || echo "not found"
```

### B) Find a live trainer

```bash
pgrep -af 'train_rainbow.py' | grep '<EXPERIMENT_NAME>' || echo "(no matching process)"
```

### C) Stop the live trainer (if any, after user confirms)

```bash
pkill -f "train_rainbow.py.*<EXPERIMENT_NAME>"
```

### D) Delete the experiment directory

```bash
rm -rf "rl_coding_game/experiments/<GAME>/<EXPERIMENT_NAME>"
```

### E) Confirm deletion

```bash
test -d "rl_coding_game/experiments/<GAME>/<EXPERIMENT_NAME>" \
    && echo "still exists" || echo "deleted"
```

---

## ── REMOTE (Azure Files) ─────────────────────────────────────────────────

### Prerequisites

```bash
source rl_coding_game/env.sh
KEY=$(az storage account keys list \
    -n "$AZURE_STORAGE_ACCT" -g "$AZURE_RG" \
    --query '[0].value' -o tsv | tr -d '\r')
```

### A) Confirm the experiment directory exists in Azure Files

```bash
az storage directory exists \
    --share-name experiments \
    --name "<GAME>/<EXPERIMENT_NAME>" \
    --account-name "$AZURE_STORAGE_ACCT" \
    --account-key "$KEY" \
    --query exists -o tsv
```

### B) Delete the experiment directory recursively

```bash
az storage remove \
    --account-name "$AZURE_STORAGE_ACCT" \
    --account-key "$KEY" \
    --share-name experiments \
    --path "<GAME>/<EXPERIMENT_NAME>" \
    --recursive
```

### C) Confirm deletion

```bash
az storage directory exists \
    --share-name experiments \
    --name "<GAME>/<EXPERIMENT_NAME>" \
    --account-name "$AZURE_STORAGE_ACCT" \
    --account-key "$KEY" \
    --query exists -o tsv
# Expected: false
```

---

## Safety Checks (both flavours)

- User must confirm **game + experiment name** in Step 0 before proceeding.
- The resolved path must be exactly under `experiments/<GAME>/` — never a parent.
- Check for a running trainer (local) before deleting.

**Never delete:**

- `offline_pretrain` experiment (immutable expert seed — refuse and warn)
- `rl_coding_game/experiments/<GAME>` or `experiments` themselves
- `rl_coding_game/data/games/<GAME>/replays`
