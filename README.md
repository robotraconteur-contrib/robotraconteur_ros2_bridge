<p align="center"><img src="https://robotraconteurpublicfiles.s3.amazonaws.com/RRheader2.jpg"></p>

# Robot Raconteur ROS 2 Bridge

The Robot Raconteur ROS 2 Bridge provides a Robot Raconteur service that can access arbitrary topics and services in ROS 2. The bridge dynamically generates equivalent Robot Raconteur types based on ROS 2 types. This bridge provides most of the benefits of Robot Raconteur to existing ROS 2 systems.

## Installation

The Robot Raconteur ROS 2 Bridge is a Python script. It requires ROS 2 (tested with ROS 2 Humble), and Robot Raconteur. Follow instructions at https://docs.ros.org/en/humble/Installation.html to install ROS 2 Humble. Other versions should work, but have not been tested.

**All ROS message and service types must have Python interfaces available.**

Robot Raconteur binaries have not been synced. Use the PPA to install:

```
sudo add-apt-repository ppa:robotraconteur/ppa
sudo apt-get update
sudo apt install python3-robotraconteur
```

MATLAB users can install the Robot Raconteur Add-In: https://www.mathworks.com/matlabcentral/fileexchange/80509-robot-raconteur-matlab

## Invocation

Before running any commands, source ROS 2 setup:

```
source /opt/ros/humble/setup.bash
```

To run the script:

```
python3 robotraconteur_ros2_bridge.py
```

The default URL for the service is `rr+tcp://localhost:34572?service=ros2_bridge` . Replace `localhost` with the IP address of the host computer if using over the network.

## Examples

The `examples` directory contains example clients in Python and Matlab. These examples use the ROS `turtlesim` package. Install using:

```
sudo apt install ros-humble-turtlesim
```

Run the turtlesim:

```
ros2 run turtlesim turtlesim_node
```

## Usage

The bridge provides the following functions:

* **subscribe**: Subscribe to a ROS 2 topic and receive the incoming messages using a `wire` or `pipe` member
* **publish**: Publish to a ROS 2 topic using a function member
* **client**: ROS 2 service client
* **service**: ROS 2 service

For all cases, first connect to the service:

```python
from RobotRaconteur.Client import *
c = RRN.ConnectService("rr+tcp://localhost:34572?service=ros2_bridge")
```

Replace `localhost` with the IP address of the server computer if using a network. Robot Raconteur Discovery and Subscriptions can also be used to automatically determine the URL.

### Subscribe

Subscriptions use the "subscribe" function, followed by the "subscriptions" objref to access the subscription. The "subscribe" function has the following signature:

```
function int32 subscribe(string topic, string msgtype)
```

`msgtype` is the ROS 2 message type and must be specified. The returned object from the objref has a wire and pipe that can be used to read the data. See `examples/turtlesim_subscriber.py` and `examples/turtlesim_subscriber_matlab.m` for examples on subscribers.

### Publisher

Publishers use the "publish" function, followed by the "publishers" objref to access subscriptions. The "publish" function has the following signature:

```
function int32 publish(string topic, string msgtype)
```

`msgtype` is the ROS 2 message type and must be specified. The returned object from the objref has a `publish` function that can be used to publish messages. See `examples/turtlesim_publisher.py` and `examples/turtlesim_publisher_matlab.m` for examples on publishers.

### Service Client

Service clients use the "client" function, followed by the "clients" objref to access subscriptions. The "client" function has the following signature:

```
function int32 client(string service, string srvtype)
```

`srvtype` is the ROS 2 service type and must be specified. The returned object from the objref has a `call` function that can be used to call the service. See `examples/turtlesim_service_client.py` and `examples/turtlesim_service_client_matlab.m` for examples on service clients.

### Services

Services use the "register_service" function, followed by the "services" objref to access subscriptions. The "services" function has the following signature:

```
function int32 register_service(string service, string srvtype)
```

`srvtype` is the ROS 2 service type and must be specified. The returned object from the objref has a `servicefunction` callback that will be called from ROS. This callback must have a function handle set by the client, and the client must remain connected for the subscription to be called. See `examples/example_service.py` and `examples/example_service_matlab.m` for examples on service clients.

## robdef pre-generation

The bridge dynamically generates equivalent Robot Raconteur robdef definitions for ROS 2 message and service types. For pregenerated languages like C++, or for reference, it is sometimes necessary to generate these files explicitly. This can be done from the command line with the `msg` and `srv` arguments.

For example, generate robdef for a messge type:

```
python3 robotraconteur_ros2_bridge.py msg turtlesim/Pose
```

This will generate the file `rosmsg_turtlesim__Pose.robdef` with the contents:

```
service rosmsg_turtlesim__Pose

struct Pose
    field single x
    field single y
    field single theta
    field single linear_velocity
    field single angular_velocity
end
```

and `rostopic_turtlesim__Pose.robdef` with the contents:

```
service rostopic_turtlesim__Pose

import rosmsg_turtlesim__Pose

object subscriber
    pipe rosmsg_turtlesim__Pose.Pose subscriberpipe [readonly]
    wire rosmsg_turtlesim__Pose.Pose subscriberwire [readonly]
    function void unsubscribe()
end

object publisher
    function void publish(rosmsg_turtlesim__Pose.Pose m)
end
```

For services, the `srv` command is used. For example, generate robdef for a service type:

```
python3 robotraconteur_ros2_bridge.py srv turtlesim/Spawn
```

This will generate the file `rosservice_turtlesim__Spawn.robdef` with the contents:

```
service rosservice_turtlesim__Spawn

struct SpawnRequest
    field single x
    field single y
    field single theta
    field string name
end

struct SpawnResponse
    field string name
end

object rosclient
    function SpawnResponse call(SpawnRequest request)
    function bool wait_for_service(double timeout)
end

object rosservice
    callback SpawnResponse servicefunction(SpawnRequest request)
end
```

These services are accessed using the main bridge types. They are found in `robotraconteur_ros2_bridge.py` which has the contents:

```
service experimental.ros2_bridge

object ROS2Bridge
    function int32 subscribe(string topic, string msgtype)
    objref varobject{int32} subscribers
    function int32 publish(string topic, string msgtype)
    objref varobject{int32} publishers
    function int32 client(string service, string srvtype)
    objref varobject{int32} clients
    function int32 register_service(string service, string srvtype)
    objref varobject{int32} services
end
```
