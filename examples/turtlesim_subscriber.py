from RobotRaconteur.Client import *
import time

c = RRN.ConnectService("rr+tcp://localhost:34572?service=ros2_bridge")

handle = c.subscribe("/turtle1/pose","turtlesim/Pose")
sub = c.get_subscribers(handle)

w = sub.subscriberwire.Connect()

while True:
    if not w.InValueValid:
        print("pose not received")
        time.sleep(1)
        continue
    pose = w.InValue
    print(f"pose: x: {pose.x}, y: {pose.y}, theta: {pose.theta}")
    time.sleep(0.2)