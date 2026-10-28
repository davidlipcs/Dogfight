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

-- the Robux shop: create the Developer Products on the Roblox site (Creator Dashboard > Monetization >
-- Developer Products) and put their ids here.  An id of 0 means "not created yet": the button is hidden.
Config.Products = {
	{ id = 0, coins = 1000, label = "Kis csomag" },
	{ id = 0, coins = 5500, label = "Közepes csomag" },
	{ id = 0, coins = 12000, label = "Nagy csomag" },
	{ id = 0, coins = 30000, label = "Hatalmas csomag" },
}
-- Game Pass (Creator Dashboard > Monetization > Passes): the coins you earn count double
Config.DoubleCoinsPass = 0

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
