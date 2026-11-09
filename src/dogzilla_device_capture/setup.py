from glob import glob

from setuptools import find_packages, setup

PACKAGE = "dogzilla_device_capture"

setup(
    name=PACKAGE,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + PACKAGE]),
        ("share/" + PACKAGE, ["package.xml"]),
        (
            "share/" + PACKAGE + "/docs",
            [
                "../../docs/development/device-capture-round.md",
                "../../docs/development/device-capture-entry.md",
            ],
        ),
        ("share/" + PACKAGE + "/launch", glob("launch/*.launch.py")),
        ("share/" + PACKAGE + "/config", glob("config/*.yaml") + glob("config/*.json")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="DOGZILLA integration team",
    maintainer_email="maintainers@example.invalid",
    description="Single-owner control and raw feedback entry for attended capture.",
    license="Proprietary",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "capture_node = dogzilla_device_capture.node:main",
            "capturectl = dogzilla_device_capture.cli:main",
            "capture-round = dogzilla_device_capture.round_session:main",
            "capture-round-archive = dogzilla_device_capture.archive:main",
        ]
    },
)
