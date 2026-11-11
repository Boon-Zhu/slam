"""Explicit startup; no device/service takeover and no automatic motion."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument("backend", default_value="vendor"),
            DeclareLaunchArgument("enable_motion", default_value="false"),
            DeclareLaunchArgument("port", default_value="/dev/ttyAMA0"),
            DeclareLaunchArgument("fresh_hardware_session", default_value="false"),
            DeclareLaunchArgument(
                "lock_path", default_value="/run/lock/dogzilla-ttyAMA0.lock"
            ),
            Node(
                package="dogzilla_device_capture",
                executable="capture_node",
                namespace="/capture/device",
                output="screen",
                parameters=[
                    {
                        "backend": LaunchConfiguration("backend"),
                        "enable_motion": ParameterValue(
                            LaunchConfiguration("enable_motion"), value_type=bool
                        ),
                        "port": LaunchConfiguration("port"),
                        "fresh_hardware_session": ParameterValue(
                            LaunchConfiguration("fresh_hardware_session"),
                            value_type=bool,
                        ),
                        "lock_path": LaunchConfiguration("lock_path"),
                        "use_sim_time": False,
                    }
                ],
            ),
        ]
    )
