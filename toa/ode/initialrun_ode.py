import numpy as np
import openmdao.api as om
from dymos.models.atmosphere import USatm1976Comp

from toa.data import Airplane
from toa.models.aero.aerodynamics import AerodynamicsGroup
from toa.models.alpha_comp import AlphaComp
from toa.models.eom.initialrun_eom import InitialRunEOM
from toa.models.propulsion.propulsion_group import PropulsionGroup
from toa.models.true_airspeed_comp import TrueAirspeedCompGroundRoll


class InitialRunODE(om.Group):
    def initialize(self):
        self.options.declare('num_nodes', types=int,
                             desc='Number of nodes to be evaluated in the RHS')
        self.options.declare('airplane', types=Airplane,
                             desc='Class containing all airplane data')
        self.options.declare('condition', default='AEO',
                             desc='Takeoff condition (AEO/OEI)')

    def setup(self):
        nn = self.options['num_nodes']
        airplane = self.options['airplane']
        condition = self.options['condition']

        assumptions = self.add_subsystem(name='assumptions', subsys=om.IndepVarComp())
        assumptions.add_output('grav', val=9.80665, units='m/s**2',
                               desc='Gravity acceleration')
        assumptions.add_output('theta', val=0.0, units='rad', desc='Pitch angle')

        self.add_subsystem(name='atmos', subsys=USatm1976Comp(num_nodes=1),
                           promotes_inputs=['h'])

        self.add_subsystem(name='tas_comp',
                           subsys=TrueAirspeedCompGroundRoll(num_nodes=nn),
                           promotes_inputs=['V', 'Vw'])

        self.add_subsystem(name='aero', subsys=AerodynamicsGroup(num_nodes=nn,
                                                                 airplane=airplane),
                           promotes_inputs=['de', 'mass'])

        self.connect('assumptions.grav', 'aero.grav')
        self.connect('assumptions.theta', 'aero.alpha')
        self.connect('atmos.rho', 'aero.rho')
        self.connect('tas_comp.tas', 'aero.tas')

        self.add_subsystem(name='prop',
                           subsys=PropulsionGroup(num_nodes=nn, airplane=airplane,
                                                  condition=condition))

        self.connect('atmos.sos', 'prop.sos')
        self.connect('atmos.pres', 'prop.p_amb')
        self.connect('tas_comp.tas', 'prop.tas')

        self.add_subsystem(name='initial_run_eom',
                           subsys=InitialRunEOM(num_nodes=nn, airplane=airplane),
                           promotes_inputs=['mass'])

        self.connect('prop.thrust', 'initial_run_eom.thrust')
        self.connect('aero.L', 'initial_run_eom.lift')
        self.connect('aero.D', 'initial_run_eom.drag')
        self.connect('aero.M', 'initial_run_eom.moment')
        self.connect('tas_comp.tas', 'initial_run_eom.V')
        self.connect('assumptions.grav', 'initial_run_eom.grav')
        self.connect('assumptions.theta', 'initial_run_eom.alpha')