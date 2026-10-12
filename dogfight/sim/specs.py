"""Aircraft, weapon and sensor data.

The numbers are modelled on the F-16C Block 50 as it appears in War Thunder
(F110-GE-129 engine, AN/APG-68 radar, M61A1 Vulcan, AIM-9M and AIM-120A),
using public data plus some rounding/tuning so the game "feels" like WT.
Everything that matters for balance lives in this one file, so it is the
place to tweak.
"""

from dataclasses import dataclass, field

# --------------------------------------------------------------------------- guns


@dataclass(frozen=True)
class GunSpec:
    name: str
    rate_rpm: float
    ammo: int
    muzzle_velocity: float      # m/s
    drag_k: float               # quadratic drag: a = -k * |v| * v
    dispersion_mrad: float
    damage: float               # damage per hit (aircraft have 100 HP)
    bullet_life: float          # s
    max_lead_range: float       # m - lead pipper shown inside this range


M61A1 = GunSpec(
    name="M61A1 Vulcan 20mm",
    rate_rpm=6000,
    ammo=511,
    muzzle_velocity=1050.0,
    drag_k=3.7e-4,
    dispersion_mrad=1.6,
    damage=9.0,
    bullet_life=3.0,
    max_lead_range=1800.0,
)

# ----------------------------------------------------------------------- missiles

IR = "IR"     # infrared homing ("Fox 2")
ARH = "ARH"   # active radar homing ("Fox 3")


@dataclass(frozen=True)
class MissileSpec:
    name: str
    guidance: str
    mass: float                 # launch mass, kg
    propellant: float           # kg burnt by the motor
    diameter: float             # m
    length: float               # m
    motor: tuple                # ((duration s, thrust N), ...) boost / sustain phases
    cd_table: tuple             # ((mach, Cd0), ...)
    cn_max: float               # max normal force coefficient (limits G at low q)
    max_g: float
    induced_drag: float         # drag per unit lateral force (≈ 1 / (L/D))
    nav_gain: float             # proportional navigation constant
    guidance_delay: float       # s after launch before it starts to steer
    guidance_time: float        # s, self destructs after this
    arm_time: float             # s, fuse is safe before this
    fuse_radius: float          # m, proximity fuse
    lethal_radius: float        # m, full damage inside
    damage_radius: float        # m, no damage outside
    damage: float               # damage at <= lethal radius
    seeker_fov: float           # deg half angle (IR: lock cone, ARH: active search cone)
    gimbal_limit: float         # deg
    track_rate: float           # deg/s
    seeker_range: float         # m (IR: rear aspect / mil power lock range, ARH: pitbull range)
    ccm: float                  # 0..1 chance to ignore one decoy (IRCCM / ECCM)
    min_range: float            # m, for the launch zone indicator
    datalink: bool = False
    loft: bool = False
    smoke: float = 0.5          # 0..1 visual smoke density
    rail_time: float = 0.25     # s of "rail" phase (no guidance, motor on)

    @property
    def ref_area(self):
        return 3.14159265 * (self.diameter * 0.5) ** 2

    @property
    def burn_time(self):
        return sum(d for d, _ in self.motor)


AIM9M = MissileSpec(
    name="AIM-9M Sidewinder",
    guidance=IR,
    mass=86.0,
    propellant=22.0,
    diameter=0.127,
    length=2.87,
    motor=((5.0, 9200.0),),
    cd_table=((0.5, 0.36), (0.9, 0.42), (1.1, 0.72), (1.6, 0.6), (2.5, 0.48), (4.0, 0.4)),
    cn_max=18.0,
    max_g=30.0,
    induced_drag=0.16,
    nav_gain=4.0,
    guidance_delay=0.2,
    guidance_time=60.0,
    arm_time=0.6,
    fuse_radius=6.0,
    lethal_radius=4.0,
    damage_radius=14.0,
    damage=140.0,
    seeker_fov=2.5,
    gimbal_limit=40.0,
    track_rate=30.0,
    seeker_range=9000.0,
    ccm=0.65,
    min_range=400.0,
    smoke=0.35,
)

AIM120A = MissileSpec(
    name="AIM-120A AMRAAM",
    guidance=ARH,
    mass=152.0,
    propellant=50.0,
    diameter=0.178,
    length=3.65,
    motor=((3.0, 28500.0), (5.0, 9500.0)),
    cd_table=((0.5, 0.34), (0.9, 0.4), (1.1, 0.7), (1.6, 0.58), (2.5, 0.45), (4.5, 0.36)),
    cn_max=20.0,
    max_g=38.0,
    induced_drag=0.13,
    nav_gain=4.0,
    guidance_delay=0.45,
    guidance_time=80.0,
    arm_time=1.0,
    fuse_radius=9.0,
    lethal_radius=6.0,
    damage_radius=22.0,
    damage=160.0,
    seeker_fov=15.0,
    gimbal_limit=50.0,
    track_rate=25.0,
    seeker_range=16000.0,
    ccm=0.55,
    min_range=1200.0,
    datalink=True,
    loft=True,
    smoke=0.3,
)

MISSILES = {"AIM-9M": AIM9M, "AIM-120A": AIM120A}

# -------------------------------------------------------------------------- radar


@dataclass(frozen=True)
class RadarSpec:
    name: str
    search_range: float     # m, detection range vs a 5 m^2 target
    scan_az: float          # deg half width of the search scan
    scan_el: float          # deg half height of the search scan
    scan_rate: float        # deg/s beam sweep speed
    stt_gimbal: float       # deg, max angle off the nose while locked
    lock_range: float       # m, max range to start a lock
    acm_range: float        # m, ACM auto-acquisition range
    acm_az: float           # deg half width of the ACM (boresight / vertical scan) window
    acm_el_low: float       # deg
    acm_el_high: float      # deg
    lock_time: float        # s needed to go from contact to STT
    notch_speed: float      # m/s, doppler notch half width
    track_memory: float     # s the lock survives without a valid return
    rwr_symbol: str


APG68 = RadarSpec(
    name="AN/APG-68(V)9",
    search_range=74000.0,
    scan_az=60.0,
    scan_el=12.0,
    scan_rate=120.0,
    stt_gimbal=60.0,
    lock_range=55000.0,
    acm_range=16000.0,
    acm_az=6.0,
    acm_el_low=-6.0,
    acm_el_high=40.0,
    lock_time=0.5,
    notch_speed=25.0,
    track_memory=0.6,
    rwr_symbol="16",
)

# ----------------------------------------------------------------- countermeasures


@dataclass(frozen=True)
class CountermeasureSpec:
    flares: int
    chaff: int
    flare_intensity: float   # IR intensity relative to an F-16 at military power, rear aspect
    flare_life: float
    chaff_life: float
    interval: float          # s between two salvos


ALE47 = CountermeasureSpec(flares=30, chaff=30, flare_intensity=3.0, flare_life=4.0, chaff_life=5.0, interval=0.35)

# ------------------------------------------------------------------------ aircraft


@dataclass(frozen=True)
class AircraftSpec:
    name: str
    empty_mass: float        # kg (incl. pilot, gun, pylons)
    internal_fuel: float     # kg
    wing_area: float         # m^2
    wing_span: float         # m
    length: float            # m
    thrust_dry: float        # N, sea level static, military power
    thrust_ab: float         # N, sea level static, full afterburner
    fuel_flow_dry: float     # kg/s at military power
    fuel_flow_ab: float      # kg/s at full afterburner
    cl_alpha: float          # lift slope per radian
    cl_max: float
    alpha_stall: float       # deg, where lift stops growing
    alpha_limit: float       # deg, FLCS AoA limiter
    cd0: float
    k_induced: float
    wave_drag: tuple         # ((mach, delta Cd0), ...)
    g_max: float
    g_min: float
    roll_rate: float         # deg/s max
    yaw_beta: float          # deg of sideslip at full rudder
    airbrake_cd: float
    hp: float
    rcs_front: float         # m^2
    rcs_side: float          # m^2
    hitboxes: tuple          # ((centre xyz), (half extents xyz)) boxes in the body frame, m
    gun: GunSpec
    radar: RadarSpec
    countermeasures: CountermeasureSpec
    stations: dict = field(default_factory=dict)   # station number -> (x, y, z) mount point
    loadouts: dict = field(default_factory=dict)   # name -> {station: missile key}


F16C = AircraftSpec(
    name="F-16C Block 50",
    empty_mass=8900.0,
    internal_fuel=3200.0,
    wing_area=27.87,
    wing_span=9.96,
    length=15.06,
    thrust_dry=76300.0,
    thrust_ab=131600.0,
    fuel_flow_dry=1.35,
    fuel_flow_ab=6.2,
    cl_alpha=4.1,
    cl_max=1.8,
    alpha_stall=30.0,
    alpha_limit=25.0,
    cd0=0.0205,
    k_induced=0.118,
    wave_drag=((0.0, 0.0), (0.8, 0.0), (0.95, 0.014), (1.05, 0.032), (1.2, 0.036), (1.6, 0.027), (2.2, 0.02)),
    g_max=9.0,
    g_min=-3.0,
    roll_rate=270.0,
    yaw_beta=6.0,
    airbrake_cd=0.06,
    hp=100.0,
    rcs_front=1.5,
    rcs_side=6.0,
    hitboxes=(
        ((0.0, 0.0, 0.0), (0.95, 7.5, 1.05)),     # fuselage + intake
        ((0.0, -1.0, 0.1), (4.9, 2.4, 0.35)),     # wings
        ((0.0, -5.6, 0.2), (2.8, 1.3, 0.3)),      # horizontal tails
        ((0.0, -5.4, 2.0), (0.3, 1.5, 1.3)),      # fin
    ),
    gun=M61A1,
    radar=APG68,
    countermeasures=ALE47,
    stations={
        # F-16 numbering: 1 = left wingtip ... 9 = right wingtip (x < 0 is left)
        1: (-4.88, -0.55, 0.10),
        2: (-3.75, -0.95, -0.38),
        3: (-2.60, -0.55, -0.45),
        7: (2.60, -0.55, -0.45),
        8: (3.75, -0.95, -0.38),
        9: (4.88, -0.55, 0.10),
    },
    loadouts={
        "default": {1: "AIM-9M", 9: "AIM-9M", 2: "AIM-9M", 8: "AIM-9M", 3: "AIM-120A", 7: "AIM-120A"},
        "amraam": {1: "AIM-120A", 9: "AIM-120A", 2: "AIM-9M", 8: "AIM-9M", 3: "AIM-120A", 7: "AIM-120A"},
        "fox2": {1: "AIM-9M", 9: "AIM-9M", 2: "AIM-9M", 8: "AIM-9M", 3: "AIM-9M", 7: "AIM-9M"},
    },
)

# Order in which stations are emptied (alternating sides, outboard first).
FIRING_ORDER = (9, 1, 8, 2, 7, 3)
