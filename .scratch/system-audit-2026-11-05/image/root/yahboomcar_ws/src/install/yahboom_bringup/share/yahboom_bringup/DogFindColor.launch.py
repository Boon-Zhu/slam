from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():

    voice_xgo_ctrl_run_node = Node(
        package='voice_xgo_ctrl_run',
        node_executable='voice_xgo_ctrl_mutl_goal_identify',
        output='screen'
    )

    xgo_image_publisher_c_node = Node(
        package='xgo_image_publisher_c',
        node_executable='xgo_image_publish_c',
        output='screen'
    )

    xgo_color_status_redis_node = Node(
        package='xgo_color_status_redis',
        node_executable='xgo_color_status_redis',
        output='screen'
    )
    
    return LaunchDescription(
        [
            voice_xgo_ctrl_run_node,
            xgo_image_publisher_c_node,
            xgo_color_status_redis_node,
        ]
    )
