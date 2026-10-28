--!nonstrict
-- Playing together: the port of the idea of web/js/net.js (every player flies their own jet in their own simulation and sees the others as
-- "ghost" aircraft that follow the packets they send) extended to a room of up to 20 players and a shared enemy:
--   * every player is the authority of their own jet (position, damage, death),
--   * in a co-op room the room's host runs the enemy AI and sends its state; the others see the enemies as ghosts,
--   * guns: the shooter finds the hit and tells the victim's machine how much damage ("dmg"); missiles: the launch is sent ("launch") and
--     every machine flies its own copy of the missile, but only the one that hits its own jet / its own AI hurts it,
--   * kills are announced to everybody ("kill").
-- The session knows nothing about Roblox: bus = { send(msg), clock() -> seconds, userId, name, team ("blue" / "red"), isHost() -> bool }.
-- Common subset of Lua 5.4 and Luau.
local M = require(script.Parent.Parent.sim.SimMath)
local Sim = require(script.Parent.Parent.sim.Sim)
local Weapons = require(script.Parent.Parent.sim.Weapons)
local Specs = require(script.Parent.Parent.sim.Specs)
local V, copy = M.V, M.copy
local exp, floor, sqrt = math.exp, math.floor, math.sqrt

local N = {}

local function r1(x) return floor(x * 10 + 0.5) / 10 end
local function r3(x) return floor(x * 1000 + 0.5) / 1000 end

-- the jet's state as a packet (positions to the decimetre, the rest rounded)
function N.snapshot(ac)
	local p, v, q, c = ac.pos, ac.vel, ac.quat, ac.controls
	return {
		t = "s", p = { r1(p.x), r1(p.y), r1(p.z) }, v = { floor(v.x + 0.5), floor(v.y + 0.5), floor(v.z + 0.5) },
		q = { r3(q.x), r3(q.y), r3(q.z), r3(q.w) }, c = { r3(c.pitch), r3(c.roll), r3(c.yaw) }, e = r3(ac.fm.engine), g = ac.fm.gearDown and 1 or 0,
		hp = floor(ac.hp), al = ac.alive and 1 or 0, bn = ac.burning and 1 or 0, cr = ac.crashed and 1 or 0, gn = (ac.gun.firing and ac.alive) and 1 or 0,
		ej = ac.ejected and 1 or 0, fl = ac.flares, ld = N.loadedMask(ac),
	}
end

-- which stations still hold a missile: "1011" (in the order of ac.stations) - the rear seat's copy of the jet needs it
function N.loadedMask(ac)
	local t = {}
	for i, st in ipairs(ac.stations) do t[i] = (st.loaded and not st.launch) and "1" or "0" end
	return table.concat(t)
end

-- ------------------------------------------------------------------ the ghost's pilot
local Ghost = {}
Ghost.__index = Ghost
local function newGhostPilot(ac, clock)
	local self = setmetatable({}, Ghost)
	self.ac, self.clock, self.fresh = ac, clock, true
	self.target = M.Q()
	self.snap = nil
	ac.pilot, ac.ghost = self, true
	return self
end
function Ghost:receive(s)
	local q = s.q
	self.target.x, self.target.y, self.target.z, self.target.w = q[1], q[2], q[3], q[4]
	self.snap = { p = s.p, v = s.v, c = s.c, e = s.e, g = s.g, at = self.clock() }
	if self.ac.slave then N.applyExtras(self.ac, s) end
end
function Ghost:think() end
function Ghost:fly(dt)
	local s, ac = self.snap, self.ac
	if not s then return end
	local fm = ac.fm
	local age = math.min(self.clock() - s.at, 0.4)
	local tx, ty, tz = s.p[1] + s.v[1] * age, s.p[2] + s.v[2] * age, s.p[3] + s.v[3] * age
	local dx, dy, dz = tx - fm.pos.x, ty - fm.pos.y, tz - fm.pos.z
	local far = sqrt(dx * dx + dy * dy + dz * dz) > 300
	local k = (self.fresh or far) and 1 or 1 - exp(-dt * 12)
	fm.pos.x, fm.pos.y, fm.pos.z = fm.pos.x + dx * k, fm.pos.y + dy * k, fm.pos.z + dz * k
	-- the attitude: a normalised linear blend towards the packet's quaternion (the short way round)
	local q, t = fm.quat, self.target
	local d = q.x * t.x + q.y * t.y + q.z * t.z + q.w * t.w
	local sg = d < 0 and -1 or 1
	q.x, q.y, q.z, q.w = q.x + (t.x * sg - q.x) * k, q.y + (t.y * sg - q.y) * k, q.z + (t.z * sg - q.z) * k, q.w + (t.w * sg - q.w) * k
	q:normalize()
	fm.vel.x, fm.vel.y, fm.vel.z = s.v[1], s.v[2], s.v[3]
	fm.engine = s.e
	ac.controls.pitch, ac.controls.roll, ac.controls.yaw, ac.controls.throttle = s.c[1], s.c[2], s.c[3], s.e
	fm.gearDown, fm.gearPos, fm.onGround = s.g == 1, s.g == 1 and 1 or 0, false
	self.fresh = false
end
N.GhostPilot = Ghost

-- the rear seat's copy of the pilot's jet: follows the packets like a ghost, but its sensors run and nothing can hurt it here
function N.applyExtras(ac, s)
	if s.fl then ac.flares = s.fl end
	if s.ld then
		for i, st in ipairs(ac.stations) do
			if st.loaded and string.sub(s.ld, i, i) == "0" then st.loaded = false end
			if not st.loaded and string.sub(s.ld, i, i) == "1" then st.loaded = true end
		end
		ac:updateStores()
		if ac.selected and ac:missileCount(ac.selected) == 0 then ac:afterLaunch() end
	end
end
function N.makeSlave(ac, clock)
	newGhostPilot(ac, clock)
	ac.slave = true
	ac.takeDamage = function() end
	ac.kill = function() end
	ac.crash = function() end
	return ac
end

local function specOf(key)
	return Specs.AIRCRAFT[key] or Specs.TRAINERS[key] or Specs.BANDITS[key]
end

local function isGunWeapon(w)
	return w ~= nil and Specs.WEAPON_CLASS[w] == nil and w ~= "crash" and w ~= "tailstrike" and w ~= "AIM-9M" and w ~= "AIM-120A"
end

-- ------------------------------------------------------------------ the session
local Session = {}
Session.__index = Session

-- match: the Match (its world, player and state are read all the time: a new world replaces the old one after a restart)
function N.new(match, bus)
	local self = setmetatable({}, Session)
	self.match, self.bus = match, bus
	self.wsoOf = match.opts.wsoOf                    -- a number: this machine sits in the rear seat of that player's jet (match.player is its copy)
	self.myId = "u" .. tostring(self.wsoOf or bus.userId)
	self.humans = {}                   -- id -> ghost of another player
	self.enemies = {}                  -- id -> ghost of the host's AI jets (guests only)
	self.local_ = {}                   -- id -> the host's own AI jets (so that messages can name them)
	self.nextEnemy = 1
	self.t = { snap = 0, hello = 0, en = 0, st = 0, need = 0, host = 0, wso = 0 }
	self.pilotSeen, self.pilotGone = bus.clock(), false
	self.wsoUser, self.wsoSeen = nil, 0             -- the pilot's side: who sits in my rear seat
	self.score = { blue = 0, red = 0 }
	self.wasHost = bus.isHost()
	self.hostNow = self.wasHost
	return self
end

function Session:world() return self.match.world end
function Session:clock() return self.bus.clock() end

-- the id of an aircraft in messages
function Session:idOf(ac)
	if not ac then return nil end
	if ac == self.match.player then return self.myId end
	if ac.netId then return ac.netId end
	return nil
end
local function newId(self, ac)
	local id = "e" .. self.nextEnemy
	self.nextEnemy = self.nextEnemy + 1
	ac.netId = id
	self.local_[id] = ac
	return id
end
function Session:byId(id)
	if id == nil then return nil end
	if id == self.myId then return self.match.player end
	return self.humans[id] or self.enemies[id] or self.local_[id]
end

local function dropGhost(self, g)
	g.alive, g.crashed, g.deathTime = false, true, self:world().time - 100
	local keep = {}
	for _, a in ipairs(self:world().aircraft) do if a ~= g then keep[#keep + 1] = a end end
	self:world().aircraft = keep
end

local function makeGhost(self, id, key, name, team, human, skin, outfit)
	local spec = specOf(key)
	if not spec then return nil end
	local w = self:world()
	local g = Sim.newAircraft(spec, name, team, V(0, 0, -5000), 0, 0, { livery = "viper", missiles = Specs.missilesFor(spec, not human), skin = skin, outfit = outfit })
	newGhostPilot(g, function() return self:clock() end)
	g.netId, g.human, g.specKey, g.tag = id, human, key, human and name or nil
	local bus = self.bus
	-- authority is the other machine: my guns tell it, my missiles are copied over there
	g.takeDamage = function(_, amount, source, weapon)
		if source == self.match.player and isGunWeapon(weapon) then bus.send({ t = "dmg", to = id, a = amount, w = weapon }) end
	end
	g.kill = function() end
	w:addAircraft(g)
	return g
end

-- a state packet of a player's jet applied to the copy of it in this world
local function applyState(self, g, m)
	local w = self:world()
	g.pilot:receive(m)
	g.lastSeen = self:clock()
	local wasCrashed = g.crashed
	g.hp, g.burning, g.ejected = m.hp, m.bn == 1, m.ej == 1
	g.gun.firing = m.gn == 1
	if m.al == 1 then g.alive, g.crashed = true, false
	else
		if g.alive then g.alive, g.deathTime = false, w.time end
		if m.cr == 1 and not wasCrashed then
			g.crashed = true
			g.fm.vel = V()
			w:emit("explosion", { pos = copy(g.pos), size = 2.5, ground = true })
		end
	end
end

-- ------------------------------------------------------------------ incoming
function Session:onMessage(from, m)
	local t = m.t
	local id = "u" .. tostring(from)
	local w = self:world()
	if self.wsoOf and id == self.myId then
		-- the pilot whose rear seat this is
		if t == "s" then
			applyState(self, self.match.player, m)
			self.pilotSeen = self:clock()
			return
		elseif t == "bye" then self.pilotGone = true; return
		elseif t == "hello" or t == "need" then return end                 -- (the jet itself is the copy; the rest - enemies, missiles - is as for anybody)
	end
	if t == "wsohello" then
		if m.to == self.bus.userId then
			if self.wsoUser ~= from then self.t.hello = 0 end
			self.wsoUser, self.wsoSeen, self.wsoName, self.wsoOutfit = from, self:clock(), m.n, m.pl
			self.match.wsoName = m.n
		end
		return
	elseif t == "wso" then
		if m.to == self.bus.userId and from == self.wsoUser then
			self.wsoSeen = self:clock()
			self.match:wsoDo(m.a, m.k, self:byId(m.tg), self.wsoName)
		end
		return
	end
	if t == "hello" then
		local g = self.humans[id]
		if g and g.specKey ~= m.a then dropGhost(self, g); self.humans[id] = nil; g = nil end
		if not g then self.humans[id] = makeGhost(self, id, m.a, m.n or "Pilóta", m.tm or "blue", true, m.sk, m.pl) end
		local gg = self.humans[id]
		if gg then
			gg.team, gg.name, gg.tag, gg.skin, gg.outfit = m.tm or "blue", m.n or gg.name, m.n or gg.tag, m.sk, m.pl
			gg.twoSeat, gg.wsoOutfit = m.ts == 1, m.wo
		end
	elseif t == "s" then
		local g = self.humans[id]
		if not g then
			if self:clock() - self.t.need > 1 then
				self.t.need = self:clock()
				self.bus.send({ t = "need" })
			end
			return
		end
		applyState(self, g, m)
	elseif t == "need" then
		self.t.hello = 0                                      -- answer with our hello next step
	elseif t == "bye" then
		local g = self.humans[id]
		if g then dropGhost(self, g); self.humans[id] = nil end
	elseif t == "en" then
		if self.hostNow then return end
		local seen = {}
		for _, e in ipairs(m.list) do
			seen[e.id] = true
			local g = self.enemies[e.id]
			if not g then
				g = makeGhost(self, e.id, e.a, e.n or "Bandita", "red", false)
				self.enemies[e.id] = g
			end
			if g then
				g.pilot:receive(e)
				g.lastSeen = self:clock()
				g.hp, g.burning = e.hp, e.bn == 1
				if e.al == 1 then g.alive, g.crashed = true, false
				elseif g.alive then g.alive, g.deathTime = false, w.time end
				if e.cr == 1 and not g.crashed then
					g.crashed = true
					w:emit("explosion", { pos = copy(g.pos), size = 2.5, ground = true })
				end
			end
		end
	elseif t == "st" then
		if self.hostNow then return end
		local st = self.match.state
		st.wave, st.waveActive = m.wave or st.wave, m.active == true
	elseif t == "launch" then
		local shooter = self:byId(m.s)
		if not shooter or (shooter == self.match.player and not self.wsoOf) then return end
		local spec = shooter.missiles and shooter.missiles[m.k] or Specs.MISSILES[m.k]
		if not spec then return end
		local target = self:byId(m.tg)
		local pos, vel, dir = V(m.p[1], m.p[2], m.p[3]), V(m.v[1], m.v[2], m.v[3]), V(m.d[1], m.d[2], m.d[3])
		local mis = Weapons.newMissile(spec, shooter, pos, vel, dir, w.rnd, target, nil)
		mis.replicated = true
		w:addMissile(mis)
	elseif t == "dmg" then
		local victim = self:byId(m.to)
		local source = self.humans[id]
		if victim and victim.alive and not victim.ghost then victim:takeDamage(m.a, source, m.w, w) end
	elseif t == "kill" then
		local victim, killer = self:byId(m.v), self:byId(m.k)
		if victim and victim ~= self.match.player and not (victim.netId and self.local_[victim.netId]) then
			victim.alive, victim.burning = false, true
			victim.deathTime = victim.deathTime or w.time
			w:emit("kill", { victim = victim, killer = killer, weapon = m.w })
		end
		if self.match:scenario() == "pvp" and victim then
			local team = killer and killer.team or nil
			if team and victim.team ~= team then self.score[team] = self.score[team] + 1 end
		end
	end
end

-- ------------------------------------------------------------------ the frame
local function remove(self, map)
	for id, g in pairs(map) do dropGhost(self, g); map[id] = nil end
end

function Session:step(dt)
	local match, bus, T = self.match, self.bus, self.t
	local now = self:clock()
	local p = match.player
	for k, v in pairs(T) do if k ~= "need" then T[k] = v - dt end end
	-- hosting changes (the host left): the new host takes over the enemies
	local host = bus.isHost()
	if host ~= self.hostNow then
		self.hostNow = host
		if host then remove(self, self.enemies); match:setGuest(false)
		else
			for _, a in ipairs(self:world().aircraft) do
				if a.team == "red" and not a.ghost and not a.human then a.alive, a.crashed, a.deathTime = false, true, self:world().time - 100 end
			end
			self.local_ = {}
			match:setGuest(true)
		end
	end
	if self.wsoOf then
		-- the rear seat: only says it is there; the jet is flown (and the packets come) from the pilot's machine
		if T.wso <= 0 then
			T.wso = 2
			bus.send({ t = "wsohello", to = self.wsoOf, n = bus.name, pl = bus.outfit })
		end
		for id, g in pairs(self.humans) do
			if g.lastSeen and now - g.lastSeen > 6 then dropGhost(self, g); self.humans[id] = nil end
		end
		for id, g in pairs(self.enemies) do
			if g.lastSeen and now - g.lastSeen > 1.5 then dropGhost(self, g); self.enemies[id] = nil end
		end
		if now - self.pilotSeen > 8 then self.pilotGone = true end
		return
	end
	if self.wsoUser and now - self.wsoSeen > 6 then
		self.wsoUser, self.wsoName, self.wsoOutfit, match.wsoName = nil, nil, nil, nil
		T.hello = 0
	end
	if T.hello <= 0 and p then
		T.hello = 3
		bus.send({ t = "hello", n = bus.name, a = p.specKey or "f16", tm = bus.team, sk = p.skin, pl = p.outfit,
			ts = p.twoSeat and 1 or 0, wo = self.wsoUser and self.wsoOutfit or nil })
	end
	if T.snap <= 0 and p then
		T.snap = 1 / 15
		bus.send(N.snapshot(p))
	end
	if host then
		if T.en <= 0 then
			T.en = 0.1
			local list = {}
			for _, a in ipairs(self:world().aircraft) do
				if a.team == "red" and not a.ghost and not a.human and (a.alive or not a.crashed) then
					local id = a.netId or newId(self, a)
					local s = N.snapshot(a)
					s.id, s.a, s.n, s.t = id, a.specKey or "f16", a.name, nil
					list[#list + 1] = s
				end
			end
			bus.send({ t = "en", list = list })
		end
		if T.st <= 0 then
			T.st = 1
			bus.send({ t = "st", wave = match.state.wave, active = match.state.waveActive })
		end
	end
	-- ghosts that went quiet
	for id, g in pairs(self.humans) do
		if g.lastSeen and now - g.lastSeen > 6 then dropGhost(self, g); self.humans[id] = nil end
	end
	for id, g in pairs(self.enemies) do
		if g.lastSeen and now - g.lastSeen > 1.5 then dropGhost(self, g); self.enemies[id] = nil end
	end
end

-- the world's events of the frame: what happened to what this machine is the authority of is told to the others
function Session:onEvents(events)
	if self.wsoOf then return end
	local match, bus = self.match, self.bus
	local p = match.player
	for _, e in ipairs(events) do
		local kind, d = e[1], e[2]
		if kind == "launch" then
			local m = d.missile
			local s = m.shooter
			if not m.replicated and s and not s.ghost and (s == p or s == match.wingman or (self.hostNow and s.team == "red")) then
				local sid = self:idOf(s) or (s.team == "red" and newId(self, s)) or nil
				if sid then
					local tg = m.guidedTarget or m.intended
					bus.send({ t = "launch", s = sid, k = (m.spec.guidance == Specs.IR) and "AIM-9M" or "AIM-120A", p = { r1(m.pos.x), r1(m.pos.y), r1(m.pos.z) }, v = { r1(m.vel.x), r1(m.vel.y), r1(m.vel.z) },
						d = { r3(m.dir.x), r3(m.dir.y), r3(m.dir.z) }, tg = tg and self:idOf(tg) or nil })
				end
			end
		elseif kind == "kill" then
			local v, k = d.victim, d.killer
			local mine = v == p or (self.hostNow and v.team == "red" and not v.ghost and not v.human)
			if mine then
				local vid = self:idOf(v) or (v.netId)
				if vid then bus.send({ t = "kill", v = vid, k = self:idOf(k), w = d.weapon }) end
				if match:scenario() == "pvp" and k and v.team ~= k.team then self.score[k.team] = self.score[k.team] + 1 end
			end
		end
	end
end

-- the rear seat gives the pilot's machine an order: a = "fire" (k: AIM-9M / AIM-120A), "flare", "mark"; target: an aircraft of this world
function Session:wsoSend(a, key, target)
	if not self.wsoOf then return end
	self.bus.send({ t = "wso", to = self.wsoOf, a = a, k = key, tg = target and target.netId or nil })
end

function Session:leave()
	if not self.wsoOf then self.bus.send({ t = "bye" }) end
	remove(self, self.humans)
	remove(self, self.enemies)
end

return N
