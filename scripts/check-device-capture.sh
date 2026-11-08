#!/usr/bin/env bash
# Run inside Ubuntu 22.04 / ROS 2 Humble; no physical devices are required.
set -eo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
capture_tools_dir="${CAPTURE_TOOLS_DIR:-/opt/python-tools/bin}"
capture_build_root="${CAPTURE_BUILD_ROOT:-$project_dir/.local/device-capture-check}"
source /opt/ros/humble/setup.bash
mkdir -p "$capture_build_root"
export ROS_LOCALHOST_ONLY=1
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-74}"
export PYTHONDONTWRITEBYTECODE=1
"$capture_tools_dir/ruff" check --isolated --target-version py310 \
  --select E4,E7,E9,F,I,UP src/dogzilla_device_capture
"$capture_tools_dir/ruff" format --check --isolated --target-version py310 src/dogzilla_device_capture
colcon --log-base "$capture_build_root/log" build --base-paths src \
  --build-base "$capture_build_root/build" --install-base "$capture_build_root/install" \
  --packages-select dogzilla_capture_interfaces dogzilla_device_capture
source "$capture_build_root/install/setup.bash"
"$capture_tools_dir/mypy" --python-version 3.10 --strict \
  src/dogzilla_device_capture/dogzilla_device_capture
"$capture_tools_dir/python" -m pytest src/dogzilla_device_capture/test -v
"$capture_tools_dir/python" -m colcon --log-base "$capture_build_root/test-log" test \
  --base-paths src --build-base "$capture_build_root/build" \
  --install-base "$capture_build_root/install" \
  --packages-select dogzilla_capture_interfaces dogzilla_device_capture \
  --return-code-on-test-failure
colcon --log-base "$capture_build_root/result-log" test-result \
  --test-result-base "$capture_build_root/build" --verbose
