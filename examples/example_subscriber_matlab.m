c = RobotRaconteur.ConnectService('rr+tcp://localhost:34572?service=ros2_bridge');
handle_ = c.subscribe('/turtle1/pose', 'turtlesim/Pose');
sub = c.get_subscribers(handle_);

pause(1);

%Use PeekInValue() for simplicity, can also connect wire
pose = sub.subscriberwire.PeekInValue();
disp(pose)
RobotRaconteur.DisconnectService(c)
