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

Config.Gun = { Damage = 7, Range = 1500, Rate = 14, Radius = 13, Heat = 0.045 }
Config.Missile = { Damage = 60, Speed = 520, TurnRate = 1.9, Life = 9, Range = 3200, FuseRadius = 14, Cone = 28 }

Config.World = {
	Half = 6000,          -- the playing field is +-Half studs
	IslandRadius = 1500,
	SpawnRadius = 900,
	SpawnHeight = 450,
	EnemyRing = 3500,     -- the enemy waves come in from this far
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

Config.PvP = false

return Config
