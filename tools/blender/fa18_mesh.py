"""F/A-18E: the airframe meshes (jk_mesh from fa18_shape.py)."""

import jk_mesh
import fa18_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(fa18_shape)
