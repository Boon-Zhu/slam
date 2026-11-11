cmake_minimum_required(VERSION 3.8)
project(dogzilla_capture_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/SerialChunk.msg"
  "msg/Feedback.msg"
  "msg/CaptureEvent.msg"
  "msg/CaptureStatus.msg"
  "msg/CaptureMetadata.msg"
  "srv/SubmitMotion.srv"
  "srv/Stop.srv"
)
ament_export_dependencies(rosidl_default_runtime)
install(FILES CMakeLists.txt DESTINATION share/${PROJECT_NAME})
ament_package()
