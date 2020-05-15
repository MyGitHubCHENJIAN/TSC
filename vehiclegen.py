import numpy as np

class VehicleGen():
    def __init__(self,netdata,conn,mode,scale,max_steps):
        self.netdata = netdata
        self.conn = conn
        self.vehicles_created = 0
        self.max_steps = max_steps
        # for generating vehicles
        self.origins = self.netdata['origin']
        self.destinaitons = self.netdata['destination']
        self.mode = mode
        self.scale = scale
        self.max_steps = max_steps
        self.add_origin_routes()
        # self.t = 0
        # self.v_schedule = self.gen_dynamic_demand()
        self.reset()
        
    
    def reset(self):
        self.t = 0
        self.v_schedule = self.gen_dynamic_demand()
        self.gen = self.gen_dynamic
    
    def run(self):
        self.gen()
        self.t += 1
        
    
    def add_origin_routes(self):
        for origin in self.origins:
            self.conn.route.add(origin, [origin] )
    
    def gen_dynamic(self):
        try:
            new_veh_edges = next(self.v_schedule)
            self.gen_vehicle(new_veh_edges)
        except StopIteration:
            print('no vehicles left')

    def gen_dynamic_demand(self):
        t = np.linspace(1*np.pi,2*np.pi,self.max_steps)
        sine = np.sin(t)+1.55

        v_schedule = []

        second = 1.0
        for t in range(int(self.max_steps)):
            n_veh = 0.0
            while second > 0.0:
                headway = np.random.exponential(sine[t],size=1)
                second -= headway
                if second > 0.0:
                    n_veh += 1
            second += 1.0
            v_schedule.append(int(n_veh))
        
        v_schedule = np.array(v_schedule)
        if self.mode == 'test':
            random_shift = 0
        else:
            random_shift = np.random.randint(0,self.max_steps)
        v_schedule = np.concatenate((v_schedule[random_shift:],v_schedule[:random_shift]))

        v_schedule[-60:] = 0

        v_schedule = [np.random.choice(self.origins, size=int(self.scale*n_veh), replace=True) if n_veh>0 else [] for n_veh in v_schedule]

        return v_schedule.__iter__()
    
    def gen_single(self):
        # generate a car if there is no car running in all the roads
        if self.conn.vehicle.getIDCount() == 0:
            ###if no vehicles in sim, spawn 1 on random link
            veh_spawn_edge = np.random.choice(self.origins)
            self.gen_vehicle( [veh_spawn_edge] )

    def gen_vehicle(self, vehilce_edges):
        for e in vehilce_edges:
            vid = e+str(self.vehicles_created)
            self.conn.vehicle.addFull(vid, e, departLane="best")
            self.set_vehilce_route(vid)
            self.vehicles_created += 1
        pass

    def set_vehilce_route(self,veh):
        current_edge = self.conn.vehicle.getRoute(veh)[0]
        route = [current_edge]
        while current_edge not in self.destinaitons:
            next_edge = np.random.choice(self.netdata['edge'][current_edge]['outgoing'])
            route.append(next_edge)
            current_edge = next_edge
        self.conn.vehicle.setRoute(veh, route)
