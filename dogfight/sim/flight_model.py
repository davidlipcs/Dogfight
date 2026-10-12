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

# Landing gear
GEAR_HEIGHT = 2.05     # m from the centre of gravity down to the bottom of the wheels
GEAR_TIME = 4.0        # s to extend / retract
GEAR_CD = 0.022        # drag of the extended gear
FLAP_CL = 0.22         # trailing edge flaps drop with the gear handle (F-16 FLCS)
FLAP_CD = 0.012
MU_ROLL_PAVED = 0.02
MU_ROLL_GRASS = 0.07
MU_BRAKE = 0.45        # anti-skid wheel brakes
MAX_SINK = 4.2         # m/s, harder than this breaks the gear
MAX_TOUCH_BANK = 12.0  # deg, a wing tip hits the runway beyond this
TAIL_STRIKE = 13.0     # deg of pitch on the ground
ROTATE_IAS = 60.0      # m/s (~215 km/h), below this the stabilator can't lift the nose
NWS_RATE = 0.45        # rad/s nose wheel steering at taxi speed


class Controls:
    """Normalised pilot inputs, all in [-1, 1] except throttle [0, 1.1]."""

    __slots__ = ("pitch", "roll", "yaw", "throttle", "airbrake", "brakes")

    def __init__(self, throttle=0.85):
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw = 0.0
        self.throttle = throttle
        self.airbrake = False
        self.brakes = False


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
        # Landing gear / ground
        self.gear_down = False      # gear handle
        self.gear_pos = 0.0         # 0 = up and locked, 1 = down and locked
        self.on_ground = False
        self.ground_pitch = 0.0     # rad, attitude while the wheels are on the ground
        self.contact_event = None   # "touchdown" | "crash" (set for one step)
        self.crash_reason = ""
        self.sink_rate = 0.0        # m/s at the last touchdown

    def place_on_ground(self, x, y, ground_z, heading_deg):
        """Park the aircraft: gear down, wheels on the ground, engine idle."""
        self.pos = Vec3(x, y, ground_z + GEAR_HEIGHT)
        self.vel = Vec3(0, 0, 0)
        self.quat = Quat()
        self.quat.setHpr((-heading_deg, 0.0, 0.0))
        self.omega = Vec3(0, 0, 0)
        self.gear_down = True
        self.gear_pos = 1.0
        self.on_ground = True
        self.ground_pitch = 0.0
        self.engine = 0.0
        self.nz_cmd = 1.0

    def set_gear(self, down):
        """Gear handle; returns False if the weight-on-wheels switch blocks it."""
        if not down and self.on_ground:
            return False
        self.gear_down = down
        return True

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
        dry = spec.thrust_dry * (0.04 + 0.96 * dry_setting ** 1.6) * lapse * (1.0 + 0.02 * mach)
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
    def step(self, dt, controls, terrain=None):
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
        self.thrust = thrust
        self.fuel = max(0.0, self.fuel - self._fuel_flow(thrust) * dt)

        # ---- aerodynamics (stability axes)
        cl = self.lift_coefficient(alpha, mach)
        flaps = 0.0
        # trailing edge flaps: down with the gear handle, blown up again above ~240 kt
        flaps = self.gear_pos * clamp((125.0 - speed * math.sqrt(rho / RHO0)) / 25.0, 0.0, 1.0)
        if flaps > 0.0:
            cl += FLAP_CL * flaps * (1.0 if alpha > -0.05 else 0.0)
        lift_dir = safe_normalized(right.cross(vhat), up)
        side_dir = vhat.cross(lift_dir)
        cd = (spec.cd0 + interp_table(spec.wave_drag, mach) + spec.k_induced * cl * cl
              + self.store_cd + 0.8 * math.sin(alpha) ** 2)
        if controls.airbrake:
            cd += spec.airbrake_cd
        cd += GEAR_CD * self.gear_pos + FLAP_CD * flaps
        area = spec.wing_area
        lift = qbar * area * cl
        side = -qbar * area * 1.1 * beta
        drag = qbar * area * cd

        aero = lift_dir * lift + side_dir * side - vhat * drag
        force = aero + fwd * thrust
        acc = force / mass + Vec3(0, 0, -G)

        # ---- landing gear
        target = 1.0 if self.gear_down else 0.0
        self.gear_pos += clamp(target - self.gear_pos, -dt / GEAR_TIME, dt / GEAR_TIME)
        self.contact_event = None
        if terrain is not None:
            ground_z = terrain.height(self.pos.x, self.pos.y)
            if self.on_ground:
                self._ground_step(dt, controls, acc, ground_z, terrain, force, mass, alpha, mach, rho, qbar, speed)
                return
            if self.pos.z - ground_z <= GEAR_HEIGHT:
                if self._touchdown(ground_z, terrain):
                    self._ground_step(dt, controls, acc, ground_z, terrain, force, mass, alpha, mach, rho, qbar,
                                      speed)
                return

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

    # ------------------------------------------------------------------ ground
    def _touchdown(self, ground_z, terrain):
        """Wheels (or something else) just reached the ground. True = rolling on."""
        fwd = self.quat.getForward()
        pitch = math.degrees(math.asin(clamp(fwd.z, -1.0, 1.0)))
        right = self.quat.getRight()
        bank = math.degrees(math.atan2(-right.z, self.quat.getUp().z))
        self.sink_rate = max(0.0, -self.vel.z)
        reason = ""
        if self.gear_pos < 0.98:
            reason = "futómű nélkül értél földet" if self.gear_pos < 0.1 else "a futómű nem volt kint"
        elif self.sink_rate > MAX_SINK:
            reason = "túl kemény földetérés (%.1f m/s)" % self.sink_rate
        elif abs(bank) > MAX_TOUCH_BANK:
            reason = "szárnyvéggel értél földet"
        elif pitch < -3.0:
            reason = "orral értél földet"
        elif pitch > TAIL_STRIKE + 7.0:
            reason = "farokkal értél földet"
        elif terrain.slope(self.pos.x, self.pos.y) > math.radians(6.0):
            reason = "egyenetlen terep"
        if reason:
            self.contact_event = "crash"
            self.crash_reason = reason
            self.pos.z = ground_z + 1.0
            return False
        self.on_ground = True
        self.contact_event = "tailstrike" if pitch > TAIL_STRIKE + 2.0 else "touchdown"
        self.ground_pitch = math.radians(max(0.0, pitch))
        self.omega = Vec3(0, 0, 0)
        self.nz_cmd = 1.0
        self.pos.z = ground_z + GEAR_HEIGHT
        self.vel.z = 0.0
        return True

    def _ground_step(self, dt, controls, acc, ground_z, terrain, force, mass, alpha, mach, rho, qbar, speed):
        fwd = self.quat.getForward()
        heading = math.atan2(fwd.x, fwd.y)
        h_dir = Vec3(math.sin(heading), math.cos(heading), 0.0)
        h_right = Vec3(h_dir.y, -h_dir.x, 0.0)

        # normal force carries whatever lift does not
        normal = 0.0
        if acc.z < 0.0:
            normal = -acc.z
            acc.z = 0.0
        paved = terrain.airfield.on_paved(self.pos.x, self.pos.y) if hasattr(terrain, "airfield") else True
        mu = (MU_ROLL_PAVED if paved else MU_ROLL_GRASS) + (MU_BRAKE if controls.brakes else 0.0)
        u = self.vel.dot(h_dir)
        w = self.vel.dot(h_right)
        if abs(u) > 1e-3:
            decel = min(mu * normal, abs(u) / dt)
            acc -= h_dir * math.copysign(decel, u)
        elif normal > 0.0:
            # standing still: friction holds the aircraft unless thrust wins
            along = acc.dot(h_dir)
            hold = mu * normal
            acc -= h_dir * (along if abs(along) <= hold else math.copysign(hold, along))
        side_grip = 0.8 * normal
        acc -= h_right * clamp(w / max(dt, 0.02), -side_grip, side_grip)

        # steering: nose wheel at taxi speed, rudder at high speed
        gs = max(abs(u), 0.1)
        nws = NWS_RATE * min(1.0, 8.0 / gs) if self.ground_pitch < math.radians(2.0) else 0.0
        yaw_rate = clamp(controls.yaw, -1.0, 1.0) * (nws + 0.03 * min(gs / 60.0, 1.0)) * (1.0 if gs > 0.3 else 0.0)

        # rotation: the stabilator can lift the nose only with enough airflow
        ias = speed * math.sqrt(rho / RHO0)
        authority = clamp((ias - ROTATE_IAS) / 12.0, 0.0, 1.0)
        stick = clamp(controls.pitch, -1.0, 1.0)
        pitch_rate = stick * math.radians(7.0) * authority if stick > 0.0 else 0.0
        if pitch_rate <= 0.0:
            pitch_rate = -math.radians(3.5)          # nose wheel comes down
        self.ground_pitch = clamp(self.ground_pitch + pitch_rate * dt, 0.0, math.radians(TAIL_STRIKE))

        self.vel += acc * dt
        self.pos += self.vel * dt
        heading += yaw_rate * dt
        self.quat = Quat()
        self.quat.setHpr((-math.degrees(heading), math.degrees(self.ground_pitch), 0.0))
        self.omega = Vec3(math.copysign(abs(pitch_rate), pitch_rate) if self.ground_pitch > 0.0 else 0.0, 0.0, 0.0)

        new_ground = terrain.height(self.pos.x, self.pos.y)
        if normal == 0.0 and self.vel.z > 0.0:
            # lift exceeds weight: the struts extend and the wheels leave the ground
            if self.pos.z > new_ground + GEAR_HEIGHT + 0.3:
                self.on_ground = False               # airborne!
        else:
            self.pos.z = new_ground + GEAR_HEIGHT
            self.vel.z = 0.0

        self.alpha = alpha
        self.beta = 0.0
        self.mach = mach
        self.rho = rho
        self.qbar = qbar
        self.ias = speed * math.sqrt(rho / RHO0)
        self.accel = acc
        self.g_load = (force / mass).dot(self.quat.getUp()) / G + (normal / G)
