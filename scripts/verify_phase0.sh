#!/usr/bin/env bash
# Environment sanity check for the cobot workspace.
# Sources ROS and the workspace install itself so it works from any shell.

WS_SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Source ROS if not already done (must happen before set -u)
if [ "${ROS_DISTRO:-}" != "humble" ]; then
  # shellcheck disable=SC1091
  source /opt/ros/humble/setup.bash
fi

# Source workspace install if built (colcon setup.bash uses unbound vars internally)
INSTALL_SETUP="$WS_SELF/install/setup.bash"
if [ -f "$INSTALL_SETUP" ]; then
  # shellcheck disable=SC1090
  source "$INSTALL_SETUP"
fi

# Enable strict mode only after all source calls are done
set -euo pipefail

PASS=0; FAIL=0

check() {
  local label="$1"; local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    echo "  [PASS] $label"
    ((PASS++)) || true
  else
    echo "  [FAIL] $label"
    ((FAIL++)) || true
  fi
}

echo "=== Phase 0 environment check ==="
echo ""

echo "--- ROS distro ---"
check "ROS_DISTRO=humble"          '[ "${ROS_DISTRO:-}" = "humble" ]'
check "ros2 CLI reachable"         'command -v ros2'

echo ""
echo "--- Gazebo ---"
check "ign CLI reachable"          'command -v ign'
check "Gazebo Fortress (v6)"       'ign gazebo --version 2>&1 | grep -q "version 6"'
check "ros_gz_sim installed"       'ros2 pkg prefix ros_gz_sim'
check "gz_ros2_control installed"  'ros2 pkg prefix gz_ros2_control'

echo ""
echo "--- Workspace packages ---"
for pkg in arm_description arm_moveit_config arm_bringup arm_perception arm_hardware arm_task arm_msgs; do
  check "$pkg built"               "ros2 pkg prefix $pkg"
done

echo ""
echo "--- Environment variables ---"
check "GZ_SIM_RESOURCE_PATH set"   '[ -n "${GZ_SIM_RESOURCE_PATH:-}" ]'
check "ROS_DOMAIN_ID set"          '[ -n "${ROS_DOMAIN_ID:-}" ]'

echo ""
echo "--- Python tooling venv ---"
check ".venv-tools exists"         '[ -d "'"$WS_SELF"'/.venv-tools" ]'
check "trimesh importable"         '"'"$WS_SELF"'/.venv-tools/bin/python" -c "import trimesh"'
check "scipy importable"           '"'"$WS_SELF"'/.venv-tools/bin/python" -c "import scipy"'

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "All $PASS checks passed. Environment is ready."
else
  echo "$FAIL check(s) FAILED, $PASS passed."
  exit 1
fi
