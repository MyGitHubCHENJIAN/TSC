import os, sys, copy

import numpy as np

from collections import deque

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
    from sumolib import checkBinary
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import traci
from trafficmetrics import TrafficMetrics
###
# each agent control a traffic signal light.
###
class TLController(object):
    def __init__(self,conn,tl_id,netdata,mode,red_t,yellow_t):
        self.conn = conn
        self.tl_id = tl_id
        self.netdata = netdata
        self.mode = mode
        self.red_t = red_t
        self.yellow_t = yellow_t
        self.green_phases = self.get_tl_green_phases()
        self.phase_lanes = self.phase_lanes(self.green_phases)
        self.all_red = len((self.green_phases[0]))*'r'
        # current phase
        self.phase = self.all_red
        self.phase_time = 0
        # subscribe the laneposition,speed and lane_id of vehicles which are closer than 150 to the tl.
        self.conn.junction.subscribeContext(self.tl_id, traci.constants.CMD_GET_VEHICLE_VARIABLE, 300, 
                                        [traci.constants.VAR_LANEPOSITION, 
                                        traci.constants.VAR_POSITION,
                                        traci.constants.VAR_SPEED, 
                                        traci.constants.VAR_LANE_ID])

        self.incoming_lanes = set()
        for p in self.phase_lanes:
            for l in self.phase_lanes[p]:
                self.incoming_lanes.add(l)

        self.incoming_lanes = sorted(list(self.incoming_lanes))
        #lane capacity is the lane length divided by the average vehicle length+stopped headway
        self.lane_capacity = np.array([float(self.netdata['lane'][lane]['length'])/7.5 for lane in self.incoming_lanes])
        if mode == 'train':
            self.metric_args = ['delay','speed']
        if mode == 'test':
            self.metric_args = ['queue', 'delay']
        self.trafficmetrics = TrafficMetrics(self.tl_id, self.incoming_lanes, netdata, self.metric_args, mode)

        self.ep_rewards = []
        self.accumulate_delay = []

    def run(self):
        data = self.get_subscription_data()
        self.trafficmetrics.update(data)
        self.update(data)
        self.increment_controller()

    def get_intermediate_phases(self, phase, next_phase):
        if phase == next_phase or phase == self.all_red:
            return []
        else:
            # turn green light to yellow(yellow phase)
            yellow_phase = ''.join([ p if p == 'r' else 'y' for p in phase ])
            return [yellow_phase, self.all_red]
    
    def input_to_one_hot(self, phases):
        identity = np.identity(len(phases))                                 
        one_hots = { phases[i]:identity[i,:]  for i in range(len(phases)) }
        return one_hots
    
    def int_to_input(self, phases):
        return { p:phases[p] for p in range(len(phases)) }

    def empty_intersection(self):
        for lane in self.incoming_lanes:
            if len(self.data[lane]) > 0:
                return False
        return True

    def increment_controller(self):
        if self.phase_time == 0:
            ###get new phase and duration
            next_phase = self.next_phase()
            self.conn.trafficlight.setRedYellowGreenState( self.tl_id, next_phase )
            self.phase = next_phase
            self.phase_time = self.next_phase_duration()
        self.phase_time -= 1
    
    def get_tl_green_phases(self):
        logic = self.conn.trafficlight.getCompleteRedYellowGreenDefinition(self.tl_id)[0]
        #get only the green phases
        green_phases = [ p.state for p in logic.getPhases() 
                         if 'y' not in p.state 
                         and ('G' in p.state or 'g' in p.state) ]

        #sort to ensure parity between sims (for RL actions)
        return sorted(green_phases)
    
    def phase_lanes(self, actions):
        phase_lanes = {a:[] for a in actions}
        for a in actions:
            green_lanes = set()
            red_lanes = set()
            for s in range(len(a)):
                if a[s] == 'g' or a[s] == 'G':
                    green_lanes.add(self.netdata['inter'][self.tl_id]['tlsindex'][s])
                elif a[s] == 'r':
                    red_lanes.add(self.netdata['inter'][self.tl_id]['tlsindex'][s])

            ###some movements are on the same lane, removes duplicate lanes
            pure_green = [l for l in green_lanes if l not in red_lanes]
            if len(pure_green) == 0:
                phase_lanes[a] = list(set(green_lanes))
            else:
                phase_lanes[a] = list(set(pure_green))
        return phase_lanes
    
    def get_subscription_data(self):
        #use SUMO subscription to retrieve vehicle info in batches
        #around the traffic signal controller
        tl_data = self.conn.junction.getContextSubscriptionResults(self.tl_id)
        # print("-----------------------")

        lane_vehicles = {l:{} for l in self.incoming_lanes}
        if tl_data is not None:
            for v in tl_data:
                lane = tl_data[v][traci.constants.VAR_LANE_ID]
                if lane not in lane_vehicles:
                    lane_vehicles[lane] = {}
                lane_vehicles[lane][v] = tl_data[v]
        return lane_vehicles

    def next_phase(self):
        raise NotImplementedError("Subclasses should implement this!")
        
    def next_phase_duration(self):
        raise NotImplementedError("Subclasses should implement this!")
    
    def get_reward(self):
        #return negative delay as reward
        delay = int(self.trafficmetrics.get_metric('delay'))
        if delay == 0:
            r = 0
        else:
            r = -delay
        self.ep_rewards.append(r)
        return r
    
    def get_state(self):
        #the state is the normalized density of all incoming lanes 
        # print(self.get_normalized_queue())
        return np.concatenate([self.get_normalized_density(), self.get_normalized_queue()])
    
    def get_normalized_density(self):
        #number of vehicles in each incoming lane divided by the lane's capacity
        return np.array([len(self.data[lane]) for lane in self.incoming_lanes])/self.lane_capacity
    
    def get_speed_loss(self):
        self.trafficmetrics.get_metric('speed')

    def get_normalized_queue(self):
        lane_queues = []
        for lane in self.incoming_lanes:
            q = 0
            for v in self.data[lane]:
                if self.data[lane][v][traci.constants.VAR_SPEED] < 0.3:
                    q += 1
            lane_queues.append(q)
        return np.array(lane_queues)/self.lane_capacity