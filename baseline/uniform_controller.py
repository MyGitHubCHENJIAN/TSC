import sys
sys.path.append("..")
from tlcontroller import TLController
import random
from itertools import cycle

class UniformController(TLController):
    
    def __init__(self, conn, tsc_id, netdata, mode, red_t, yellow_t, uniform_t):
        super().__init__(conn, tsc_id, netdata, mode, red_t, yellow_t)
        self.uniform_t = uniform_t
        self.cycle = self.get_phase_cycle()
        
    
    def get_phase_cycle(self):
        phase_cycle = []
        greens = self.green_phases
        # 妙啊
        next_greens = self.green_phases[1:] + [self.green_phases[0]]
        for g, next_g in zip(greens, next_greens):
            phases = self.get_intermediate_phases(g, next_g)
            phase_cycle.append(g) #current green phase
            phase_cycle.extend(phases) # next corresponding yellow phase and a all-red pahse
        return cycle(phase_cycle)

    def next_phase(self):
        return next(self.cycle)
    
    def next_phase_duration(self):
        if self.phase in self.green_phases:
            return self.uniform_t
        elif 'y' in self.phase:
            return self.yellow_t
        else:
            return self.red_t
    
    def update(self, data):
        pass
    

        