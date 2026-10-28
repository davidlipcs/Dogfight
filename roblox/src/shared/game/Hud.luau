--!nonstrict
-- The HUD, radar scope, RWR and cockpit warnings: the port of web/js/hud.js.  It draws on an abstract canvas g (the client's
-- GuiCanvas, or a recorder in the tests) with: g:line(x1,y1,x2,y2,c), g:arc(x,y,r,c,a0,a1), g:strokeRect(x,y,w,h,c), g:fillRect(x,y,w,h,c),
-- g:fillCircle(x,y,r,c), g:dashed(x1,y1,x2,y2,c,on,off), g:text(str,x,y,c,size,align,font), g:vignette(rgb,alpha,inner), g:lineWidth(w).
-- Colours are { r, g, b, a } (0..255, a 0..1).  Common subset of Lua 5.4 and Luau.
local M = require(script.Parent.Parent.sim.SimMath)
local Specs = require(script.Parent.Parent.sim.Specs)
local W = require(script.Parent.Parent.sim.Weapons)
local V, add, sub, mul, dot, len, norm, clamp, DEG = M.V, M.add, M.sub, M.mul, M.dot, M.len, M.norm, M.clamp, M.DEG
local toLocal, xform, angleBetween, headingDeg, atan2 = M.toLocal, M.xform, M.angleBetween, M.headingDeg, M.atan2
local sin, cos, floor, abs, min, max, sqrt, pi = math.sin, math.cos, math.floor, math.abs, math.min, math.max, math.sqrt, math.pi
local IR, ARH = Specs.IR, Specs.ARH
local STT, ACM, OFF, SEARCH = W.STT, W.ACM, W.OFF, W.SEARCH

local H = {}
local GREEN, DIM, AMBER, RED = { 107, 255, 133, 0.95 }, { 107, 255, 133, 0.5 }, { 255, 200, 64, 1 }, { 255, 77, 64, 1 }
local WHITE, ENEMY, CYAN = { 245, 245, 245, 0.95 }, { 255, 84, 72, 0.95 }, { 115, 217, 255, 0.95 }
H.GREEN, H.DIM, H.AMBER, H.RED, H.WHITE, H.ENEMY, H.CYAN = GREEN, DIM, AMBER, RED, WHITE, ENEMY, CYAN
local LEVEL_COLOR = { good = GREEN, warn = AMBER, bad = RED, info = WHITE }
local TITLE = "title"                                   -- the display font of the browser game (Oswald / Impact)

local function fix(x, n) return string.format("%." .. (n or 1) .. "f", x) end
local function round(x) return floor(x + 0.5) end
local function pad(s, n) s = tostring(s); return string.rep(" ", max(0, n - #s)) .. s end
local function pad0(s, n) s = tostring(s); return string.rep("0", max(0, n - #s)) .. s end
local function padEnd(s, n) s = tostring(s); return s .. string.rep(" ", max(0, n - #s)) end
local function blinkOf(t, rate) return floor(t * rate) % 2 == 0 end

local Hud = {}
Hud.__index = Hud
function H.new(g)
	local self = setmetatable({}, Hud)
	self.g = g
	self.messages, self.killfeed, self.markers, self.hitmarker, self.time = {}, {}, true, 0, 0
	self.dlz, self.dlzTimer, self.popups, self.damage, self.medal = nil, 0, {}, 0, nil
	self.w, self.h, self.u = 1280, 720, 0.8
	self.black, self.red = 0, 0
	return self
end

-- score popup under the centre ("+150 ÁGYÚ"), rises and fades
function Hud:popup(text, color)
	self.popups[#self.popups + 1] = { text = text, color = color or GREEN, t = 1.8 }
	while #self.popups > 4 do table.remove(self.popups, 1) end
end
function Hud:showMedal(a) self.medal = { a = a, t = 4.5 } end
function Hud:message(text, level, duration, key)
	level, duration = level or "info", duration or 2.5
	key = key or text
	for _, m in ipairs(self.messages) do
		if m.key == key then
			m.text, m.color, m.t = text, LEVEL_COLOR[level] or WHITE, duration
			return
		end
	end
	self.messages[#self.messages + 1] = { text = text, color = LEVEL_COLOR[level] or WHITE, t = duration, key = key }
	while #self.messages > 4 do table.remove(self.messages, 1) end
end
function Hud:handleEvent(kind, d, player)
	if kind == "message" and d.to == player then self:message(d.text, d.level or "info")
	elseif kind == "kill" then
		local text
		if d.killer and d.killer ~= d.victim then text = d.killer.name .. " → " .. d.victim.name .. "  [" .. tostring(d.weapon) .. "]"
		else text = d.victim.name .. " lezuhant" end
		self.killfeed[#self.killfeed + 1] = { text = text, color = d.killer == player and GREEN or d.victim == player and RED or WHITE, t = 7 }
		while #self.killfeed > 5 do table.remove(self.killfeed, 1) end
		if d.killer == player and d.victim ~= player then self:message("CÉLPONT MEGSEMMISÍTVE", "good", 3) end
	elseif kind == "hit" and d.shooter == player and d.target ~= player then self.hitmarker = 0.25
	elseif kind == "hit" and d.target == player then self.damage = min(0.8, self.damage + 0.45)
	elseif kind == "pitbull" and d.missile.shooter == player then self:message("PITBULL - AIM-120 aktív", "good") end
end

-- screen projection of a world point: x, y in px or nil when it is behind the camera (the picture is a perspective view)
function Hud:project(p)
	local c = self.cam
	local v = toLocal(c.orientation, sub(p, c.position))
	if v.y < 1 then return nil end
	local f = self.h / 2 / math.tan(c.fov * DEG / 2)
	return self.w / 2 + v.x / v.y * f, self.h / 2 - v.z / v.y * f
end

-- ------------------------------------------------------------ primitives
function Hud:line(x1, y1, x2, y2, c) self.g:line(x1, y1, x2, y2, c) end
function Hud:circle(x, y, r, c, a0, a1) self.g:arc(x, y, r, c, a0, a1) end
function Hud:rect(x, y, hw, hh, c) self.g:strokeRect(x - hw, y - hh, 2 * hw, 2 * hh, c) end
function Hud:poly(pts, c, closed)
	if closed == nil then closed = true end
	for i = 1, #pts - 1 do self.g:line(pts[i][1], pts[i][2], pts[i + 1][1], pts[i + 1][2], c) end
	if closed and #pts > 2 then self.g:line(pts[#pts][1], pts[#pts][2], pts[1][1], pts[1][2], c) end
end
function Hud:brackets(x, y, r, c)
	for _, sx in ipairs({ -1, 1 }) do
		for _, sy in ipairs({ -1, 1 }) do
			self:poly({ { x + sx * r, y + sy * r * 0.6 }, { x + sx * r, y + sy * r }, { x + sx * r * 0.6, y + sy * r } }, c, false)
		end
	end
end
function Hud:text(t, x, y, c, size, align, font) self.g:text(t, x, y, c, size or 13, align or "left", font) end
function Hud:dashed(x1, y1, x2, y2, c, on, off) self.g:dashed(x1, y1, x2, y2, c, on, off) end

-- player: the Aircraft; world; view = { position, orientation, fov }; camCtl: the flight camera; game: the state table of the match
-- (wave, kills, deaths, score, streak, credits, modeLine, banner, subBanner, meatball, bt, raceTarget, missionLine)
function Hud:update(dt, player, world, view, camCtl, game, w, h)
	self.player, self.cam = player, view
	self.w, self.h, self.u = w, h, min(w, h) / 900
	local g = self.g
	g:lineWidth(max(1.2, 1.6 * self.u))
	self.time, self.dt = self.time + dt, dt
	self.hitmarker = max(0, self.hitmarker - dt)
	for _, l in ipairs({ self.messages, self.killfeed, self.popups }) do for _, m in ipairs(l) do m.t = m.t - dt end end
	local function alive(list) local out = {} for _, m in ipairs(list) do if m.t > 0 then out[#out + 1] = m end end return out end
	self.messages, self.killfeed, self.popups = alive(self.messages), alive(self.killfeed), alive(self.popups)
	self:gEffects(player, dt)
	self:damageFlash(dt)
	if player and player.alive and camCtl.cockpit and camCtl.panelLook then
		-- looking down at the displays: only the warnings and messages stay over them
		self.cockpit = true
		self:warnings(player, world)
	elseif player and player.alive then
		self:incomingMissiles(player)
		if not camCtl.follow then self:flightSymbols(player, camCtl) end
		self:targets(player, world)
		self:navMarks(player)
		if game.raceTarget then self:raceMark(player, game.raceTarget) end
		self:weaponSymbols(player, world, dt)
		if not camCtl.follow then self:panels(player, world) end
		self:radarScope(player)
		self:rwrScope(player)
		self:warnings(player, world)
		self:missileList(player, world)
	end
	self:overlay(game)
	self:extras(game, camCtl)
end

-- the carrier's optical landing system: the amber ball against the green datum lights, the line-up error and the distance to the wires
function Hud:meatballBox(m)
	local u, g = self.u, self.g
	local cx, cy, hh = self.w - 70 * u, self.h / 2 - 40 * u, 70 * u
	g:fillRect(cx - 34 * u, cy - hh - 26 * u, 68 * u, 2 * hh + 70 * u, { 4, 10, 14, 0.55 })
	self:line(cx - 28 * u, cy, cx - 10 * u, cy, GREEN); self:line(cx + 10 * u, cy, cx + 28 * u, cy, GREEN)
	self:rect(cx, cy, 6 * u, hh, DIM)
	local k = clamp(m.high / 12, -1, 1)
	local by = cy - k * hh
	local col = abs(k) < 0.7 and AMBER or RED
	g:fillCircle(cx, by, 7 * u, k < -0.7 and RED or col)
	self:text("MEATBALL", cx, cy - hh - 14 * u, CYAN, 10 * u + 2, "center")
	local lu
	if abs(m.off) < 8 then lu = { "VONALBAN", GREEN } elseif m.off > 0 then lu = { "◀ BALRA", AMBER } else lu = { "JOBBRA ▶", AMBER } end
	self:text(lu[1], cx, cy + hh + 14 * u, lu[2], 10 * u + 2, "center")
	self:text(k > 0.25 and "MAGAS" or k < -0.25 and "ALACSONY" or "JÓ", cx, cy + hh + 28 * u, k < -0.7 and RED or WHITE, 10 * u + 2, "center")
	self:text(round(m.dist) .. " m", cx, cy + hh + 42 * u, DIM, 10 * u + 2, "center")
end
-- ring race: the next ring - a ring marker with the distance, or an arrow at the edge
function Hud:raceMark(ac, c)
	local u = self.u
	local px, py = self:project(c)
	local d = len(sub(c, ac.pos))
	if not px then self:edgeArrow(c, AMBER); return end
	self:circle(px, py, 16 * u, AMBER); self:circle(px, py, 3 * u, AMBER)
	self:text("GYŰRŰ " .. fix(d / 1000) .. " km", px, py - 26 * u, AMBER, 12 * u + 2, "center")
end
-- red flash at the screen edges when the player is hit
function Hud:damageFlash(dt)
	if self.damage <= 0.01 then self.damage = 0; return end
	self.g:vignette({ 255, 30, 20 }, self.damage * 0.75, 0.45)
	self.damage = max(0, self.damage - dt * 1.4)
end
-- added layer: score, game mode line, popups, medal banner, camera label
function Hud:extras(game, camCtl)
	local u = self.u
	local fs = 12 * u + 3
	if game.score ~= nil and not self.tutorial then
		local streak = (game.streak or 0) > 1 and ("   SOROZAT " .. game.streak) or ""
		self:text("PONT " .. game.score .. streak .. "   KREDIT " .. (game.credits or 0), 20 * u, 82 * u, AMBER, fs)
	end
	if game.bt then                                       -- bullet time (hangar mod): charge bar
		local x, y, w, b = 20 * u, 122 * u, 120 * u, game.bt
		local on = b.active > 0
		self.g:strokeRect(x, y - 5 * u, w, 10 * u, DIM)
		self.g:fillRect(x, y - 5 * u, w * (on and b.active / 4 or b.charge), 10 * u, on and AMBER or b.charge >= 1 and GREEN or DIM)
		self:text(on and "BULLET TIME" or b.charge >= 1 and "O = bullet time" or "bullet time töltődik", x + w + 8 * u, y, on and AMBER or DIM, 10 * u + 2)
	end
	if game.modeLine and game.modeLine ~= "" then self:text(game.modeLine, 20 * u, 102 * u, WHITE, 11 * u + 2) end
	local y = self.h / 2 + 70 * u
	for _, p in ipairs(self.popups) do
		local k = min(1, p.t / 0.5)
		local rise = (1.8 - p.t) * 26 * u
		local c = { p.color[1], p.color[2], p.color[3], (p.color[4] or 1) * k }
		self:text(p.text, self.w / 2, y - rise, c, 22 * u + 4, "center", TITLE)
		y = y + 30 * u
	end
	if self.medal then
		local m = self.medal
		m.t = m.t - (self.dt or 1 / 60)
		if m.t <= 0 then self.medal = nil
		else
			local k = min(1, m.t / 0.6)
			local bw, bh = 360 * u, 64 * u
			local x, top = self.w / 2 - bw / 2, 120 * u
			self.g:fillRect(x, top, bw, bh, { 20, 27, 34, 0.88 * k })
			self.g:strokeRect(x, top, bw, bh, { 255, 200, 64, k })
			self:text("★ ÚJ KITÜNTETÉS", self.w / 2, top + 18 * u, AMBER, 11 * u + 2, "center")
			self:text(m.a.name, self.w / 2, top + 36 * u, WHITE, 18 * u + 3, "center", TITLE)
			self:text(m.a.desc, self.w / 2, top + 54 * u, DIM, 10 * u + 2, "center")
		end
	end
	if game.meatball then self:meatballBox(game.meatball) end
	if camCtl and camCtl.followLabel and camCtl.followLabel ~= "" then self:text(camCtl.followLabel, self.w / 2, 70 * u, CYAN, 15 * u + 3, "center", TITLE) end
end

function Hud:flightSymbols(ac, camCtl)
	local u = self.u
	local aimPos = add(camCtl.position, mul(camCtl:aimDirection(), 3000))
	local ax, ay = self:project(aimPos)
	if camCtl.stick and not self.touchLayout then self:stickGauge(camCtl.stick)
	elseif ax and not (camCtl.freeLook and not camCtl.cockpit) then self:circle(ax, ay, 14 * u, WHITE)
	elseif not ax and camCtl.cockpit then self:edgeArrow(aimPos, WHITE) end
	local x, y = self:project(add(ac.pos, mul(ac.forward, 800)))
	if x then
		local r, gap = 22 * u, 6 * u
		self:line(x - r, y, x - gap, y, GREEN); self:line(x + gap, y, x + r, y, GREEN)
		self:line(x, y - r, x, y - gap, GREEN); self:line(x, y + gap, x, y + r, GREEN)
		if self.hitmarker > 0 then
			local k = 20 * u
			for _, s in ipairs({ { -1, -1 }, { 1, 1 }, { -1, 1 }, { 1, -1 } }) do self:line(x + s[1] * k, y + s[2] * k, x + s[1] * k * 0.4, y + s[2] * k * 0.4, WHITE) end
		end
	end
	if ac.speed > 20 then
		local fx, fy = self:project(add(ac.pos, mul(norm(ac.vel), 800)))
		if fx then
			local r = 8 * u
			self:circle(fx, fy, r, GREEN)
			self:line(fx - 22 * u, fy, fx - r, fy, GREEN); self:line(fx + r, fy, fx + 22 * u, fy, GREEN); self:line(fx, fy - r, fx, fy - 17 * u, GREEN)
		end
	end
	self.cockpit = camCtl.cockpit
	if camCtl.cockpit then self:pitchLadder(ac, camCtl) end
end
-- where the mouse joystick is: box = full deflection, dot = the stick (down = pulled back)
function Hud:stickGauge(s)
	local u = self.u
	local r, cx, cy = 26 * u, 116 * u, self.h - 270 * u                      -- above the RWR scope
	self:rect(cx, cy, r, r, DIM)
	self:line(cx - r, cy, cx + r, cy, DIM); self:line(cx, cy - r, cx, cy + r, DIM)
	local x, y, dz = cx + s.x * r, cy + s.y * r, 0.07
	self:rect(cx, cy, r * dz, r * dz, DIM)                                   -- neutral band
	local neutral = abs(s.x) < dz and abs(s.y) < dz
	self.g:fillCircle(x, y, 4 * u + 1, neutral and GREEN or WHITE)
	self:text("BOTKORMÁNY", cx, cy + r + 12 * u, DIM, 9 * u + 2, "center")
end
function Hud:pitchLadder(ac, camCtl)
	local hdg = atan2(ac.forward.x, ac.forward.y)
	local pitch = math.asin(clamp(ac.forward.z, -1, 1)) / DEG
	local function dir(h, e) return V(sin(h) * cos(e), cos(h) * cos(e), sin(e)) end
	for e = -80, 80, 10 do
		if abs(e - pitch) <= 16 then                                           -- like the real HUD: only near the boresight
			local inner, outer = 2, 9
			if e == 0 then inner, outer = 1.5, 25 end
			for _, s in ipairs({ -1, 1 }) do
				local ax, ay = self:project(add(camCtl.position, mul(dir(hdg + s * inner * DEG, e * DEG), 5000)))
				local bx, by = self:project(add(camCtl.position, mul(dir(hdg + s * outer * DEG, e * DEG), 5000)))
				if ax and bx then
					self:line(ax, ay, bx, by, e >= 0 and GREEN or DIM)
					if e ~= 0 and s == 1 then self:text(tostring(e), bx + 6, by, e >= 0 and GREEN or DIM, 11 * self.u + 2) end
				end
			end
		end
	end
end
function Hud:lockTarget(ac, sp)
	if sp and sp.guidance == IR and ac.irSeeker.locked and not ac.irSeeker.target.isFlare then return ac.irSeeker.target end
	local r = ac.radar
	if r.mode == STT and r.locked and r.locked.alive then return r.locked end
	return nil
end
function Hud:targets(ac, world)
	if not self.markers then return end
	local u = self.u
	local nearest = nil
	for _, t in ipairs(world.aircraft) do
		if t.alive and t.team ~= ac.team and (not nearest or len(sub(t.pos, ac.pos)) < len(sub(nearest.pos, ac.pos))) then nearest = t end
	end
	self.nearestEnemy = nearest
	local locked = self:lockTarget(ac, ac.selectedSpec)
	for _, t in ipairs(world.aircraft) do
		if t ~= ac and t.alive and t.team == ac.team then               -- wingman: cyan ring with the distance
			local px, py = self:project(t.pos)
			local d = len(sub(t.pos, ac.pos))
			if px and d < 40000 then
				self:circle(px, py, 9 * u, CYAN)
				self:text((t.tag or "KÍSÉRŐ") .. " " .. ((t.ghost and d < 10000) and (round(d) .. " m") or fix(d / 1000)), px, py - 18 * u, CYAN, 10 * u + 2, "center")
			end
		elseif t ~= ac and t.alive and t.team ~= ac.team then
			local d = len(sub(t.pos, ac.pos))
			if d <= 80000 then
				local px, py = self:project(t.pos)
				if px and t ~= locked then                                    -- (the locked one is drawn by the lock box)
					self:poly({ { px - 8 * u, py - 20 * u }, { px + 8 * u, py - 20 * u }, { px, py - 10 * u } }, ENEMY)
					self:text(fix(d / 1000), px, py - 30 * u, ENEMY, 11 * u + 2, "center")
					-- in radar lock range and not locked yet: tell how (a stealthy F-22 only shows up on radar much closer)
					local lockable = min(ac.spec.radar.lockRange, W.radarRange(ac.spec.radar.searchRange, W.rcs(t, ac.pos)))
					if ac.radar.mode ~= STT and t == nearest then
						if d < lockable then self:text("T = lock", px, py + 2 * u, AMBER, 11 * u + 2, "center")
						elseif t.spec.rcsFront < 0.01 and d < 40000 then
							self:text("lopakodó - radar ~" .. string.format("%.0f", lockable / 1000) .. " km-től", px, py + 2 * u, DIM, 10 * u + 2, "center")
						end
					end
				end
			end
		end
	end
end
-- the combat zone (amber) and the home base (cyan): marker with the distance, and an arrow at the screen edge towards the zone
function Hud:navMarks(ac)
	local n, u = self.nav, self.u
	if not n then return end
	local dz = sqrt((n.zone.x - ac.pos.x) ^ 2 + (n.zone.y - ac.pos.y) ^ 2)
	local db = sqrt((n.base.x - ac.pos.x) ^ 2 + (n.base.y - ac.pos.y) ^ 2)
	local where = nil
	if db < n.base.r then where = { "BIZTONSÁGI ZÓNA (bázis) - itt nem támadnak", CYAN } elseif dz < n.zone.r then where = { "HARCI ZÓNA", ENEMY } end
	if where then self:text(where[1], 20 * u, 62 * u, where[2], 11 * u + 2) end
	if not self.markers then return end
	if dz > n.zone.r then
		local pos = V(n.zone.x, n.zone.y, max(ac.pos.z, 3500))
		local px, py = self:project(pos)
		if px then
			local k = 11 * u
			self:poly({ { px, py - k }, { px + k, py }, { px, py + k }, { px - k, py } }, AMBER)
			self:text("HARCI ZÓNA " .. string.format("%.0f", (dz - n.zone.r) / 1000) .. " km", px, py - 22 * u, AMBER, 12 * u + 2, "center")
		else self:edgeArrow(pos, AMBER) end
	end
	if n.carrier then                                      -- the carrier: cyan ship mark with the distance
		local dc = sqrt((n.carrier.x - ac.pos.x) ^ 2 + (n.carrier.y - ac.pos.y) ^ 2)
		local px, py
		if dc > 900 then px, py = self:project(V(n.carrier.x, n.carrier.y, 40)) end
		if px then
			local k = 9 * u
			self:poly({ { px - k, py }, { px - k * 0.6, py + k * 0.6 }, { px + k * 0.6, py + k * 0.6 }, { px + k, py } }, CYAN)
			self:text("HORDOZÓ " .. fix(dc / 1000, dc < 10000 and 1 or 0) .. " km", px, py + 20 * u, CYAN, 11 * u + 2, "center")
		end
	end
	if db > 3000 then
		local px, py = self:project(V(n.base.x, n.base.y, 300))
		if px then
			local k = 8 * u
			self:rect(px, py, k, k, CYAN)
			self:text("BÁZIS " .. string.format("%.0f", db / 1000) .. " km", px, py + 20 * u, CYAN, 11 * u + 2, "center")
		end
	end
end
function Hud:edgeArrow(pos, c)
	local v = toLocal(self.cam.orientation, sub(pos, self.cam.position))
	local ang = atan2(v.x, v.z)
	local r = min(self.w, self.h) * 0.38
	local x, y = self.w / 2 + sin(ang) * r, self.h / 2 - cos(ang) * r
	local tip = { x + sin(ang) * 22 * self.u, y - cos(ang) * 22 * self.u }
	local side = { cos(ang) * 12 * self.u, sin(ang) * 12 * self.u }
	self:poly({ { x + side[1], y + side[2] }, tip, { x - side[1], y - side[2] } }, c)
end
function Hud:weaponSymbols(ac, world, dt)
	local u, r = self.u, ac.radar
	if r.mode == STT and r.trackPos then
		local t = r.locked
		local px, py = self:project(r.trackPos)
		local col = r.lostTime == 0 and GREEN or AMBER
		if not px then self:edgeArrow(r.trackPos, col)
		elseif r.lostTime > 0 then self:text("MEM", px, py + 40 * u, AMBER, 12 * u + 2, "center") end
		if t and len(sub(t.pos, ac.pos)) < ac.spec.gun.maxLeadRange then
			local aim = W.gunLead(ac.pos, ac.vel, t.pos, t.vel, ac.spec.gun)
			local d = len(sub(t.pos, ac.pos))
			local lx, ly = self:project(add(ac.pos, mul(aim, d)))
			if lx then
				self:circle(lx, ly, 20 * u, WHITE); self:circle(lx, ly, 2.5 * u, WHITE)
				local frac = clamp(d / ac.spec.gun.maxLeadRange, 0, 1)
				self:circle(lx, ly, 24 * u, WHITE, -pi / 2, -pi / 2 + pi * 2 * (1 - frac))
			end
		end
	elseif r.pending then
		local px, py = self:project(r.pending.pos)
		if px and blinkOf(self.time, 8) then self:brackets(px, py, 24 * u, AMBER) end
	elseif r.mode == ACM then
		local s, pts = r.spec, {}
		local corners = { { -s.acmAz, s.acmElLow }, { s.acmAz, s.acmElLow }, { s.acmAz, s.acmElHigh }, { -s.acmAz, s.acmElHigh } }
		local all = true
		for _, c in ipairs(corners) do
			local az, el = c[1], c[2]
			local d = xform(ac.quat, V(sin(az * DEG) * cos(el * DEG), cos(az * DEG) * cos(el * DEG), sin(el * DEG)))
			local x, y = self:project(add(ac.pos, mul(d, 3000)))
			if x then pts[#pts + 1] = { x, y } else all = false end
		end
		if all then self:poly(pts, { 255, 200, 64, 0.5 }) end
	end
	if r.selected and r.mode ~= STT and r.selected.alive then
		local px, py = self:project(r.selected.pos)
		if px then self:brackets(px, py, 20 * u, DIM) end
	end
	local sp = ac.selectedSpec
	self:missilePaths(ac, world)
	if not sp then return end
	if sp.guidance == IR and ac.irSeeker.axis then
		local s = ac.irSeeker
		local px, py = self:project(add(ac.pos, mul(s.axis, 2000)))
		if px then
			if s.locked then
				self:circle(px, py, 26 * u, GREEN); self:circle(px, py, 29 * u, GREEN)
				self:poly({ { px, py - 7 * u }, { px + 7 * u, py }, { px, py + 7 * u }, { px - 7 * u, py } }, GREEN)
			else
				-- search circle as big as the seeker's search cone (wide with the lock assist)
				local fov = (s.acqFov or s.spec.seekerFov) * DEG
				local rad = max(26 * u, math.tan(fov) / math.tan(self.cam.fov * DEG / 2) * self.h / 2)
				self:circle(px, py, rad, s.candidate and (floor(self.time * 10) % 2 == 1 and WHITE or GREEN) or DIM)
			end
		end
	end
	self:dlzBar(ac, sp, dt)
	self:lockBox(ac, sp)
end
-- big square around the locked aircraft + where a missile fired now would meet it
function Hud:lockBox(ac, sp)
	local t = self:lockTarget(ac, sp)
	if not t then return end
	local u, r = self.u, ac.radar
	local pos = (r.mode == STT and r.locked == t and r.trackPos) and r.trackPos or t.pos
	local px, py = self:project(pos)
	local rel = sub(pos, ac.pos)
	local d = len(rel)
	local inRange = self.dlz and sp and d > sp.minRange and d < self.dlz[1]
	local blink = blinkOf(self.time, 4)
	local col = inRange and RED or GREEN
	-- predicted intercept point: where the target will be when a missile launched now reaches it
	if sp then
		local tt = W.flyoutTime(sp, ac.speed, ac.pos.z, d)
		local ip = pos
		for _ = 1, 4 do
			if tt == nil then break end
			ip = add(pos, mul(t.vel, tt))
			tt = W.flyoutTime(sp, ac.speed, ac.pos.z, len(sub(ip, ac.pos)))
		end
		local ax, ay = self:project(add(ac.pos, mul(ac.forward, 25)))
		local bx, by
		if tt ~= nil then bx, by = self:project(ip) end
		if ax and bx then
			self:dashed(ax, ay, bx, by, col, 10 * u, 7 * u)
			if px then self:dashed(px, py, bx, by, ENEMY, 4 * u, 5 * u) end
			local k = 9 * u
			self:line(bx - k, by - k, bx + k, by + k, col); self:line(bx - k, by + k, bx + k, by - k, col)
			self:circle(bx, by, 13 * u, col)
			self:text("találat ~" .. fix(tt, 0) .. " s", bx + 18 * u, by + 14 * u, col, 11 * u + 2)
		end
	end
	if not px then return end
	-- box sized to the target's wingspan on screen
	local pxPerM = self.h / 2 / math.tan(self.cam.fov * DEG / 2) / max(d, 1)
	local hs = clamp(7 * pxPerM, 26 * u, 140 * u)
	self.g:lineWidth(max(2.5, 3 * u))
	self:rect(px, py, hs, hs, col)
	self.g:lineWidth(max(1.2, 1.6 * u))
	for _, s in ipairs({ { -1, -1 }, { 1, -1 }, { -1, 1 }, { 1, 1 } }) do
		-- outer corner ticks make the box readable against bright clouds
		self:line(px + s[1] * (hs + 4 * u), py + s[2] * hs, px + s[1] * (hs + 12 * u), py + s[2] * hs, col)
		self:line(px + s[1] * hs, py + s[2] * (hs + 4 * u), px + s[1] * hs, py + s[2] * (hs + 12 * u), col)
	end
	local vc = -dot(sub(t.vel, ac.vel), norm(rel))
	self:text("LOCK  " .. (sp and sp.name or ""), px - hs, py - hs - 14 * u, col, 13 * u + 3, "left", TITLE)
	self:text(fix(d / 1000) .. " km   Vc " .. (vc * 3.6 >= 0 and "+" or "") .. round(vc * 3.6), px - hs, py + hs + 14 * u, col, 11 * u + 2)
	if inRange and blink then self:text("LŐHETSZ!  (Space)", px, py + hs + 34 * u, RED, 15 * u + 4, "center", TITLE)
	elseif not inRange and sp and sp.guidance == IR and d > 9000 and ac:missileCount("AIM-120A") > 0 then
		self:text("messze van - válts AIM-120-ra (2)", px, py + hs + 34 * u, AMBER, 12 * u + 2, "center")
	elseif not inRange and sp and self.dlz and d >= self.dlz[1] then self:text("még messze", px, py + hs + 34 * u, AMBER, 12 * u + 2, "center")
	elseif not inRange and sp and d <= sp.minRange then self:text("túl közel", px, py + hs + 34 * u, AMBER, 12 * u + 2, "center") end
end
-- own missiles in flight: marker on the missile and its path to the target
function Hud:missilePaths(ac, world)
	local u = self.u
	for _, m in ipairs(world.missiles) do
		if m.shooter == ac and m.alive then
			local mx, my = self:project(m.pos)
			local aim = m.guidedTarget and m.guidedTarget.pos or m.estPos
			local ax, ay
			if aim then ax, ay = self:project(aim) end
			if mx and ax then self:dashed(mx, my, ax, ay, CYAN, 6 * u, 6 * u) end
			if mx then
				self:poly({ { mx, my - 7 * u }, { mx + 7 * u, my }, { mx, my + 7 * u }, { mx - 7 * u, my } }, CYAN)
				local ttg = W.timeToImpact(m)
				if ttg ~= nil and ttg < 99 then self:text(fix(ttg) .. " s", mx + 10 * u, my - 10 * u, CYAN, 11 * u + 2) end
			end
		end
	end
end
function Hud:dlzBar(ac, sp, dt)
	local r = ac.radar
	local tgt = r.mode == STT and r.locked or nil
	if sp.guidance == IR and ac.irSeeker.locked and not ac.irSeeker.target.isFlare then tgt = ac.irSeeker.target end
	if not tgt then self.dlz = nil; return end
	local rel = sub(tgt.pos, ac.pos)
	local d = len(rel)
	local closing = -dot(tgt.vel, norm(rel))
	self.dlzTimer = self.dlzTimer - dt
	if not self.dlz or self.dlzTimer <= 0 then
		local zmax, zne = W.launchZone(sp, ac.speed, ac.pos.z, closing)
		self.dlz = { zmax, zne }
		self.dlzTimer = 0.5
	end
	local rmax, rne = self.dlz[1], self.dlz[2]
	local rmin, u = sp.minRange, self.u
	local x, y0, y1 = self.w / 2 + 210 * u, self.h / 2 + 140 * u, self.h / 2 - 140 * u
	local scale = max(rmax * 1.25, d * 1.05, 2000)
	local function ry(v) return y0 + (y1 - y0) * clamp(v / scale, 0, 1) end
	self:line(x, ry(rmin), x, ry(rmax), GREEN)
	for _, v in ipairs({ rmax, rmin }) do self:line(x - 8 * u, ry(v), x + 8 * u, ry(v), GREEN) end
	self:line(x - 13 * u, ry(rne), x + 13 * u, ry(rne), GREEN)
	local yy = ry(d)
	self:poly({ { x - 24 * u, yy - 8 * u }, { x - 10 * u, yy }, { x - 24 * u, yy + 8 * u } }, WHITE, false)
	self:text(fix(rmax / 1000), x + 14 * u, ry(rmax), DIM, 11 * u + 2)
	local tag = nil
	if rmin < d and d < rne then tag = { "NO ESC", RED } elseif rmin < d and d < rmax then tag = { "IN RNG", GREEN } elseif d <= rmin then tag = { "MIN", AMBER } end
	if tag then self:text(tag[1], x - 20 * u, y0 + 22 * u, tag[2], 12 * u + 2) end
end
function Hud:panels(ac, world)
	local fm, u = ac.fm, self.u
	local fs = 13 * u + 3
	local lh = fs * 1.35
	local x, y = self.w / 2 - 330 * u, self.h / 2 - 90 * u
	local cmd = ac.controls.throttle
	local thr = cmd > 1 and "AB" or (round(cmd * 100) .. "%")
	local eng = fm.engine > 1.001 and "AB" or (round(fm.engine * 100) .. "%")
	local rows = {
		{ "IAS " .. pad(round(fm.ias * 3.6), 5) .. " km/h", GREEN }, { "TAS " .. pad(round(ac.speed * 3.6), 5), DIM },
		{ "M   " .. pad(fix(fm.mach, 2), 5), GREEN }, { "G   " .. pad(fix(fm.gLoad), 5), fm.gLoad > ac.spec.gMax * 0.85 and AMBER or GREEN },
		{ "AoA " .. pad(fix(fm.alpha / DEG), 5), fm.alpha / DEG > ac.spec.alphaLimit * 0.8 and AMBER or GREEN },
		{ "THR  " .. thr, cmd > 1 and AMBER or GREEN }, { "MOT  " .. eng, abs(fm.engine - cmd) > 0.02 and DIM or GREEN },
		{ fm.gearPos > 0.98 and "GEAR DOWN" or fm.gearPos > 0.02 and "GEAR TRANSIT" or "GEAR UP", fm.gearPos > 0.98 and GREEN or fm.gearPos > 0.02 and AMBER or DIM },
	}
	if ac.onGround then rows[#rows + 1] = { "GS  " .. pad(round(ac.speed * 3.6), 5) .. " km/h", GREEN } end
	if ac.extreme then rows[#rows + 1] = { (ac.spec.tvcAlways and "TVC" or "TVC EXTRÉM") .. (ac.fm.alpha / DEG > 50 and "  COBRA" or ""), ac.spec.tvcAlways and DIM or AMBER } end
	if ac.bayOpenAny > 0.05 then rows[#rows + 1] = { "FEGYVERTÉR NYITVA", AMBER } end
	if ac.controls.brakes and ac.onGround then rows[#rows + 1] = { "BRAKES", AMBER }
	elseif ac.controls.airbrake then rows[#rows + 1] = { "SPD BRK", AMBER } end
	for i, r in ipairs(rows) do self:text(r[1], x, y + (i - 1) * lh, r[2], fs) end
	-- during the tutorial its card covers the right side: the right column goes under the left one
	local terr = world.terrain:height(ac.pos.x, ac.pos.y)
	local xr = self.tutorial and x or self.w / 2 + 250 * u
	local yr = self.tutorial and y + (#rows + 0.6) * lh or y
	local fuelCol = fm.fuel < ac.spec.internalFuel * 0.12 and RED or fm.fuel < ac.spec.internalFuel * 0.28 and AMBER or GREEN
	local right = {
		{ "ALT " .. pad(round(ac.pos.z), 6) .. " m", GREEN }, { "AGL " .. pad(round(ac.pos.z - terr), 6), DIM },
		{ "VS  " .. ((fm.vel.z >= 0 and "+" or "") .. round(fm.vel.z)), GREEN }, { "HDG    " .. pad0(round(headingDeg(ac.forward)), 3), GREEN },
		{ "FUEL " .. pad(round(fm.fuel), 5) .. " kg", fuelCol }, { "HP   " .. pad(max(0, round(ac.hp)), 5), ac.hp > 50 and GREEN or RED },
	}
	for i, r in ipairs(right) do self:text(r[1], xr, yr + (i - 1) * lh, r[2], fs) end
	-- weapons
	local function reloadText(k)
		local n, lo = 0, nil
		for _, s in ipairs(ac.stations) do
			if s.key == k and not s.loaded and s.reload ~= nil then n = n + 1; lo = lo and min(lo, s.reload) or s.reload end
		end
		if n > 0 then return " +" .. n .. " (" .. math.ceil(lo) .. "s)" end
		return ""
	end
	-- in the cockpit the weapon lines go to the top of the screen: the bottom shows the displays
	local yb = self.cockpit and 92 * u or self.h - 78 * u
	local parts = {}
	for _, k in ipairs(ac:weaponKeys()) do
		local t = k .. " ×" .. ac:missileCount(k) .. reloadText(k)
		parts[#parts + 1] = k == ac.selected and ("[" .. t .. "]") or (" " .. t .. " ")
	end
	self:text(table.concat(parts, "   "), self.w / 2, yb, GREEN, fs, "center")
	self:text("GUN " .. ac.gun.ammo .. "    FLR " .. ac.flares .. "   CHF " .. ac.chaff, self.w / 2, yb + lh, GREEN, fs, "center")
	local sp = ac.selectedSpec
	local status, col = "", GREEN
	if sp and sp.guidance == IR then
		local s = ac.irSeeker
		if s.locked then status = "AIM-9M: LOCK  (F: elenged)"
		elseif s.candidate then status, col = "AIM-9M: HŐFORRÁS A KERESŐBEN - F: lock", WHITE
		else status, col = "AIM-9M: keresés (growl)", DIM end
	elseif sp and sp.guidance == ARH then
		if ac.radar.mode == STT then status = "AIM-120A: radar lock OK"
		else status, col = "AIM-120A: nincs lock (maddog) - T: radar lock", AMBER end
	end
	self:text(status, self.w / 2, yb + 2 * lh, col, fs, "center")
	local r = ac.radar
	if r.mode == STT and r.trackPos then
		local rel = sub(r.trackPos, ac.pos)
		local vc = -dot(sub(r.trackVel, ac.vel), norm(rel))
		local asp = round(angleBetween(r.trackVel, sub(ac.pos, r.trackPos)) / DEG)
		self:text("STT " .. fix(len(rel) / 1000) .. " km  Vc " .. round(vc * 3.6) .. " km/h  ASP " .. asp .. (r.notched and "  NOTCH!" or ""), self.w / 2, yb + 3 * lh, r.notched and AMBER or GREEN, fs, "center")
	elseif r.mode == ACM then self:text("ACM: tedd az orrod elé a célt", self.w / 2, yb + 3 * lh, AMBER, fs, "center") end
end
function Hud:radarScope(ac)
	local r = ac.radar
	local sp, u = r.spec, self.u
	local size = 200 * u
	local hw = size / 2
	-- touch layout: the buttons own the bottom corners, the scope goes up under the top buttons
	local cx = self.w - hw - 24 * u
	local cy = self.touchLayout and 175 * u + hw or self.h - hw - 24 * u
	local left, top, bottom = cx - hw, cy - hw, cy + hw
	self.g:fillRect(left, top, size, size, { 4, 16, 8, 0.45 })
	self:rect(cx, cy, hw, hw, DIM)
	local tgt = r.locked or r.selected or r.pending
	local scale = 40000
	if r.mode == ACM then scale = 20000
	elseif tgt then
		local d = len(sub(tgt.pos, ac.pos))
		scale = 80000
		for _, s in ipairs({ 10000, 20000, 40000, 80000 }) do if d < s * 0.85 then scale = s; break end end
	end
	local azMax = sp.scanAz * DEG
	local function toXY(az, d) return cx + clamp(az / azMax, -1, 1) * hw, bottom - min(d / scale, 1) * size end
	for k = 1, 3 do
		local y = bottom - size * k / 4
		self:line(left, y, left + 8 * u, y, DIM); self:line(left + size - 8 * u, y, left + size, y, DIM)
	end
	for _, az in ipairs({ -30, 0, 30 }) do
		local x = cx + az / sp.scanAz * hw
		self:line(x, bottom, x, bottom - 8 * u, DIM)
	end
	self:text(r.mode .. "  " .. (scale / 1000) .. " km", left + 4 * u, top - 10 * u, GREEN, 11 * u + 2)
	self:text("RADAR", left + size, top - 10 * u, DIM, 11 * u + 2, "right")
	if r.mode == OFF then self:text("KI", cx, cy, DIM, 18 * u, "center"); return end
	if r.mode == SEARCH then
		local x = cx + r.beamAz / azMax * hw
		self:line(x, bottom, x, top, { 107, 255, 133, 0.25 })
	elseif r.mode == ACM then
		local w = sp.acmAz / sp.scanAz * hw
		local y = bottom - min(sp.acmRange / scale, 1) * size
		self:poly({ { cx - w, bottom }, { cx - w, y }, { cx + w, y }, { cx + w, bottom } }, AMBER, false)
	end
	for t, c in pairs(r.contacts) do
		if t ~= r.locked then
			local x, y = toXY(c.az, c.range)
			self.g:fillRect(x - 4 * u, y - 4 * u, 8 * u, 8 * u, GREEN)
			if t == r.selected then
				self:brackets(x, y, 12 * u, GREEN)
				self:text(fix(t.pos.z / 1000), x + 15 * u, y, DIM, 10 * u + 2)
			end
		end
	end
	if r.pending and blinkOf(self.time, 8) then
		local az, _, d = r:anglesTo(r.pending.pos)
		local x, y = toXY(az, d)
		self:brackets(x, y, 14 * u, AMBER)
	end
	if r.locked and r.trackPos then
		local az, _, d = r:anglesTo(r.trackPos)
		local x, y = toXY(az, d)
		local col = r.lostTime > 0 and AMBER or GREEN
		self:poly({ { x, y - 10 * u }, { x + 10 * u, y }, { x, y + 10 * u }, { x - 10 * u, y } }, col)
		local hl = toLocal(ac.quat, r.trackVel)
		local hn = sqrt(hl.x * hl.x + hl.y * hl.y)
		if hn > 1 then self:line(x, y, x + hl.x / hn * 24 * u, y - hl.y / hn * 24 * u, col) end
		self:text(fix(r.trackPos.z / 1000), x + 15 * u, y, col, 10 * u + 2)
	end
end
function Hud:rwrScope(ac)
	local u = self.u
	local R = 90 * u
	local cx = R + 26 * u
	local cy = self.touchLayout and 125 * u + R or self.h - R - 26 * u
	self.g:fillCircle(cx, cy, R, { 4, 16, 8, 0.45 })
	self:circle(cx, cy, R, DIM); self:circle(cx, cy, R * 0.5, { 107, 255, 133, 0.25 })
	for k = 0, 11 do
		local a = k * pi / 6
		self:line(cx + sin(a) * R, cy - cos(a) * R, cx + sin(a) * R * 0.92, cy - cos(a) * R * 0.92, DIM)
	end
	self:text("RWR", cx - R, cy - R + 4 * u, DIM, 11 * u + 2)
	local blink = blinkOf(self.time, 6)
	for _, t in ipairs(ac.rwr.threats) do
		local rad, col = R * 0.82, GREEN
		local skip = false
		if t.level == "launch" then
			if not blink then skip = true end
			rad, col = R * 0.32, RED
		elseif t.level == "lock" then rad, col = R * 0.58, AMBER end
		if not skip then
			local x, y = cx + sin(t.bearing) * rad, cy - cos(t.bearing) * rad
			self:text(t.symbol, x, y, col, 14 * u + 2, "center")
			if t.level ~= "search" then self:circle(x, y, 13 * u, col) end
		end
	end
end
function Hud:warnings(ac, world)
	local u, terr = self.u, world.terrain
	local blink = blinkOf(self.time, 4)
	local y = self.h / 2 - 220 * u
	local function big(t, c, s)
		s = s or 30
		self:text(t, self.w / 2, y, c, s * u + 4, "center", TITLE)
		y = y + (s + 12) * u
	end
	local ahead = add(ac.pos, mul(ac.vel, 4))
	local agl = ac.pos.z - terr:height(ac.pos.x, ac.pos.y)
	if not ac.onGround and ac.fm.gearPos < 0.5 and (ahead.z < terr:height(ahead.x, ahead.y) + 60 or (agl < 150 and ac.vel.z < -15)) and blink then big("PULL UP", RED) end
	if ac.rwr.maxLevel >= 3 then
		if blink then big("MISSILE!", RED) end
	elseif ac.rwr.maxLevel == 2 then big("RADAR LOCK", AMBER, 22) end
	if ac.fm.ias < 70 and not ac.onGround then big("SPEED LOW", AMBER, 22) end
	if not ac.onGround and ac.fm.gearPos < 0.98 and agl < 300 and ac.fm.ias < 95 and ac.vel.z < -2 and blink then big("FUTÓMŰ!", RED, 24) end
	if ac.fm.gearPos > 0.02 and ac.fm.ias > 155 and blink then big("GEAR SPEED", AMBER, 22) end
	if ac.fm.fuel > 0 and ac.fm.fuel < ac.spec.internalFuel * 0.12 then big("BINGO FUEL", AMBER, 22) end
	local my = self.h / 2 - 130 * u
	for _, m in ipairs(self.messages) do
		self:text(m.text, self.w / 2, my, m.color, 16 * u + 3, "center")
		my = my + 22 * u + 4
	end
end
function Hud:missileList(ac, world)
	local y = 110 * self.u
	for _, m in ipairs(world.missiles) do
		if m.shooter == ac then
			local ttg = W.timeToImpact(m)
			local col = (m.status == "TRACK" or m.status == "ACTIVE" or m.status == "DATALINK") and CYAN or AMBER
			self:text(m.spec.name .. " " .. padEnd(m.status, 8) .. " " .. ((ttg ~= nil and ttg < 99) and (fix(ttg) .. "s") or "--"), self.w - 20 * self.u, y, col, 11 * self.u + 3, "right")
			y = y + 18 * self.u + 3
		end
	end
end
-- G-LOC grey-out / blackout under sustained positive G, red-out under negative G
function Hud:gEffects(ac, dt)
	if not ac or not ac.alive then self.black, self.red = 0, 0; return end
	local g = ac.fm.gLoad
	-- G-suit: up to ~8 G the pilot keeps the picture; a held 9 G turn greys out slowly (~6 s)
	self.black = clamp(self.black + (g > 8.2 and (g - 8.2) * 0.12 or g < 7 and -0.4 or 0) * dt, 0, 1)
	self.red = clamp(self.red + (g < -1.8 and (-g - 1.8) * 0.35 or -0.6) * dt, 0, 1)
	if self.black > 0.01 then self.g:vignette({ 0, 0, 0 }, min(0.97, self.black * 1.4), 0.75 - self.black * 0.8, self.black > 0.6 and (self.black - 0.6) * 2.2 or 0) end
	if self.red > 0.01 then self.g:vignette({ 150, 0, 0 }, min(0.97, self.red * 1.4), 0.75 - self.red * 0.8, self.red > 0.6 and (self.red - 0.6) * 2.2 or 0) end
end
-- missiles flying at the player: red marker (or edge arrow) with distance and time to impact
function Hud:incomingMissiles(ac)
	local u = self.u
	local blink = blinkOf(self.time, 6)
	for _, e in ipairs(ac.rwr.incoming) do
		local m, dist = e.missile, e.dist
		local px, py = self:project(m.pos)
		local closing = dot(sub(m.vel, ac.vel), norm(sub(ac.pos, m.pos)))
		local tti = closing > 1 and dist / closing or nil
		if not px then self:edgeArrow(m.pos, RED)
		else
			local k = 14 * u
			self:poly({ { px, py - k }, { px + k, py }, { px, py + k }, { px - k, py } }, RED)
			if blink then self:circle(px, py, 22 * u, RED) end
			self:text("RAKÉTA " .. fix(dist / 1000) .. " km" .. ((tti ~= nil and tti < 60) and ("  " .. fix(tti) .. " s") or ""), px + 26 * u, py, RED, 12 * u + 2)
		end
	end
end
function Hud:overlay(game)
	local u = self.u
	local fs = 12 * u + 3
	self:text((game.missionLine or ("HULLÁM " .. (game.wave or 0))) .. "   LELŐVE " .. (game.kills or 0) .. "   HALÁL " .. (game.deaths or 0), 20 * u, 22 * u, WHITE, fs)
	local hint = self.cockpit and "H = súgó   Esc = menü   N = kijelzők nézése   J / K / L = lapozás" or "H = súgó   Esc = menü   V = kabin   N = kijelzők"
	self:text(hint, 20 * u, 42 * u, DIM, 11 * u + 2)
	-- F-16: where the extreme mode is (it has no menu entry, only the key)
	local p = self.player
	if p and p.alive and p.spec.tvc and not p.spec.tvcAlways then
		self:text(p.extreme and "Tab = EXTRÉM mód KI" or "Tab = EXTRÉM mód (TVC, 9 G, Cobra)", 20 * u + self.g:measure(hint .. "   ", 11 * u + 2), 42 * u, AMBER, 11 * u + 2)
	end
	local y = 22 * u
	for _, k in ipairs(self.killfeed) do
		self:text(k.text, self.w - 20 * u, y, k.color, fs, "right")
		y = y + 20 * u + 3
	end
	if game.banner and game.banner ~= "" then self:text(game.banner, self.w / 2, self.h / 2 - 40 * u, WHITE, 44 * u + 6, "center", TITLE) end
	if game.subBanner and game.subBanner ~= "" then self:text(game.subBanner, self.w / 2, (game.banner and game.banner ~= "") and self.h / 2 + 10 * u or 80 * u, WHITE, 15 * u + 3, "center") end
end

return H
