"""Controls / how-to-lock help panel (toggle with H or F1)."""

from panda3d.core import CardMaker, TextNode, TransparencyAttrib

HELP_TEXT = """\
F-16C VIPER  -  IRÁNYÍTÁS

REPÜLÉS (War Thunder "egeres célzás")
  Egér ............ ide repül a gép (fehér kör)
  S / W ........... orr fel / orr le (magassági kormány)
  A / D ........... orsózás   Q / E: oldalkormány
  Shift / Ctrl .... gáz fel / le: koppintás 5%, tartva folyamatos;
                    100%-nál megáll, újra Shift = UTÁNÉGETŐ
  B (tartva) ...... földön kerékfék, levegőben légfék
  G ............... futómű ki / be
  C vagy jobb egér  szabad körülnézés
  Z (tartva) ...... zoom      V: kabin (együtt mozog a géppel)

FELSZÁLLÁS ÉS LESZÁLLÁS
  Shift-tel told a gázt 100% fölé (utánégető), ~280 km/h-nál
  emeld meg az egeret (vagy S) -> elemelkedik. Utána G.
  Leszállás: G (futómű ki), ~270 km/h, lassú süllyedés
  (< 4 m/s!), szárnyak vízszintesen, földön B = fék.
  A bázison megállva: újrafegyverzés, tankolás, javítás.

FEGYVEREK
  Bal egér ........ M61A1 gépágyú
  Space ........... rakéta indítása
  Görgő ........... fegyverváltás
  1 / 2 ........... AIM-9M / AIM-120A kiválasztása
  X (tartva) ...... flare + chaff

RADAR ÉS LOCKOLÁS
  R ............... radar be / ki
  T ............... radar LOCK arra az ellenségre, amerre
                    nézel (±30°); újra T: következő cél
  F ............... AIM-9M LOCK / elengedés (±30°)
  Y ............... következő cél kijelölése a radaron

HOGYAN LOCKOLJ?
  AIM-9M (hőkövető): a kör a keresőfej. Vidd a célt
   a nagy körbe -> MAGÁTÓL LOCKOL (vagy F) -> Space.
   Radar lockkal a kereső magától ráfordul.
   A hátsó félgömbből és utánégetős célra a legjobb.
  AIM-120A (radar): nézz a célra, T = lock (zöld négyzet),
   jobbra a DLZ csík mutatja a hatótávot -> Space.
   Tartsd a lockot amíg "PITBULL" (aktív) nem lesz!
  Védekezés: fordulj 90 fokra a rakétára (NOTCH),
   szórj chaffot; hőkövető ellen flare + éles forduló.

KONTROLLER: bal kar = gép, jobb kar = célzás, RT/LT = gáz,
  RB = ágyú, A = rakéta, LB = flare, X/B = lock, Y = fegyver

  M: célpont jelölők   P: szünet   Enter: újraéledés
  Esc: kilépés         H / F1: súgó be / ki
"""


class HelpOverlay:
    def __init__(self, base, fonts):
        self.root = base.aspect2d.attachNewNode("help")
        cm = CardMaker("bg")
        cm.setFrame(-0.95, 0.95, -0.92, 0.92)
        bg = self.root.attachNewNode(cm.generate())
        bg.setColor(0.02, 0.04, 0.03, 0.9)
        bg.setTransparency(TransparencyAttrib.MAlpha)
        text = TextNode("help")
        text.setFont(fonts.mono)
        text.setText(fonts.t(HELP_TEXT))
        text.setTextColor(0.75, 1.0, 0.8, 1.0)
        text.setAlign(TextNode.ALeft)
        np = self.root.attachNewNode(text)
        np.setScale(0.031)
        np.setPos(-0.9, 0, 0.86)
        self.root.setBin("gui-popup", 50)
        self.visible = True

    def toggle(self):
        self.set_visible(not self.visible)

    def set_visible(self, visible):
        self.visible = visible
        if visible:
            self.root.show()
        else:
            self.root.hide()
