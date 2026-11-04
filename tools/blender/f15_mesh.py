"""F-15EX: the airframe meshes (jk_mesh from f15_shape.py)."""

import jk_mesh
import f15_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(f15_shape)
