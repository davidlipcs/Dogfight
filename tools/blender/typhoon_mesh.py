"""Typhoon: the airframe meshes (jk_mesh from typhoon_shape.py)."""

import jk_mesh
import typhoon_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(typhoon_shape)
