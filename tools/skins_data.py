"""The paint schemes (aircraft) and flight outfits (pilot) of the shop: the one source for the web game
(web/js/skins.js) and the Roblox game (roblox/src/shared/Catalog.luau) - `python3 tools/gen_skins.py`.

AIR rows:   (id, name, tint, pattern, pattern colour, metal, rough, glow, rarity)
PILOT rows: (id, name, suit, helmet, visor, accent, decal, rarity)
rarity: C common, R rare, E epic, L legendary.  Colours are 0xRRGGBB.
metal / rough: None leaves the factory paint's own finish.  patterns: camo digital tiger stripes checker hex dots
wave flame splinter rainbow (None = plain tint)."""

PRICE = {'C': 600, 'R': 1500, 'E': 3500, 'L': 8000}
RARITY = {'C': 'Gyakori', 'R': 'Ritka', 'E': 'Epikus', 'L': 'Legendás'}

N = None
AIR = [
    # --- terep
    ('woodland', 'Erdei terep', 0x9fb08a, 'camo', 0x4a5a38, N, N, 0x000000, 'C'),
    ('sandcamo', 'Sivatagi terep', 0xe6cf9f, 'camo', 0xb08a54, N, N, 0x000000, 'C'),
    ('snowcamo', 'Hó terep', 0xf4f6f8, 'camo', 0x9aa6b2, N, 0.5, 0x101418, 'C'),
    ('urban', 'Városi szürke terep', 0xb9bcc0, 'digital', 0x6c7076, N, N, 0x000000, 'C'),
    ('digigrey', 'Digitális szürke', 0xc4c7cc, 'digital', 0x8d939b, N, N, 0x000000, 'C'),
    ('tigerstripe', 'Tigriscsík', 0xd9b374, 'tiger', 0x3b2a14, N, N, 0x000000, 'R'),
    ('savanna', 'Szavanna', 0xe0c58a, 'camo', 0x7a8a4a, N, N, 0x000000, 'C'),
    ('jungle', 'Dzsungel', 0x7fa072, 'splinter', 0x22381c, N, N, 0x000000, 'C'),
    ('splintergrey', 'Szilánk terep', 0xa8aeb2, 'splinter', 0x3a4046, N, N, 0x000000, 'R'),
    ('alpine', 'Alpesi', 0x98a6b6, 'camo', 0xe8eef4, N, 0.45, 0x050810, 'R'),
    # --- fémek
    ('rosegold', 'Rózsaarany', 0xf0b5a0, N, 0, 0.9, 0.25, 0x2a1008, 'E'),
    ('titanium', 'Titán', 0xb5bcc4, N, 0, 0.95, 0.3, 0x080a0c, 'R'),
    ('gunmetal', 'Ágyúfém', 0x6b7078, N, 0, 0.9, 0.3, 0x000000, 'R'),
    ('copper', 'Réz', 0xd98a5a, N, 0, 0.9, 0.28, 0x240c02, 'R'),
    ('bronze', 'Bronz', 0xc79a52, N, 0, 0.85, 0.35, 0x1c1204, 'R'),
    ('platinum', 'Platina', 0xe6e9ee, N, 0, 1.0, 0.15, 0x101216, 'E'),
    ('obsidian', 'Obszidián', 0x2a2c33, N, 0, 0.8, 0.1, 0x000000, 'E'),
    ('pearl', 'Gyöngyház', 0xf5eee8, N, 0, 0.6, 0.2, 0x201c1e, 'R'),
    ('mirror', 'Tükör', 0xffffff, N, 0, 1.0, 0.02, 0x101010, 'L'),
    ('blackchrome', 'Fekete króm', 0x4a4d55, N, 0, 1.0, 0.08, 0x000000, 'L'),
    # --- neon
    ('neoncyan', 'Neon ciánkék', 0x5fe8ff, N, 0, N, 0.4, 0x0a4a58, 'R'),
    ('neonmagenta', 'Neon magenta', 0xff5fd2, N, 0, N, 0.4, 0x58104a, 'R'),
    ('neonlime', 'Neon lime', 0xb6ff4a, N, 0, N, 0.4, 0x30580a, 'R'),
    ('neonorange', 'Neon narancs', 0xff9a3a, N, 0, N, 0.4, 0x582a04, 'R'),
    ('neonviolet', 'Neon ibolya', 0x9a6bff, N, 0, N, 0.4, 0x24105a, 'R'),
    ('neonpink', 'Neon rózsaszín', 0xff8fb8, N, 0, N, 0.4, 0x58182c, 'R'),
    ('neonyellow', 'Neon sárga', 0xfff04a, N, 0, N, 0.4, 0x585004, 'R'),
    ('neonaqua', 'Neon akvamarin', 0x4affd2, N, 0, N, 0.4, 0x045844, 'R'),
    ('neonred', 'Neon vörös', 0xff4a4a, N, 0, N, 0.4, 0x580808, 'R'),
    ('ultraviolet', 'Ultraibolya', 0x6a3aff, 'stripes', 0xc9b0ff, N, 0.35, 0x1c0c5a, 'E'),
    # --- mintás
    ('zebra', 'Zebra', 0xf2f2f2, 'stripes', 0x16171a, N, 0.5, 0x000000, 'R'),
    ('checkered', 'Sakktábla', 0xf0f0f0, 'checker', 0x1a1a1e, N, 0.4, 0x000000, 'R'),
    ('honeycomb', 'Méhsejt', 0xf0c040, 'hex', 0x3a2a08, N, 0.4, 0x241a00, 'R'),
    ('polka', 'Pöttyös', 0xf06a8a, 'dots', 0xfff0f4, N, 0.5, 0x2a0812, 'C'),
    ('waves', 'Hullám', 0x4a8ad8, 'wave', 0xd8ecff, N, 0.35, 0x040c1c, 'C'),
    ('flames', 'Lángnyelv', 0x2a2a30, 'flame', 0xff7a1a, 0.4, 0.4, 0x1c0a00, 'E'),
    ('racing', 'Versenycsík', 0xf2f2f2, 'stripes', 0xd02020, N, 0.35, 0x000000, 'C'),
    ('cheetah', 'Gepárd', 0xe8c070, 'dots', 0x3a2a12, N, N, 0x000000, 'R'),
    ('bluetiger', 'Kék tigris', 0x3a7ad0, 'tiger', 0x0a1c3a, N, 0.4, 0x040a18, 'E'),
    ('retro80', 'Retró 80-as', 0xff6ad0, 'stripes', 0x40e0ff, N, 0.4, 0x2a1030, 'E'),
    # --- állatok
    ('dragon', 'Sárkány', 0x3a8a4a, 'hex', 0x0c2a12, 0.3, 0.4, 0x041a08, 'E'),
    ('shark', 'Cápa', 0x8a9eb0, 'wave', 0xeaf2f8, N, 0.45, 0x040810, 'R'),
    ('wasp', 'Darázs', 0xf2c418, 'stripes', 0x16140c, N, 0.4, 0x2a2200, 'R'),
    ('cobra', 'Kobra', 0x4a5a2a, 'hex', 0xd8c85a, N, 0.45, 0x0c1004, 'R'),
    ('viperskin', 'Vipera', 0x2a4a3a, 'tiger', 0xa8e0a0, N, 0.4, 0x061a10, 'R'),
    ('falcon', 'Sólyom', 0x8a6a4a, 'camo', 0xe8dcc0, N, 0.5, 0x000000, 'C'),
    ('wolf', 'Farkas', 0x8a9098, 'splinter', 0x2a2e34, N, 0.55, 0x000000, 'C'),
    ('scorpion', 'Skorpió', 0x8a5a2a, 'hex', 0x1a0e04, N, 0.4, 0x1c0e00, 'R'),
    ('phoenix', 'Főnix', 0xe8501a, 'flame', 0xffd040, 0.3, 0.35, 0x3a1000, 'L'),
    ('panther', 'Párduc', 0x1c1c22, 'dots', 0x3a3a46, 0.5, 0.3, 0x000000, 'E'),
    # --- évszakok, ünnepek
    ('halloween', 'Halloween', 0xf08a1a, 'stripes', 0x1a1020, N, 0.45, 0x2a1000, 'R'),
    ('xmas', 'Karácsony', 0xd02828, 'dots', 0xf4f4f4, N, 0.4, 0x2a0404, 'R'),
    ('easter', 'Húsvét', 0xf0d8f0, 'dots', 0x90d8a0, N, 0.5, 0x1a1020, 'C'),
    ('valentine', 'Valentin', 0xff7a9a, 'dots', 0xffffff, N, 0.45, 0x2a0c14, 'C'),
    ('summer', 'Nyár', 0xffd84a, 'wave', 0x30b8e8, N, 0.45, 0x2a2000, 'C'),
    ('autumn', 'Ősz', 0xc8742a, 'camo', 0x6a2a0a, N, 0.6, 0x120800, 'C'),
    ('spring', 'Tavasz', 0xa8e08a, 'dots', 0xfff088, N, 0.5, 0x0c1a08, 'C'),
    ('winter', 'Tél', 0xdceaf8, 'hex', 0x8ab8e8, N, 0.3, 0x0c1424, 'R'),
    ('harvest', 'Szüret', 0x8a2a5a, 'camo', 0xd8b84a, N, 0.55, 0x120408, 'C'),
    ('newyear', 'Szilveszter', 0x1a1a2a, 'dots', 0xffd860, 0.8, 0.2, 0x1c1808, 'E'),
    # --- zászlók színei
    ('flaghu', 'Magyar trikolór', 0xd03a3a, 'stripes', 0x2a8a4a, N, 0.4, 0x180404, 'R'),
    ('flagse', 'Svéd kék-sárga', 0x2a5aa8, 'stripes', 0xf0c820, N, 0.4, 0x040a1c, 'R'),
    ('flagpl', 'Lengyel fehér-piros', 0xf4f4f4, 'stripes', 0xd02a3a, N, 0.4, 0x000000, 'R'),
    ('flagfr', 'Francia kék-fehér-piros', 0x2a4aa0, 'stripes', 0xd83a3a, N, 0.4, 0x040818, 'R'),
    ('flagde', 'Német fekete-piros-arany', 0x1c1c20, 'stripes', 0xe0b020, N, 0.4, 0x100404, 'R'),
    ('flagit', 'Olasz zöld-fehér-piros', 0x3a9a4a, 'stripes', 0xd83a3a, N, 0.4, 0x040c04, 'R'),
    ('flaguk', 'Brit kék-piros', 0x1c2a60, 'stripes', 0xd8283a, N, 0.4, 0x040818, 'R'),
    ('flagjp', 'Japán fehér-piros', 0xf4f4f4, 'dots', 0xd8202a, N, 0.4, 0x000000, 'R'),
    ('flagca', 'Kanadai piros-fehér', 0xd8282a, 'stripes', 0xf4f4f4, N, 0.4, 0x180404, 'R'),
    ('flagch', 'Svájci piros-fehér', 0xe02020, 'checker', 0xf8f8f8, N, 0.4, 0x180404, 'R'),
    # --- sci-fi
    ('cyberpunk', 'Cyberpunk', 0x1c1030, 'stripes', 0xff3ad0, 0.5, 0.25, 0x30104a, 'E'),
    ('matrix', 'Mátrix', 0x0c2a14, 'digital', 0x40ff70, N, 0.5, 0x04301a, 'E'),
    ('stealth', 'Lopakodó', 0x2e3036, N, 0, 0.1, 0.9, 0x000000, 'R'),
    ('ghost', 'Szellem', 0xdfe6ec, 'camo', 0xb8c4d0, N, 0.9, 0x2a3036, 'R'),
    ('void', 'Üresség', 0x080810, 'hex', 0x5a2aa8, 0.6, 0.2, 0x10042a, 'E'),
    ('plasma', 'Plazma', 0x8a40ff, 'wave', 0x40e0ff, 0.3, 0.3, 0x2a0a5a, 'E'),
    ('nebula', 'Köd', 0x3a2a7a, 'camo', 0xff7ac8, N, 0.4, 0x1a0c3a, 'E'),
    ('galaxy', 'Galaxis', 0x101030, 'dots', 0xffffff, 0.4, 0.3, 0x080830, 'E'),
    ('hologram', 'Hologram', 0x9ae8ff, 'stripes', 0xff9ae8, 0.7, 0.1, 0x2a4a58, 'L'),
    ('toxic', 'Toxikus', 0x7aff3a, 'hex', 0x18340a, N, 0.4, 0x24580a, 'E'),
    # --- századjelek, bemutató csapatok
    ('aggrblue', 'Agresszor kék', 0x6a8ab0, 'camo', 0x3a5a80, N, N, 0x000000, 'R'),
    ('aggrgrey', 'Agresszor szürke', 0x9aa0a8, 'splinter', 0x5a6068, N, N, 0x000000, 'R'),
    ('display', 'Bemutató piros-fehér', 0xf4f4f4, 'stripes', 0xd02828, N, 0.35, 0x000000, 'R'),
    ('bluegold', 'Kék-arany bemutató', 0x1c3a8a, 'stripes', 0xe8c030, 0.3, 0.3, 0x040a1c, 'E'),
    ('redarrow', 'Vörös nyíl', 0xd02828, 'wave', 0xf4f4f4, N, 0.3, 0x180404, 'R'),
    ('silvereagle', 'Ezüst sas', 0xc8ccd2, 'stripes', 0x6a7078, 0.8, 0.25, 0x0c0e10, 'E'),
    ('blackbird', 'Fekete madár', 0x1a1a1e, 'stripes', 0x3a3a40, 0.4, 0.35, 0x000000, 'R'),
    ('skyblue', 'Égkék', 0x78b0e8, 'wave', 0xf0f8ff, N, 0.4, 0x040c1c, 'C'),
    ('sandstorm', 'Homokvihar', 0xd8b078, 'wave', 0xf0dca8, N, 0.6, 0x120c04, 'C'),
    ('navyghost', 'Tengerész szellem', 0x5a6a80, 'camo', 0x2a3444, N, 0.55, 0x000000, 'C'),
    # --- ultra ritka
    ('rainbow', 'Szivárvány', 0xffffff, 'rainbow', 0xffffff, 0.3, 0.3, 0x181818, 'L'),
    ('lava', 'Láva', 0x2a1008, 'flame', 0xff5a0a, 0.2, 0.5, 0x3a1200, 'L'),
    ('ice', 'Jég', 0xbfe8ff, 'hex', 0xffffff, 0.5, 0.08, 0x102030, 'E'),
    ('diamond', 'Gyémánt', 0xe8f6ff, 'hex', 0xa8d8ff, 1.0, 0.03, 0x203040, 'L'),
    ('candy', 'Cukorka', 0xff9ad0, 'stripes', 0xfff4a0, N, 0.3, 0x2a1020, 'E'),
    ('glitch', 'Glitch', 0x20e0a0, 'digital', 0xff2a8a, N, 0.4, 0x082a20, 'E'),
    ('sunset', 'Naplemente', 0xff7a3a, 'wave', 0xffd060, N, 0.35, 0x3a1000, 'E'),
    ('ocean', 'Óceán', 0x0a4a9a, 'wave', 0x40d0ff, 0.2, 0.2, 0x04183a, 'E'),
    ('aurora', 'Sarki fény', 0x2a1a5a, 'wave', 0x40ffb0, 0.4, 0.3, 0x0a3a30, 'L'),
    ('goldendragon', 'Arany sárkány', 0xf0c860, 'hex', 0xa03010, 1.0, 0.18, 0x3a2400, 'L'),
]

# The pilot's flight outfits: ten, each one drawn in detail.  The visor is real glass: its tint (visor, a colour) and
# its transmission (visorT, 1 = clear glass, 0.3 = dark) darken and colour what you see from the cockpit; mirror = a
# reflective coating.  pattern: the livery of the helmet (stripes chevron camo wolf circuit tricolor trim).
# Paint schemes that exist on real aircraft (approximated by tint + pattern: the units' badges cannot be drawn).
# REAL rows: (id, name, jets, tint, pattern, pattern colour, second pattern colour, metal, rough, glow, rarity, note)
# jets: the models (Config.JetModels keys) the scheme is worn on; on any other jet the factory paint stays.
REAL = [
    ('thunderbirds', 'USAF Thunderbirds', ['f16'], 0xf2f4f6, 'tricolor', 0xc8102e, 0x1c3f94, N, 0.35, 0x000000, 'E', 'az amerikai légierő műrepülő csapata: fehér gép, piros-kék sávok'),
    ('blueangels', 'US Navy Blue Angels', ['fa18'], 0x0b2d7a, 'tricolor', 0xffcb05, 0x0b2d7a, N, 0.3, 0x000000, 'E', 'az amerikai haditengerészet műrepülő csapata: kék gép, sárga díszítéssel'),
    ('soloturk', 'SoloTürk', ['f16'], 0xd62828, 'tricolor', 0xffffff, 0xd62828, N, 0.35, 0x000000, 'E', 'a török légierő bemutató F-16-osa: piros-fehér, félholddal'),
    ('flanker64', '64th Aggressor "Flanker"', ['f16'], 0x9fb0c2, 'splinter', 0x4f6785, 0, N, N, 0x000000, 'R', 'az amerikai ellenfél-gyakorló század kék-szürke szilánkterepe (a Szu-27-et utánozza)'),
    ('jasdf_aggr', 'JASDF Aggressor', ['f15'], 0xa4aebb, 'splinter', 0x4a5d73, 0, N, N, 0x000000, 'R', 'a japán légierő ellenfél-gyakorló F-15-ösének szilánkterepe'),
    ('strizhi', 'Strizhi (Sarlósfecskék)', ['mig29'], 0xf2f6fa, 'tricolor', 0x1d5fc2, 0xd02020, N, 0.4, 0x000000, 'E', 'az orosz MiG-29-es műrepülő csapat fehér-kék-piros festése'),
    ('russianknights', 'Russian Knights (Orosz Vitézek)', ['su35'], 0xeef3f8, 'tricolor', 0x2e6fd1, 0x9cc4f0, N, 0.4, 0x000000, 'E', 'az orosz Szu-27-es család műrepülő csapatának fehér-kék festése'),
    ('pl_pixel', 'Lengyel digitális terep', ['mig29'], 0xaab3b8, 'digital', 0x5c7080, 0, N, N, 0x000000, 'R', 'a lengyel légierő MiG-29-eseinek "pixel" álcája'),
    ('ua_pixel', 'Ukrán digitális terep', ['mig29'], 0x9aa6ad, 'digital', 0x4d5f6a, 0, N, N, 0x000000, 'R', 'az ukrán légierő MiG-29-eseinek szürke-kék digitális álcája'),
    ('ghost', 'USAF "Compass Ghost"', ['f16', 'f15'], 0xaab1b8, N, 0, 0, N, 0.55, 0x000000, 'C', 'a légierő világosszürke, alacsony láthatóságú festése (F-15, F-16)'),
    ('asb', 'Air Superiority Blue', ['f15'], 0x7f9ab4, N, 0, 0, N, 0.5, 0x000000, 'C', 'az F-15C klasszikus "légifölény-kék" festése'),
    ('gunship', 'Gunship Gray', ['f35', 'f22'], 0x7c8085, N, 0, 0, N, 0.6, 0x000000, 'C', 'az F-22 és az F-35 sötétszürke, lopakodó festése'),
    ('navylowvis', 'US Navy alacsony láthatóságú szürke', ['fa18'], 0x8a8f94, N, 0, 0, N, 0.55, 0x000000, 'C', 'a Super Hornet hordozós szürke festése'),
    ('jollyrogers', 'VFA-103 "Jolly Rogers"', ['fa18'], 0x3d4046, 'tricolor', 0xf2f2f2, 0x3d4046, N, 0.4, 0x000000, 'R', 'a haditengerészet híres fekete-fehér "kalóz" százada'),
    ('nasa_t38', 'NASA T-38', ['t38'], 0xf5f7f8, 'tricolor', 0x1550a8, 0xf5f7f8, N, 0.35, 0x000000, 'R', 'a NASA űrhajósainak fehér-kék T-38-asa'),
    ('navy_t45', 'US Navy T-45 oktató', ['t45'], 0xf6f4ee, 'tricolor', 0xea5a14, 0xf6f4ee, N, 0.4, 0x000000, 'R', 'a haditengerészeti kiképző gép fehér-narancs festése'),
]

PILOT = [
    dict(id='alpha', name='Alfa ász', rarity='C', desc='A légierő alap repülőruhája: olajzöld overall, fehér sisak sárga csíkkal, tiszta napellenző – a legjobb kilátás.',
         suit=0x56603f, suit2=0x3c442c, helmet=0xe8e8e2, helmet2=0xe8c030, pattern='stripes', visor=0xe8f0f4, visorT=0.97, mirror=False, accent=0xe8c030, glove=0x3a3d33, callsign='ALPHA', patch='unit'),
    dict(id='navy', name='Tengerész', rarity='R', desc='Haditengerészeti sötétkék ruha, fehér sisak kék V-jelekkel, füstszürke napellenző: kellemes, nyugodt kilátás.',
         suit=0x3d4c66, suit2=0x232c3d, helmet=0xf2f2f2, helmet2=0x1f4fa8, pattern='chevron', visor=0x6e727a, visorT=0.45, mirror=False, accent=0xd8b040, glove=0x232a38, callsign='HORNET', patch='anchor'),
    dict(id='desert', name='Sivatagi sólyom', rarity='R', desc='Homokszínű ruha, sivatagi terepmintás sisak, borostyánsárga napellenző: a napfényben kontrasztos, meleg kilátás.',
         suit=0xb59a6a, suit2=0x8a7248, helmet=0xcdb98a, helmet2=0x7a6232, pattern='camo', visor=0xd9a441, visorT=0.55, mirror=False, accent=0x6b4a1e, glove=0x5a4a2c, callsign='SAND', patch='unit'),
    dict(id='arctic', name='Sarki farkas', rarity='R', desc='Fehér-szürke téli ruha, szögletes farkas-csíkos sisak, kék tükörbevonatú napellenző: erős fényben is hűvös, éles kép.',
         suit=0xdfe5ea, suit2=0x9fb0c0, helmet=0xf4f8fb, helmet2=0x6a8cb0, pattern='wolf', visor=0x4a78c8, visorT=0.3, mirror=True, accent=0x2a5ab0, glove=0x6c7a88, callsign='WOLF', patch='unit'),
    dict(id='night', name='Éjszakai vadász', rarity='E', desc='Fekete ruha, matt fekete sisak vörös áramköri csíkokkal, zöld éjjellátó-üveg: sötétben tiszta, de zöld a világ.',
         suit=0x1b1d21, suit2=0x2c2f35, helmet=0x16181b, helmet2=0xc8281e, pattern='circuit', visor=0x2e9a48, visorT=0.38, mirror=False, accent=0xc8281e, glove=0x101113, callsign='GHOST', patch='skull'),
    dict(id='baron', name='Vörös báró', rarity='E', desc='Sötétvörös ruha, vörös sisak fehér csíkkal, réz színű polarizált üveg: a fényes felhők fölött csökkenti a vakítást.',
         suit=0x8a2a24, suit2=0x4a1410, helmet=0xb83026, helmet2=0xf4f0e8, pattern='stripes', visor=0xc87a28, visorT=0.5, mirror=False, accent=0xf4f0e8, glove=0x2a1210, callsign='BARON', patch='cross'),
    dict(id='commander', name='Arany parancsnok', rarity='L', desc='Éjkék ruha arany zsinórral, hófehér sisak arany peremmel és csillaggal, arany tükörüveg: nagyon sötét, nagyon elegáns.',
         suit=0x1d2a4a, suit2=0x0f1730, helmet=0xf8f4e8, helmet2=0xd4a832, pattern='trim', visor=0xd9b24a, visorT=0.28, mirror=True, accent=0xd4a832, glove=0x14182a, callsign='COMMAND', patch='star'),
    dict(id='cyber', name='Nexus', rarity='E', desc='Sötétszürke ruha ciánkék LED-csíkokkal, fényes sisak áramköri mintával, ciánkék kijelző-üveg: hideg, jövőbeli kilátás.',
         suit=0x24282e, suit2=0x3b424b, helmet=0x2b3139, helmet2=0x38e6ff, pattern='circuit', visor=0x38d2ff, visorT=0.55, mirror=False, accent=0x38e6ff, glove=0x15181c, callsign='NEXUS', patch='unit'),
    dict(id='hu', name='Magyar sas', rarity='R', desc='Zöld ruha piros-fehér-zöld szegéllyel, fehér sisak nemzeti csíkkal, rézszínű polarizált üveg.',
         suit=0x40603f, suit2=0x2a402b, helmet=0xf4f4f0, helmet2=0xcd2a3e, pattern='tricolor', visor=0xb8742f, visorT=0.5, mirror=False, accent=0xcd2a3e, glove=0x24301f, callsign='SAS', patch='flag-hu'),
    dict(id='orbit', name='Magaslati pilóta', rarity='L', desc='Fehér nyomásálló ruha, kupolás fehér sisak narancs részletekkel, arany napellenzővel: a legmagasabb szintű védelem és a legsötétebb arany kilátás.',
         suit=0xf0f0ee, suit2=0xd0d4d8, helmet=0xf8f8f8, helmet2=0xe86a1a, pattern='trim', visor=0xdcb64a, visorT=0.35, mirror=True, accent=0xe86a1a, glove=0xc8ccd0, callsign='ORBIT', patch='unit', pressure=True),
]
