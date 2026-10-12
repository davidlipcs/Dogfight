"""Point-mass aerodynamics + an F-16 style fly-by-wire (FLCS) controller.

The stick does not move control surfaces directly.  Like the real F-16 the
pitch stick commands a load factor (neutral stick = 1 G, full aft = 9 G,
full forward = -3 G) and the roll stick commands a roll rate.  The FLCS turns
those commands into body rotation rates while respecting the AoA limiter
(25 deg) and the G limits, so the aircraft can't be over-stressed but it
*can* run out of energy: pull 9 G for a while and the speed bleeds away,
exactly like in War Thunder's "realistic" mode.
"""

import math

from panda3d.core import Quat, Vec3

from ..mathutil import DEG, G, clamp, interp_table, quat_axis_angle, safe_normalized
from .atmosphere import RHO0, isa

# Mach correction of the lift slope (compressibility).
CLA_MACH = ((0.0, 1.0), (0.8, 1.08), (0.95, 1.12), (1.1, 0.95), (1.5, 0.8), (2.2, 0.62))

K_ALPHA = 6.0          # 1/s, how fast the FLCS drives AoA to the commanded value
K_BETA = 3.0           # 1/s, sideslip correction (yaw damper / coordination)
TAU_PITCH = 0.06       # s, actuator lag
TAU_ROLL = 0.09
TAU_YAW = 0.12
# F110-GE-129 spool: idle -> military ~4 s, afterburner light-off and zones ~1.5 s
SPOOL_UP_CORE = 0.30   # throttle units / s at high rpm (slower near idle)
SPOOL_DOWN_CORE = 0.40
SPOOL_UP_AB = 0.07     # 0.1 throttle units (min -> max AB) in ~1.5 s
SPOOL_DOWN_AB = 0.25
RHO_TROPOPAUSE = 0.36392
MAX_AB = 1.1           # throttle above 1.0 = afterburner (War Thunder style "110 %")
G_ONSET = 10.0         # G/s, FLCS limit on how fast the commanded load factor may change


class Controls:
    """Normalised pilot inputs, all in [-1, 1] except throttle [0, 1.1]."""

    __slots__ = ("pitch", "roll", "yaw", "throttle", "airbrake")

    def __init__(self, throttle=0.85):
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw = 0.0
        self.throttle = throttle
        self.airbrake = False


class FlightModel:
    def __init__(self, spec, pos, vel, quat, fuel=None):
        self.spec = spec
        self.pos = Vec3(pos)
        self.vel = Vec3(vel)
        self.quat = Quat(quat)
        # Body rotation rates as a local rotation vector:
        # x = pitch (nose up +), y = roll (right wing down +), z = yaw (nose left +)
        self.omega = Vec3(0, 0, 0)
        self.fuel = spec.internal_fuel if fuel is None else fuel
        self.fuel_mult = 1.0
        self.store_mass = 0.0
        self.store_cd = 0.0
        self.engine = 0.85          # spooled engine setting 0..1.1
        self.nz_cmd = 1.0           # load factor the FLCS currently commands (onset limited)
        # Telemetry (read by HUD / AI / sensors)
        self.alpha = 0.0            # rad
        self.beta = 0.0             # rad
        self.mach = 0.0
        self.ias = self.vel.length()
        self.rho = RHO0
        self.qbar = 0.0
        self.g_load = 1.0
        self.thrust = 0.0
        self.accel = Vec3(0, 0, 0)  # total acceleration incl. gravity

    # ------------------------------------------------------------------ helpers
    @property
    def mass(self):
        return self.spec.empty_mass + self.fuel + self.store_mass

    @property
    def speed(self):
        return self.vel.length()

    @property
    def forward(self):
        return self.quat.getForward()

    @property
    def up(self):
        return self.quat.getUp()

    @property
    def right(self):
        return self.quat.getRight()

    @property
    def afterburner(self):
        return self.engine > 1.0 + 1e-3 and self.fuel > 0.0

    def lift_coefficient(self, alpha, mach):
        spec = self.spec
        cla = spec.cl_alpha * interp_table(CLA_MACH, mach)
        a = abs(alpha)
        stall = spec.alpha_stall * DEG
        if a <= stall:
            cl = cla * a
            cl = min(cl, spec.cl_max)
        else:
            # Past the stall blend into a flat plate: CL = sin(2a)
            peak = min(cla * stall, spec.cl_max)
            t = clamp((a - stall) / (15 * DEG), 0.0, 1.0)
            plate = 0.95 * math.sin(2.0 * min(a, math.pi - a))
            cl = peak * (1.0 - t) + plate * t
        return math.copysign(cl, alpha)

    def thrust_at(self, setting, rho, mach):
        spec = self.spec
        if self.fuel <= 0.0:
            return 0.0
        # thrust lapse: ~sigma^0.75 in the troposphere, faster above 11 km
        if rho >= RHO_TROPOPAUSE:
            lapse = (rho / RHO0) ** 0.75
        else:
            lapse = (RHO_TROPOPAUSE / RHO0) ** 0.75 * (rho / RHO_TROPOPAUSE) ** 1.25
        dry_setting = min(setting, 1.0)
        dry = spec.thrust_dry * (0.06 + 0.94 * dry_setting ** 1.6) * lapse * (1.0 + 0.02 * mach)
        if setting <= 1.0:
            return dry
        ab_frac = clamp((setting - 1.0) / (MAX_AB - 1.0), 0.0, 1.0)
        full_ab = spec.thrust_ab * lapse * (1.0 + 0.3 * mach)
        return dry + (full_ab - dry) * ab_frac

    def _spool(self, target, dt):
        """Rate limited engine response (no instant thrust like in arcade games)."""
        e = self.engine
        if target > e:
            if e < 1.0:
                rate = SPOOL_UP_CORE * (0.45 + 0.55 * e)       # sluggish near idle
                e = min(e + rate * dt, min(target, 1.0))
            elif self.fuel > 0.0:
                e = min(e + SPOOL_UP_AB * dt, target)
        elif target < e:
            rate = SPOOL_DOWN_AB if e > 1.0 else SPOOL_DOWN_CORE
            e = max(e - rate * dt, target)
        self.engine = e

    def _fuel_flow(self, thrust):
        spec = self.spec
        dry_sfc = spec.fuel_flow_dry / spec.thrust_dry
        ab_sfc = spec.fuel_flow_ab / spec.thrust_ab
        sfc = dry_sfc if self.engine <= 1.0 else ab_sfc
        return thrust * sfc * self.fuel_mult

    # --------------------------------------------------------------------- step
    def step(self, dt, controls):
        spec = self.spec
        fwd = self.quat.getForward()
        up = self.quat.getUp()
        right = self.quat.getRight()

        rho, a_sound = isa(self.pos.z)
        speed = self.vel.length()
        vhat = self.vel / speed if speed > 1.0 else Vec3(fwd)
        u = self.vel.dot(fwd)
        w = self.vel.dot(up)
        alpha = math.atan2(-w, u) if speed > 1.0 else 0.0
        beta = math.asin(clamp(self.vel.dot(right) / max(speed, 1.0), -1.0, 1.0))
        mach = speed / a_sound
        qbar = 0.5 * rho * speed * speed
        mass = self.mass

        # ---- engine
        self._spool(clamp(controls.throttle, 0.0, MAX_AB), dt)
        thrust = self.thrust_at(self.engine, rho, mach)
        self.fuel = max(0.0, self.fuel - self._fuel_flow(thrust) * dt)

        # ---- aerodynamics (stability axes)
        cl = self.lift_coefficient(alpha, mach)
        lift_dir = safe_normalized(right.cross(vhat), up)
        side_dir = vhat.cross(lift_dir)
        cd = (spec.cd0 + interp_table(spec.wave_drag, mach) + spec.k_induced * cl * cl
              + self.store_cd + 0.8 * math.sin(alpha) ** 2)
        if controls.airbrake:
            cd += spec.airbrake_cd
        area = spec.wing_area
        lift = qbar * area * cl
        side = -qbar * area * 1.1 * beta
        drag = qbar * area * cd

        aero = lift_dir * lift + side_dir * side - vhat * drag
        force = aero + fwd * thrust
        acc = force / mass + Vec3(0, 0, -G)

        # ---- FLCS: pitch (G command with AoA limiter)
        stick = clamp(controls.pitch, -1.0, 1.0)
        if stick >= 0.0:
            nz_cmd = 1.0 + stick * (spec.g_max - 1.0)
        else:
            nz_cmd = 1.0 + stick * (1.0 - spec.g_min)
        step = G_ONSET * dt
        self.nz_cmd += clamp(nz_cmd - self.nz_cmd, -step, step)
        nz_cmd = self.nz_cmd
        cla_eff = spec.cl_alpha * interp_table(CLA_MACH, mach)
        if qbar > 1.0:
            alpha_req = nz_cmd * mass * G / (qbar * area * cla_eff)
        else:
            alpha_req = spec.alpha_limit * DEG * (1 if nz_cmd > 0 else -1)
        alpha_req = clamp(alpha_req, -10.0 * DEG, spec.alpha_limit * DEG)

        v_safe = max(speed, 30.0)
        path_pitch = acc.dot(lift_dir) / v_safe
        path_lat = acc.dot(side_dir) / v_safe
        authority = clamp(qbar / 9000.0, 0.12, 1.0)
        q_cmd = path_pitch + K_ALPHA * (alpha_req - alpha) * authority
        q_cmd = clamp(q_cmd, -0.9, 0.9)

        # ---- roll rate command (reduced at high AoA and low dynamic pressure)
        roll_eff = clamp(qbar / 9000.0, 0.15, 1.0) * (1.0 - 0.5 * clamp(alpha / (spec.alpha_limit * DEG), 0.0, 1.0))
        p_cmd = clamp(controls.roll, -1.0, 1.0) * spec.roll_rate * DEG * roll_eff

        # ---- yaw: rudder commands sideslip, otherwise coordinate the turn
        beta_cmd = -clamp(controls.yaw, -1.0, 1.0) * spec.yaw_beta * DEG
        r_cmd = path_lat + K_BETA * (beta - beta_cmd) * authority   # + = nose right

        self.omega.x += (q_cmd - self.omega.x) * min(1.0, dt / TAU_PITCH)
        self.omega.y += (p_cmd - self.omega.y) * min(1.0, dt / TAU_ROLL)
        self.omega.z += (-r_cmd - self.omega.z) * min(1.0, dt / TAU_YAW)

        # ---- integrate
        self.vel += acc * dt
        self.pos += self.vel * dt
        rot = self.omega * dt
        angle = rot.length()
        if angle > 1e-9:
            self.quat = quat_axis_angle(rot / angle, angle) * self.quat
            self.quat.normalize()

        # ---- telemetry
        self.alpha = alpha
        self.beta = beta
        self.mach = mach
        self.rho = rho
        self.qbar = qbar
        self.ias = speed * math.sqrt(rho / RHO0)
        self.thrust = thrust
        self.accel = acc
        self.g_load = (force / mass).dot(up) / G
