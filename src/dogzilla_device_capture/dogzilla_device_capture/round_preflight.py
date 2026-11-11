"""部署时显式选择的 chrony 校时及版本检查适配器，不在导入时操作系统。"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path


def check_chrony(text: str) -> dict[str, object]:
    fields = dict(line.split(":", 1) for line in text.splitlines() if ":" in line)
    values = {key.strip(): value.strip() for key, value in fields.items()}
    match = re.match(
        r"([0-9.eE+-]+) seconds (slow|fast)", values.get("System time", "")
    )
    if not match:
        raise ValueError("chronyc tracking 缺少可解析的 System time")
    stratum = int(values.get("Stratum", "0"))
    return {
        "synced": values.get("Leap status") == "Normal" and 0 < stratum < 16,
        "offset_s": float(match[1]) * (-1 if match[2] == "slow" else 1),
        "source": values.get("Reference ID", ""),
        "stratum": stratum,
        "measured_ns": time.time_ns(),
        "raw_tracking": text,
    }


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="显式运行才修改时钟；需部署在可控制宿主 chronyd 的权限环境"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("clock-sync")
    sub.add_parser("clock-check")
    environment = sub.add_parser("environment")
    environment.add_argument(
        "--image-evidence",
        type=Path,
        required=True,
        help="宿主 docker inspect 对正在运行容器的 .Image 输出文件，只读挂载",
    )
    environment.add_argument(
        "--package",
        action="append",
        required=True,
        help="需要已安装的 Debian/ROS package，可多次指定",
    )
    options = parser.parse_args(args)
    if options.command == "clock-sync":
        subprocess.run(["chronyc", "makestep"], check=True, timeout=15)
        subprocess.run(
            ["chronyc", "waitsync", "30", "0", "0", "1"], check=True, timeout=35
        )
    elif options.command == "clock-check":
        result = subprocess.run(
            ["chronyc", "tracking"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        print(json.dumps(check_chrony(result.stdout), ensure_ascii=False))
    else:
        versions = {}
        for package in options.package:
            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status} ${Version}", package],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            if not result.stdout.startswith("install ok installed "):
                raise RuntimeError(f"package 未安装: {package}")
            versions[package] = result.stdout.removeprefix("install ok installed ")
        print(
            json.dumps(
                {
                    "ok": True,
                    "image": options.image_evidence.read_text().strip(),
                    "versions": versions,
                }
            )
        )


if __name__ == "__main__":
    main()
