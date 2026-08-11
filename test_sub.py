import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

class MinimalSubscriber(Node):
    def __init__(self):
        super().__init__('minimal_subscriber')
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.listener_callback,
            10)
        self.subscription  # prevent unused variable warning
        self.got_msg = False

    def listener_callback(self, msg):
        self.get_logger().info('I heard: "%s"' % msg.name)
        self.got_msg = True

def main(args=None):
    rclpy.init(args=args)
    minimal_subscriber = MinimalSubscriber()
    
    # Spin until we get a message
    while rclpy.ok() and not minimal_subscriber.got_msg:
        rclpy.spin_once(minimal_subscriber, timeout_sec=0.5)

    minimal_subscriber.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
