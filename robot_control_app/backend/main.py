import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import yaml
import os

from backend.ros.ros_node import RobotAppNode

app = FastAPI(title="Robot Control API")

# Mount ROS workspace install share directory so frontend can load meshes
workspace_share = os.path.expanduser("~/cobot_ws/install/arm_description/share/arm_description")
if os.path.exists(workspace_share):
    app.mount("/ros_packages/arm_description", StaticFiles(directory=workspace_share), name="ros_packages")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ros_node = None

background_tasks = set()

@app.on_event("startup")
async def startup_event():
    global ros_node
    
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "robot_config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    loop = asyncio.get_event_loop()
    ros_node = RobotAppNode(config, loop)
    
    # Start ROS node in a background task
    task1 = asyncio.create_task(ros_node.spin())
    background_tasks.add(task1)
    
    # Start broadcast loop
    task2 = asyncio.create_task(broadcast_loop())
    background_tasks.add(task2)

async def broadcast_loop():
    while True:
        if ros_node and len(ros_node.ws_clients) > 0:
            state = ros_node.get_status()
            if state["joints"]:
                msg = {"type": "robot_state", "joints": state["joints"]}
                await ros_node.broadcast(msg)
        await asyncio.sleep(0.1) # 10 Hz

@app.on_event("shutdown")
async def shutdown_event():
    if ros_node:
        ros_node.shutdown()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/robot/description")
def get_robot_description():
    import subprocess
    # Run xacro to generate URDF xml on the fly
    xacro_path = os.path.expanduser("~/cobot_ws/src/arm_description/urdf/arm_sim.urdf.xacro")
    if not os.path.exists(xacro_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Xacro file not found")
        
    try:
        # Use ROS 2 command to parse xacro
        result = subprocess.run(['xacro', xacro_path], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Xacro compilation failed: {e.stderr}")

@app.get("/api/system/readiness")
def get_readiness():
    if not ros_node:
        return {"backend": False}
    return ros_node.get_readiness()

@app.get("/api/robot/status")
def get_robot_status():
    if not ros_node:
        return {"status": "disconnected"}
    return ros_node.get_status()

from pydantic import BaseModel
from typing import Dict

class JointTarget(BaseModel):
    joints: Dict[str, float]

@app.post("/api/motion/joint")
async def execute_joint_motion(target: JointTarget):
    if not ros_node:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ROS Node not ready")
        
    success, message = await ros_node.moveit_manager.plan_and_execute_joint_target(target.joints)
    return {"success": success, "message": message}

@app.post("/api/motion/jog_joint")
def execute_jog_joint(target: JointTarget):
    if not ros_node:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ROS Node not ready")
        
    success = ros_node.publish_direct_joint_target(target.joints)
    return {"success": success, "message": "Jog sent"}

@app.post("/api/motion/estop")
def execute_estop():
    if not ros_node:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ROS Node not ready")
        
    success = ros_node.publish_estop()
    return {"success": success, "message": "ESTOP Triggered"}

class CartesianTarget(BaseModel):
    axis: str
    distance: float

@app.post("/api/motion/cartesian")
async def execute_cartesian_motion(target: CartesianTarget):
    if not ros_node:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ROS Node not ready")
        
    success, message = await ros_node.moveit_manager.plan_and_execute_cartesian_target(target.axis, target.distance)
    return {"success": success, "message": message}

import Xlib.display
from Xlib.ext import composite
import io
from PIL import Image
from fastapi.responses import Response

def _find_rviz_window(win):
    try:
        name = win.get_wm_name()
        wm_class = win.get_wm_class()
        
        if name and ('rviz' in name.lower() or 'moveit' in name.lower()):
            geom = win.get_geometry()
            if geom.width > 100 and geom.height > 100:
                return win
                
        if wm_class and ('rviz' in wm_class[0].lower() or 'moveit' in wm_class[0].lower()):
            geom = win.get_geometry()
            if geom.width > 100 and geom.height > 100:
                return win
                
        for child in win.query_tree().children:
            res = _find_rviz_window(child)
            if res:
                return res
    except Exception:
        pass
    return None

def _capture_rviz_composite() -> bytes:
    try:
        d = Xlib.display.Display()
        root = d.screen().root
        win = _find_rviz_window(root)
        
        if not win:
            d.close()
            return b''
            
        composite.redirect_window(win, composite.RedirectAutomatic)
        d.sync()
        geom = win.get_geometry()
        
        try:
            raw = win.get_image(0, 0, geom.width, geom.height, Xlib.X.ZPixmap, 0xffffffff)
            img_pil = Image.frombytes("RGB", (geom.width, geom.height), raw.data, "raw", "BGRX")
            img_pil.thumbnail((960, 720), Image.LANCZOS)
            buf = io.BytesIO()
            img_pil.save(buf, format='JPEG', quality=75)
            return buf.getvalue()
        finally:
            composite.unredirect_window(win, composite.RedirectAutomatic)
            d.sync()
            d.close()
    except Exception as e:
        print(f"[RVIZ] XComposite Capture error: {e}")
        return b''

@app.get("/api/rviz/snapshot")
def rviz_snapshot():
    frame = _capture_rviz_composite()
    if not frame:
        img = Image.new('RGB', (640, 480), color=(17, 24, 39))
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=50)
        return Response(content=buf.getvalue(), media_type="image/jpeg",
                       headers={"X-Rviz-Status": "capture-failed"})
    
    return Response(content=frame, media_type="image/jpeg",
                   headers={"X-Rviz-Status": "ok", "Cache-Control": "no-cache"})

@app.websocket("/ws/robot")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    if not ros_node:
        await websocket.close()
        return
        
    ros_node.add_client(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ros_node.remove_client(websocket)
