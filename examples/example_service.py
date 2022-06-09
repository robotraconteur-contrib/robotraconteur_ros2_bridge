from RobotRaconteur.Client import *
import random
import math

c = RRN.ConnectService("rr+tcp://localhost:34572?service=ros2_bridge")

handle = c.register_service("/rr_spawn","turtlesim/Spawn")
service = c.get_services(handle)

res_type = RRN.GetStructureType("rosservice_turtlesim__Spawn.SpawnResponse",service)

def rr_service(req):
    print (f"Received spawn request: x: {req.x}, y: {req.y}, theta: {req.theta}, name: {req.name}")

    res = res_type()
    if len(req.name) > 0:
        res.name = req.name
    else:
        res.name = "rr_turtle"
    return res

service.servicefunction.Function = rr_service

input ("Press enter to quit")