from RobotRaconteur.Client import *
import random
import math

c = RRN.ConnectService("rr+tcp://localhost:34572?service=ros2_bridge")

handle = c.client("/spawn","turtlesim/Spawn")
client = c.get_clients(handle)

req_type = RRN.GetStructureType("rosservice_turtlesim__Spawn.SpawnRequest",client)

req = req_type()

req.x = random.random() * 10.0
req.y = random.random() * 10.0
req.theta = random.random()*2.0*math.pi
# req.name = "turtle2" # Use implicit name

assert client.wait_for_service(10)
res = client.call(req)

print(res.name)