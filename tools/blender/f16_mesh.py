"""F-16C: the airframe meshes (jk_mesh from f16_shape.py)."""

import jk_mesh
import f16_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(f16_shape)
