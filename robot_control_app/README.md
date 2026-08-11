# COBOT HMI - Robot Control Application

A fully integrated, real-time Web Human-Machine Interface (HMI) for controlling and simulating a 6-DOF collaborative robotic arm using ROS 2 Humble, MoveIt 2, and Ignition Gazebo.

## 🌟 Features

* **Real-Time Synchronization**: Instantly mirrors joint states and Cartesian poses between the web interface, MoveIt 2, and the Gazebo 3D simulation.
* **Joint & Cartesian Jogging**: Control individual joints or jog the end-effector in Cartesian space (XYZ / RPY) directly from the browser.
* **Task Program Editor**: Record waypoints and build complex motion sequences (pick-and-place, trajectories) via a visual sequence editor.
* **Automated Bringup**: A single Python orchestrator (`start_app.py`) manages the entire lifecycle of the simulation, planning scene, backend, and frontend with robust zombie-process cleanup.
* **Modern Web Stack**: Built with React, Vite, and Tailwind CSS on the frontend, powered by a high-performance asynchronous FastAPI backend communicating with `rclpy`.

## 🛠️ Technology Stack

* **ROS 2**: Humble Hawksbill
* **Simulation**: Ignition Gazebo (Fortress)
* **Motion Planning**: MoveIt 2
* **Backend**: FastAPI (Python 3.10), WebSockets, `rclpy`
* **Frontend**: React 18, Vite, TypeScript, Three.js (for 3D context)

## 📦 Prerequisites

Ensure you have the following dependencies installed on an Ubuntu 22.04 system:

- ROS 2 Humble Desktop
- Ignition Gazebo Fortress
- MoveIt 2 for Humble
- Node.js (v18+) and npm
- Python 3.10+ with FastAPI, Uvicorn, and Websockets

```bash
sudo apt install ros-humble-desktop ros-humble-ign-ros2-control ros-humble-moveit
sudo apt install nodejs npm
pip install fastapi uvicorn websockets rclpy
```

## 🚀 Installation & Setup

1. **Build the ROS 2 Workspace:**
   ```bash
   cd ~/cobot_ws
   source /opt/ros/humble/setup.bash
   colcon build --symlink-install
   ```

2. **Install Frontend Dependencies:**
   ```bash
   cd ~/cobot_ws/robot_control_app/frontend
   npm install
   ```

## 🎮 Running the Application

The entire application stack is managed by a single orchestrator script that gracefully handles dependency timing, Gazebo node spawning, and MoveIt initialization.

```bash
cd ~/cobot_ws/robot_control_app
python3 start_app.py
```

**Startup Sequence:**
1. Kills any lingering zombie processes (`gzserver`, `move_group`, etc.) from previous sessions.
2. Launches Ignition Gazebo and loads the `workcell.sdf` environment.
3. Spawns the URDF model and automatically configures `joint_state_broadcaster` and `manipulator_controller`.
4. Initializes the MoveIt 2 pipeline (`move_group`).
5. Starts the FastAPI backend (port `8000`).
6. Starts the Vite frontend (port `5173`) and automatically opens your default web browser.

## 🏗️ Architecture Overview

- **Gazebo Physics & `ros2_control`**: The robotic arm is simulated using Ignition Gazebo. Hardware abstractions are handled by the `ign_ros2_control` plugin, ensuring the physics engine correctly interprets commands from the `joint_trajectory_controller`.
- **FastAPI Bridge**: The `backend/main.py` runs a multi-threaded ROS 2 Node alongside an ASGI web server. It bridges ROS 2 topics (`/joint_states`) and MoveIt services via WebSockets to the web clients.
- **State Machine**: Ensures `robot_state_publisher` and `controller_manager` are strictly synchronized with the simulation's `use_sim_time`, preventing TF drift or "failed to configure controller" race conditions.

## 🛑 Troubleshooting

- **"Error creating WebGL context" in Browser**: If running on a headless server/VM, the 3D viewer may fail to initialize. The UI will gracefully fallback and disable the 3D viewer while keeping all controls functional.
- **Gazebo is completely blank**: Ensure `sim_controllers.yaml` has `use_sim_time: true`. A missing sim time parameter can cause physics to collapse (NaN errors), forcing Gazebo to blank the screen.
- **"Controller already loaded" errors**: The `start_app.py` automatically runs a cleanup routine. If errors persist, manually run `pkill -9 -f "ign gazebo|move_group|uvicorn"`.
