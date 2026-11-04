"""T-38C: the airframe meshes (jk_mesh from t38_shape.py)."""

import jk_mesh
import t38_shape
from jk_mesh import Piece  # noqa: F401


def airframe():
    return jk_mesh.airframe(t38_shape)
