import openmdao.api as om
import dymos as dm
import matplotlib.pyplot as plt

from toa.data import get_airplane_data
from toa.ode.initialrun_ode import InitialRunODE
from toa.ode.rotation_ode import RotationODE
from scipy.constants import degree

from toa.runway import Runway

p = om.Problem(model=om.Group())

# set driver
p.driver = om.pyOptSparseDriver()
p.driver.options['optimizer'] = 'SLSQP'

runway = Runway(1800, 0.0, 0.0, 0.0, 0.0)
airplane = get_airplane_data('b744')

external_params = p.model.add_subsystem('external_params', subsys=om.IndepVarComp())
external_params.add_output('elevation', val=runway.elevation, units='m',
                           desc='Runway elevation')
external_params.add_output('rw_slope', val=runway.slope, units='rad',
                           desc='Runway slope')

traj = p.model.add_subsystem('traj', dm.Trajectory())
transcription0 = dm.GaussLobatto(num_segments=30, order=3)
phase0 = dm.Phase(ode_class=InitialRunODE, transcription=transcription0,
                  ode_init_kwargs={'airplane': airplane})
traj.add_phase(name='phase0', phase=phase0)

# Set time options
phase0.set_time_options(fix_initial=True, units='s')

# Configure states
phase0.add_state('V', fix_initial=True, fix_final=False, units='kn',
                 rate_source='initial_run_eom.v_dot', lower=0,
                 targets=['V'])
phase0.add_state('x', fix_initial=True, fix_final=False, units='m',
                 rate_source='initial_run_eom.x_dot', lower=0)
phase0.add_state('mass', fix_initial=False, fix_final=False, units='kg',
                 rate_source='prop.m_dot', lower=0, upper=airplane.limits.MTOW,
                 targets=['mass'])

# Configure controls
phase0.add_control(name='de', fix_initial=False, fix_final=False, units='deg',
                   lower=-30.0, upper=30.0, targets=['de'])
# phase0.add_parameter(name='de', units='deg', opt=True, dynamic=False,
#                     lower=-30.0, upper=30.0, targets=['de'],
#                     include_timeseries=True)

# Configure path constraints
phase0.add_path_constraint('initial_run_eom.f_mg', lower=0, units='N')
phase0.add_path_constraint('initial_run_eom.f_ng', lower=0, units='N')
phase0.add_boundary_constraint('initial_run_eom.f_ng', loc='final',
                               constraint_name='final_f_ng',
                               upper=0.01, units='N', shape=(1,))

phase0.add_objective('mass', loc='initial', scaler=-1)

phase0.add_timeseries_output(
        ['aero.*', 'prop.*', 'initial_run_eom.f_mg', 'initial_run_eom.f_ng'])
# Rotation
transcription1 = dm.GaussLobatto(num_segments=10, order=3)
phase1 = dm.Phase(ode_class=RotationODE, transcription=transcription1,
                  ode_init_kwargs={'airplane': airplane})
traj.add_phase(name='phase1', phase=phase1)

# Set time options
phase1.set_time_options(units='s')

# Configure states
phase1.add_state('V', fix_initial=False, fix_final=False, units='kn',
                 rate_source='rotation_eom.v_dot', lower=0,
                 targets=['V'])
phase1.add_state('x', fix_initial=False, fix_final=False, units='m',
                 rate_source='rotation_eom.x_dot', upper=runway.tora)
phase1.add_state('q', fix_initial=True, fix_final=False, lower=0, units='deg/s',
                 rate_source='rotation_eom.q_dot',
                 targets=['q'])
phase1.add_state('theta', fix_initial=True, fix_final=False, units='deg',
                 rate_source='rotation_eom.theta_dot',
                 targets=['alpha'], lower=0, upper=25)
phase1.add_state('mass', fix_initial=False, fix_final=False, units='kg',
                 rate_source='prop.m_dot',
                 targets=['mass'], upper=airplane.limits.MTOW)

# Configure controls
phase1.add_control(name='de', fix_initial=False, fix_final=False, units='deg',
                   lower=-30.0, upper=30.0, targets=['de'])

phase1.add_path_constraint('rotation_eom.f_mg', lower=0, units='N')
phase1.add_boundary_constraint('rotation_eom.f_mg', loc='final',
                               constraint_name='final_f_mg', upper=0.01,
                               units='N', shape=(1,))
phase1.add_boundary_constraint('x', loc='final', constraint_name='RunwayLength',
                               upper=runway.tora)

phase1.add_timeseries_output(['aero.*', 'prop.*', 'rotation_eom.f_mg'])

# Connect external parameters
traj.add_parameter('flap_angle', targets={
    'phase0': ['aero.flap_angle'], 'phase1': ['aero.flap_angle']
}, shape=(1,), desc='Flap Angle', units='deg', opt=False, dynamic=False)

traj.add_parameter('elevation',
                   targets={'phase0': ['elevation'], 'phase1': ['elevation']},
                   shape=(1,), units='m', opt=False, dynamic=False)

traj.add_parameter('rw_slope', targets={
    'phase0': ['initial_run_eom.rw_slope'], 'phase1': ['rotation_eom.rw_slope']
}, shape=(1,), units='rad', opt=False, dynamic=False)

traj.add_parameter('Vw', targets={'phase0': ['Vw'], 'phase1': ['Vw']},
                   shape=(1,),
                   desc='Wind speed along the runway, defined as positive for a headwind',
                   units='m/s', opt=False, dynamic=False)

traj.link_phases(phases=['phase0', 'phase1'], vars=['time', 'x', 'V', 'mass'])
traj.add_linkage_constraint('phase0', 'phase1', 'de', 'de', loc_a='final',
                            loc_b='initial')

p.model.connect('external_params.elevation', 'traj.parameters:elevation')
p.model.connect('external_params.rw_slope', 'traj.parameters:rw_slope')

# Setup the problem
p.setup(check=True)
# p.final_setup()
# om.view_connections(p, outfile= "teste.html", show_browser=False)

p.set_val('traj.parameters:elevation', runway.elevation)
p.set_val('traj.parameters:rw_slope', runway.slope)
p.set_val('traj.parameters:flap_angle', 0.0)
p.set_val('traj.parameters:Vw', 0.0)

# Initial guesses
p.set_val('traj.phase0.states:x',
          phase0.interpolate(ys=[0, 0.8 * runway.tora], nodes='state_input'),
          units='m')
p.set_val('traj.phase0.states:V',
          phase0.interpolate(ys=[0, 130], nodes='state_input'),
          units='kn')
p.set_val('traj.phase0.states:mass',
          phase0.interpolate(ys=[airplane.limits.MTOW, airplane.limits.MTOW - 600],
                             nodes='state_input'),
          units='kg')

p.set_val('traj.phase1.states:x',
          phase1.interpolate(ys=[0.8 * runway.tora, runway.tora],
                             nodes='state_input'),
          units='m')
p.set_val('traj.phase1.states:V',
          phase1.interpolate(ys=[130, 180], nodes='state_input'),
          units='kn')
p.set_val('traj.phase1.states:theta',
          phase1.interpolate(ys=[0, 20], nodes='state_input'),
          units='deg')
p.set_val('traj.phase1.states:q',
          phase1.interpolate(ys=[0, 30], nodes='state_input'),
          units='deg/s')
p.set_val('traj.phase1.states:mass',
          phase1.interpolate(
                  ys=[airplane.limits.MTOW - 600, airplane.limits.MTOW - 1000],
                  nodes='state_input'),
          units='kg')

p.set_val('traj.phase0.t_duration', 60.0)
p.set_val('traj.phase1.t_initial', 60.0)
p.set_val('traj.phase1.t_duration', 10.0)

dm.run_problem(p)

plt.figure(0)
plt.plot(p.get_val('traj.phase0.timeseries.time'),
         p.get_val('traj.phase0.timeseries.states:x'), '.-',
         p.get_val('traj.phase1.timeseries.time'),
         p.get_val('traj.phase1.timeseries.states:x'), '.-')
plt.title('position')
plt.grid()

plt.figure(1)
plt.plot(p.get_val('traj.phase0.timeseries.time'),
         p.get_val('traj.phase0.timeseries.f_mg', units='kN'), '.-',
         p.get_val('traj.phase1.timeseries.time'),
         p.get_val('traj.phase1.timeseries.f_mg', units='kN'), '.-',
         p.get_val('traj.phase0.timeseries.time'),
         p.get_val('traj.phase0.timeseries.f_ng', units='kN'), '.-')
plt.title('Landing gear forces')
plt.grid()

plt.figure(2)
plt.plot(p.get_val('traj.phase0.timeseries.time'),
         p.get_val('traj.phase0.timeseries.controls:de', units='deg'), '.-',
         p.get_val('traj.phase1.timeseries.time'),
         p.get_val('traj.phase1.timeseries.controls:de', units='deg'), '.-')
plt.title('Elevator deflection')
plt.grid()

plt.figure(3)
plt.plot(p.get_val('traj.phase0.timeseries.time'),
         p.get_val('traj.phase0.timeseries.states:V', units='kn'), '.-',
         p.get_val('traj.phase1.timeseries.time'),
         p.get_val('traj.phase1.timeseries.states:V', units='kn'), '.-')
plt.title('V')
plt.grid()

plt.figure(4)
plt.plot(p.get_val('traj.phase1.timeseries.time'),
         p.get_val('traj.phase1.timeseries.states:theta', units='deg'), '.-')
plt.title('Pitch Angle')
plt.grid()

plt.figure(5)
plt.plot(p.get_val('traj.phase1.timeseries.time'),
         p.get_val('traj.phase1.timeseries.states:q', units='deg/s'), '.-')
plt.title('Pitch rate')
plt.grid()

plt.figure(6)
plt.plot(p.get_val('traj.phase0.timeseries.time'),
         p.get_val('traj.phase0.timeseries.thrust', units='kN'), '.-',
         p.get_val('traj.phase1.timeseries.time'),
         p.get_val('traj.phase1.timeseries.thrust', units='kN'), '.-')
plt.title('Thrust')
plt.grid()

plt.figure(7)
plt.plot(p.get_val('traj.phase0.timeseries.time'),
         p.get_val('traj.phase0.timeseries.L', units='kN'),
         p.get_val('traj.phase1.timeseries.time'),
         p.get_val('traj.phase1.timeseries.L', units='kN'))
plt.title('Lift')
plt.grid()

plt.figure(8)
plt.plot(p.get_val('traj.phase0.timeseries.time'),
         p.get_val('traj.phase0.timeseries.M', units='N*m'),
         p.get_val('traj.phase1.timeseries.time'),
         p.get_val('traj.phase1.timeseries.M', units='N*m'))
plt.title('Moment')
plt.grid()

plt.figure(9)
plt.plot(p.get_val('traj.phase0.timeseries.time'),
         p.get_val('traj.phase0.timeseries.states:mass', units='kg'), '.-',
         p.get_val('traj.phase1.timeseries.time'),
         p.get_val('traj.phase1.timeseries.states:mass', units='kg'), '.-')
plt.title('mass')
plt.grid()
plt.show()
