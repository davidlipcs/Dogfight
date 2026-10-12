"""Find a system TrueType font that has the Hungarian accented letters.

Panda3D's built-in font is ASCII only.  If no system font is found the
accents are stripped (``"Lelőttek"`` -> ``"Lelottek"``) so text stays readable.
"""

import os
import unicodedata

from panda3d.core import Filename, TextNode

_WIN = os.environ.get("WINDIR", "C:/Windows").replace("\\", "/") + "/Fonts/"

TEXT_FONTS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    _WIN + "segoeui.ttf",
    _WIN + "arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
)

MONO_FONTS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
    _WIN + "consola.ttf",
    _WIN + "cour.ttf",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/Library/Fonts/Courier New.ttf",
)


def strip_accents(text):
    norm = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in norm if not unicodedata.combining(ch))


class Fonts:
    def __init__(self, loader):
        self.text = self._load(loader, TEXT_FONTS)
        self.mono = self._load(loader, MONO_FONTS) or self.text
        self.unicode = self.text is not None
        if self.text is None:
            self.text = TextNode.getDefaultFont()
        if self.mono is None:
            self.mono = self.text

    @staticmethod
    def _load(loader, paths):
        for path in paths:
            if not os.path.exists(path):
                continue
            try:
                font = loader.loadFont(Filename.fromOsSpecific(path).getFullpath())
            except (IOError, OSError):
                continue
            if font is not None and font.isValid():
                font.setPixelsPerUnit(48)
                return font
        return None

    def t(self, text):
        """Make a string displayable with the loaded font."""
        return text if self.unicode else strip_accents(text)
