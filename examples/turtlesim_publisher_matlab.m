c = RobotRaconteur.ConnectService('rr+tcp://localhost:34572?service=ros2_bridge');
handle_ = c.publish('/turtle1/cmd_vel', 'geometry_msgs/Twist');
pub = c.get_publishers(handle_);

pause(1);

cmd_vel = struct;
cmd_vel.linear = struct;
cmd_vel.linear.x = rand() - 0.5;
cmd_vel.linear.y = rand() - 0.5;
cmd_vel.linear.z = 0.0;
cmd_vel.angular = struct;
cmd_vel.angular.x = 0.0;
cmd_vel.angular.y = 0.0;
cmd_vel.angular.z = rand() - 0.5;

pub.publish(cmd_vel)

RobotRaconteur.DisconnectService(c)