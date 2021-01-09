import numpy as np
import openmdao.api as om


class DynamicPressureComp(om.ExplicitComponent):
    """Compute the dynamic pressure based on the velocity and the atmospheric density. """

    def initialize(self):
        self.options.declare('num_nodes', types=int)

    def setup(self):
        nn = self.options['num_nodes']

        # Inputs
        self.add_input(name='rho', shape=(1,), desc='Atmospheric density',
                       units='kg/m**3')
        self.add_input(name='tas', shape=(nn,), desc='True airspeed', units='m/s')

        # Outputs
        self.add_output(name='qbar', val=np.zeros(nn), desc='Dynamic pressure',
                        units='Pa')

    def setup_partials(self):
        self.declare_partials(of='qbar', wrt='rho')
        self.declare_partials(of='qbar', wrt='tas')

    def compute(self, inputs, outputs, **kwargs):
        outputs['qbar'] = 0.5 * inputs['rho'] * inputs['tas'] ** 2

    def compute_partials(self, inputs, partials, **kwargs):
        tas = inputs['tas']
        rho = inputs['rho']

        partials['qbar', 'rho'] = 0.5 * tas ** 2
        partials['qbar', 'tas'] = rho * tas
