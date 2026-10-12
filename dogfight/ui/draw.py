"""Immediate-mode 2D drawing on aspect2d: lines are rebuilt every frame, labels are pooled."""

import math

from panda3d.core import LineSegs, TextNode


class Canvas:
    def __init__(self, parent, thickness=1.6):
        self.parent = parent
        self.thickness = thickness
        self.np = None
        self.ls = None

    def begin(self):
        self.ls = LineSegs("hud")
        self.ls.setThickness(self.thickness)

    def end(self):
        new = self.parent.attachNewNode(self.ls.create())
        if self.np is not None:
            self.np.removeNode()
        self.np = new
        self.ls = None

    def line(self, x1, y1, x2, y2, color):
        self.ls.setColor(*color)
        self.ls.moveTo(x1, 0, y1)
        self.ls.drawTo(x2, 0, y2)

    def polyline(self, points, color, closed=False):
        if len(points) < 2:
            return
        self.ls.setColor(*color)
        self.ls.moveTo(points[0][0], 0, points[0][1])
        for x, y in points[1:]:
            self.ls.drawTo(x, 0, y)
        if closed:
            self.ls.drawTo(points[0][0], 0, points[0][1])

    def circle(self, x, y, r, color, segments=28, start=0.0, end=2 * math.pi):
        pts = [(x + r * math.sin(start + (end - start) * k / segments),
                y + r * math.cos(start + (end - start) * k / segments)) for k in range(segments + 1)]
        self.polyline(pts, color)

    def rect(self, x, y, hw, hh, color):
        self.polyline([(x - hw, y - hh), (x + hw, y - hh), (x + hw, y + hh), (x - hw, y + hh)], color, closed=True)

    def brackets(self, x, y, r, color, k=0.4):
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.polyline([(x + sx * r, y + sy * r * (1 - k)), (x + sx * r, y + sy * r),
                               (x + sx * r * (1 - k), y + sy * r)], color)

    def diamond(self, x, y, r, color):
        self.polyline([(x, y + r), (x + r, y), (x, y - r), (x - r, y)], color, closed=True)

    def cross(self, x, y, r, gap, color):
        self.line(x - r, y, x - gap, y, color)
        self.line(x + gap, y, x + r, y, color)
        self.line(x, y - r, x, y - gap, color)
        self.line(x, y + gap, x, y + r, color)

    def filled_box(self, x, y, r, color):
        for k in range(4):
            yy = y - r + (2 * r) * k / 3
            self.line(x - r, yy, x + r, yy, color)


class Label:
    __slots__ = ("node", "np", "text")

    def __init__(self, parent, font, scale, align):
        self.node = TextNode("label")
        self.node.setFont(font)
        self.node.setAlign(align)
        self.node.setShadow(0.06, 0.06)
        self.node.setShadowColor(0, 0, 0, 0.65)
        self.np = parent.attachNewNode(self.node)
        self.np.setScale(scale)
        self.text = None

    def set(self, text, x, y, color, scale=None, align=None):
        if text != self.text:
            self.node.setText(text)
            self.text = text
        self.node.setTextColor(*color)
        if align is not None:
            self.node.setAlign(align)
        if scale is not None:
            self.np.setScale(scale)
        self.np.setPos(x, 0, y)
        self.np.show()


class TextPool:
    """Re-usable labels; call begin(), text(...) any number of times, end()."""

    def __init__(self, parent, font, scale, translate=None):
        self.parent = parent
        self.font = font
        self.scale = scale
        self.translate = translate or (lambda s: s)
        self.items = []
        self.used = 0

    def begin(self):
        self.used = 0

    def text(self, text, x, y, color, scale=None, align=TextNode.ALeft):
        if self.used >= len(self.items):
            self.items.append(Label(self.parent, self.font, self.scale, align))
        label = self.items[self.used]
        self.used += 1
        label.set(self.translate(text), x, y, color, scale if scale is not None else self.scale, align)

    def end(self):
        for label in self.items[self.used:]:
            label.np.hide()
