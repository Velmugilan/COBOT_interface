import asyncio
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from rclpy.executors import MultiThreadedExecutor
from threading import Thread
import json
import cv2
from cv_bridge import CvBridge

class RobotAppNode(Node):
    def __init__(self, config, loop):
        if not rclpy.ok():
            rclpy.init()
            
        super().__init__('robot_control_app_backend')
        self.config = config
        self.ws_clients = []
        self.loop = loop
        
        self.joint_states = {}
        self.latest_camera_jpeg = b''
        self.cv_bridge = CvBridge()
        
        from backend.ros.moveit_manager import MoveItManager
        self.moveit_manager = MoveItManager(self, config)
        
        self.get_logger().info('Initializing Robot Control App Node')
        
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Publishers
        from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
        self.traj_pub = self.create_publisher(JointTrajectory, '/manipulator_controller/joint_trajectory', 10)
        
        # Subscriptions
        self.js_sub = self.create_subscription(
            JointState,
            self.config['ros']['joint_states_topic'],
            self.joint_state_callback,
            10
        )
        
        from sensor_msgs.msg import Image
        self.cam_sub = self.create_subscription(
            Image,
            '/wrist_camera/image',
            self.camera_callback,
            10
        )
        
        from std_msgs.msg import Empty
        self.attach_pub = self.create_publisher(Empty, '/red_block/attach', 10)
        self.detach_pub = self.create_publisher(Empty, '/red_block/detach', 10)

        self._is_running = True
        self._readiness = {
            "ros2": True,
            "gazebo": False,
            "robot_description": False,
            "controllers": False,
            "moveit": False,
            "joint_states": False,
            "tf": False,
            "backend": True
        }

    def joint_state_callback(self, msg):
        self._readiness['joint_states'] = True
        for idx, name in enumerate(msg.name):
            self.joint_states[name] = msg.position[idx]

    def camera_callback(self, msg):
        try:
            cv_image = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            _, buffer = cv2.imencode('.jpg', cv_image)
            self.latest_camera_jpeg = buffer.tobytes()
        except Exception as e:
            self.get_logger().error(f"Failed to process camera image: {e}")

    def get_camera_jpeg(self):
        return self.latest_camera_jpeg

    async def broadcast(self, message):
        for client in self.ws_clients:
            try:
                await client.send_text(json.dumps(message))
            except Exception as e:
                self.get_logger().error(f"WebSocket send error: {e}")

    def add_client(self, websocket):
        self.ws_clients.append(websocket)
        
    def remove_client(self, websocket):
        if websocket in self.ws_clients:
            self.ws_clients.remove(websocket)

    def get_readiness(self):
        # In a full implementation, we'd check action servers and tf buffer.
        # For this skeleton, we assume true if we've received joint states.
        self._readiness['controllers'] = self._readiness['joint_states']
        self._readiness['gazebo'] = self._readiness['joint_states']
        self._readiness['moveit'] = self._readiness['joint_states']
        self._readiness['robot_description'] = True
        self._readiness['tf'] = True
        return self._readiness

    def get_status(self):
        ready = all(self.get_readiness().values())
        return {
            "status": "READY" if ready else "INITIALIZING",
            "joints": self.joint_states
        }

    def publish_direct_joint_target(self, joint_target_dict):
        from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
        from builtin_interfaces.msg import Duration
        
        msg = JointTrajectory()
        msg.joint_names = list(joint_target_dict.keys())
        
        point = JointTrajectoryPoint()
        point.positions = [float(v) for v in joint_target_dict.values()]
        # Fast movement for jogging
        point.time_from_start = Duration(sec=0, nanosec=300_000_000) 
        
        msg.points.append(point)
        self.traj_pub.publish(msg)
        return True

    def publish_estop(self):
        from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
        from builtin_interfaces.msg import Duration
        
        msg = JointTrajectory()
        if self.joint_states:
            msg.joint_names = [k for k in self.joint_states.keys() if k.startswith('joint_')]
            
            point = JointTrajectoryPoint()
            point.positions = [float(self.joint_states[k]) for k in msg.joint_names]
            # Instruct the controller to hold current position immediately
            point.time_from_start = Duration(sec=0, nanosec=1000000) 
            msg.points.append(point)
            
        self.traj_pub.publish(msg)
        
        # Also try to cancel any active MoveIt goals
        self.moveit_manager.estopped = True
        
        if hasattr(self.moveit_manager, 'current_goal_handle') and self.moveit_manager.current_goal_handle:
            try:
                self.moveit_manager.current_goal_handle.cancel_goal_async()
            except Exception as e:
                self.get_logger().error(f"Failed to cancel MoveIt goal: {e}")
                
        return True

    async def spin(self):
        executor = MultiThreadedExecutor()
        executor.add_node(self)
        def spin_node():
            try:
                executor.spin()
            except Exception as e:
                self.get_logger().error(f"Executor crashed: {e}")
                print(f"EXECUTOR CRASHED: {e}")
        self.spin_thread = Thread(target=spin_node, daemon=True)
        self.spin_thread.start()
        # Do not join the thread, as it will block the asyncio event loop!
        self.get_logger().info("ROS 2 Executor spinning in background thread")
        try:
            while rclpy.ok() and self._is_running:
                await asyncio.sleep(0.1)
        finally:
            executor.shutdown()

    def shutdown(self):
        self._is_running = False
        if rclpy.ok():
            rclpy.shutdown()
