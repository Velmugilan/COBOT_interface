#!/usr/bin/env python3
"""Pick and place a block using MoveIt via the move_group action.

Reads the target position from the red_block TF frame published by the
perception node, so the arm picks up the block wherever it actually is.
Falls back to a hardcoded position if no detection is available.

Targets grasp_frame (the fingertip midpoint) rather than tool0, so no
manual offset arithmetic is needed.

Uses Gazebo's DetachableJoint to hold the block during transit. Rigid-body
friction alone cannot reliably hold an object between rigid fingers, so the
block is welded to the gripper on close and released on open. Real grippers
have compliant pads that do this physically.
"""
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Empty
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints, PositionConstraint, OrientationConstraint,
    MotionPlanRequest, PlanningOptions, BoundingVolume,
)
from shape_msgs.msg import SolidPrimitive
from control_msgs.action import ParallelGripperCommand
from tf2_ros import Buffer, TransformListener

# --- task parameters -------------------------------------------------
BLOCK_SIZE = 0.05
BLOCK_FRAME = "red_block"
GRASP_XYZ = (1.20, 0.00, 0.535)     # fallback if no detection
PLACE_XYZ = (1.10, 0.15, 0.535)
HOVER = 0.15
GRIPPER_OPEN = 0.04
GRIPPER_CLOSED = 0.015


def down_quaternion():
    """Tool pointing straight down: 180 deg about X."""
    return (1.0, 0.0, 0.0, 0.0)


class PickPlace(Node):
    def __init__(self):
        super().__init__("pick_place")
        self.move = ActionClient(self, MoveGroup, "move_action")
        self.grip = ActionClient(self, ParallelGripperCommand,
                                 "/gripper_controller/gripper_cmd")
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.attach_pub = self.create_publisher(Empty, "/red_block/attach", 10)
        self.detach_pub = self.create_publisher(Empty, "/red_block/detach", 10)

        self.get_logger().info("waiting for action servers")
        self.move.wait_for_server()
        self.grip.wait_for_server()
        self.get_logger().info("connected")

        # The plugin starts attached; make sure we begin free.
        time.sleep(1.0)
        self.detach_pub.publish(Empty())
        time.sleep(0.5)

    # ---------------- perception ----------------
    def find_block(self, frame=BLOCK_FRAME, timeout=10.0):
        """Look up the detected block pose from TF.

        The detector reports the top face of the block, so subtract half the
        block height to get the grasp centre.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
            try:
                t = self.tf_buffer.lookup_transform(
                    "base_link", frame, rclpy.time.Time())
                x = t.transform.translation.x
                y = t.transform.translation.y
                z_top = t.transform.translation.z
                z = z_top - BLOCK_SIZE / 2.0
                self.get_logger().info(
                    f"detected {frame}: top z={z_top:.3f}, "
                    f"grasp centre ({x:.3f}, {y:.3f}, {z:.3f})")
                return (x, y, z)
            except Exception:
                continue
        self.get_logger().warn(
            f"no '{frame}' frame after {timeout:.0f}s - using fallback position")
        return None

    # ---------------- gripper ----------------
    def set_gripper(self, position):
        goal = ParallelGripperCommand.Goal()
        goal.command.name = ["finger_joint"]
        goal.command.position = [float(position)]
        fut = self.grip.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut)
        handle = fut.result()
        if not handle.accepted:
            self.get_logger().error("gripper goal rejected")
            return False
        res_fut = handle.get_result_async()
        rclpy.spin_until_future_complete(self, res_fut)
        r = res_fut.result().result
        self.get_logger().info(
            f"gripper -> {position:.3f} reached={r.reached_goal} stalled={r.stalled}")
        return True

    def attach_block(self):
        self.attach_pub.publish(Empty())
        self.get_logger().info("block attached to gripper")
        time.sleep(0.5)
        return True

    def detach_block(self):
        self.detach_pub.publish(Empty())
        self.get_logger().info("block released")
        time.sleep(0.5)
        return True

    # ---------------- arm ----------------
    def move_to(self, xyz, quat, label="", tol_pos=0.01, tol_ang=0.1):
        px, py, pz = xyz
        qx, qy, qz, qw = quat

        req = MotionPlanRequest()
        req.group_name = "manipulator"
        req.num_planning_attempts = 40
        req.allowed_planning_time = 30.0
        req.max_velocity_scaling_factor = 0.3
        req.max_acceleration_scaling_factor = 0.3

        pc = PositionConstraint()
        pc.header.frame_id = "base_link"
        pc.link_name = "grasp_frame"
        pc.weight = 1.0
        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [tol_pos]
        bv = BoundingVolume()
        bv.primitives.append(sphere)
        target = PoseStamped().pose
        target.position.x, target.position.y, target.position.z = px, py, pz
        target.orientation.w = 1.0
        bv.primitive_poses.append(target)
        pc.constraint_region = bv

        oc = OrientationConstraint()
        oc.header.frame_id = "base_link"
        oc.link_name = "grasp_frame"
        oc.orientation.x, oc.orientation.y = qx, qy
        oc.orientation.z, oc.orientation.w = qz, qw
        oc.absolute_x_axis_tolerance = tol_ang
        oc.absolute_y_axis_tolerance = tol_ang
        oc.absolute_z_axis_tolerance = 3.15
        oc.weight = 1.0

        c = Constraints()
        c.position_constraints.append(pc)
        c.orientation_constraints.append(oc)
        req.goal_constraints.append(c)

        goal = MoveGroup.Goal()
        goal.request = req
        goal.planning_options = PlanningOptions()
        goal.planning_options.plan_only = False

        self.get_logger().info(
            f"{label}: moving grasp_frame to ({px:.3f}, {py:.3f}, {pz:.3f})")
        fut = self.move.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut)
        handle = fut.result()
        if not handle.accepted:
            self.get_logger().error(f"{label}: goal rejected")
            return False
        res_fut = handle.get_result_async()
        rclpy.spin_until_future_complete(self, res_fut)
        code = res_fut.result().result.error_code.val
        ok = (code == 1)
        self.get_logger().info(f"{label}: {'OK' if ok else f'FAILED code={code}'}")
        return ok

    # ---------------- sequence ----------------
    def run(self):
        q = down_quaternion()

        detected = self.find_block()
        if detected:
            gx, gy, gz = detected
        else:
            gx, gy, gz = GRASP_XYZ
        px, py, pz = PLACE_XYZ

        steps = [
            ("open gripper",  lambda: self.set_gripper(GRIPPER_OPEN)),
            ("pre-grasp",     lambda: self.move_to((gx, gy, gz + HOVER), q, "pre-grasp")),
            ("descend",       lambda: self.move_to((gx, gy, gz), q, "descend")),
            ("close gripper", lambda: self.set_gripper(GRIPPER_CLOSED)),
            ("attach",        lambda: self.attach_block()),
            ("lift",          lambda: self.move_to((gx, gy, gz + HOVER), q, "lift")),
            ("transit",       lambda: self.move_to((px, py, pz + HOVER), q, "transit")),
            ("place",         lambda: self.move_to((px, py, pz), q, "place")),
            ("detach",        lambda: self.detach_block()),
            ("release",       lambda: self.set_gripper(GRIPPER_OPEN)),
            ("retreat",       lambda: self.move_to((px, py, pz + HOVER), q, "retreat")),
        ]

        for name, fn in steps:
            self.get_logger().info(f"--- {name} ---")
            if not fn():
                self.get_logger().error(f"aborting at '{name}'")
                return False
            time.sleep(0.5)

        self.get_logger().info("=== pick and place complete ===")
        return True


def main():
    rclpy.init()
    node = PickPlace()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()