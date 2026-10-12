"""International Standard Atmosphere, 0 - 32 km."""

import math

from ..mathutil import G

R_AIR = 287.05
GAMMA = 1.4
RHO0 = 1.225


def isa(alt_m):
    """Return (density kg/m^3, speed of sound m/s) at a geometric altitude."""
    h = min(max(alt_m, 0.0), 32000.0)
    if h < 11000.0:                       # troposphere: -6.5 K / km
        temp = 288.15 - 0.0065 * h
        pressure = 101325.0 * (temp / 288.15) ** 5.25588
    elif h < 20000.0:                     # tropopause: constant -56.5 C
        temp = 216.65
        pressure = 22632.1 * math.exp(-G * (h - 11000.0) / (R_AIR * temp))
    else:                                 # lower stratosphere: +1 K / km
        temp = 216.65 + 0.001 * (h - 20000.0)
        pressure = 5474.89 * (temp / 216.65) ** (-G / (R_AIR * 0.001))
    rho = pressure / (R_AIR * temp)
    return rho, math.sqrt(GAMMA * R_AIR * temp)
