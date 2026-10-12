"""Controls / how-to-lock help panel (toggle with H or F1)."""

from panda3d.core import CardMaker, TextNode, TransparencyAttrib

HELP_TEXT = """\
F-16C VIPER  -  IRÁNYÍTÁS

REPÜLÉS (War Thunder "egeres célzás")
  Egér ............ ide repül a gép (fehér kör)
  W / S ........... magassági kormány felülbírálás
  A / D ........... orsózás   Q / E: oldalkormány
  Shift / Ctrl .... gáz fel / le (100% felett: UTÁNÉGETŐ)
  B (tartva) ...... légfék
  C vagy jobb egér  szabad körülnézés
  Z (tartva) ...... zoom      V: kabin / külső nézet

FEGYVEREK
  Bal egér ........ M61A1 gépágyú
  Space ........... rakéta indítása
  1 / 2 ........... AIM-9M / AIM-120A kiválasztása
  X (tartva) ...... flare + chaff

RADAR ÉS LOCKOLÁS
  R ............... radar be / ki
  Y ............... következő cél kijelölése a radaron
  T ............... radar LOCK / unlock
                    (ha nincs kijelölt cél: ACM mód -
                     ami az orr elé kerül, azt lockolja)
  F ............... AIM-9M kereső LOCK / elengedés

HOGYAN LOCKOLJ?
  AIM-9M (hőkövető): a kör a keresőfej. Vidd a célt
   a körbe -> a morgás magas hangra vált -> F = lock
   -> Space. Radar lockkal a kereső magától ráfordul.
   A hátsó félgömbből és utánégetős célra a legjobb.
  AIM-120A (radar): T = radar lock (zöld négyzet),
   jobbra a DLZ csík mutatja a hatótávot -> Space.
   Tartsd a lockot amíg "PITBULL" (aktív) nem lesz!
  Védekezés: fordulj 90 fokra a rakétára (NOTCH),
   szórj chaffot; hőkövető ellen flare + éles forduló.

  M: célpont jelölők   P: szünet   Enter: újraéledés
  Esc: kilépés         H / F1: súgó be / ki
"""


class HelpOverlay:
    def __init__(self, base, fonts):
        self.root = base.aspect2d.attachNewNode("help")
        cm = CardMaker("bg")
        cm.setFrame(-0.95, 0.95, -0.92, 0.92)
        bg = self.root.attachNewNode(cm.generate())
        bg.setColor(0.02, 0.04, 0.03, 0.82)
        bg.setTransparency(TransparencyAttrib.MAlpha)
        text = TextNode("help")
        text.setFont(fonts.mono)
        text.setText(fonts.t(HELP_TEXT))
        text.setTextColor(0.75, 1.0, 0.8, 1.0)
        text.setAlign(TextNode.ALeft)
        np = self.root.attachNewNode(text)
        np.setScale(0.036)
        np.setPos(-0.9, 0, 0.84)
        self.root.setBin("fixed", 100)
        self.visible = True

    def toggle(self):
        self.set_visible(not self.visible)

    def set_visible(self, visible):
        self.visible = visible
        if visible:
            self.root.show()
        else:
            self.root.hide()
