---
name: aca-tensorboard
description: "Use when the user wants to view TensorBoard metrics for a training experiment stored in Azure Files. Syncs TF event files from Azure Files to a local temp directory and opens TensorBoard in the browser."
---

# ACA TensorBoard — View Remote Experiment Locally

Use this skill when training is running (or has run) on ACA and the user wants
to inspect TensorBoard metrics locally.

Event files live in Azure Files at:
```
experiments/<game>/<experiment>/runs/events.out.tfevents.*
```

The script downloads them to a local temp directory and launches TensorBoard
pointing at that directory.

---

## Execution context

**Local (WSL)**: Use the bash script. It sources `env.sh` for defaults.

```bash
source pz_cellularena/env.sh
./pz_cellularena/remote/aca/tensorboard_local.sh -a "$AZURE_STORAGE_ACCT"
```

A PowerShell version (`tensorboard_local.ps1`) also exists for Windows hosts.

---

## Inputs To Ask Or Confirm

- Storage account name (from `aca-setup` output, or `$AZURE_STORAGE_ACCT` in `env.sh`)
- Game (default: `cellularena`)
- Experiment name — leave empty to view **all** experiments for the game
- Port (default: `6006`)
- Watch mode? (`-w` keeps re-syncing every 30 s while TensorBoard runs)

---

## Commands (bash / WSL)

### View a single experiment

```bash
./pz_cellularena/remote/aca/tensorboard_local.sh \
    -a <STORAGE_ACCOUNT_NAME> \
    -x exp_001_baseline
```

### View all experiments for the game (compare runs)

```bash
./pz_cellularena/remote/aca/tensorboard_local.sh \
    -a <STORAGE_ACCOUNT_NAME>
```

### Keep syncing during live training

```bash
./pz_cellularena/remote/aca/tensorboard_local.sh \
    -a <STORAGE_ACCOUNT_NAME> \
    -x exp_001_baseline \
    -w
```

---

## What The Script Does

1. Fetches the storage key from Azure (`az storage account keys list`)
2. Downloads event files via `az storage file download-batch` matching `events.out.tfevents.*`
3. Starts TensorBoard via `conda run -n cellularena tensorboard --logdir <local_dir>`
4. In `-w` mode: re-runs the sync every 30 s until TensorBoard exits

Local sync directory: `/tmp/cellularena_tb/`

---

## Manual Sync (without TensorBoard)

```bash
source pz_cellularena/env.sh
KEY=$(az storage account keys list -n "$AZURE_STORAGE_ACCT" -g "$AZURE_RG" --query '[0].value' -o tsv)
az storage file download-batch \
    --source experiments \
    --destination /tmp/cellularena_tb \
    --account-name "$AZURE_STORAGE_ACCT" \
    --account-key "$KEY" \
    --pattern "experiments/cellularena/<EXPERIMENT>/runs/events.out.tfevents.*"
```

---

## What To Report Back

- Local logdir path where events were synced
- TensorBoard URL: `http://localhost:<port>`
- Number of event files synced
