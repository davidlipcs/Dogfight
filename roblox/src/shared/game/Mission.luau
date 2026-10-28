--!nonstrict
-- A sortie of the war career: the jets of both sides in the sky of a front, your flight, the radio and the result for the war
-- (Campaign.luau).  The port of web/js/mission.js for the kinds 'sweep' (clear the sky of enemy fighters) and 'cap' (hold the area for
-- the time given).  The air policing (intercept) and the fighter school of the browser career are not in the Roblox version.
--  role: 'wing' (an AI lead flies ahead, you are number two) or 'lead' (you lead, your AI wingman follows your orders)
-- Written in the common subset of Lua 5.4 and Luau, so it is tested outside of Roblox (roblox/tests).
local M = require(script.Parent.Parent.sim.SimMath)
local Sim = require(script.Parent.Parent.sim.Sim)
local AI = require(script.Parent.Parent.sim.AI)
local Specs = require(script.Parent.Parent.sim.Specs)
local V, add, sub, mul, len, norm, clamp, DEG = M.V, M.add, M.sub, M.mul, M.len, M.norm, M.clamp, M.DEG
local atan2, rng = M.atan2, M.rng
local BANDITS = Specs.BANDITS

local Mission = {}
Mission.__index = Mission

local MAX_ACTIVE_RED, REINFORCE_GAP = 4, 90
local function copyVec(v) return V(v.x, v.y, v.z) end

-- m: { kind, role, playerType, blue = { { type, n, power, label } }, red = { { type, n, power } }, skill, minutes, title, front, bearing, callsign }
function Mission.new(g, m)
	local self = setmetatable({}, Mission)
	self.g, self.m = g, m
	self.t, self.over, self.result = 0, false, nil
	self.phase = "ingress"
	self.kills, self.blueLost, self.redLost = {}, {}, {}
	local f = g.terrain.airfield
	local r = rng(math.floor(g.rnd() * 1e9))
	self.rnd = r
	-- the fight: 24 km from the base, on the enemy's side of it
	local bearing = m.bearing or 60 * DEG
	local dir = norm(V(math.sin(bearing), math.cos(bearing), 0))
	local lim = g.terrain.half - 12000
	local P = V(clamp(f.x + dir.x * 24000, -lim, lim), clamp(f.y + dir.y * 24000, -lim, lim), 0)
	self.P = P
	self.dir = norm(sub(P, V(f.x, f.y, 0)), dir)
	self.area = { x = P.x, y = P.y, r = 20000, engage = 36000, safe = g.nav.base }
	g.nav.zone = { x = P.x, y = P.y, r = 20000, engage = 36000 }               -- the HUD's zone mark: the fight
	local p = g.player
	local start = add(P, mul(self.dir, -16000))
	local z = math.max(5000, g.terrain:height(start.x, start.y) + 1800)
	local hdg = atan2(self.dir.x, self.dir.y)
	-- an air start on the way to the fight
	local delta = V(start.x - p.pos.x, start.y - p.pos.y, z - p.pos.z)
	local fm = p.fm
	fm.onGround = false
	fm.pos = V(start.x, start.y, z)
	fm.vel = mul(V(math.sin(hdg), math.cos(hdg), 0), 230)
	fm.quat = M.qheading(hdg / DEG, 0)
	fm.gearDown, fm.gearPos = false, 0
	fm.groundZ = nil
	p.controls.throttle = 0.9
	fm.engine = 0.9
	if g.wingman and g.wingman.alive then
		local w = g.wingman
		w.fm.pos = add(w.fm.pos, delta)
		w.fm.vel = copyVec(fm.vel)
		w.fm.quat = fm.quat:clone()
	end
	if g.env.onTeleport then g.env.onTeleport() end
	g.radio.callsign = m.callsign or "VIPER 1-1"

	local side = V(self.dir.y, -self.dir.x, 0)
	self.side = side
	local function mk(spec, team, pos, heading, name)
		local loadout = (spec.proc or spec.internal or spec.id == "f16") and "default" or Specs.buildLoadout(spec, 2, 4).layout
		local ac = Sim.newAircraft(spec, name, team, pos, heading / DEG, 230,
			{ livery = "viper", missiles = Specs.missilesFor(spec, true), loadout = loadout, rnd = rng(math.floor(r() * 1e9)) })
		ac.specKey = spec.id
		g.world:addAircraft(ac)
		if g.env.onSpawn then g.env.onSpawn(ac, spec) end
		return ac
	end
	self.mk = mk
	-- your flight: the AI lead (you on its wing)
	if m.role == "wing" then
		local spec = BANDITS[m.leadType or m.playerType] or BANDITS.f16
		local lead = mk(spec, "blue", add(add(p.pos, add(mul(self.dir, 260), mul(side, -180))), V(0, 0, 20)), hdg, ((m.callsign or "VIPER 1-1"):gsub("-%d$", "-1")) .. " (vezér)")
		AI.newAIPilot(lead, "ace", self.area)
		lead.isLead = true
		self.lead = lead
		g.radio.callsign = (m.callsign or "VIPER 1-1"):gsub("-%d$", "-2")
	end
	-- more friendly flights (allies), on both sides of yours
	local k = 0
	for _, grp in ipairs(m.blue or {}) do
		for _ = 1, grp.n do
			k = k + 1
			local spec = BANDITS[grp.type] or BANDITS.f16
			local pos = add(add(p.pos, mul(side, ((k % 2 == 1) and 1 or -1) * (2500 + 1200 * math.floor(k / 2)))), mul(self.dir, -800 * math.floor(k / 2)))
			local ac = mk(spec, "blue", pos, hdg, string.format("%s %d (%s)", grp.label or "Szövetséges", k, spec.short))
			AI.newAIPilot(ac, m.allySkill or "normal", self.area)
			ac.power = grp.power
		end
	end
	-- the other side: at most 4 at once, the rest as reinforcements once the first group is thinned out
	self.red = {}
	local queue = {}
	for _, grp in ipairs(m.red or {}) do
		for _ = 1, grp.n do queue[#queue + 1] = grp end
	end
	self.reserveRed = {}
	for i = MAX_ACTIVE_RED + 1, #queue do self.reserveRed[#self.reserveRed + 1] = queue[i] end
	self.reinfT, self.redK = 0, 0
	for i = 1, math.min(MAX_ACTIVE_RED, #queue) do self:spawnRed(queue[i], 0) end
	self:say("awacs", self:briefLine(), 0.4)
	return self
end

function Mission:spawnRed(grp, back)
	local g, m, r = self.g, self.m, self.rnd
	self.redK = self.redK + 1
	local k = self.redK - 1
	local spec = BANDITS[grp.type] or BANDITS.su35
	local pos = add(add(self.P, mul(self.dir, 14000 + back + r() * 5000)), mul(self.side, ((k % 5) - 2) * 2600))
	pos.z = math.max(r() * 3000 + 4000, g.terrain:height(pos.x, pos.y) + 1500)
	local hdg = atan2(self.dir.x, self.dir.y) + math.pi
	local ac = self.mk(spec, "red", pos, hdg, string.format("%s %d", spec.short, self.redK))
	ac.power = grp.power
	AI.newAIPilot(ac, m.skill or "normal", self.area)
	self.red[#self.red + 1] = ac
	return ac
end

function Mission:say(who, text, delay) self.g.radio:say(who, text, delay or 0.4) end

function Mission:bearingTo(a)
	local p = self.g.player
	return string.format("%03d", math.floor(((atan2(a.pos.x - p.pos.x, a.pos.y - p.pos.y) / DEG) + 360) % 360 + 0.5) % 360)
end

function Mission:briefLine()
	local cs = self.g.radio.callsign
	local brg = string.format("%03d", math.floor(((atan2(self.P.x, self.P.y) / DEG) + 360) % 360 + 0.5) % 360)
	return string.format("%s, Magic: %d hostile%s, bullseye %s. %s Fence in.", cs, #self.red, #self.red > 1 and "s" or "", brg, self.m.kind == "cap" and "Hold the CAP." or "Clear the sky.")
end

function Mission:aliveReds()
	local out = {}
	for _, a in ipairs(self.red) do
		if a.alive then out[#out + 1] = a end
	end
	return out
end

function Mission:onEvent(kind, d)
	if self.over or kind ~= "kill" then return end
	local v = d.victim
	local g = self.g
	local id = v.specKey or (v.spec and (v.spec.model or v.spec.id))
	if v.team == "red" then
		self.redLost[#self.redLost + 1] = { type = id, power = v.power or self.m.foe }
		if d.killer == g.player then self.kills[#self.kills + 1] = v.spec.short end
		if self.lead and self.lead.alive and d.killer == self.lead then self:say("lead", "Splash one!", 0.2) end
	elseif v.team == "blue" then
		if v ~= g.player then self.blueLost[#self.blueLost + 1] = { type = id, power = v.power or self.m.power } end
		if v == self.lead then self:say("awacs", g.radio.callsign .. ", your lead is down! You have the flight.", 0.6) end
	end
end

function Mission:update(dt)
	if self.over then return end
	self.t = self.t + dt
	local g, m = self.g, self.m
	local p = g.player
	local reds = self:aliveReds()
	local near = 1e9
	for _, a in ipairs(reds) do near = math.min(near, len(sub(a.pos, p.pos))) end
	if self.phase == "ingress" and near < 32000 then
		self.phase = "merge"
		local cs = g.radio.callsign
		if m.role == "wing" then self:say("lead", string.format("%s, tally %d, engage! Two, cover me.", (cs:gsub("-%d$", "-1")), #reds))
		else self:say("awacs", string.format("%s, %d hostiles, %d miles, hot. Cleared to engage.", cs, #reds, math.floor(near / 1852 + 0.5))) end
	end
	if #self.reserveRed > 0 and self.phase ~= "ingress" then
		self.reinfT = self.reinfT + dt
		if #reds <= 1 or self.reinfT > REINFORCE_GAP then
			local n = math.min(#self.reserveRed, 3)
			for _ = 1, n do
				local grp = table.remove(self.reserveRed, 1)
				self:spawnRed(grp, 6000)
			end
			self.reinfT = 0
			self:say("awacs", string.format("%s, reinforcements: %d more hostile%s inbound, bearing %s.", g.radio.callsign, n, n > 1 and "s" or "", self:bearingTo(self.red[#self.red])))
		end
	end
	if #reds == 0 and #self.red > 0 and #self.reserveRed == 0 then
		self:say("awacs", g.radio.callsign .. ", picture clean. Good work, RTB.")
		self:finish(true)
		return
	end
	if m.kind == "cap" and self.t > (m.minutes or 8) * 60 then
		self:say("awacs", "CAP time complete, RTB.")
		self:finish(true)
		return
	end
	if self.t > (m.minutes or 12) * 60 + 300 then self:finish(m.kind == "cap") return end
	if not p.alive and not self.over then self:finish(false, "killed") end
	if p.ejected and not self.over then self:finish(false, "ejected") end
end

function Mission:finish(won, why)
	if self.over then return end
	self.over = true
	local g = self.g
	local p = g.player
	local lostOwn = p.ejected or not p.alive
	local blueLost = {}
	for _, e in ipairs(self.blueLost) do blueLost[#blueLost + 1] = e end
	if lostOwn then blueLost[#blueLost + 1] = { type = self.m.playerType, power = self.m.power } end
	self.result = {
		won = won, why = why, status = p.ejected and "ejected" or (not p.alive and "shot_down" or "ok"), kills = #self.kills, killTypes = self.kills,
		blueLost = blueLost, redLost = self.redLost, time = self.t,
	}
	g.hud:message(won and "KÜLDETÉS TELJESÍTVE – Enter: jelentés" or "KÜLDETÉS VÉGE – Enter: jelentés", won and "good" or "warn", 6, "mission")
	g.state.subBanner = "Enter: jelentés (debriefing)"
end

-- Enter after the mission: the report
function Mission:leave()
	if self.left then return end
	self.left = true
	if not self.result then self:finish(false, "abort") end
	if self.g.env.onMissionEnd then self.g.env.onMissionEnd(self.result, self.m) end
end

-- the HUD's line under the top
function Mission:line()
	local m = self.m
	local reds = #self:aliveReds()
	local total = #self.red + #self.reserveRed
	local head = (m.title or "BEVETÉS"):upper()
	if m.kind == "cap" then
		return string.format("%s · CAP %d s · ellenség %d", head, math.max(0, math.floor((m.minutes or 8) * 60 - self.t)), reds)
	end
	return string.format("%s · ellenség %d/%d · lelövéseid %d", head, reds + #self.reserveRed, total, #self.kills)
end

return Mission
