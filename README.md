# Cobot — 6-DOF Collaborative Arm

ROS 2 workspace for a 6-DOF collaborative robotic arm: description, kinematics,
motion planning, physics simulation, and vision-based object localisation.

Currently built against the open-source `r6bot` model as a stand-in until the
production CAD is available. All geometry, mass, and limit values are
placeholders that get replaced at that point — what carries over is the
structure and the process.

## Status

| Phase | Scope | State |
|---|---|---|
| 0 | Environment setup | Done |
| 1 | Robot description (URDF) | Done |
| 2 | Kinematics analysis | Done |
| 3 | MoveIt 2 configuration | Done |
| 4 | Gazebo simulation | Done |
| 5 | Perception | Done |
| 6 | Grasping | Not started |
| 7 | Hardware bring-up | Blocked on hardware |
| 8 | Jetson integration | Blocked on hardware |
| 9 | Productisation | Blocked |
| 10 | Go to market | Blocked |

## Requirements

- Ubuntu 22.04 LTS (ARM64 or x86_64)
- ROS 2 Humble
- Gazebo Fortress (v6) via `ros_gz`
- NVIDIA GPU recommended

Deployment target is a Jetson on **JetPack 6.x**, which matches the
Ubuntu 22.04 + Humble pairing. JetPack 7 boards run Ubuntu 24.04 + Jazzy
and would need a port.

## Setup

```bash
git clone <REPO_URL> ~/cobot_ws
cd ~/cobot_ws
source /opt/ros/humble/setup.bash
./setup.sh
```

Then add to `~/.bashrc`:

```bash
source /opt/ros/humble/setup.bash
source ~/cobot_ws/install/setup.bash
export GZ_SIM_RESOURCE_PATH=$HOME/cobot_ws/install/arm_description/share:$GZ_SIM_RESOURCE_PATH
export ROS_DOMAIN_ID=42
```

`GZ_SIM_RESOURCE_PATH` is not optional. Gazebo cannot resolve `package://`
mesh URIs without it, and the arm spawns invisible with no collision geometry.

## Running

### View the model

```bash
ros2 launch arm_description display.launch.py
```

RViz with joint sliders. Use this to sanity-check the URDF.

### Motion planning only

```bash
ros2 launch arm_moveit_config demo.launch.py
```

MoveIt with fake controllers. Set Goal State to `<random valid>`, click Plan,
then Execute.

### Physics simulation

```bash
ros2 launch arm_bringup gazebo.launch.py
```

Spawns the arm in the workcell world: table at z = 0.5 m, red and blue 5 cm
blocks on top, wrist-mounted RGB-D camera.

Command a joint trajectory directly:

```bash
ros2 topic pub --once /manipulator_controller/joint_trajectory \
  trajectory_msgs/msg/JointTrajectory \
  '{joint_names: ["joint_1","joint_2","joint_3","joint_4","joint_5","joint_6"],
    points: [{positions: [0.0,-0.6,1.2,0.0,1.2,0.0], time_from_start: {sec: 3}}]}'
```

### Full stack — plan in RViz, execute in Gazebo

```bash
# Terminal 1
ros2 launch arm_bringup gazebo.launch.py

# Terminal 2, once controllers report active
ros2 launch arm_bringup moveit_gazebo.launch.py
```

Check controllers came up:

```bash
ros2 control list_controllers
# expect joint_state_broadcaster and manipulator_controller, both active
```

### Perception

Move to the scan pose — camera aimed at the red block, 55 cm standoff,
0 degrees alignment error:

```bash
ros2 topic pub --once /manipulator_controller/joint_trajectory \
  trajectory_msgs/msg/JointTrajectory \
  '{joint_names: ["joint_1","joint_2","joint_3","joint_4","joint_5","joint_6"],
    points: [{positions: [2.1529,-0.7304,2.3128,2.4587,2.09,2.3569],
              time_from_start: {sec: 4}}]}'
```

Run the detector:

```bash
PYTHONNOUSERSITE=1 ros2 run arm_perception block_detector \
  --ros-args -p use_sim_time:=true
```

Both flags are required. See Known gotchas below.

Expected output:

```
red: px=(319,238) d=0.523m -> base_link (1.191, 0.004, 0.550)
```

Ground truth is (1.200, 0.000, 0.525). The 25 mm Z offset is correct
behaviour — the camera sees the top face of a 50 mm cube, not its centre.

Switch target colour:

```bash
PYTHONNOUSERSITE=1 ros2 run arm_perception block_detector \
  --ros-args -p colour:=blue -p use_sim_time:=true
```

Debug views:

```bash
ros2 run rqt_image_view rqt_image_view /wrist_camera/image
ros2 run rqt_image_view rqt_image_view /block_detector/debug_image
ros2 run tf2_ros tf2_echo base_link red_block
```

## Packages

| Package | Contents |
|---|---|
| `arm_description` | URDF/xacro, meshes, camera mount, joint limits |
| `arm_moveit_config` | SRDF, planners, kinematics, controller configs |
| `arm_bringup` | Launch files, worlds, simulation controller config |
| `arm_perception` | Block detector node |
| `arm_hardware` | ros2_control hardware interface (Phase 7) |
| `arm_task` | Task orchestration (Phase 6) |
| `arm_msgs` | Custom messages and actions |

### URDF files

Two top-level descriptions, deliberately:

- `arm.urdf.xacro` — root is `base_link`. Used by MoveIt. Declaring `world`
  here conflicts with MoveIt's virtual joint and silently breaks planning.
- `arm_sim.urdf.xacro` — declares `world` and a fixed joint to it, because
  Gazebo needs it to anchor the base. Also pulls in `arm_gazebo.xacro`
  (ros2_control plugin) and `camera.xacro` (wrist RGB-D).

## Scripts

Run with the tooling venv: `.venv-tools/bin/python scripts/<name>.py`

| Script | Purpose |
|---|---|
| `compute_inertia.py` | Derive URDF inertial blocks from mesh files |
| `reachability.py` | Sample joint space, map the reachable workspace |
| `check_wrist.py` | Test whether the last three axes intersect |
| `verify_phase0.sh` | Environment sanity check |

## Known gotchas

### MoveIt Setup Assistant produces incomplete configs

Every regeneration needs these hand-edits:

1. **`joint_limits.yaml`** — the wizard writes `has_acceleration_limits: false`
   because URDF has no acceleration field. Time parameterisation then fails
   with "No acceleration limit was defined for joint joint_1". Set `true` and
   a real `max_acceleration`.
2. **`moveit_controllers.yaml`** — needs `action_ns: follow_joint_trajectory`.
   Without it, planning succeeds and execution silently does nothing.
3. **Controller names** — `ros2_controllers.yaml` and `moveit_controllers.yaml`
   are written by two separate wizard pages and can disagree. They must match.
4. **Root link** — see the URDF section above.

Config files are read at startup. Rebuild **and** relaunch after any change.

### Python environment

`~/.local/lib/python3.10/site-packages` may contain a numpy version
incompatible with the ROS Humble `cv2` build. Any node importing `cv2`
may fail with `numpy.core.multiarray failed to import`.

Run perception nodes with `PYTHONNOUSERSITE=1`. Do not delete the user-site
numpy — other tooling on the dev machine depends on it. Never use
`pip install --user` for ROS dependencies.

### Sim time

Every node must run with `use_sim_time:=true` while Gazebo is active, or TF
lookups fail with "Lookup would require extrapolation into the future".

### Camera aiming

Don't guess joint angles for a camera view — solve for them. The scan pose
above came from numerically optimising three objectives at once: optical Z
axis aligned with the target, ~55 cm standoff, camera above the table.

### Camera frame rate

The RGB-D sensor is configured for 15 Hz but delivers ~4 Hz on this hardware.
Rendering 640x480 RGB plus depth is the bottleneck. Fine for detection from a
stationary pose.

## Model notes

Derived in Phases 1–2, all superseded when production CAD arrives:

- Max reach: **1.82 m** (industrial scale, not a desktop cobot)
- Total mass: **~31.6 kg** at an effective density of 400 kg/m³, chosen to
  model hollow shells rather than solid aluminium
- Wrist: **not spherical** — joint 4 and joint 6 axes are 246 mm apart

Inertials were computed from convex hulls of non-watertight meshes, since the
source meshes have holes and no CAD was available. With real CAD you skip this
entirely — SolidWorks reports exact mass properties per link.

### Design recommendation for the production arm

Specify a **spherical wrist**: last three joint axes intersecting at a point.

This enables closed-form inverse kinematics — roughly 100x faster than
numerical solvers, returns all 8 solutions so you can pick the one that avoids
joint limits, never fails to converge, and is deterministic (the same target
always yields the same joint angles, which matters for a product where
customers expect repeatability).

The mechanical cost is that motor and cable placement is constrained. Nearly
every industrial arm (UR, ABB, KUKA, Fanuc) accepts that trade. Worth raising
before the design freezes.

## Attribution

Practice geometry is `r6bot` from
[ros-controls/ros2_control_demos](https://github.com/ros-controls/ros2_control_demos)
(jazzy branch), Apache 2.0.
