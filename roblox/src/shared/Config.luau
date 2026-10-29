--!nonstrict
-- Everything that can be tuned (economy, weapons, the jet, the Robux shop) in one place.
local Config = {}

Config.DataStoreName = "DogfightPlus_v1"

Config.Coins = {
	Start = 500,          -- a new player's coins
	PerKill = 100,        -- for one enemy jet
	WaveBonus = 150,      -- for clearing a wave (times the wave number, at most 10x)
	Survive = 1,          -- coins per second in the air (a trickle, so a calm minute still pays)
}

-- Money: what a Robux is worth in forints (check the current price in the Roblox shop and change it here) and the
-- most a single skin may cost in real money.  The Robux price of a skin is its rarity's tier, capped by this.
Config.Money = { HufPerRobux = 4.5, MaxSkinHuf = 500 }
local maxRobux = math.floor(Config.Money.MaxSkinHuf / Config.Money.HufPerRobux)     -- 111 Robux = 500 Ft at 4.5 Ft / Robux
Config.SkinRobux = {                    -- Robux price of a skin by rarity (C common, R rare, E epic, L legendary)
	C = math.min(15, maxRobux), R = math.min(35, maxRobux), E = math.min(65, maxRobux), L = math.min(110, maxRobux),
}
-- the skin purchases go through four Developer Products, one per rarity, priced at the Robux amounts above
-- (Creator Dashboard > Monetization > Developer Products).  The skin the player picked is remembered on the server
-- and handed over when the receipt arrives.  An id of 0 = not created yet: the Robux button stays hidden.
Config.SkinProducts = { C = 0, R = 0, E = 0, L = 0 }
Config.TierCoins = { C = 600, R = 1500, E = 3500, L = 8000 }        -- the coin price of the same tiers (the fallback value of a lost purchase)

-- coin packs for Robux (robux = the price you set on the product).  Even the biggest skin (8000 coins) stays under 500 Ft.
Config.Products = {
	{ id = 0, coins = 1500, robux = 20, label = "Kis csomag" },
	{ id = 0, coins = 4000, robux = 50, label = "Közepes csomag" },
	{ id = 0, coins = 9000, robux = 110, label = "Nagy csomag" },
	{ id = 0, coins = 20000, robux = 220, label = "Hatalmas csomag" },
}
-- Game Pass (Creator Dashboard > Monetization > Passes): the coins you earn count double
Config.DoubleCoinsPass = 0

-- the daily reward (a streak: every day in a row pays more, the 7th day the most; a missed day starts again) and the daily missions (three
-- a day, picked from this list; progress comes from the career counters of the match)
Config.Daily = { 200, 300, 400, 500, 700, 900, 1500 }
Config.PremiumBonus = 0.25          -- Roblox Premium members earn this much more coins
Config.Missions = {
	{ id = "kills5", text = "Lőj le 5 ellenséget", stat = "kills", target = 5, reward = 400 },
	{ id = "kills12", text = "Lőj le 12 ellenséget", stat = "kills", target = 12, reward = 900 },
	{ id = "gun3", text = "Lőj le 3 ellenséget gépágyúval", stat = "gunKills", target = 3, reward = 600 },
	{ id = "ir3", text = "Lőj le 3 ellenséget AIM-9M-mel", stat = "irKills", target = 3, reward = 500 },
	{ id = "arh3", text = "Lőj le 3 ellenséget AIM-120A-val", stat = "arhKills", target = 3, reward = 500 },
	{ id = "duel2", text = "Nyerj 2 párbajt", stat = "duelWins", target = 2, reward = 700 },
	{ id = "fly10", text = "Repülj 10 percet", stat = "flightTime", target = 600, reward = 500 },
	{ id = "fly25", text = "Repülj 25 percet", stat = "flightTime", target = 1500, reward = 1000 },
	{ id = "crash2", text = "Csalj 2 ellenséget a földbe (manőverkill)", stat = "crashKills", target = 2, reward = 800 },
}

Config.Rooms = {
	MaxPlayers = 20,      -- the most people in one room (hangar group)
	NameMax = 24,
	PvpKillCoins = 150,
	ScoreToWin = 0,       -- 0: the team fight never ends
}

Config.Jet = {
	Health = 100,
	StallSpeed = 140,     -- studs/s
	CornerSpeed = 330,
	Accel = 180,          -- studs/s^2 at full throttle
	Drag = 0.001247,
	Afterburner = 1.6,    -- thrust multiplier
	PitchRate = 1.35,     -- rad/s at the corner speed
	RollRate = 2.8,
	YawRate = 0.45,
	StartSpeed = 300,
	Missiles = 4,
	MissileReload = 9,    -- seconds per missile
	Flares = 12,
	FlareTime = 1.6,      -- how long a flare burst protects
	FlareCooldown = 0.5,
}

-- The jets of the game (the same .glb models as the browser game, imported into Studio - see roblox/README.md).  length: the
-- real length in metres = studs; a jet that is not imported (not in ReplicatedStorage.JetModels) is built from parts instead.
-- flip: true / false forces the nose direction of an imported model (nil: worked out from the shape).
Config.JetModels = {
	{ key = "f16", name = "F-16C Viper", length = 15.0 },
	{ key = "fa18", name = "F/A-18E Super Hornet", length = 18.3 },
	{ key = "f15", name = "F-15EX Eagle II", length = 19.4 },
	{ key = "f22", name = "F-22A Raptor", length = 18.9 },
	{ key = "f35", name = "F-35A Lightning II", length = 15.7 },
	{ key = "gripen", name = "JAS 39 Gripen", length = 14.1 },
	{ key = "typhoon", name = "Eurofighter Typhoon", length = 15.96 },
	{ key = "rafale", name = "Dassault Rafale", length = 15.3 },
	{ key = "su35", name = "Szu-35", length = 21.9 },
	{ key = "su57", name = "Szu-57", length = 20.1 },
	{ key = "mig29", name = "MiG-29", length = 17.3 },
	{ key = "mig31", name = "MiG-31", length = 22.7 },
	{ key = "j20", name = "J-20", length = 20.3 },
	{ key = "t38", name = "T-38 Talon", length = 14.1 },
	{ key = "t45", name = "T-45 Goshawk", length = 12.0 },
	{ key = "t6", name = "T-6 Texan II", length = 10.2 },
}
-- the match starts only when the island is built under the air base and the jets of the match are imported (the tests switch this off)
Config.RequireIsland, Config.RequireJets = true, true
Config.JetModelFlip = {}                -- e.g. { f16 = true } turns an imported jet round if it flies backwards
Config.EnemyModels = { "su35", "mig29", "typhoon", "su57", "mig31", "rafale", "j20" }   -- the enemies use these when imported

Config.Gun = { Damage = 7, Range = 1500, Rate = 14, Radius = 13, Heat = 0.045 }
Config.Missile = { Damage = 60, Speed = 520, TurnRate = 1.9, Life = 9, Range = 3200, FuseRadius = 14, Cone = 28 }

-- The island is the game's own (IslandBuilder.luau): 1 metre of the game = Island.StudsPerMeter studs, in all three
-- directions (the whole 102.4 km island is 10240 studs across, the highest peak 443 studs).  The aircraft and the missiles are
-- drawn bigger than that scale (Config.Scale), or they would be a stud or two long.
Config.Island = { StudsPerMeter = 0.1, HeightScale = 0.1, Voxel = 4 }

-- The aircraft, the missiles and their effects are drawn this many times bigger than the island's scale (a 15 m jet is 1.5 studs at
-- 0.1 stud per metre): 8 times makes the F-16 12 studs long.  The chase camera and the distances in the HUD keep the true metres.
Config.ModelScale = 8

Config.World = {
	Half = 5120,          -- the playing field is +-Half studs (the whole island: 102.4 km * 0.1)
	SpawnHeight = 520,    -- above the air base
	SpawnRadius = 700,
	EnemyRing = 3300,     -- the enemy waves come in from this far (from the island's middle)
	EnemyAltitude = { 450, 1000 },
}

Config.Enemy = {
	Speed = 310,
	TurnRate = 1.05,      -- rad/s, the player can out-turn them at the corner speed
	GunRange = 700,
	GunDamage = 3,        -- per shot, 5 shots a second while on target
	MissileRange = 2400,
	MissileCooldown = 14,
	FlareChance = 0.25,   -- the chance that an enemy shakes off a missile (once per missile)
	Health = 70,
	WaveBase = 2,         -- wave n has WaveBase + n jets, at most MaxActive at once
	MaxActive = 6,
	WaveDelay = 8,
}

-- the asset id of the uploaded sound sheet (roblox/audio/dogfight_sounds.wav): a number, or leave 0 and set the attribute SoundAssetId of
-- ReplicatedStorage (Properties > Attributes) - see roblox/README.md.  0 = the game is silent.
Config.SoundId = 0

Config.PvP = false

return Config
