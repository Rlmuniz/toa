import numpy as np
import openmdao.api as om

from toa.data import Airplane
from toa.data import get_airplane_data


class TransitionOEM(om.ExplicitComponent):
    """Models the transition phase (3 DoF) from liftoff to screen height."""

    def initialize(self):
        self.options.declare('num_nodes', types=int)
        self.options.declare('airplane', types=Airplane,
                             desc='Class containing all airplane data')

    def setup(self):
        nn = self.options['num_nodes']
        airplane = self.options['airplane']
        ar = np.arange(nn)
        zz = np.zeros(nn)
        ones = np.ones(nn)

        self.add_input(name='thrust', val=ones, desc='Engine total thrust',
                       units='N')
        self.add_input(name='lift', val=ones, desc='Lift', units='N')
        self.add_input(name='drag', val=ones, desc='Drag force', units='N')
        self.add_input(name='moment', val=ones, desc='Aerodynamic moment',
                       units='N*m')
        self.add_input(name='V', val=ones, desc='Body x axis velocity',
                       units='m/s')
        self.add_input(name='mass', val=ones, desc='Airplane mass', units='kg')
        self.add_input(name='alpha', val=ones, desc='Angle of attack',
                       units='rad')
        self.add_input(name='q', val=ones, desc='Pitch rate', units='rad/s')
        self.add_input(name='gam', val=ones, desc='Flight path angle',
                       units='rad')
        self.add_input(name='grav', val=0.0, desc='Gravity acceleration',
                       units='m/s**2')

        self.add_output(name='v_dot', val=ones, desc='Body x axis acceleration',
                        units='m/s**2')
        self.add_output(name='gam_dot', val=ones, desc='Flight path angle rate',
                        units='rad/s')
        self.add_output(name='x_dot', val=ones, desc='Derivative of position',
                        units='m/s')
        self.add_output(name='h_dot', val=ones, desc="Climb rate", units='m/s')
        self.add_output(name='q_dot', val=ones, desc="Pitch rate derivate",
                        units='rad/s**2')
        self.add_output(name='theta_dot', val=ones, desc="Pitch rate",
                        units='rad/s')

        self.declare_partials(of='v_dot', wrt='thrust', rows=ar, cols=ar)
        self.declare_partials(of='v_dot', wrt='alpha', rows=ar, cols=ar)
        self.declare_partials(of='v_dot', wrt='drag', rows=ar, cols=ar)
        self.declare_partials(of='v_dot', wrt='mass', rows=ar, cols=ar)
        self.declare_partials(of='v_dot', wrt='grav', rows=ar, cols=zz)
        self.declare_partials(of='v_dot', wrt='gam', rows=ar, cols=ar)

        self.declare_partials(of='gam_dot', wrt='thrust', rows=ar, cols=ar)
        self.declare_partials(of='gam_dot', wrt='alpha', rows=ar, cols=ar)
        self.declare_partials(of='gam_dot', wrt='lift', rows=ar, cols=ar)
        self.declare_partials(of='gam_dot', wrt='mass', rows=ar, cols=ar)
        self.declare_partials(of='gam_dot', wrt='grav', rows=ar, cols=zz)
        self.declare_partials(of='gam_dot', wrt='gam', rows=ar, cols=ar)
        self.declare_partials(of='gam_dot', wrt='V', rows=ar, cols=ar)

        self.declare_partials(of='x_dot', wrt='V', rows=ar, cols=ar)
        self.declare_partials(of='x_dot', wrt='gam', rows=ar, cols=ar)

        self.declare_partials(of='h_dot', wrt='V', rows=ar, cols=ar)
        self.declare_partials(of='h_dot', wrt='gam', rows=ar, cols=ar)

        self.declare_partials(of='q_dot', wrt='moment', rows=ar, cols=ar, val=1 / airplane.inertia.iy)
        self.declare_partials(of='theta_dot', wrt='q', rows=ar, cols=ar, val=1.0)

    def compute(self, inputs, outputs, **kwargs):
        thrust = inputs['thrust']
        lift = inputs['lift']
        drag = inputs['drag']
        moment = inputs['moment']
        V = inputs['V']
        mass = inputs['mass']
        alpha = inputs['alpha']
        q = inputs['q']
        gam = inputs['gam']
        grav = inputs['grav']
        airplane = self.options['airplane']

        weight = mass * grav

        cosgam = np.cos(gam)
        singam = np.sin(gam)
        cosalpha = np.cos(alpha)
        sinalpha = np.sin(alpha)

        outputs['v_dot'] = (thrust * cosalpha - drag - weight * singam) / mass
        outputs['gam_dot'] = (thrust * sinalpha + lift - weight * cosgam) / (mass * V)
        outputs['x_dot'] = V * cosgam
        outputs['h_dot'] = V * singam
        outputs['q_dot'] = moment / airplane.inertia.iy
        outputs['theta_dot'] = q

    def compute_partials(self, inputs, partials, **kwargs):
        thrust = inputs['thrust']
        alpha = inputs['alpha']
        mass = inputs['mass']
        grav = inputs['grav']
        gam = inputs['gam']
        drag = inputs['drag']
        V = inputs['V']
        lift = inputs['lift']

        cosalpha = np.cos(alpha)
        sinalpha = np.sin(alpha)
        singam = np.sin(gam)
        cosgam = np.cos(gam)

        partials['v_dot', 'thrust'] = cosalpha / mass
        partials['v_dot', 'alpha'] = - thrust * sinalpha / mass
        partials['v_dot', 'drag'] = - 1 / mass
        partials['v_dot', 'mass'] = (drag - thrust * cosalpha) / mass ** 2
        partials['v_dot', 'grav'] = -singam
        partials['v_dot', 'gam'] = -grav * cosgam

        partials['gam_dot', 'thrust'] = sinalpha / (V * mass)
        partials['gam_dot', 'alpha'] = thrust * cosalpha / (V * mass)
        partials['gam_dot', 'lift'] = 1 / (V * mass)
        partials['gam_dot', 'mass'] = -(lift + thrust * sinalpha) / (V * mass ** 2)
        partials['gam_dot', 'grav'] = - cosgam / V
        partials['gam_dot', 'gam'] = grav * singam / V
        partials['gam_dot', 'V'] = (grav * mass * cosgam - lift - thrust * sinalpha) / (V ** 2 * mass)

        partials['x_dot', 'V'] = cosgam
        partials['x_dot', 'gam'] = -V*singam

        partials['h_dot', 'V'] = singam
        partials['h_dot', 'gam'] = V*cosgam


if __name__ == '__main__':
    prob = om.Problem()
    airplane = get_airplane_data('b734')
    num_nodes = 1
    prob.model.add_subsystem('comp', TransitionOEM(num_nodes=1, airplane=airplane))

    prob.set_solver_print(level=0)

    prob.setup()
    prob.run_model()

    prob.check_partials(compact_print=True, show_only_incorrect=True)
