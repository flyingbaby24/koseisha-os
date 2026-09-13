#!/usr/bin/env bash
# Measure the public-demo runtime on Linux, under a real memory ceiling.
#
#   ./deploy/verify_memory_linux.sh /mnt/d/ThoughtMap
#
# Every memory figure published for ThoughtMap so far was measured on Windows,
# where the CRT cannot return free heap to the OS. Two things therefore remain
# unverified, and both decide whether a 512 MB instance is enough:
#
#   * whether glibc's malloc_trim(0) reclaims the ~113 MB of free-but-retained
#     heap the corpus load leaves behind, and
#   * whether the process survives a hard 512 MB ceiling rather than merely
#     reporting a number below it on a machine with 32 GB to spare.
#
# This runs the harness twice — once unconstrained for the stage-by-stage
# numbers, once inside a 512 MB cgroup for the verdict. A process that is OOM
# killed in the second run has answered the question.
#
# Needs: python3.13, the artifacts (embedding CSV + .vectors.npz + encoder),
# and cgroup v2. Under WSL2 the Windows drives are already mounted at /mnt/*,
# so the artifacts on D: need no copying.

set -euo pipefail

ARTIFACT_ROOT="${1:-/mnt/d/ThoughtMap}"
LIMIT_MB="${LIMIT_MB:-512}"
WEB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../web" && pwd)"

export THOUGHTMAP_EMBEDDINGS_PATH="${ARTIFACT_ROOT}/master/thoughtmap_canonical_embeddings.csv"
export THOUGHTMAP_ENCODER_DIR="${ARTIFACT_ROOT}/encoder"
export THOUGHTMAP_ENCODER_PROVIDER=onnx
export THOUGHTMAP_ENCODER_TOKENIZER="${THOUGHTMAP_ENCODER_TOKENIZER:-sentencepiece}"

echo "web           : ${WEB_DIR}"
echo "artifacts     : ${ARTIFACT_ROOT}"
echo "limit         : ${LIMIT_MB} MB"
echo

for required in "$THOUGHTMAP_EMBEDDINGS_PATH" "$THOUGHTMAP_ENCODER_DIR/model.onnx"; do
  if [[ ! -e "$required" ]]; then
    echo "MISSING: $required" >&2
    echo "Pass the artifact root as the first argument." >&2
    exit 2
  fi
done

if [[ ! -e "$THOUGHTMAP_ENCODER_DIR/tokenizer.spm" ]]; then
  echo "Building tokenizer.spm (one-off, no torch needed) ..."
  (cd "$WEB_DIR" && python3 -m api.prepare_query_tokenizer \
      --encoder-dir "$THOUGHTMAP_ENCODER_DIR")
  echo
fi

echo "=== 1. stage-by-stage, unconstrained ==========================="
(cd "$WEB_DIR" && python3 -m api.measure_memory --label "linux unconstrained" \
    --json /tmp/thoughtmap-linux-stages.json)

echo
echo "=== 2. what malloc_trim reclaims ==============================="
(cd "$WEB_DIR" && python3 -m api.verify_heap_trim --limit-mb "$LIMIT_MB" \
    --json /tmp/thoughtmap-linux-trim.json)

echo
echo "=== 3. the same process under a hard ${LIMIT_MB} MB ceiling ============"
BYTES=$(( LIMIT_MB * 1024 * 1024 ))

if command -v systemd-run >/dev/null 2>&1 && [[ -d /sys/fs/cgroup ]]; then
  # MemorySwapMax=0 matters: with swap available the kernel pages out instead
  # of OOM killing, and the run would pass without proving anything.
  set +e
  systemd-run --user --scope --quiet \
      -p "MemoryMax=${BYTES}" -p "MemorySwapMax=0" \
      -- bash -c "cd '${WEB_DIR}' && python3 -m api.verify_heap_trim --limit-mb ${LIMIT_MB}"
  STATUS=$?
  set -e
  if [[ $STATUS -eq 137 ]]; then
    echo
    echo "RESULT: OOM KILLED at ${LIMIT_MB} MB. The runtime does not fit."
    exit 1
  fi
  echo
  echo "RESULT: survived a hard ${LIMIT_MB} MB ceiling (exit ${STATUS})."
  exit "$STATUS"
fi

echo "systemd-run is unavailable. Cap the shell manually:" >&2
cat >&2 <<EOF

  sudo mkdir -p /sys/fs/cgroup/thoughtmap
  echo ${BYTES} | sudo tee /sys/fs/cgroup/thoughtmap/memory.max
  echo 0        | sudo tee /sys/fs/cgroup/thoughtmap/memory.swap.max
  echo \$\$       | sudo tee /sys/fs/cgroup/thoughtmap/cgroup.procs
  cd ${WEB_DIR} && python3 -m api.verify_heap_trim --limit-mb ${LIMIT_MB}

EOF
exit 2
