#!/usr/bin/env python3
"""Detect a coloured block and publish its 3D pose as a TF frame.

Pipeline: RGB -> HSV threshold -> largest contour -> centroid pixel
-> depth lookup -> camera intrinsics deprojection -> TF into base_link.
"""
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from message_filters import ApproximateTimeSynchronizer, Subscriber
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped, TransformStamped
from tf2_ros import Buffer, TransformListener, TransformBroadcaster
import tf2_geometry_msgs  # noqa: F401  (registers PoseStamped support)

# HSV ranges. Red wraps around hue 0, so it needs two bands.
COLOURS = {
    "red":  [((0, 120, 70), (10, 255, 255)), ((170, 120, 70), (180, 255, 255))],
    "blue": [((100, 120, 70), (130, 255, 255))],
}


class BlockDetector(Node):
    def __init__(self):
        super().__init__("block_detector")

        self.declare_parameter("colour", "red")
        self.declare_parameter("min_area_px", 300)
        self.declare_parameter("target_frame", "base_link")
        self.declare_parameter("publish_debug", True)

        self.colour = self.get_parameter("colour").value
        self.min_area = self.get_parameter("min_area_px").value
        self.target_frame = self.get_parameter("target_frame").value
        self.debug = self.get_parameter("publish_debug").value

        self.bridge = CvBridge()
        self.K = None

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tf_broadcaster = TransformBroadcaster(self)

        qos = QoSProfile(depth=5)
        qos.reliability = ReliabilityPolicy.BEST_EFFORT

        self.create_subscription(
            CameraInfo, "/wrist_camera/camera_info", self.on_info, qos)

        rgb = Subscriber(self, Image, "/wrist_camera/image", qos_profile=qos)
        depth = Subscriber(self, Image, "/wrist_camera/depth_image",
                           qos_profile=qos)
        sync = ApproximateTimeSynchronizer([rgb, depth], queue_size=10,
                                           slop=0.15)
        sync.registerCallback(self.on_frame)

        self.pose_pub = self.create_publisher(PoseStamped, "~/block_pose", 10)
        if self.debug:
            self.debug_pub = self.create_publisher(Image, "~/debug_image", 5)

        self.get_logger().info(f"looking for '{self.colour}' blocks")

    def on_info(self, msg):
        if self.K is None:
            self.K = np.array(msg.k).reshape(3, 3)
            self.get_logger().info(
                f"intrinsics: fx={self.K[0,0]:.1f} fy={self.K[1,1]:.1f} "
                f"cx={self.K[0,2]:.1f} cy={self.K[1,2]:.1f}")

    def on_frame(self, rgb_msg, depth_msg):
        if self.K is None:
            return

        rgb = self.bridge.imgmsg_to_cv2(rgb_msg, "bgr8")
        depth = self.bridge.imgmsg_to_cv2(depth_msg, "passthrough")
        hsv = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)

        mask = np.zeros(hsv.shape[:2], np.uint8)
        for lo, hi in COLOURS[self.colour]:
            mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))

        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        contours = [c for c in contours if cv2.contourArea(c) >= self.min_area]

        dbg = rgb.copy() if self.debug else None

        if not contours:
            if self.debug:
                self.debug_pub.publish(
                    self.bridge.cv2_to_imgmsg(dbg, "bgr8"))
            return

        c = max(contours, key=cv2.contourArea)
        M = cv2.moments(c)
        u = int(M["m10"] / M["m00"])
        v = int(M["m01"] / M["m00"])

        # Median depth over a small patch: single pixels are noisy.
        h, w = depth.shape[:2]
        y0, y1 = max(0, v - 3), min(h, v + 4)
        x0, x1 = max(0, u - 3), min(w, u + 4)
        patch = depth[y0:y1, x0:x1].astype(np.float32)
        patch = patch[np.isfinite(patch) & (patch > 0.05) & (patch < 5.0)]
        if patch.size == 0:
            self.get_logger().warn("no valid depth at centroid")
            return
        z = float(np.median(patch))

        fx, fy = self.K[0, 0], self.K[1, 1]
        cx, cy = self.K[0, 2], self.K[1, 2]
        x = (u - cx) * z / fx
        y = (v - cy) * z / fy

        pose = PoseStamped()
        pose.header.stamp = rclpy.time.Time().to_msg()
        pose.header.frame_id = rgb_msg.header.frame_id or "camera_optical_frame"
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = z
        pose.pose.orientation.w = 1.0

        try:
            out = self.tf_buffer.transform(
                pose, self.target_frame, timeout=rclpy.duration.Duration(seconds=0.3))
        except Exception as e:
            self.get_logger().warn(f"tf failed: {e}", throttle_duration_sec=2.0)
            return

        self.pose_pub.publish(out)

        t = TransformStamped()
        t.header.stamp = out.header.stamp
        t.header.frame_id = self.target_frame
        t.child_frame_id = f"{self.colour}_block"
        t.transform.translation.x = out.pose.position.x
        t.transform.translation.y = out.pose.position.y
        t.transform.translation.z = out.pose.position.z
        t.transform.rotation.w = 1.0
        self.tf_broadcaster.sendTransform(t)

        self.get_logger().info(
            f"{self.colour}: px=({u},{v}) d={z:.3f}m -> "
            f"{self.target_frame} "
            f"({out.pose.position.x:.3f}, {out.pose.position.y:.3f}, "
            f"{out.pose.position.z:.3f})",
            throttle_duration_sec=1.0)

        if self.debug:
            cv2.drawContours(dbg, [c], -1, (0, 255, 0), 2)
            cv2.circle(dbg, (u, v), 5, (255, 255, 255), -1)
            cv2.putText(dbg, f"{z:.3f}m", (u + 10, v),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            self.debug_pub.publish(self.bridge.cv2_to_imgmsg(dbg, "bgr8"))


def main():
    rclpy.init()
    node = BlockDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
