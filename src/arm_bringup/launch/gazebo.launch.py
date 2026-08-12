import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    desc_share = get_package_share_directory("arm_description")
    bringup_share = get_package_share_directory("arm_bringup")

    xacro_file = os.path.join(desc_share, "urdf", "arm_sim.urdf.xacro")
    ctrl_yaml = os.path.join(bringup_share, "config", "sim_controllers.yaml")

    robot_description = ParameterValue(
        Command([
            FindExecutable(name="xacro"), " ", xacro_file,
            " controller_config:=", ctrl_yaml,
        ]),
        value_type=str,
    )

    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")),
        launch_arguments={"gz_args": "-r -v 3 " + os.path.join(bringup_share, "worlds", "workcell.sdf")}.items(),
    )

    rsp = Node(
        package="robot_state_publisher", executable="robot_state_publisher",
        output="screen", parameters=[{"robot_description": robot_description,
                                      "use_sim_time": True}],
    )

    spawn = Node(
        package="ros_gz_sim", executable="create", output="screen",
        arguments=["-topic", "robot_description", "-name", "cobot", "-z", "0.0"],
    )

    bridge = Node(
        package="ros_gz_bridge", executable="parameter_bridge", output="screen",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/wrist_camera/image@sensor_msgs/msg/Image[gz.msgs.Image",
            "/wrist_camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image",
            "/wrist_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
            "/wrist_camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked",
            "/red_block/attach@std_msgs/msg/Empty]gz.msgs.Empty",
            "/red_block/detach@std_msgs/msg/Empty]gz.msgs.Empty",
        ],
    )

    # Humble fix: gz_ros2_control auto-loads controllers from the YAML a few
    # physics steps after spawn.  Spawning immediately via OnProcessExit hits
    # a race where the controller appears in list_controllers but its plugin
    # library isn't fully initialised yet, so configure_controller fails.
    # TimerAction delays give the plugin time to settle before we touch it.
    jsb = TimerAction(
        period=15.0,
        actions=[Node(
            package="controller_manager", executable="spawner",
            arguments=["joint_state_broadcaster",
                       "--controller-manager-timeout", "30"],
            output="screen",
        )],
    )
    arm = TimerAction(
        period=18.0,
        actions=[Node(
            package="controller_manager", executable="spawner",
            arguments=["manipulator_controller",
                       "--controller-manager-timeout", "30"],
            output="screen",
        )],
    )

    grip = TimerAction(
        period=21.0,
        actions=[Node(
            package="controller_manager", executable="spawner",
            arguments=["gripper_controller",
                       "--controller-manager-timeout", "30"],
            output="screen",
        )],
    )
    return LaunchDescription([gz, rsp, bridge, spawn, jsb, arm, grip])
