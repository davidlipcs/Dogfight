"""Rafale: the airframe meshes (jk_mesh from rafale_shape.py)."""

import jk_mesh
import rafale_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(rafale_shape)
