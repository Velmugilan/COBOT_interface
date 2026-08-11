#!/usr/bin/env bash
# Bootstrap the cobot workspace on a fresh machine.
# Assumes Ubuntu 22.04 + ROS 2 Humble already installed.
set -euo pipefail

WS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "workspace: $WS"

if [ "${ROS_DISTRO:-}" != "humble" ]; then
  echo "ERROR: source /opt/ros/humble/setup.bash first"; exit 1
fi

echo "--- system dependencies ---"
sudo apt update
sudo apt install -y \
  ros-humble-moveit ros-humble-ros2-control ros-humble-ros2-controllers \
  ros-humble-controller-manager ros-humble-joint-state-publisher-gui \
  ros-humble-xacro ros-humble-tf2-tools ros-humble-ros-gz \
  ros-humble-gz-ros2-control ros-humble-cv-bridge \
  liburdfdom-tools python3-colcon-common-extensions python3-vcstool git-lfs

echo "--- git lfs ---"
git lfs install
git lfs pull

echo "--- external repos ---"
if [ ! -d "$WS/src/ros2_control_demos" ]; then
  vcs import "$WS/src" < "$WS/cobot.repos"
fi

echo "--- python tooling venv ---"
if [ ! -d "$WS/.venv-tools" ]; then
  python3 -m venv "$WS/.venv-tools"
  "$WS/.venv-tools/bin/pip" install --quiet trimesh scipy numpy matplotlib
fi

echo "--- build ---"
cd "$WS"
colcon build --symlink-install
echo
echo "Done. Add to your ~/.bashrc:"
echo "  source $WS/install/setup.bash"
echo "  export GZ_SIM_RESOURCE_PATH=$WS/install/arm_description/share:\$GZ_SIM_RESOURCE_PATH"
echo "  export ROS_DOMAIN_ID=42"
