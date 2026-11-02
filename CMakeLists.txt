cmake_minimum_required(VERSION 3.16)
project(ros2_vg10_gripper)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/VacuumState.msg"
  "msg/CommandEvent.msg"
  DEPENDENCIES builtin_interfaces
)

# rosidl generates the Python package and its __init__.py. Install the driver
# modules alongside the generated messages.
ament_get_python_install_dir(PYTHON_INSTALL_DIR)
install(FILES
  ros2_vg10_gripper/vg10_driver.py
  ros2_vg10_gripper/vg10_node.py
  DESTINATION "${PYTHON_INSTALL_DIR}/${PROJECT_NAME}"
)
install(PROGRAMS ros2_vg10_gripper/vg10_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME vg10_node
)
install(FILES README.md DESTINATION share/${PROJECT_NAME})
install(DIRECTORY launch/ DESTINATION share/${PROJECT_NAME}/launch
  FILES_MATCHING PATTERN "*.launch.py"
)
install(DIRECTORY urdf/ DESTINATION share/${PROJECT_NAME}/urdf
  FILES_MATCHING PATTERN "*.xacro"
)
install(DIRECTORY meshes/ DESTINATION share/${PROJECT_NAME}/meshes
  FILES_MATCHING PATTERN "*.stl"
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
