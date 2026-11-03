"""MiG-29: the airframe meshes (jk_mesh from mig29_shape.py)."""

import jk_mesh
import mig29_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(mig29_shape)
