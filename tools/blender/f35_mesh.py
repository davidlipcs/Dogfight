"""F-35A: the airframe meshes (jk_mesh from f35_shape.py)."""

import jk_mesh
import f35_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(f35_shape)
