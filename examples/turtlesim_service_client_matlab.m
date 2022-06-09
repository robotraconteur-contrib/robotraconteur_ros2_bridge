c = RobotRaconteur.ConnectService('rr+tcp://localhost:34572?service=ros2_bridge');
handle_ = c.client('/spawn', 'turtlesim/Spawn');
client = c.get_clients(handle_);

pause(1);

req = struct;
req.x = single(rand() * 10.0);
req.y = single(rand() * 10.0);
req.theta = single(rand() * 2.0 * pi);
req.name = 'turtle5';

res = client.call(req);

disp(res);

RobotRaconteur.DisconnectService(c)