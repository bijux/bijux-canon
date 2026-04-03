#!/usr/bin/env bash
# Robust, repo-local Kaggle downloader + extractor for a CS-only 10k sample
set -Eeuo pipefail
export LC_ALL=C.UTF-8

### --- Config (overridable via env/.env) ---
DATASET_ID="${DATASET_ID:-mayurrane/arxiv-metadata-oai-snapshot}"
SAMPLE_N="${SAMPLE_N:-10000}"
CATEGORY_PATTERN="${CATEGORY_PATTERN:-(^|[[:space:]])cs\.}"   # matches any 'cs.' token
OUT_FILENAME="${OUT_FILENAME:-arxiv_cs_abstracts_10k.csv}"
### ----------------------------------------

# --- Require tools ---
command -v git    >/dev/null || { echo "git required"; exit 1; }
command -v unzip  >/dev/null || { echo "unzip required"; exit 1; }
command -v kaggle >/dev/null || { echo "kaggle CLI required (pip install kaggle)"; exit 1; }

# --- Resolve repo root & load .env if present ---
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export REPO_ROOT
if [[ -f "${REPO_ROOT}/.env" ]]; then set -a; source "${REPO_ROOT}/.env"; set +a; fi

# --- Python interpreter (prefer repo venv) ---
if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
  elif command -v python3 >/dev/null; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null; then
    PYTHON_BIN="$(command -v python)"
  else
    echo "Python interpreter not found. Activate the project venv or set PYTHON_BIN." >&2
    exit 1
  fi
fi
export PYTHON_BIN

# --- Fallback to ~/.kaggle/kaggle.json if env vars absent ---
if [[ -z "${KAGGLE_USERNAME:-}" || -z "${KAGGLE_KEY:-}" ]]; then
  if [[ -f "$HOME/.kaggle/kaggle.json" ]]; then
    eval "$(
      "$PYTHON_BIN" - <<'PY'
import json, os, sys
p=os.path.expanduser("~/.kaggle/kaggle.json")
d=json.load(open(p,encoding="utf-8"))
u, k = d.get("username",""), d.get("key","")
if not u or not k: sys.exit("kaggle.json present but missing username/key")
print(f'export KAGGLE_USERNAME="{u}"')
print(f'export KAGGLE_KEY="{k}"')
PY
    )"
  fi
fi

# Kaggle CLI will also read ~/.kaggle/kaggle.json directly; env vars are optional

# --- Paths ---
DATA_DIR="${DATA_DIR:-${REPO_ROOT}/data}"
DATASET_SLUG="${DATASET_ID##*/}"
OUT="${DATA_DIR}/${OUT_FILENAME}"
ZIP="${DATA_DIR}/${DATASET_SLUG}.zip"
JSON="${DATA_DIR}/${DATASET_SLUG}.json"
mkdir -p "${DATA_DIR}"
export DATA_DIR

# --- Idempotency: exit if output already exists ---
if [[ -f "$OUT" ]]; then
  echo "Dataset already present: $OUT"
  exit 0
fi

# --- Download (skip if ZIP already present) ---
if [[ -f "$ZIP" ]]; then
  echo "ZIP already exists; skipping download: $ZIP"
else
  echo "Downloading ${DATASET_ID} -> ${ZIP}"
  kaggle datasets download -d "${DATASET_ID}" -p "${DATA_DIR}" -q
fi

# --- Unzip (overwrite JSON if present) ---
unzip -o "$ZIP" -d "${DATA_DIR}" >/dev/null

# --- Transform JSONL -> filtered CSV (cs.*; sample N) ---
JSON_PATH="$JSON" OUT_PATH="$OUT" SAMPLE_N="$SAMPLE_N" CATEGORY_PATTERN="$CATEGORY_PATTERN" "$PYTHON_BIN" - <<'PY'
import json, os, re, pandas as pd
jpath = os.environ["JSON_PATH"]
opath = os.environ["OUT_PATH"]
sample_n = int(os.environ.get("SAMPLE_N", "10000"))
pattern = re.compile(os.environ.get("CATEGORY_PATTERN", "(^|[\\s])cs\\."), flags=re.IGNORECASE)

# Stream JSONL -> DataFrame
with open(jpath, "r", encoding="utf-8") as fh:
    rows = (json.loads(line) for line in fh)
    df = pd.DataFrame(rows)

required = {"id","title","abstract","categories"}
missing = required - set(df.columns)
if missing:
    raise SystemExit(f"Source JSON missing columns: {sorted(missing)}")

cat = df["categories"].fillna("")
cs = df[cat.str.contains(pattern)]  # any token starting with 'cs.'
if len(cs) > sample_n:
    cs = cs.sample(sample_n, random_state=42)

out = cs[["id","title","abstract","categories"]].rename(columns={"id":"doc_id"})
out.to_csv(opath, index=False)
print(f"Wrote {len(out)} rows to {opath}")
PY

# --- Cleanup (leave output only) ---
rm -f "$ZIP" "$JSON"
