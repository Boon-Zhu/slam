#!/usr/bin/env bash
# 在单个隔离网络/IPC的Humble容器内执行；全部为合成数据，无硬件或系统校时。
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
export CAPTURE_BUILD_ROOT="${CAPTURE_BUILD_ROOT:-$project_dir/.local/capture-round-check}"
export CAPTURE_ROUND_ARTIFACT_ROOT="${CAPTURE_ROUND_ARTIFACT_ROOT:-$CAPTURE_BUILD_ROOT/e2e}"
export PYTHONDONTWRITEBYTECODE=1
export ROS_LOCALHOST_ONLY=1
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-86}"
mkdir -p "$CAPTURE_BUILD_ROOT"
capture_check_log="$CAPTURE_BUILD_ROOT/check-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
bash scripts/check-device-capture.sh 2>&1 | tee "$capture_check_log"
