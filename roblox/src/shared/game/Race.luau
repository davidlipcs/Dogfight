--!nonstrict
-- Ring race (Gyűrűverseny), canyon run (Kanyonfutam) and tunnel run (Alagútfutam): the port of web/js/race.js, canyon.js and
-- tube.js without the pictures.  Every ring has c (centre), n (the way through), and the fields color / opacity / visible that
-- paint() sets and the client draws.  The course is worked out from the terrain itself, so times can be compared.
-- Common subset of Lua 5.4 and Luau (tested outside of Roblox).
local M = require(script.Parent.Parent.sim.SimMath)
local V, add, sub, mul, dot, len, norm = M.V, M.add, M.sub, M.mul, M.dot, M.len, M.norm
local sin, cos, atan, abs, max, min, sqrt, pi = math.sin, math.cos, math.atan, math.abs, math.max, math.min, math.sqrt, math.pi
local atan2 = M.atan2

local R = {}

local function wrap(a) return atan2(sin(a), cos(a)) end

-- ------------------------------------------------------------------ the ring race
local Race = {}
Race.__index = function(t, k)
	local m = Race[k]
	if m ~= nil then return m end
	if k == "target" then
		if t.finished then return nil end
		return t.rings[t.next + 1]
	end
	return nil
end
R.Race = Race

R.RINGS, R.STEP, R.RING_R = 18, 1600, 55

-- opts: rings (count), goal (where the course heads), best (the record so far), R (ring radius), onRecord(time)
function Race.new(terrain, start, heading, opts)
	local self = setmetatable({}, Race)
	Race.init(self, terrain, start, heading, opts)
	return self
end
function Race.init(self, terrain, start, heading, opts)
	opts = opts or {}
	self.terrain = terrain
	self.count = opts.rings or R.RINGS
	self.goal = opts.goal
	self.keep = opts.record ~= false
	self.R = opts.R or R.RING_R
	self.onRecord = opts.onRecord
	self.best = opts.best
	self.rings = self:layout(start, heading)
	self:reset()
end
function Race:layout(start, heading)
	local t = self.terrain
	local lim, out = t.half * 0.8, {}
	local p, h = V(start.x, start.y, 0), heading
	local function ground(x, y) return t:height(x, y) end
	local goal = self.goal or V(-12000, 9000, 0)
	for i = 0, self.count - 1 do
		local best = nil
		local want = 28 * sin(i * 0.9) * pi / 180
		local toGoal = atan2(goal.x - p.x, goal.y - p.y)
		for a = -50, 50, 10 do
			local hh = h + a * pi / 180
			local q = V(p.x + sin(hh) * R.STEP, p.y + cos(hh) * R.STEP, 0)
			local g, gm = ground(q.x, q.y), ground((p.x + q.x) / 2, (p.y + q.y) / 2)
			local score = (g + gm * 0.6) * 0.5 + abs(a * pi / 180 - want) * 260 + abs(wrap(hh - toGoal)) * 220
			if g < 15 then score = score + 900 end
			if abs(q.x) > lim or abs(q.y) > lim then score = score + 5000 end
			if not best or score < best.score then best = { score = score, q = q, hh = hh } end
		end
		local top = 0
		for k = 0, 6 do
			top = max(top, ground(p.x + (best.q.x - p.x) * k / 6, p.y + (best.q.y - p.y) * k / 6))
		end
		local c = V(best.q.x, best.q.y, max(top + 140, ground(best.q.x, best.q.y) + 110, 180))
		out[#out + 1] = { c = c, n = norm(V(best.q.x - p.x, best.q.y - p.y, 0)) }
		p, h = best.q, best.hh
	end
	return out
end
function Race:reset()
	self.next, self.time, self.running, self.finished, self.missTime = 0, 0, false, false, -9
	self:paint()
end
-- colours are sRGB hex numbers like the browser's
function Race:paint()
	for i, r in ipairs(self.rings) do
		local k = i - 1
		r.visible = k >= self.next
		r.color = k == self.next and 0xffc840 or k == self.next + 1 and 0x6bff85 or 0x9fb0bf
		r.opacity = k == self.next and 0.95 or k == self.next + 1 and 0.7 or 0.35
	end
end
-- returns "ring" | "finish" | "miss" | nil.  prev: where the aircraft was a step ago
function Race:update(dt, ac, prev)
	if self.finished then return nil end
	if self.running then self.time = self.time + dt end
	local r = self.rings[self.next + 1]
	local s0, s1 = dot(sub(prev, r.c), r.n), dot(sub(ac.pos, r.c), r.n)
	if s0 < 0 and s1 >= 0 then
		local hit = add(prev, mul(sub(ac.pos, prev), s0 / (s0 - s1)))
		local off = len(sub(hit, r.c))
		if off <= self.R then
			self.next = self.next + 1
			self.running = true
			if self.next >= #self.rings then
				self.finished = true
				self.record = (not self.best) or self.time < self.best
				if self.record and self.keep then
					self.best = self.time
					if self.onRecord then self.onRecord(self.time) end
				end
				self:paint()
				return "finish"
			end
			self:paint()
			return "ring"
		end
		if off < self.R * 2.5 then return "miss" end
	end
	return nil
end

-- m:ss.s
function R.fmtTime(s)
	if s == nil then return "--" end
	local m = math.floor(s / 60)
	local sec = string.format("%.1f", s % 60)
	if #sec < 4 then sec = "0" .. sec end
	return m .. ":" .. sec
end

-- ------------------------------------------------------------------ the canyon run
local Canyon = setmetatable({}, { __index = Race })
Canyon.__index = function(t, k)
	local m = Canyon[k]
	if m ~= nil then return m end
	if k == "finalTime" then return t.time + t.penalty end
	return getmetatable(Canyon).__index[k] or Race.__index(t, k)
end
R.Canyon = Canyon
R.CANYON_LIMIT, R.CANYON_GATES, R.CANYON_STEP, R.CANYON_FLOOR = 135, 30, 850, 75

function Canyon.new(terrain, opts)
	opts = opts or {}
	local self = setmetatable({}, Canyon)
	self.limit, self.penalty, self.exposure = R.CANYON_LIMIT, 0, 0
	self.canyonOnRecord = opts.onRecord
	Race.init(self, terrain, V(0, 0, 0), 0, { rings = R.CANYON_GATES + 2, R = 60, record = false, best = opts.best })
	local g = self.rings[self.targetIdx + 1]
	local tp = add(g.c, mul(g.n, 260))
	self.targetPos = V(tp.x, tp.y, terrain:height(tp.x, tp.y))
	self:reset()
	return self
end
function Canyon:layout()
	local t = self.terrain
	local function g(x, y) return t:height(x, y) end
	local lim = t.half * 0.82
	local GATES, STEP, FLOOR = R.CANYON_GATES, R.CANYON_STEP, R.CANYON_FLOOR
	-- 1. the deepest gorge: the point with the most relief around it
	local best = nil
	local x = -lim
	while x <= lim do
		local y = -lim
		while y <= lim do
			local h = g(x, y)
			if h >= 25 then
				local top = h
				for a = 0, 7 do
					top = max(top, g(x + cos(a * pi / 4) * 2400, y + sin(a * pi / 4) * 2400))
				end
				local score = top - h - max(0, h - 600) * 0.2
				if not best or score > best.score then best = { score = score, x = x, y = y, h = h } end
			end
			y = y + 800
		end
		x = x + 800
	end
	local function follow(p0, h0, n)
		local out, p, h, cost = {}, V(p0.x, p0.y, 0), h0, 0
		for _ = 1, n do
			local pick = nil
			for a = -24, 24, 4 do
				local hh = h + a * pi / 180
				local q = V(p.x + sin(hh) * STEP, p.y + cos(hh) * STEP, 0)
				local gq, gm = g(q.x, q.y), g((p.x + q.x) / 2, (p.y + q.y) / 2)
				local sx, sy = cos(hh) * 220, -sin(hh) * 220
				local wall = min(g(q.x + sx, q.y + sy), g(q.x - sx, q.y - sy)) - gq
				local score = gq + gm * 0.5 + abs(a) * 1.4 - min(wall, 300) * 0.35
				if gq < 15 then score = score + 800 end
				if abs(q.x) > lim or abs(q.y) > lim then score = score + 6000 end
				if not pick or score < pick.score then pick = { score = score, q = q, hh = hh, gq = gq } end
			end
			cost = cost + pick.gq
			out[#out + 1] = pick
			p, h = pick.q, pick.hh
		end
		return { out = out, cost = cost }
	end
	-- 2. the direction along the gorge that is longest and lowest
	local line = nil
	for k = 0, 15 do
		local h0 = k * pi / 8
		local r = follow(best, h0, GATES)
		if not line or r.cost < line.cost then line = r end
	end
	local rings = {}
	local prev = V(best.x, best.y, 0)
	for _, s in ipairs(line.out) do
		rings[#rings + 1] = { c = V(s.q.x, s.q.y, s.gq + FLOOR), n = norm(V(s.q.x - prev.x, s.q.y - prev.y, 0)) }
		prev = s.q
	end
	-- 3. the target gate is the last gate; after it the pull-up over the ridge
	self.targetIdx = #rings - 1
	local last = rings[#rings]
	local fwd = last.n
	local base = V(last.c.x + fwd.x * 260, last.c.y + fwd.y * 260, 0)
	local climb = nil
	local hBase, zT = atan2(fwd.x, fwd.y), last.c.z
	for a = -70, 70, 10 do
		local hh = hBase + a * pi / 180
		local D = 2600
		local q = V(base.x + sin(hh) * D, base.y + cos(hh) * D, 0)
		local top = g(q.x, q.y)
		for k = 1, 8 do top = max(top, g(base.x + (q.x - base.x) * k / 8, base.y + (q.y - base.y) * k / 8)) end
		local z = top + 170
		local slope = (z - zT) / D
		local score = (slope > 0.84 and 1000 + slope * 100 or 0) - top + abs(a) * 0.8
		if not climb or score < climb.score then climb = { score = score, q = q, z = z, hh = hh } end
	end
	rings[#rings + 1] = { c = V(climb.q.x, climb.q.y, climb.z), n = norm(V(sin(climb.hh), cos(climb.hh), 0.2)) }
	return rings
end
function Canyon:reset()
	Race.reset(self)
	self.penalty, self.exposure, self.hit, self.warnT = 0, 0, false, 0
	self.targetVisible = true
end
function Canyon:paint()
	Race.paint(self)
	local t = self.rings[self.targetIdx + 1]
	if t and self.next <= self.targetIdx then
		t.color = self.next == self.targetIdx and 0xff3b2a or 0xb0463a
		t.opacity = self.next == self.targetIdx and 0.95 or 0.5
	end
	local c = self.rings[#self.rings]
	if c and self.next == #self.rings - 1 then c.color, c.opacity = 0x62d9ff, 0.95 end
end
-- "ring" | "target" | "finish" | "miss" | "radar" | nil
function Canyon:update(dt, ac, prev)
	local ev = Race.update(self, dt, ac, prev)
	if self.finished then
		if ev ~= "finish" then return nil end
		self.time = self.time + self.penalty                          -- the radar penalties count
		self.success = self.time <= self.limit
		self.record = self.success and ((not self.best) or self.time < self.best)
		if self.record then
			self.best = self.time
			if self.canyonOnRecord then self.canyonOnRecord(self.time) end
		end
		return "finish"
	end
	-- above 350 m the enemy radar sees you (not on the final climb)
	if self.running and self.next <= self.targetIdx then
		local agl = ac.pos.z - self.terrain:height(ac.pos.x, ac.pos.y)
		if agl > 350 then self.exposure = self.exposure + dt else self.exposure = max(0, self.exposure - dt) end
		if self.exposure > 4 then
			self.exposure = 0
			self.penalty = self.penalty + 5
			return "radar"
		end
	end
	if ev == "ring" and self.next - 1 == self.targetIdx then
		self.hit = true
		self.targetVisible = false
		return "target"
	end
	return ev
end

-- ------------------------------------------------------------------ the tunnel run
local Tube = setmetatable({}, { __index = Race })
Tube.__index = function(t, k)
	local m = Tube[k]
	if m ~= nil then return m end
	if k == "total" then return t.laps * t.count end
	if k == "lap" then return min(t.laps, math.floor(t.next / t.count) + 1) end
	if k == "target" then
		if t.finished then return nil end
		return t.rings[t.next % t.count + 1]
	end
	if k == "clock" then return t.time + t.penalty end
	return nil
end
R.Tube = Tube
R.TUBE_GATES, R.TUBE_LAPS, R.TUBE_R = 28, 3, 95
local SAMPLES, SHAPE_R = 360, 1500

-- centre: the middle of the circuit (x, y); opts.best / opts.bestLap / opts.onRecord(best, lap)
function Tube.new(terrain, centre, opts)
	opts = opts or {}
	local self = setmetatable({}, Tube)
	self.laps, self.limit = R.TUBE_LAPS, nil
	self.centre = centre
	self.bestLap = opts.bestLap
	self.tubeOnRecord = opts.onRecord
	Race.init(self, terrain, centre, 0, { rings = R.TUBE_GATES, R = 80, record = false, best = opts.best })
	self:reset()
	return self
end
function Tube:layout(centre)
	local t = self.terrain
	local N = SAMPLES
	local function shape(u) return SHAPE_R * (1 + 0.18 * sin(2 * u + 0.6) + 0.1 * sin(3 * u + 1.9)) end
	local flat = {}
	local top = 0
	for i = 0, N - 1 do
		local u = i / N * pi * 2
		local r = shape(u)
		local x, y = centre.x + sin(u) * r, centre.y - cos(u) * r
		flat[#flat + 1] = { x, y, u }
		for a = 0, 5 do
			top = max(top, t:height(x + cos(a * 1.047) * 120, y + sin(a * 1.047) * 120))
		end
	end
	local base = top + 240
	self.samples = {}
	for i, f in ipairs(flat) do self.samples[i] = V(f[1], f[2], base + 70 * sin(2 * f[3] + 1)) end
	self.lapLength = 0
	for i = 0, N - 1 do
		self.lapLength = self.lapLength + len(sub(self.samples[(i + 1) % N + 1], self.samples[i + 1]))
	end
	local out = {}
	for k = 0, self.count - 1 do
		local i = math.floor(k * N / self.count)
		local a, b = self.samples[(i + N - 1) % N + 1], self.samples[(i + 1) % N + 1]
		out[#out + 1] = { c = M.copy(self.samples[i + 1]), n = norm(sub(b, a)) }
	end
	return out
end
-- where the player starts: a little before the start gate, on the middle line, flying along it
function Tube:startPose(back)
	back = back or 550
	local N = SAMPLES
	local step = self.lapLength / N
	local i = (N - math.floor(back / step + 0.5)) % N
	local a, b = self.samples[i + 1], self.samples[(i + 3) % N + 1]
	local d = norm(sub(b, a))
	return { pos = M.copy(a), heading = atan2(d.x, d.y) / (pi / 180), dir = d }
end
function Tube:reset()
	Race.reset(self)
	self.next, self.penalty, self.outside, self.warnT = 0, 0, false, 0
	self.lapStart, self.lapTimes, self.lastLap, self.finalTime, self.success = 0, {}, nil, nil, true
	self:paint()
end
function Tube:paint()
	local P = #self.rings
	local cur = self.next % P
	for i, r in ipairs(self.rings) do
		local k = i - 1
		r.visible = true
		r.color = k == cur and 0xffc840 or k == (cur + 1) % P and 0x6bff85 or k == 0 and 0xfff2b0 or 0x9fb0bf
		r.opacity = k == cur and 0.95 or k == (cur + 1) % P and 0.7 or k == 0 and 0.6 or 0.3
	end
end
-- distance of a point from the middle line of the tube
function Tube:offAxis(p)
	local best = 1e18
	for _, s in ipairs(self.samples) do
		local d = (s.x - p.x) ^ 2 + (s.y - p.y) ^ 2 + (s.z - p.z) ^ 2
		if d < best then best = d end
	end
	return sqrt(best)
end
-- "ring" | "lap" | "finish" | "out" | nil
function Tube:update(dt, ac, prev)
	if self.finished then return nil end
	local ev = nil
	if self.running then self.time = self.time + dt end
	local P = self.count
	local r = self.rings[self.next % P + 1]
	local s0, s1 = dot(sub(prev, r.c), r.n), dot(sub(ac.pos, r.c), r.n)
	if s0 < 0 and s1 >= 0 then
		local hit = add(prev, mul(sub(ac.pos, prev), s0 / (s0 - s1)))
		if len(sub(hit, r.c)) <= self.R then
			self.next = self.next + 1
			self.running = true
			ev = "ring"
			if self.next % P == 0 then
				local t = self.clock
				self.lastLap = t - self.lapStart
				self.lapStart = t
				self.lapTimes[#self.lapTimes + 1] = self.lastLap
				if not self.bestLap or self.lastLap < self.bestLap then self.bestLap = self.lastLap end
				ev = "lap"
				if self.next >= self.total then
					self.finished = true
					self.finalTime = t
					self.record = (not self.best) or t < self.best
					if self.record then self.best = t end
					if self.tubeOnRecord then self.tubeOnRecord(self.best, self.bestLap) end
					self:paint()
					return "finish"
				end
			end
			self:paint()
		end
	end
	if self.running then
		local out = self:offAxis(ac.pos) > R.TUBE_R
		if out then
			self.penalty = self.penalty + dt
			self.warnT = self.warnT - dt
		end
		if out and not self.outside and self.warnT <= 0 then
			self.outside = true
			self.warnT = 3
			if not ev then ev = "out" end
		end
		if not out then self.outside = false end
	end
	return ev
end

return R
