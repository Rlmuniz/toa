import openmdao.api as om
import numpy as np
from dymos.models.atmosphere import USatm1976Comp

from toa.data import Airplane
from toa.models.aero.aerodynamics import AerodynamicsGroup
from toa.models.alpha_comp import AlphaComp
from toa.models.eom.rotation_eom import RotationEOM
from toa.models.main_landing_gear_pos import MainLandingGearPosComp
from toa.models.propulsion.propulsion_group import PropulsionGroup
from toa.models.true_airspeed_comp import TrueAirspeedCompGroundRoll


class RotationODE(om.Group):
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

        self.add_subsystem(name='atmos', subsys=USatm1976Comp(num_nodes=1),
                           promotes_inputs=[('h', 'elevation')])

        self.add_subsystem(name='tas_comp',
                           subsys=TrueAirspeedCompGroundRoll(num_nodes=nn),
                           promotes_inputs=['V', 'Vw'])

        self.add_subsystem(name='aero', subsys=AerodynamicsGroup(num_nodes=nn,
                                                                 airplane=airplane,
                                                                 AllWheelsOnGround=False),
                           promotes_inputs=['q', 'mass'])

        self.connect('assumptions.grav', 'aero.grav')
        self.connect('atmos.rho', 'aero.rho')
        self.connect('tas_comp.tas', 'aero.tas')

        self.add_subsystem(name='prop',
                           subsys=PropulsionGroup(num_nodes=nn, airplane=airplane,
                                                  condition=condition),
                           promotes_inputs=['elevation'])

        self.connect('atmos.sos', 'prop.sos')
        self.connect('atmos.pres', 'prop.p_amb')
        self.connect('tas_comp.tas', 'prop.tas')

        self.add_subsystem(name='rotation_eom',
                           subsys=RotationEOM(num_nodes=nn, airplane=airplane),
                           promotes_inputs=['mass', 'V', 'q'])

        self.connect('prop.thrust', 'rotation_eom.thrust')
        self.connect('aero.L', 'rotation_eom.lift')
        self.connect('aero.D', 'rotation_eom.drag')
        self.connect('aero.M', 'rotation_eom.moment')
        self.connect('assumptions.grav', 'rotation_eom.grav')

        self.add_subsystem(name='mlg_pos',
                           subsys=MainLandingGearPosComp(num_nodes=nn, airplane=airplane))

        self.set_input_defaults('elevation', val=0.0, units='m')
