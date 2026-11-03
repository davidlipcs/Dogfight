"""J-20: the airframe meshes (jk_mesh from j20_shape.py)."""

import jk_mesh
import j20_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(j20_shape)
