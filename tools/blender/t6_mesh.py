"""T-6A: the airframe meshes (jk_mesh from t6_shape.py)."""

import jk_mesh
import t6_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(t6_shape)
