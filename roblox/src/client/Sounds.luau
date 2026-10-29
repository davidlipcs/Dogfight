--!nonstrict
-- The sounds of the game: the port of Sounds of web/js/audio.js.  The browser makes them from formulas; here they are one sound sheet
-- (roblox/audio/dogfight_sounds.wav, rendered from the same formulas by tools/make_roblox_sounds.py) that is uploaded to Roblox once;
-- every sound is a region of it (shared/SoundMap.luau).  Without an asset id (Config.SoundId or the attribute SoundAssetId of
-- ReplicatedStorage) the game is silent.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local SoundService = game:GetService("SoundService")
local ContentProvider = game:GetService("ContentProvider")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Map = require(Shared.SoundMap)
local SimMath = require(Shared.sim.SimMath)
local Specs = require(Shared.sim.Specs)

local len, sub, dot, norm = SimMath.len, SimMath.sub, SimMath.dot, SimMath.norm

local Sounds = {}
Sounds.__index = Sounds

local function assetId()
	local id = ReplicatedStorage:GetAttribute("SoundAssetId")
	if typeof(id) == "string" and id ~= "" then
		if tonumber(id) then return "rbxassetid://" .. id end
		return id
	end
	if typeof(id) == "number" and id > 0 then return "rbxassetid://" .. tostring(math.floor(id)) end
	if Config.SoundId and Config.SoundId ~= 0 then return "rbxassetid://" .. tostring(Config.SoundId) end
	return nil
end

function Sounds.new(volume)
	local self = setmetatable({}, Sounds)
	self.volume = volume or 0.7
	self.id = assetId()
	self.loops, self.shots = {}, {}
	self.prevSup, self.boomT, self.prevNew = nil, 0, false
	local folder = Instance.new("Folder")
	folder.Name = "DogfightSounds"
	folder.Parent = SoundService
	self.folder = folder
	self.manual = {}
	-- does the sound sheet load?  (a wrong id, a sound that is still being checked by Roblox or one that this place may not use stays silent)
	self.error = nil
	if self.id then
		local probe = Instance.new("Sound")
		probe.Name = "Probe"
		probe.SoundId = self.id
		probe.Volume = 0
		probe.Parent = folder
		task.spawn(function()
			local status = nil
			local ok, err = pcall(function()
				ContentProvider:PreloadAsync({ probe }, function(_, st) status = st end)
			end)
			if not ok then self.error = tostring(err)
			elseif status ~= nil and status ~= Enum.AssetFetchStatus.Success then self.error = tostring(status)
			elseif probe.TimeLength == 0 and not probe.IsLoaded then self.error = "nem töltődött be" end
			if self.error then
				warn("Dogfight Plus: the sound sheet " .. self.id .. " does not load (" .. self.error .. "). Check the id, and that the audio has passed Roblox's review (create.roblox.com > Creations > Audio).")
			end
		end)
	end
	return self
end

local function make(self, name, loop)
	local m = Map[name]
	local s = Instance.new("Sound")
	s.Name = name
	s.SoundId = self.id
	s.Looped = loop
	s.Volume = 0
	local ok = pcall(function()
		s.PlaybackRegionsEnabled = true
		s.PlaybackRegion = NumberRange.new(m.start, m.start + m.length)
		s.LoopRegion = NumberRange.new(m.start, m.start + m.length)
	end)
	if not ok then
		-- no regions: the sound is cut by hand (see step)
		s.Looped = false
		self.manual[s] = { start = m.start, stop = m.start + m.length, loop = loop }
		s.TimePosition = m.start
	end
	s.Parent = self.folder
	return s
end

function Sounds:setVolume(v) self.volume = v end

-- a one-shot (a pool of a few players per sound, so that explosions can overlap)
function Sounds:play(name, volume, rate)
	if not self.id or not Map[name] then return end
	volume, rate = volume or 1, rate or 1
	local pool = self.shots[name]
	if not pool then pool = { i = 0 }; self.shots[name] = pool end
	pool.i = pool.i % 4 + 1
	local s = pool[pool.i]
	if not s then s = make(self, name, false); pool[pool.i] = s end
	s.Volume = volume * self.volume * 2
	s.PlaybackSpeed = rate
	local man = self.manual[s]
	if man then s.TimePosition = man.start end
	s:Play()
end

-- a loop that is on or off, at a volume and a pitch (rate); it fades in and out
function Sounds:loop(name, on, volume, rate)
	if not self.id then return end
	local l = self.loops[name]
	if not l then
		if not on then return end
		l = { s = make(self, name, true), v = 0 }
		self.loops[name] = l
	end
	local target = on and (volume or 1) * self.volume * 2 or 0
	l.target, l.rate = target, rate or 1
	l.on = on
	if on and not l.s.IsPlaying then
		local man = self.manual[l.s]
		if man then l.s.TimePosition = man.start end
		l.s:Play()
	end
end

-- the per-frame smoothing of the loops (and the hand-made cutting)
function Sounds:step(dt)
	local k = math.min(1, dt * 14)
	for name, l in pairs(self.loops) do
		l.v += ((l.target or 0) - l.v) * k
		l.s.Volume = l.v
		if l.rate then l.s.PlaybackSpeed = l.s.PlaybackSpeed + (l.rate - l.s.PlaybackSpeed) * math.min(1, dt * 8) end
		if not l.on and l.v < 0.002 and l.s.IsPlaying then l.s:Pause() end
	end
	for s, m in pairs(self.manual) do
		if s.IsPlaying and s.TimePosition >= m.stop then
			if m.loop then s.TimePosition = m.start else s:Stop() end
		end
	end
end

function Sounds:stopAll()
	for name, l in pairs(self.loops) do self:loop(name, false) end
end

function Sounds:handleEvent(kind, d, player)
	if not self.id or not player then return end
	if kind == "launch" and d.shooter == player then self:play("launch", 0.8)
	elseif kind == "explosion" then
		local dist = len(sub(d.pos, player.pos))
		if dist < 12000 then self:play("explosion", math.max(0.15, 1 - dist / 12000), 0.8 + 0.3 * math.random()) end
	elseif kind == "hit" and (d.target == player or d.shooter == player) then self:play("hit", 0.7)
	elseif kind == "kill" and d.killer == player and d.victim ~= player then self:play("splash", 0.6)
	elseif kind == "medal" then self:play("medal", 0.7) end
end

function Sounds:update(player, paused, world, listener, dt)
	if not self.id then return end
	if dt then self:step(dt) end
	if not player or not player.alive or paused then self:stopAll(); return end
	local e = player.fm.engine
	local e1 = math.min(e, 1)
	self:loop("engine", true, 0.35 + 0.35 * e1, 0.6 + 0.6 * e1)
	self:loop("whine", true, 0.05 + 0.12 * e1, 0.7 + 0.45 * e1)
	self:loop("afterburner", e > 1.0, 0.55)
	self:loop("gun", player.gun.firing, 0.8)
	local sp = player.selectedSpec
	local tone = (sp and sp.guidance == Specs.IR) and player.irSeeker:tone() or "none"
	self:loop("growl", tone == "growl", 0.22)
	self:loop("lock_tone", tone == "lock", 0.25)
	local level = player.rwr.maxLevel
	-- missile warning: the warble speeds up as the nearest missile closes in
	local near = #player.rwr.incoming > 0 and player.rwr.incoming[1].dist or 1e9
	self:loop("rwr_launch", level >= 3, 0.45, 1 + 0.8 * math.max(0, math.min(1, (8000 - near) / 8000)))
	self:loop("rwr_lock", level == 2, 0.3)
	-- wind over the canopy rises with the airspeed, and buffets at a high angle of attack
	local ias = player.fm.ias or 0
	local aoa = math.abs(player.fm.alpha or 0) * 57.3
	local wind = math.min(1, math.max(0, (ias - 50) / 320)) * 0.22 + math.min(1, math.max(0, (aoa - 14) / 16)) * 0.25 * math.min(1, ias / 120)
	self:loop("wind", wind > 0.01, wind, 0.55 + math.min(1, ias / 500) * 0.7)
	-- sonic boom when the player goes through Mach 1 (either way), not more than once every few seconds
	local sup = player.fm.mach >= 1
	local now = os.clock()
	if self.prevSup ~= nil and sup ~= self.prevSup and now - self.boomT > 4 then
		self:play("boom", 0.7)
		self.boomT = now
	end
	self.prevSup = sup
	if world then
		-- other jets passing close: engine roar, pitch shifted by their closing speed (Doppler)
		local ear = listener or player.pos
		local best, bd = nil, 900
		for _, a in ipairs(world.aircraft) do
			if a ~= player and a.alive then
				local d = len(sub(a.pos, ear))
				if d < bd then bd, best = d, a end
			end
		end
		if best then
			local los = norm(sub(best.pos, ear))
			local closing = -dot(sub(best.vel, player.vel), los)
			local k = 1 - bd / 900
			self:loop("flyby", true, 0.75 * k * k * (0.5 + 0.5 * math.min(1, best.engineSetting)), math.max(0.55, math.min(1.7, 1 + closing / 420)))
		else self:loop("flyby", false) end
		-- a missile flying close by
		local md = 500
		for _, m in ipairs(world.missiles) do
			if m.alive and m.shooter ~= player then md = math.min(md, len(sub(m.pos, ear))) end
		end
		self:loop("whoosh", md < 500, 0.6 * (1 - md / 500) ^ 2, 1.4)
	end
	if player.rwr.newSearch and not self.prevNew then self:play("rwr_new", 0.3) end
	self.prevNew = player.rwr.newSearch
end

function Sounds:destroy()
	self.folder:Destroy()
end

return Sounds
