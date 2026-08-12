import os
import sys
import subprocess
import time
import signal

# Track child processes
processes = []

def signal_handler(sig, frame):
    print("\n[ROBOT APP] Shutting down application and child processes...")
    for p in reversed(processes):
        try:
            print(f"[ROBOT APP] Terminating process {p.pid}...")
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except:
                pass
    print("[ROBOT APP] Shutdown complete.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def wait_for_port(port, timeout=30):
    import socket
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            time.sleep(1)
    return False

def cleanup_zombies():
    """Kill all leftover ROS/Gazebo processes from previous runs."""
    print("[ROBOT APP] Cleaning up zombie processes from previous runs...")
    targets = [
        "gzserver", "gzclient", "ign gazebo", "ruby",  # Gazebo Ignition
        "move_group",                                     # MoveIt
        "rviz2",                                          # RViz
        "controller_manager",                             # ros2_control
        "robot_state_publisher",                          # RSP
        "parameter_bridge",                               # ros_gz_bridge
        "ros_gz_sim",                                     # spawn entity
        "uvicorn",                                        # FastAPI backend
    ]
    for t in targets:
        subprocess.run(
            ["pkill", "-9", "-f", t],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    # Clean up DDS shared memory locks that cause RTPS_TRANSPORT_SHM errors
    subprocess.run(
        "rm -f /dev/shm/fastrtps_* 2>/dev/null",
        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(2)  # Let the OS fully reclaim resources
    print("[ROBOT APP] Cleanup complete.")

def main():
    print("[ROBOT APP] Starting Robot Control Application...")
    
    workspace_dir = os.path.expanduser("~/cobot_ws")
    if not os.path.exists(workspace_dir):
        print(f"[ERROR] Workspace {workspace_dir} not found!")
        sys.exit(1)

    app_dir = os.path.join(workspace_dir, "robot_control_app")
    
    # 0. Kill any zombie processes from previous runs
    cleanup_zombies()
    
    # 1. Start Gazebo + Controllers
    print("[ROBOT APP] Starting simulation (Gazebo + Controllers)...")
    env = os.environ.copy()
    env["ROS_LOCALHOST_ONLY"] = "1"
    # Do NOT set ROS_DOMAIN_ID — it breaks DDS shared-memory transport
    
    # We must source bashrc or setup.bash before running ros2 launch
    gazebo_cmd = f"source {workspace_dir}/install/setup.bash && ros2 launch arm_bringup gazebo.launch.py"
    gazebo_proc = subprocess.Popen(["bash", "-c", gazebo_cmd], env=env)
    processes.append(gazebo_proc)
    
    print("[ROBOT APP] Waiting for Gazebo and controllers to initialize (25s)...")
    time.sleep(25)

    # 2. Start MoveIt
    print("[ROBOT APP] Starting MoveIt 2 pipeline...")
    moveit_cmd = f"source {workspace_dir}/install/setup.bash && ros2 launch arm_bringup moveit_gazebo.launch.py"
    moveit_proc = subprocess.Popen(["bash", "-c", moveit_cmd], env=env)
    processes.append(moveit_proc)
    
    print("[ROBOT APP] Waiting for MoveIt to initialize (10s)...")
    time.sleep(10)

    # 3. Start Backend
    print("[ROBOT APP] Starting FastAPI backend...")
    backend_cmd = f"source {workspace_dir}/install/setup.bash && cd {app_dir} && python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
    backend_proc = subprocess.Popen(["bash", "-c", backend_cmd], env=env)
    processes.append(backend_proc)
    
    if not wait_for_port(8000):
        print("[ERROR] Backend failed to start!")
        signal_handler(None, None)

    # 4. Start Frontend
    print("[ROBOT APP] Starting Vite frontend...")
    frontend_cmd = f"cd {app_dir}/frontend && npm run dev"
    frontend_proc = subprocess.Popen(["bash", "-c", frontend_cmd], env=env)
    processes.append(frontend_proc)
    
    if not wait_for_port(5173):
        print("[ERROR] Frontend failed to start!")
        signal_handler(None, None)

    print("[ROBOT APP] Robot application READY")
    print("[ROBOT APP] Opening UI in browser...")
    
    # Open browser
    try:
        subprocess.Popen(["xdg-open", "http://localhost:5173"])
    except:
        pass

    # Wait indefinitely
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
