# OnRobot VG10

ROS 2 Jazzy driver for the VG10 through the OnRobot URCap's XML-RPC server.
Requires the URCap to be installed and running on the UR control box.

`/vg10/grip` and `/vg10/release` are Trigger services that command both A/B
channels. `/vg10/state` publishes measured vacuum A/B using
[VacuumState](msg/VacuumState.msg).
`/vg10/command_events` publishes each command's timestamps and acceptance result,
including RPC failures, using [CommandEvent](msg/CommandEvent.msg).
