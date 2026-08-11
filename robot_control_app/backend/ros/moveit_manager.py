import rclpy
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, WorkspaceParameters, Constraints, JointConstraint, PositionConstraint, OrientationConstraint, BoundingVolume
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import PoseStamped, Point
import math
import asyncio

class MoveItManager:
    def __init__(self, node, config):
        self.node = node
        self.config = config
        self.group_name = config['robot']['planning_group']
        self.base_frame = config['robot']['base_frame']
        self.tool_frame = config['robot']['tool_frame']
        
        # MoveGroup Action Client
        action_name = config['ros'].get('move_group_action', '/move_action')
        self._action_client = ActionClient(self.node, MoveGroup, action_name)
        
    def _create_base_request(self):
        req = MotionPlanRequest()
        req.workspace_parameters.header.frame_id = self.base_frame
        req.workspace_parameters.min_corner.x = -1.0
        req.workspace_parameters.min_corner.y = -1.0
        req.workspace_parameters.min_corner.z = -1.0
        req.workspace_parameters.max_corner.x = 1.0
        req.workspace_parameters.max_corner.y = 1.0
        req.workspace_parameters.max_corner.z = 1.0
        
        req.group_name = self.group_name
        req.num_planning_attempts = 3
        req.allowed_planning_time = 2.0
        req.max_velocity_scaling_factor = 0.5
        req.max_acceleration_scaling_factor = 0.5
        return req

    async def plan_and_execute_joint_target(self, joint_target_dict):
        """Plans and executes a trajectory to a target joint configuration."""
        if not self._action_client.wait_for_server(timeout_sec=1.0):
            return False, "MoveIt action server not available"
            
        goal_msg = MoveGroup.Goal()
        goal_msg.request = self._create_base_request()
        
        constraints = Constraints()
        for joint_name, position in joint_target_dict.items():
            jc = JointConstraint()
            jc.joint_name = joint_name
            jc.position = float(position)
            jc.tolerance_above = 0.01
            jc.tolerance_below = 0.01
            jc.weight = 1.0
            constraints.joint_constraints.append(jc)
            
        goal_msg.request.goal_constraints.append(constraints)
        
        return await self._send_goal(goal_msg)

    async def _send_goal(self, goal_msg):
        self.node.get_logger().info("Sending MoveGroup goal...")
        send_goal_future = self._action_client.send_goal_async(goal_msg)
        
        # Wait for goal to be accepted
        while not send_goal_future.done():
            await asyncio.sleep(0.1)
            
        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            return False, "Goal was rejected by MoveIt"
            
        # Wait for result
        result_future = goal_handle.get_result_async()
        while not result_future.done():
            await asyncio.sleep(0.1)
            
        result = result_future.result().result
        error_code = result.error_code.val
        
        if error_code == 1: # SUCCESS
            return True, "Success"
        else:
            return False, f"MoveIt Error Code: {error_code}"

    async def plan_and_execute_cartesian_target(self, axis: str, distance: float):
        """Calculates new pose based on current TF and executes Cartesian motion."""
        try:
            # Get current pose from TF
            now = rclpy.time.Time()
            trans = self.node.tf_buffer.lookup_transform(
                self.base_frame,
                self.tool_frame,
                now,
                timeout=rclpy.duration.Duration(seconds=1.0)
            )
        except Exception as e:
            return False, f"Could not get current pose: {e}"

        goal_msg = MoveGroup.Goal()
        goal_msg.request = self._create_base_request()
        
        # Build position constraint based on current position + delta
        pc = PositionConstraint()
        pc.header.frame_id = self.base_frame
        pc.link_name = self.tool_frame
        
        target_pt = Point()
        target_pt.x = trans.transform.translation.x
        target_pt.y = trans.transform.translation.y
        target_pt.z = trans.transform.translation.z
        
        if axis == 'x': target_pt.x += distance
        elif axis == 'y': target_pt.y += distance
        elif axis == 'z': target_pt.z += distance
        # Note: Rotation requires quaternion math (scipy.spatial.transform or tf_transformations).
        # We will restrict to translation for this prototype to guarantee stability.
        if axis in ['rx', 'ry', 'rz']:
            return False, "Rotation jogging requires quaternion math (Phase 10+)"

        bv = BoundingVolume()
        sp = SolidPrimitive()
        sp.type = SolidPrimitive.SPHERE
        sp.dimensions = [0.01] # 1cm tolerance sphere
        bv.primitives.append(sp)
        
        pose = PoseStamped()
        pose.pose.position = target_pt
        bv.primitive_poses.append(pose.pose)
        
        pc.constraint_region = bv
        pc.weight = 1.0
        
        # We also need an orientation constraint to keep the current orientation
        oc = OrientationConstraint()
        oc.header.frame_id = self.base_frame
        oc.link_name = self.tool_frame
        oc.orientation = trans.transform.rotation
        oc.absolute_x_axis_tolerance = 0.05
        oc.absolute_y_axis_tolerance = 0.05
        oc.absolute_z_axis_tolerance = 0.05
        oc.weight = 1.0

        constraints = Constraints()
        constraints.position_constraints.append(pc)
        constraints.orientation_constraints.append(oc)
        
        goal_msg.request.goal_constraints.append(constraints)
        
        return await self._send_goal(goal_msg)
