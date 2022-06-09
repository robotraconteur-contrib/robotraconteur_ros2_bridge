function example_service_matlab
    
    c = RobotRaconteur.ConnectService('rr+tcp://localhost:34572?service=ros2_bridge');
    handle_ = c.register_service('/rr_spawn', 'turtlesim/Spawn');
    service = c.get_services(handle_);
    
    service.servicefunction = @rr_service;
    
    while 1
        RobotRaconteur.ProcessRequests()
    end

    RobotRaconteur.DisconnectService(c)
    
    function res = rr_service(req)
        disp(req)
        res = struct;
        res.name = req.name;
    end
end