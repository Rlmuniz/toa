import openmdao.api as om

from toa.data import Airplane
from toa.models.aero.drag_coef_comp import DragCoeffComp
from toa.models.aero.dynamic_pressure_comp import DynamicPressureComp
from toa.models.aero.lift_coef_comp import LiftCoeffAllWheelsOnGroundComp
from toa.models.aero.lift_coef_comp import LiftCoeffComp
from toa.models.aero.lift_drag_moment_comp import LiftDragMomentComp
from toa.models.aero.moment_coef_comp import MomentCoeffAllWheelsOnGroundComp
from toa.models.aero.moment_coef_comp import MomentCoeffComp


class AerodynamicsGroup(om.Group):
    """Computes the lift and drag forces on the aircraft."""

    def initialize(self):
        self.options.declare('num_nodes', types=int)
        self.options.declare('airplane', types=Airplane,
                             desc='Class containing all airplane data')
        self.options.declare('landing_gear', default=True,
                             desc='Accounts landing gear drag')
        self.options.declare('AllWheelsOnGround', default=True)

    def setup(self):
        nn = self.options['num_nodes']
        airplane = self.options['airplane']
        landing_gear = self.options['landing_gear']
        all_wheels_on_ground = self.options['AllWheelsOnGround']

        if all_wheels_on_ground:
            self.add_subsystem(name='cl_comp',
                               subsys=LiftCoeffAllWheelsOnGroundComp(num_nodes=nn,
                                                                     airplane=airplane),
                               promotes_inputs=['alpha', 'de'], promotes_outputs=['CL'])
            self.add_subsystem(name='cm_comp',
                               subsys=MomentCoeffAllWheelsOnGroundComp(num_nodes=nn,
                                                                       airplane=airplane),
                               promotes_inputs=['alpha', 'de'],
                               promotes_outputs=['Cm'])
        else:
            self.add_subsystem(name='cl_comp',
                               subsys=LiftCoeffComp(num_nodes=nn, airplane=airplane),
                               promotes_inputs=['alpha', 'de', 'tas', 'q'],
                               promotes_outputs=['CL'])
            self.add_subsystem(name='cm_comp',
                               subsys=MomentCoeffComp(num_nodes=nn, airplane=airplane),
                               promotes_inputs=['alpha', 'de', 'tas', 'q'],
                               promotes_outputs=['Cm'])
        self.add_subsystem(name='cd_comp',
                           subsys=DragCoeffComp(num_nodes=nn, airplane=airplane,
                                                landing_gear=landing_gear),
                           promotes_inputs=['flap_angle', 'CL', 'grav', 'mass'],
                           promotes_outputs=['CD'])

        self.add_subsystem(name='dyn_press',
                           subsys=DynamicPressureComp(num_nodes=nn),
                           promotes_inputs=['rho', 'tas'],
                           promotes_outputs=['qbar'])

        self.add_subsystem(name='lift_drag_moment_comp',
                           subsys=LiftDragMomentComp(num_nodes=nn,
                                                     airplane=airplane),
                           promotes_inputs=['CL', 'CD', 'Cm', 'qbar'],
                           promotes_outputs=['L', 'D', 'M'])
