"""Gripen: the airframe meshes (jk_mesh from gripen_shape.py)."""

import jk_mesh
import gripen_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(gripen_shape)
