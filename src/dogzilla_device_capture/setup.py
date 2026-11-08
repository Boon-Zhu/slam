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
        ("share/" + PACKAGE + "/launch", glob("launch/*.launch.py")),
        ("share/" + PACKAGE + "/config", glob("config/*.yaml")),
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
        ]
    },
)
