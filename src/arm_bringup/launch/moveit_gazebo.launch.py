import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder("cobot", package_name="arm_moveit_config")
        .robot_description(
            file_path=os.path.join(
                get_package_share_directory("arm_description"),
                "urdf", "arm_sim.urdf.xacro"),
            mappings={"controller_config": os.path.join(
                get_package_share_directory("arm_bringup"),
                "config", "sim_controllers.yaml")},
        )
        .to_moveit_configs()
    )

    move_group = Node(
        package="moveit_ros_move_group", executable="move_group",
        output="screen",
        parameters=[moveit_config.to_dict(), {"use_sim_time": True}],
    )

    rviz = Node(
        package="rviz2", executable="rviz2", output="screen",
        arguments=["-d", os.path.join(
            get_package_share_directory("arm_moveit_config"),
            "config", "moveit.rviz")],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
            {"use_sim_time": True},
        ],
    )

    return LaunchDescription([move_group, rviz])
