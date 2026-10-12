"""International Standard Atmosphere (troposphere + lower stratosphere)."""

import math

from ..mathutil import G

R_AIR = 287.05
GAMMA = 1.4
RHO0 = 1.225


def isa(alt_m):
    """Return (density kg/m^3, speed of sound m/s) at a geometric altitude."""
    h = min(max(alt_m, 0.0), 20000.0)
    if h < 11000.0:
        temp = 288.15 - 0.0065 * h
        pressure = 101325.0 * (temp / 288.15) ** 5.25588
    else:
        temp = 216.65
        pressure = 22632.1 * math.exp(-G * (h - 11000.0) / (R_AIR * temp))
    rho = pressure / (R_AIR * temp)
    return rho, math.sqrt(GAMMA * R_AIR * temp)
