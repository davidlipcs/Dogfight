"""T-45C: the airframe meshes (jk_mesh from t45_shape.py)."""

import jk_mesh
import t45_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(t45_shape)
