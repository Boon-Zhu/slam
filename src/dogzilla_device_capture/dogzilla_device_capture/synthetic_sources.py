"""仅供无硬件测试的合成雷达与图像发布器，绝不代表设备能力。"""

from __future__ import annotations

import argparse
import math
import time

import rclpy  # type: ignore[import-untyped]
from rclpy.qos import qos_profile_sensor_data  # type: ignore[import-untyped]
from sensor_msgs.msg import Image, LaserScan  # type: ignore[import-untyped]


def positive_seconds(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("必须为有限正数")
    return value


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan-topic", default="/scan")
    parser.add_argument("--image-topic", default="/camera/image_raw")
    parser.add_argument("--hz", type=positive_seconds, default=5.0)
    parser.add_argument("--omit-scan", action="store_true")
    parser.add_argument("--omit-image", action="store_true")
    parser.add_argument("--exit-after-s", type=positive_seconds)
    args = parser.parse_args(argv)
    rclpy.init(args=[])
    node = rclpy.create_node("synthetic_capture_sources")
    scan_pub = node.create_publisher(
        LaserScan, args.scan_topic, qos_profile_sensor_data
    )
    image_pub = node.create_publisher(Image, args.image_topic, qos_profile_sensor_data)
    started = time.monotonic()
    sequence = 0

    def publish() -> None:
        nonlocal sequence
        sequence += 1
        stamp = node.get_clock().now().to_msg()
        if not args.omit_scan:
            scan = LaserScan()
            scan.header.stamp = stamp
            scan.header.frame_id = "synthetic_laser_not_hardware"
            scan.angle_min = -math.pi
            scan.angle_max = math.pi - math.pi / 4
            scan.angle_increment = math.pi / 4
            scan.scan_time = 1 / args.hz
            scan.range_min = 0.1
            scan.range_max = 10.0
            scan.ranges = [1.0 + index * 0.1 for index in range(8)]
            scan_pub.publish(scan)
        if not args.omit_image:
            image = Image()
            image.header.stamp = stamp
            image.header.frame_id = "synthetic_camera_not_hardware"
            image.height = image.width = 16
            image.encoding = "rgb8"
            image.step = 48
            image.data = bytes([sequence % 256, 0, 255] * 256)
            image_pub.publish(image)

    node.create_timer(1 / args.hz, publish)
    print(
        "SYNTHETIC SOFTWARE TEST: scan/image are generated, no hardware evidence",
        flush=True,
    )
    try:
        while rclpy.ok() and (
            args.exit_after_s is None or time.monotonic() - started < args.exit_after_s
        ):
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
