"""Su-35S: the airframe meshes (jk_mesh from su35_shape.py)."""

import jk_mesh
import su35_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(su35_shape)
