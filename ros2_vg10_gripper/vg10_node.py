#! /usr/bin/env python3
"""ROS 2 services and vacuum feedback for the OnRobot VG10 through the URCap."""

from functools import partial
from http.client import HTTPException
from typing import Literal
from xml.parsers.expat import ExpatError
from xmlrpc.client import Error

import rclpy
from rcl_interfaces.msg import FloatingPointRange, ParameterDescriptor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from ros2_vg10_gripper.vg10_driver import VG10
from std_srvs.srv import Trigger

from ros2_vg10_gripper.msg import CommandEvent, VacuumState

RPC_ERRORS = (OSError, HTTPException, Error, ExpatError)


class VG10Node(Node):
    """ROS 2 node for VG10 commands and measured vacuum feedback.

    ``~/command_events`` reports completed service calls. ``~/state`` publishes
    measured vacuum after successful reads.
    Polling and commands use separate connections and callback groups.
    """

    def __init__(self, node_name: str = "vg10") -> None:
        """Create the services, publishers, and polling timer.

        ``robot_ip`` selects the UR control box and ``vg_id`` its OnRobot device
        index. ``rpc_timeout`` bounds socket operations in seconds.
        ``poll_rate`` requests state reads per second; actual rate depends on
        RPC latency. ``vacuum_percent`` is the target for grip commands on both
        channels.
        """
        super().__init__(node_name)
        robot_ip = self.declare_parameter(
            "robot_ip", "192.168.100.102", ParameterDescriptor(read_only=True)
        ).value
        vg_id = self.declare_parameter(
            "vg_id", 0, ParameterDescriptor(read_only=True)
        ).value
        timeout = self.declare_parameter(
            "rpc_timeout", 2.0, ParameterDescriptor(read_only=True)
        ).value
        poll_rate = self.declare_parameter(
            "poll_rate", 10.0, ParameterDescriptor(read_only=True)
        ).value
        self.vacuum_percent = self.declare_parameter(
            "vacuum_percent",
            60.0,
            ParameterDescriptor(
                read_only=True,
                floating_point_range=[
                    FloatingPointRange(from_value=0.0, to_value=80.0)
                ],
            ),
        ).value
        if timeout <= 0 or poll_rate <= 0:
            raise ValueError("rpc_timeout and poll_rate must be positive")

        self._command_driver = VG10(robot_ip, vg_id, timeout=timeout)
        self._state_driver = VG10(robot_ip, vg_id, timeout=timeout)
        self.state_publisher = self.create_publisher(VacuumState, "~/state", 10)
        self.command_event_publisher = self.create_publisher(
            CommandEvent, "~/command_events", 10
        )
        self._poll_group = MutuallyExclusiveCallbackGroup()
        self._timer = self.create_timer(
            1.0 / poll_rate, self.publish_state, callback_group=self._poll_group
        )
        self.grip_service = self.create_service(
            Trigger, "~/grip", partial(self.command_callback, action="grip")
        )
        self.release_service = self.create_service(
            Trigger, "~/release", partial(self.command_callback, action="release")
        )

    def command_callback(
        self,
        request: Trigger.Request,
        response: Trigger.Response,
        *,
        action: Literal["grip", "release"],
    ) -> Trigger.Response:
        requested_at = self.get_clock().now().to_msg()
        try:
            if action == "grip":
                result = self._command_driver.vg10_grip(2, self.vacuum_percent)
            else:
                result = self._command_driver.vg10_release(True, True)
        except RPC_ERRORS as error:
            response.success = False
            response.message = f"{action} RPC failed: {error}"
            self.get_logger().error(response.message)
        else:
            response.success = result == 0
            response.message = (
                "" if response.success else f"{action} command returned {result}"
            )
        self.command_event_publisher.publish(
            CommandEvent(
                requested_at=requested_at,
                completed_at=self.get_clock().now().to_msg(),
                command=action,
                accepted=response.success,
                message=response.message,
            )
        )
        return response

    def publish_state(self) -> None:
        """Read both vacuum levels and publish them with the response receipt time.

        Read failures and responses without both vacuum levels are logged and
        publication is skipped.
        """
        try:
            values = self._state_driver.vg10_get_vacuum()
        except RPC_ERRORS as error:
            self.get_logger().error(
                f"Vacuum read failed: {error}", throttle_duration_sec=5.0
            )
            return
        try:
            a_vacuum = values["a_vacuum"]
            b_vacuum = values["b_vacuum"]
        except (KeyError, TypeError):
            self.get_logger().error(
                f"Unexpected vacuum response: {values!r}", throttle_duration_sec=5.0
            )
            return
        self.state_publisher.publish(
            VacuumState(
                stamp=self.get_clock().now().to_msg(),
                a_vacuum=a_vacuum,
                b_vacuum=b_vacuum,
            )
        )

    def destroy_node(self) -> bool:
        """Close the XML-RPC connections and destroy the node.

        Stop the executor's callbacks before calling this method.
        """
        self._command_driver.close()
        self._state_driver.close()
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = VG10Node()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
