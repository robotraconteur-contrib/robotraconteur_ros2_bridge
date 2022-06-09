# Copyright 2022 Wason Technology, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import RobotRaconteur as RR
RRN = RR.RobotRaconteurNode.s
import threading
import threading
import random
import sys

import rclpy
from rclpy.node import Node

from pathlib import Path
import importlib


class MsgAdapter(object):
    def __init__(self, msgname, rrmsgname, rrtopicname, rr2ros, ros2rr, rosmsgtype):
        self.msgname = msgname
        self.rrmsgname = rrmsgname
        self.rrtopicname = rrtopicname
        self.rr2ros = rr2ros
        self.ros2rr = ros2rr
        self.rosmsgtype = rosmsgtype


class SrvAdapter(object):
    def __init__(self, rossrvtype, rrservicename, reqadapter, resadapter):
        self.rossrvtype = rossrvtype
        self.rrservicename = rrservicename
        self.reqadapter = reqadapter
        self.resadapter = resadapter


class rr2ros_class(object):
    def __init__(self, func, rostype, adapters):
        self.rostype = rostype
        self.func = func
        self.adapters = adapters

    def __call__(self, i, o=None):
        return self.func(i, self.rostype, self.adapters, o)


class ros2rr_class(object):
    def __init__(self, func, adapters):
        self.func = func
        self.adapters = adapters

    def __call__(self, i):
        return self.func(i, self.adapters)


def _get_slots(rostype):
    slots = []
    slot_types = []

    slots_and_types = rostype.get_fields_and_field_types()

    for k,v in slots_and_types.items():
        slots.append(k)
        slot_types.append(v)

    return slots, slot_types

class ROSTypeAdapterManager(object):

    def __init__(self):
        self.rosmsgs = dict()
        self.rossrvs = dict()
        self.lock = threading.RLock()

    def getMsgAdapter(self, msgname):
        with self.lock:
            if (msgname in self.rosmsgs):
                return self.rosmsgs[msgname]

            (packagename, messagename) = msgname.split('/')

            rostype = getattr(importlib.import_module(f"{packagename}.msg"),messagename)

            

            rrtype = RR.ServiceDefinition()
            rrtypename = "rosmsg_" + packagename + "__" + messagename
            rrtopicname = "rostopic_" + packagename + "__" + messagename
            # print rrtypename
            # print rrtype
            rrtype.Name = rrtypename

            slots, slot_types = _get_slots(rostype)

            rr2ros, ros2rr = self._generateAdapters(
                msgname, rrtype, messagename, slot_types, slots, rostype)

            a = MsgAdapter(msgname, rrtypename + "." + messagename,
                           rrtopicname, rr2ros, ros2rr, rostype)
            self.rosmsgs[msgname] = a

            # print rrtype.ToString()

            RR.RobotRaconteurNode.s.RegisterServiceType(
                rrtype.ToString())  # @UndefinedVariable

            topic = "service " + "rostopic_" + packagename + "__" + messagename + "\n\n"
            #topic+="import ROSBridge\n"
            topic += "import " + rrtypename + "\n\n"
            topic += "object subscriber\n"
            topic += "\tpipe " + rrtypename + "." + messagename + " subscriberpipe [readonly]\n"
            topic += "\twire " + rrtypename + "." + messagename + " subscriberwire [readonly]\n"
            topic += "\tfunction void unsubscribe()\n"
            topic += "end\n"
            topic += "\n"
            topic += "object publisher\n"
            topic += "\tfunction void publish(" + \
                rrtypename + "." + messagename + " m)\n"
            topic += "end\n"

            # print topic

            RR.RobotRaconteurNode.s.RegisterServiceType(
                topic) 

            return a

    def getSrvAdapter(self, srvname):
        with self.lock:
            if (srvname in self.rossrvs):
                return self.rossrvs[srvname]

            (packagename, servicename) = srvname.split('/')

            rostype = getattr(importlib.import_module(packagename + '.srv'),servicename)
            rosreqtype = getattr(rostype,"Request")
            rosrestype = getattr(rostype,"Response")

            rrtype = RR.ServiceDefinition()
            rrtypename = "rosservice_" + packagename + "__" + servicename
            rrtype.Name = rrtypename

            # Generate the request adapter
            rosreqtype_slots, rosreqtype_slot_types = _get_slots(rosreqtype)
            rr2ros_req, ros2rr_req = self._generateAdapters(
                srvname, rrtype, servicename+"Request", rosreqtype_slot_types, rosreqtype_slots, rosreqtype)
            reqadapter = MsgAdapter(
                srvname, rrtypename + "." + servicename+"Request", "", rr2ros_req, ros2rr_req, rosreqtype)

            # Generate the response adapter
            rosrestype_slots, rosrestype_slot_types = _get_slots(rosrestype)
            rr2ros_res, ros2rr_res = self._generateAdapters(
                srvname, rrtype, servicename+"Response", rosrestype_slot_types, rosrestype_slots, rosrestype)
            resadapter = MsgAdapter(
                srvname, rrtypename + "." + servicename+"Response", "", rr2ros_res, ros2rr_res, rosrestype)

            a = SrvAdapter(rostype, rrtypename, reqadapter, resadapter)

            self.rossrvs[srvname] = a

            clientstr = "object rosclient\n"
            clientstr += "function " + servicename + \
                "Response call(" + servicename + "Request request)\n"
            clientstr += "function bool wait_for_service(double timeout)\n"
            clientstr += "end\n"
            clientobj = RR.ServiceEntryDefinition(rrtype)
            clientobj.FromString(clientstr)

            servicestr = "object rosservice\n"
            servicestr += "callback " + servicename + \
                "Response servicefunction(" + \
                servicename + "Request request)\n"
            servicestr += "end\n"
            serviceobj = RR.ServiceEntryDefinition(rrtype)
            serviceobj.FromString(servicestr)

            rrtype.Objects.append(clientobj)
            rrtype.Objects.append(serviceobj)

            # print rrtype.ToString()

            RR.RobotRaconteurNode.s.RegisterServiceType(rrtype.ToString())

            return a

    def _generateAdapters(self, rostype, rrtype, messagename, slot_types, slots, rosmsgtype):

        def fixname(name):
            rr_reserved = ["object", "end", "option", "service", "object", "struct", "import", "implements", "field", "property", "function", "event", "objref", "pipe", "callback", "wire",
                           "memory", "void", "int8", "uint8", "int16", "uint16", "int32", "uint32", "int64", "uint64", "single", "double", "varvalue", "varobject", "exception", "using", "import", "as"]
            if (name in rr_reserved):
                return "ros" + name
            if (name.lower().startswith("rr") or name.lower().startswith("robotraconteur")):
                return "ros" + name
            return name

        rrslots = [fixname(s) for s in slots]

        __primtypes__ = ["int8", "uint8", "int16", "uint16",
                         "int32", "uint32", "int64", "uint64", "float", "double", "boolean"]

        rrtype_entry = RR.ServiceEntryDefinition(rrtype)
        rrtype_entry.Name = messagename
        rrtype_entry.EntryType = RR.DataTypes_structure_t

        rrtype.Structures.append(rrtype_entry)

        rr2ros_str = "def rr2ros(i, rostype, adapters, o=None):\n\tif o is None:\t\to=rostype()\n"
        ros2rr_str = "def ros2rr(i, adapters):\n\to=RR.RobotRaconteurNode.s.NewStructure('" + \
            rrtype.Name + "." + messagename + "')\n"

        adapters = dict()

        for i in range(len(slots)):
            slot_type = slot_types[i]
            isarray = False
            arrlength = 0
            arrfixed = False
            if ('[' in slot_type):
                isarray = True
                (slot_type, a) = slot_type.split('[')
                a = a.rstrip(']').strip()
                if (len(a) != 0):
                    arrfixed = True
                    arrlength = int(a)

            if (slot_type in __primtypes__):
                slot_type2 = slot_type
                if (slot_type == 'float'):
                    slot_type2 = 'single'
                if (slot_type == 'boolean'):
                    slot_type2 = 'bool'
                if (slot_type == 'char'):
                    slot_type2 = 'uint8'

                t = RR.TypeDefinition()
                t.Name = rrslots[i]
                t.Type = RR.TypeDefinition.DataTypeFromString(slot_type2)
                if isarray:
                    t.ArrayType = RR.DataTypes_ArrayTypes_array
                    t.ArrayVarLength = not arrfixed
                    if arrfixed:
                        t.ArrayLength.append(arrlength)
                        

                field = RR.PropertyDefinition(rrtype_entry)
                field.Name = rrslots[i]
                field.Type = t

                t._SetMember(field)

                rrtype_entry.Members.append(field)

                if (isarray and arrfixed):
                    rr2ros_str += "\tif (len(i." + rrslots[i] + ")!=" + str(
                        arrlength) + "): raise Exception('Invalid length')\n"
                    ros2rr_str += "\tif (len(i." + slots[i] + ")!=" + str(
                        arrlength) + "): raise Exception('Invalid length')\n"
                if (not ((slot_type == 'int8' or slot_type == 'uint8') and isarray)):
                    rr2ros_str += "\to." + slots[i] + "=i." + rrslots[i] + "\n"
                    ros2rr_str += "\to." + rrslots[i] + "=i." + slots[i] + "\n"
                else:
                    rr2ros_str += "\to." + slots[i] + "=i." + rrslots[i] + "\n"
                    ros2rr_str += "\to." + \
                        rrslots[i] + "=bytearray(i." + slots[i] + ")\n"

            elif (slot_type == 'string'):
                t = RR.TypeDefinition()
                t.Name = rrslots[i]
                t.Type = RR.DataTypes_string_t
                if isarray:         
                    t.ContainerType = RR.DataTypes_ContainerTypes_list

                field = RR.PropertyDefinition(rrtype_entry)
                field.Name = rrslots[i]
                field.Type = t

                t._SetMember(field)

                rrtype_entry.Members.append(field)

                if (isarray and arrfixed):
                    rr2ros_str += "\tif (len(i." + rrslots[i] + ")!=" + str(
                        arrlength) + "): raise Exception('Invalid length')\n"
                    ros2rr_str += "\tif (len(i." + slots[i] + ")!=" + str(
                        arrlength) + "): raise Exception('Invalid length')\n"
                if (not isarray):
                    rr2ros_str += "\to." + slots[i] + "=i." + rrslots[i] + "\n"
                    ros2rr_str += "\to." + rrslots[i] + "=i." + slots[i] + "\n"
                else:
                    rr2ros_str += "\to." + \
                        slots[i] + "=(i." + rrslots[i] + ")\n"
                    ros2rr_str += "\to." + \
                        rrslots[i] + "=(i." + slots[i] + ")\n"
            elif ('/' in slot_type):

                if (not slot_type in adapters):
                    adapters[slot_type] = self.getMsgAdapter(slot_type)

                (ipackage, imessage) = slot_type.split('/')

                rripackagename = "rosmsg_" + ipackage + "__" + imessage
                if (not rripackagename in rrtype.Imports):
                    rrtype.Imports.append(rripackagename)
                t = RR.TypeDefinition()
                t.Name = rrslots[i]
                t.Type = RR.DataTypes_namedtype_t
                t.TypeString = rripackagename + "." + imessage
                if isarray:
                    t.ContainerType = RR.DataTypes_ContainerTypes_list
                
                field = RR.PropertyDefinition(rrtype_entry)
                field.Name = rrslots[i]
                field.Type = t

                t._SetMember(field)

                rrtype_entry.Members.append(field)

                if (isarray and arrfixed):
                    rr2ros_str += "\tif (len(i." + rrslots[i] + ")!=" + str(
                        arrlength) + "): raise Exception('Invalid length')\n"
                    ros2rr_str += "\tif (len(i." + slots[i] + ")!=" + str(
                        arrlength) + "): raise Exception('Invalid length')\n"
                if (not isarray):
                    rr2ros_str += "\to." + \
                        slots[i] + "=adapters['" + slot_type + \
                        "'].rr2ros(i." + rrslots[i] + ")\n"
                    ros2rr_str += "\to." + \
                        rrslots[i] + "=adapters['" + slot_type + \
                        "'].ros2rr(i." + slots[i] + ")\n"
                else:
                    rr2ros_str += "\to." + \
                        slots[i] + "=[adapters['" + slot_type + \
                        "'].rr2ros(d) for d in (i." + rrslots[i] + ")]\n"
                    ros2rr_str += "\to." + \
                        rrslots[i] + "=[adapters['" + slot_type + \
                        "'].ros2rr(d) for d in (i." + slots[i] + ")]\n"

            else:
                if (hasattr(rostype, "_type")):
                    raise Exception(
                        "Cannot convert message type " + rostype._type)
                else:
                    raise Exception(
                        "Cannot convert message type " + str(rostype))

        rr2ros_str += "\treturn o"
        ros2rr_str += "\treturn o"

        # print(rr2ros_str)
        # print(ros2rr_str)

        exec(rr2ros_str)
        rr2ros1 = locals()["rr2ros"]
        exec(ros2rr_str)
        ros2rr1 = locals()["ros2rr"]

        return rr2ros_class(rr2ros1, rosmsgtype, adapters), ros2rr_class(ros2rr1, adapters)


class ROS2Bridge(object):

    def __init__(self, ros_node):
        self._subscribers = dict()
        self._publishers = dict()
        self._clients = dict()
        self._services = dict()
        self._ros_node = ros_node
        self.adapterManager = ROSTypeAdapterManager()

    def subscribe(self, topic, msgtype):
        # print topic
        # print msgtype
        adapter = self.adapterManager.getMsgAdapter(str(msgtype))
        s = subscriber(str(topic), adapter, self._ros_node)

        handle = random.randint(1, 2**30)
        if (handle in self._subscribers):
            handle = random.randint(1, 2**30)
        self._subscribers[handle] = s

        return handle

    def publish(self, topic, msgtype):
        # print topic
        # print msgtype
        adapter = self.adapterManager.getMsgAdapter(str(msgtype))
        s = publisher(str(topic), adapter, self._ros_node)

        handle = random.randint(1, 2**30)
        if (handle in self._subscribers):
            handle = random.randint(1, 2**30)
        self._publishers[handle] = s

        return handle

    def client(self, service, srvtype):
        adapter = self.adapterManager.getSrvAdapter(str(srvtype))
        c = client(str(service), adapter, self._ros_node)

        handle = random.randint(1, 2**30)
        if (handle in self._subscribers):
            handle = random.randint(1, 2**30)
        self._clients[handle] = c

        return handle

    def register_service(self, service_, srvtype):
        adapter = self.adapterManager.getSrvAdapter(str(srvtype))
        c = service(str(service_), adapter, self._ros_node)

        handle = random.randint(1, 2**30)
        if (handle in self._subscribers):
            handle = random.randint(1, 2**30)
        self._services[handle] = c

        return handle

    def get_subscribers(self, handle):
        s = self._subscribers[int(handle)]
        return s, s.rrtype

    def get_publishers(self, handle):
        s = self._publishers[int(handle)]
        return s, s.rrtype

    def get_clients(self, handle):
        s = self._clients[int(handle)]
        return s, s.rrtype

    def get_services(self, handle):
        s = self._services[int(handle)]
        return s, s.rrtype


class subscriber(object):
    def __init__(self, topic, msgadapter, ros_node):

        self.topic = topic
        self.msgadapter = msgadapter
        self.wires = dict()
        self.pipes = dict()
        self.rrtype = msgadapter.rrtopicname + ".subscriber"
        self._calllock = threading.RLock()
        self._ros_node = ros_node

        self._ros_node.create_subscription(
            msgadapter.rosmsgtype, topic, self.callback, 10)

    def callback(self, data):
        rrmsg = self.msgadapter.ros2rr(data)

        try:
            self.subscriberwire.OutValue = rrmsg
            self.subscriberpipe.SendPacket(rrmsg)
        except AttributeError: pass

    def unsubscribe(self):
        pass


class publisher(object):
    def __init__(self, topic, msgadapter, ros_node):

        self.topic = topic
        self.msgadapter = msgadapter
        self.rrtype = msgadapter.rrtopicname + ".publisher"
        self._calllock = threading.RLock()
        self._ros_node = ros_node

        self.pub = self._ros_node.create_publisher(
            msgadapter.rosmsgtype, topic, 10)

    def publish(self, rrmsg):
        with self._calllock:
            msg = self.msgadapter.rr2ros(rrmsg)
            self.pub.publish(msg)


class client(object):
    def __init__(self, service, srvadapter, ros_node):

        self.service = service
        self.srvadapter = srvadapter
        self.rrtype = srvadapter.rrservicename + ".rosclient"
        self._calllock = threading.RLock()
        self._ros_node = ros_node

        self.rosproxy = self._ros_node.create_client(
            srvadapter.rossrvtype, service)

    def call(self, rrreq):
        with self._calllock:
            req = self.srvadapter.reqadapter.rr2ros(rrreq)
            res = self.rosproxy.call(req)
            return self.srvadapter.resadapter.ros2rr(res)

    def wait_for_service(self, timeout):
        return self.rosproxy.wait_for_service(timeout)
            


class service(object):
    def __init__(self, service, srvadapter, ros_node):

        self.service = service
        self.srvadapter = srvadapter
        self.rrtype = srvadapter.rrservicename + ".rosservice"
        self._calllock = threading.RLock()
        self._ros_node = ros_node

        self.rosproxy = self._ros_node.create_service(
            srvadapter.rossrvtype, service, self.call)
        self.endpoint = RR.ServerEndpoint.GetCurrentEndpoint()

    def call(self, req, res):
        with self._calllock:
            rrreq = self.srvadapter.reqadapter.ros2rr(req)
            rrres = self.servicefunction.GetClientFunction(
                self.endpoint)(rrreq)
            return self.srvadapter.resadapter.rr2ros(rrres,res)

def main():

    script_dir = Path(__file__).parent

    RR.RobotRaconteurNode.s.RegisterServiceTypeFromFile(str(script_dir / "experimental.ros2_bridge"))

    if (len(sys.argv) > 1):
        if (sys.argv[1] == 'msg'):
            a = ROSTypeAdapterManager()
            a.getMsgAdapter(sys.argv[2])
            rrtype = RR.RobotRaconteurNode.s.GetRegisteredServiceTypes()
            for t in rrtype:
                if (t != 'RobotRaconteurServiceIndex'):
                    t1 = RR.RobotRaconteurNode.s.GetServiceType(t)
                    dat = t1.ToString()
                    f = open(t+".robdef", "w")
                    f.write(dat)
                    f.close()

            return
        if (sys.argv[1] == 'srv'):
            a = ROSTypeAdapterManager()
            a.getSrvAdapter(sys.argv[2])
            rrtype = RR.RobotRaconteurNode.s.GetRegisteredServiceTypes()
            for t in rrtype:
                if (t != 'RobotRaconteurServiceIndex'):
                    t1 = RR.RobotRaconteurNode.s.GetServiceType(t)
                    dat = t1.ToString()
                    f = open(t+".robdef", "w")
                    f.write(dat)
                    f.close()
            return

        print("Invalid command for robotraconteur_ros2_bridge")
        return

    rclpy.init(args=sys.argv)
    ros_node = Node("robotraconteur_ros2_bridge")
    o = ROS2Bridge(ros_node)

    with RR.ServerNodeSetup("ros2_bridge", 34572):

        RRN.RegisterService(
            "ros2_bridge", "experimental.ros2_bridge.ROS2Bridge", o)  # @UndefinedVariable

        print('Press ctrl-c to quit')

        rclpy.spin(ros_node)


if __name__ == '__main__':
    main()
