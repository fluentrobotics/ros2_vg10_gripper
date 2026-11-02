# ROS times when the service callback started and the XML-RPC call finished.
builtin_interfaces/Time requested_at
builtin_interfaces/Time completed_at

# Command issued through the service: "grip" or "release".
string command

# Whether the URCap accepted the command. Vacuum feedback indicates the grasp state.
bool accepted
string message
