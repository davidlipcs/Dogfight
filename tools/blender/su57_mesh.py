"""Su-57: the airframe meshes (jk_mesh from su57_shape.py)."""

import jk_mesh
import su57_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(su57_shape)
