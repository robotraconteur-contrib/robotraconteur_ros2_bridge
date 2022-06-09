from RobotRaconteur.Client import *
import time
import random

c = RRN.ConnectService("rr+tcp://localhost:34572?service=ros2_bridge")

handle = c.publish("/turtle1/cmd_vel","geometry_msgs/Twist")
pub = c.get_publishers(handle)

twist_type = RRN.GetStructureType("rosmsg_geometry_msgs__Twist.Twist",pub)
vector3_type = RRN.GetStructureType("rosmsg_geometry_msgs__Vector3.Vector3",pub)

while True:
    linear = vector3_type()
    linear.x = random.random() - 0.5
    angular = vector3_type()
    angular.z = random.random() - 0.5
    cmd = twist_type()
    cmd.linear = linear
    cmd.angular = angular
    pub.publish(cmd)
    time.sleep(1)