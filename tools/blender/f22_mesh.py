"""F-22A: the airframe meshes (jk_mesh from f22_shape.py)."""

import jk_mesh
import f22_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(f22_shape)
