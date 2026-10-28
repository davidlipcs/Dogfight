--!nonstrict
-- Career: what the player did over every match, plus the medals - the port of web/js/career.js.  The data is a plain table that
-- the client keeps with the server's profile (Profile.career); onSave(data) is called when it should be stored.
-- Common subset of Lua 5.4 and Luau.
local C = {}

C.ACHIEVEMENTS = {
	{ id = "first", name = "Első győzelem", desc = "Lőj le egy ellenséget" },
	{ id = "guns", name = "Közelharcos", desc = "Lelövés gépágyúval" },
	{ id = "fox2", name = "Fox 2!", desc = "Lelövés AIM-9M hőkövetővel" },
	{ id = "fox3", name = "Fox 3!", desc = "Lelövés AIM-120A-val" },
	{ id = "maneuver", name = "Manőverkill", desc = "Az üldözött ellenség a földbe csapódik" },
	{ id = "ace", name = "Ász", desc = "5 lelövés egyetlen életen belül" },
	{ id = "evade", name = "Kicselezve", desc = "Kerülj ki egy rád kilőtt rakétát" },
	{ id = "cobra", name = "Kobra", desc = "Rázz le egy rakétát Cobra manőverrel (F-16 extrém mód)" },
	{ id = "home", name = "Hazaértem", desc = "Szállj le a bázison, és fegyverezz újra" },
	{ id = "wave5", name = "Kitartó", desc = "Érd el az 5. hullámot" },
	{ id = "stealth", name = "Raptor-vadász", desc = "Lőj le egy F-22A-t" },
	{ id = "duel3", name = "Párbajhős", desc = "Nyerj 3 párbajt egymás után" },
	{ id = "survivor", name = "Túlélő", desc = "Túlélés módban érd el a 4. hullámot" },
	{ id = "veteran", name = "Veterán", desc = "Lelövés Nehéz vagy Ász fokozaton" },
	{ id = "team", name = "Csapatjátékos", desc = "A kísérőd lelő egy ellenséget" },
	{ id = "score5k", name = "Ötezres", desc = "Szerezz 5000 pontot egy játékban" },
	{ id = "trap", name = "Hordozós pilóta", desc = "Szállj le a hordozóra fékezőkötéllel" },
	{ id = "gsuit", name = "Centrifuga", desc = "Bírd ki a 7 G-t a centrifugában" },
	{ id = "wings", name = "Pilótaszárnyak", desc = "Végezd el a pilótaképzést" },
	{ id = "ww3", name = "A szabad világ védője", desc = "Nyerd meg a 3. világháborús hadjáratot" },
}

local function fresh()
	return {
		matches = 0, kills = 0, deaths = 0, gunKills = 0, irKills = 0, arhKills = 0, crashKills = 0, missilesFired = 0,
		flightTime = 0, bestScore = 0, bestWave = 0, bestStreak = 0, bestSurvival = 0, duelWins = 0, perPlane = {}, medals = {},
	}
end

local Career = {}
Career.__index = Career
-- data: the stored table (or nil); onSave(data): store it
function C.new(data, onSave)
	local self = setmetatable({}, Career)
	self.data = fresh()
	if data then
		for k, v in pairs(data) do self.data[k] = v end
	end
	self.data.perPlane = self.data.perPlane or {}
	self.data.medals = self.data.medals or {}
	self.onSave, self.dirty, self.saveTimer = onSave, false, 0
	return self
end
function Career:save()
	self.dirty = false
	if self.onSave then self.onSave(self.data) end
end
function Career:tick(dt)
	self.data.flightTime = self.data.flightTime + dt
	self.saveTimer = self.saveTimer + dt
	if self.saveTimer > 10 then
		self.saveTimer = 0
		self:save()
	end
end
function Career:reset()
	self.data = fresh()
	self:save()
end
function Career:has(id) return self.data.medals[id] ~= nil end
-- returns the achievement when it is new
function Career:award(id)
	if self:has(id) then return nil end
	for _, a in ipairs(C.ACHIEVEMENTS) do
		if a.id == id then
			self.data.medals[id] = os.time()
			self:save()
			return a
		end
	end
	return nil
end
function Career:best(key, value)
	if value > (self.data[key] or 0) then
		self.data[key] = value
		self.dirty = true
	end
end

-- points for a kill: by weapon, times the difficulty, plus a bonus for a streak (kills in one life)
C.DIFF_MULT = { easy = 0.6, normal = 1, hard = 1.5, ace = 2 }
function C.killPoints(weapon, difficulty, streak)
	local base = weapon == "crash" and 120 or weapon == "AIM-9M" and 100 or weapon == "AIM-120A" and 80 or 150
	local streakMult = 1 + math.min(4, math.max(0, streak - 1)) * 0.25
	return math.floor(base * (C.DIFF_MULT[difficulty] or 1) * streakMult + 0.5)
end
function C.isGun(weapon)
	return weapon ~= nil and weapon ~= "AIM-9M" and weapon ~= "AIM-120A" and weapon ~= "crash" and weapon ~= "tailstrike"
end
function C.weaponLabel(weapon)
	if weapon == "crash" then return "MANŐVER" end
	if weapon == "AIM-9M" or weapon == "AIM-120A" then return weapon end
	return "ÁGYÚ"
end
function C.formatTime(s)
	local h, m = math.floor(s / 3600), math.floor((s % 3600) / 60)
	if h > 0 then return h .. " ó " .. m .. " p" end
	return m .. " perc"
end

return C
