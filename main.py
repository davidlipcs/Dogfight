"""Dogfight - War Thunder style F-16C air combat.  Run:  python main.py  (python main.py --help)."""

import argparse


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="F-16C légiharc (War Thunder stílus)")
    p.add_argument("--difficulty", choices=("easy", "normal", "hard"), default="normal", help="AI nehézség")
    p.add_argument("--enemies", type=int, default=2, help="ellenségek száma az első hullámban")
    p.add_argument("--loadout", choices=("default", "amraam", "fox2"), default="default",
                   help="default: 4x AIM-9M + 2x AIM-120A, amraam: 4x AIM-120A + 2x AIM-9M, fox2: 6x AIM-9M")
    p.add_argument("--size", type=lambda s: tuple(int(v) for v in s.lower().split("x")), default=(1600, 900),
                   help="ablakméret, pl. 1920x1080")
    p.add_argument("--fullscreen", action="store_true", help="teljes képernyő")
    p.add_argument("--sensitivity", type=float, default=0.09, help="egér érzékenység (fok / pixel)")
    p.add_argument("--invert-y", action="store_true", help="fordított egér Y tengely")
    p.add_argument("--volume", type=float, default=0.8, help="hangerő 0..1")
    p.add_argument("--mute", action="store_true", help="hang kikapcsolása")
    p.add_argument("--clouds", type=int, default=70, help="felhők száma (gyengébb gépen kevesebb)")
    p.add_argument("--no-aa", action="store_true", help="élsimítás kikapcsolása")
    p.add_argument("--fps", action="store_true", help="FPS kijelzés")
    p.add_argument("--seed", type=int, default=None, help="véletlen mag")
    p.add_argument("--offscreen", action="store_true", help=argparse.SUPPRESS)
    return p.parse_args(argv)


def main(argv=None):
    options = parse_args(argv)
    from dogfight.game import DogfightApp
    DogfightApp(options).run()


if __name__ == "__main__":
    main()
