--!nonstrict
-- The cockpit displays (multi function displays): the port of web/js/mfd.js.  Pages like the real ones - radar (B-scope), situation map
-- (HSD), stores (SMS), engines and performance, RWR and the data line (DED / UFCD) - drawn on canvases the client gives to the displays
-- (display.g, a GuiCanvas of display.w x display.h pixels with the methods of shared/game/Hud.luau plus g:fillPoly(pts, c)).
-- Common subset of Lua 5.4 and Luau.
local M = require(script.Parent.Parent.sim.SimMath)
local Specs = require(script.Parent.Parent.sim.Specs)
local W = require(script.Parent.Parent.sim.Weapons)
local Flight = require(script.Parent.Parent.sim.Flight)
local V, sub, len, norm, dot, clamp, DEG = M.V, M.sub, M.len, M.norm, M.dot, M.clamp, M.DEG
local toLocal, headingDeg, angleBetween = M.toLocal, M.headingDeg, M.angleBetween
local sin, cos, floor, abs, min, max, sqrt, atan2, pi = math.sin, math.cos, math.floor, math.abs, math.min, math.max, math.sqrt, M.atan2, math.pi
local IR, ARH = Specs.IR, Specs.ARH
local STT, ACM, OFF = W.STT, W.ACM, W.OFF

local C = {
	bg = { 2, 8, 5, 1 }, g = { 82, 255, 115, 1 }, gd = { 44, 156, 71, 1 }, gdd = { 20, 69, 31, 1 }, w = { 234, 255, 234, 1 }, a = { 255, 194, 58, 1 },
	r = { 255, 75, 59, 1 }, c = { 98, 217, 255, 1 },
}
local PAGE_NAMES = { radar = "RDR", sa = "SA", sms = "SMS", eng = "ENG", rwr = "RWR" }

-- screen name -> size, pages and the key that cycles them (the screens of the browser's cockpit models)
local LAYOUTS = {
	f16 = {
		{ name = "mfd_l", w = 512, h = 512, pages = { "radar", "sms", "eng" }, key = "J" },
		{ name = "mfd_r", w = 512, h = 512, pages = { "sa", "eng", "sms" }, key = "K" },
		{ name = "ded", w = 512, h = 180, pages = { "ded" } },
		{ name = "rwr", w = 256, h = 256, pages = { "rwrmini" } },
	},
	fa18 = {
		{ name = "screen_ddi_l", w = 512, h = 512, pages = { "eng", "sms", "rwr" }, key = "J" },
		{ name = "screen_ddi_r", w = 512, h = 512, pages = { "radar", "sms" }, key = "K" },
		{ name = "screen_ampcd", w = 512, h = 512, pages = { "sa", "rwr" }, key = "L" },
		{ name = "screen_ufcd", w = 512, h = 420, pages = { "ded" } },
	},
	f15 = {
		{ name = "screen_lad_l", w = 512, h = 512, pages = { "radar", "sms" }, key = "J" },
		{ name = "screen_lad_r", w = 512, h = 512, pages = { "sa", "eng", "rwr" }, key = "K" },
		{ name = "screen_ufc", w = 512, h = 205, pages = { "ded" } },
	},
	f22 = {
		{ name = "screen_mfd_l", w = 512, h = 512, pages = { "eng", "rwr" }, key = "J" },
		{ name = "screen_mfd_r", w = 512, h = 512, pages = { "radar", "sms" }, key = "K" },
		{ name = "screen_pmfd", w = 512, h = 512, pages = { "sa", "rwr" }, key = "L" },
		{ name = "screen_mfd_c", w = 512, h = 512, pages = { "sms" } },
		{ name = "screen_ufd_l", w = 512, h = 394, pages = { "ded" } },
		{ name = "screen_ufd_r", w = 333, h = 256, pages = { "rwrmini" } },
	},
}
local SIDE_KEYS = { left = "J", right = "K", center = "L" }

local function bearingTo(ac, p) return ((atan2(p.x - ac.pos.x, p.y - ac.pos.y) / DEG) + 360) % 360 end
local function pad3(d) return string.format("%03d", floor(d + 0.5) % 360) end
local function km(m) return m >= 10000 and string.format("%.0f", m / 1000) or string.format("%.1f", m / 1000) end
local function fix(x, n) return string.format("%." .. (n or 1) .. "f", x) end
local function round(x) return floor(x + 0.5) end
local function padL(s, n) s = tostring(s); return string.rep(" ", max(0, n - #s)) .. s end
local function padR(s, n) s = tostring(s); return s .. string.rep(" ", max(0, n - #s)) end
local function count(t) local n = 0 for _ in pairs(t) do n = n + 1 end return n end

local D = {}
D.LAYOUTS = LAYOUTS

local Mfd = {}
Mfd.__index = Mfd

-- spec: the aircraft spec; returns the displays (a list of { name, w, h, pages, key, page }) - the client gives each one its canvas g
function D.new(spec)
	local self = setmetatable({}, Mfd)
	self.spec, self.time, self.gHi, self.gLo, self.dlzCache = spec, 0, 1, 1, {}
	self.list = {}
	local layout = LAYOUTS[spec.mfdLayout or ""] or LAYOUTS[spec.model] or LAYOUTS.f16
	for _, lay in ipairs(layout) do
		self.list[#self.list + 1] = { name = lay.name, w = lay.w, h = lay.h, pages = lay.pages, key = lay.key, page = 1 }
	end
	return self
end

function Mfd:cycle(side)
	for _, d in ipairs(self.list) do
		if d.key == SIDE_KEYS[side] and #d.pages > 1 then
			d.page = d.page % #d.pages + 1
			return PAGE_NAMES[d.pages[d.page]]
		end
	end
	return nil
end

-- every display with a canvas is drawn; info: { zone, base, wave, enemies }
function Mfd:update(dt, ac, world, info)
	self.time = self.time + dt
	if ac.alive then
		self.gHi = max(self.gHi, ac.fm.gLoad)
		self.gLo = min(self.gLo, ac.fm.gLoad)
	end
	for _, d in ipairs(self.list) do
		if d.g then self:draw(d, ac, world, info) end
	end
end

-- ----------------------------------------------------------------- primitives
local function text(g, t, x, y, col, size, align) g:text(t, x, y, col, size, align or "left") end
local function line(g, x1, y1, x2, y2, col, w)
	g:lineWidth(w or 2.5)
	g:line(x1, y1, x2, y2, col)
end
local function circle(g, x, y, r, col, w)
	g:lineWidth(w or 2.5)
	g:arc(x, y, r, col)
end
local function poly(g, pts, col, fill, w)
	if fill then g:fillPoly(pts, col)
	else
		g:lineWidth(w or 2.5)
		for i = 1, #pts do
			local a, b = pts[i], pts[i % #pts + 1]
			g:line(a[1], a[2], b[1], b[2], col)
		end
	end
end
local function box(g, x, y, w, h, col, lw)
	g:lineWidth(lw or 2.5)
	g:strokeRect(x, y, w, h, col)
end
local function dashedLine(g, x1, y1, x2, y2, col, w, on, off)
	g:lineWidth(w or 2.5)
	g:dashed(x1, y1, x2, y2, col, on, off)
end

function Mfd:draw(d, ac, world, info)
	local g, Wd, H = d.g, d.w, d.h
	g:fillRect(0, 0, Wd, H, C.bg)
	if not ac.alive then
		text(g, "NO DATA", Wd / 2, H / 2, C.gd, round(H / 8), "center")
		return
	end
	local page = d.pages[d.page]
	self[page](self, g, Wd, H, ac, world, info, d)
	if #d.pages > 1 then self:osb(g, Wd, H, d) end
end

-- push-button labels along the bottom edge: the pages of this display, the shown one boxed
function Mfd:osb(g, Wd, H, d)
	local n = #d.pages
	local step = Wd / (n + 1)
	for i, p in ipairs(d.pages) do
		local x = step * i
		local active = i == d.page
		text(g, PAGE_NAMES[p], x, H - 18, active and C.w or C.gd, 24, "center")
		if active then box(g, x - 34, H - 34, 68, 32, C.w, 2) end
	end
	if d.key then text(g, d.key, Wd - 14, H - 18, C.gdd, 20, "right") end
end

-- ------------------------------------------------------------------ radar
function Mfd:radar(g, Wd, H, ac, world, info)
	local r = ac.radar
	local sp = r.spec
	local x0, x1, y0, y1 = 34, Wd - 74, 62, H - 150
	local cx, sw, sh = (x0 + x1) / 2, x1 - x0, y1 - y0
	local tgt = r.locked or r.pending or r.selected
	local scale = sp.searchRange > 80000 and 80000 or 40000
	if r.mode == ACM then scale = 20000
	elseif tgt then
		local dd = len(sub(tgt.pos, ac.pos))
		scale = 160000
		for _, s in ipairs({ 10000, 20000, 40000, 80000, 160000 }) do if dd < s * 0.85 then scale = s; break end end
	end
	text(g, r.mode == OFF and "RDR OFF" or r.mode, 14, 24, r.mode == STT and C.w or C.g, 28)
	text(g, (scale / 1000) .. " KM", Wd / 2 - 20, 24, C.g, 28, "center")
	text(g, string.match(sp.name, "APG%-%d+") or "RADAR", Wd - 14, 24, C.gd, 22, "right")
	-- scope frame, azimuth and range ticks
	box(g, x0, y0, sw, sh, C.gd, 2)
	local azMax = sp.scanAz * DEG
	local function toXY(az, dist) return cx + clamp(az / azMax, -1, 1) * sw / 2, y1 - min(dist / scale, 1) * sh end
	for _, az in ipairs({ -30, 0, 30 }) do
		local x = cx + az / sp.scanAz * sw / 2
		dashedLine(g, x, y0, x, y1, C.gdd, 2, 4, 10)
	end
	for k = 1, 3 do
		local y = y1 - sh * k / 4
		line(g, x0, y, x0 + 14, y, C.gd); line(g, x1 - 14, y, x1, y, C.gd)
	end
	text(g, tostring(scale / 2000), x0 + 18, y1 - sh / 2, C.gd, 20)
	if r.mode == OFF then text(g, "R = RADAR BE", cx, (y0 + y1) / 2, C.a, 30, "center")
	elseif r.mode == ACM then
		local w = sp.acmAz / sp.scanAz * sw / 2
		local y = y1 - min(sp.acmRange / scale, 1) * sh
		poly(g, { { cx - w, y1 }, { cx - w, y }, { cx + w, y }, { cx + w, y1 } }, C.a)
	elseif r.mode ~= STT then
		local x = cx + r.beamAz / azMax * sw / 2
		line(g, x, y1, x, y0, { 82, 255, 115, 0.35 }, 3)
	end
	-- own heading caret
	poly(g, { { cx, y1 + 4 }, { cx - 10, y1 + 20 }, { cx + 10, y1 + 20 } }, C.g)
	for t, c in pairs(r.contacts) do
		if t ~= r.locked then
			local x, y = toXY(c.az, c.range)
			local col = t.team == ac.team and C.c or C.g
			g:fillRect(x - 9, y - 9, 18, 18, col)
			local hl = toLocal(ac.quat, c.vel)
			local hn = sqrt(hl.x * hl.x + hl.y * hl.y)
			if hn > 1 then line(g, x, y, x + hl.x / hn * 30, y - hl.y / hn * 30, col) end
			text(g, string.format("%.0f", c.pos.z / 1000), x + 14, y + 16, C.gd, 20)
			if t == r.selected then box(g, x - 16, y - 16, 32, 32, C.w, 2) end
		end
	end
	if r.pending and floor(self.time * 8) % 2 == 0 then
		local az, _, dd = r:anglesTo(r.pending.pos)
		local x, y = toXY(az, dd)
		box(g, x - 20, y - 20, 40, 40, C.a, 3)
	end
	local lines
	if r.locked and r.trackPos then
		local az, _, dd = r:anglesTo(r.trackPos)
		local x, y = toXY(az, dd)
		local col = r.lostTime > 0 and C.a or C.w
		poly(g, { { x, y - 16 }, { x + 16, y }, { x, y + 16 }, { x - 16, y } }, col, true)
		local hl = toLocal(ac.quat, r.trackVel)
		local hn = sqrt(hl.x * hl.x + hl.y * hl.y)
		if hn > 1 then line(g, x, y, x + hl.x / hn * 44, y - hl.y / hn * 44, col, 3.5) end
		local t = r.locked
		local rel = sub(r.trackPos, ac.pos)
		local vc = -dot(sub(r.trackVel, ac.vel), norm(rel))
		local aspDeg = angleBetween(r.trackVel, sub(ac.pos, r.trackPos)) / DEG
		local side = toLocal(t.quat, sub(ac.pos, t.pos)).x >= 0 and "R" or "L"
		local tm = len(r.trackVel) / select(2, Flight.isa(r.trackPos.z))
		lines = {
			{ "STT  " .. km(dd) .. " KM   VC " .. (vc >= 0 and "+" or "") .. round(vc * 3.6), r.notched and C.a or C.w },
			{ "MAG " .. fix(r.trackPos.z / 1000) .. " KM  M" .. fix(tm, 2) .. "  ASP " .. round(aspDeg) .. side, C.g },
			{ "NCTR: " .. (t.spec.short or t.spec.name) .. (r.notched and "   NOTCH!" or r.lostTime > 0 and "   MEMÓRIA" or ""), (r.notched or r.lostTime > 0) and C.a or C.g },
		}
	else
		local n = 0
		for t in pairs(r.contacts) do if t.team ~= ac.team then n = n + 1 end end
		lines = {
			{ "CÉLOK: " .. n, C.g },
			{ r.mode == ACM and "ACM: CÉL AZ ORR ELÉ" or "T = LOCK   Y = KÖV. CÉL", r.mode == ACM and C.a or C.gd },
			{ r.selected and ("KIJELÖLT: " .. km(len(sub(r.selected.pos, ac.pos))) .. " KM  " .. fix(r.selected.pos.z / 1000) .. " KM MAG") or "", C.gd },
		}
	end
	for i, l in ipairs(lines) do text(g, l[1], 22, y1 + 40 + (i - 1) * 30, l[2], 24) end
	self:dlz(g, Wd, H, ac, x1 + 34, y0, y1)
end

-- launch zone of the selected missile against the locked target: Rmax, no-escape range, Rmin, the target
function Mfd:dlz(g, Wd, H, ac, x, y0, y1)
	local sp, r = ac.selectedSpec, ac.radar
	local t = r.mode == STT and r.locked or nil
	if sp and sp.guidance == IR and ac.irSeeker.locked and not ac.irSeeker.target.isFlare then t = ac.irSeeker.target end
	text(g, sp and (sp.guidance == IR and "9M" or "120") or "--", x, y0 - 18, C.g, 22, "center")
	if not sp or not t then return end
	local rel = sub(t.pos, ac.pos)
	local dd = len(rel)
	local closing = -dot(t.vel, norm(rel))
	local z = self.dlzCache[sp]
	if not z or self.time - z.time > 0.5 then
		local a, b = W.launchZone(sp, ac.speed, ac.pos.z, closing)
		z = { time = self.time, rmax = a, rne = b }
		self.dlzCache[sp] = z
	end
	local rmax, rne, rmin = z.rmax, z.rne, sp.minRange
	local scale = max(rmax * 1.25, dd * 1.05, 2000)
	local function ry(v) return y1 - (y1 - y0) * clamp(v / scale, 0, 1) end
	line(g, x, ry(rmin), x, ry(rmax), C.g, 4)
	for _, v in ipairs({ rmax, rmin }) do line(g, x - 12, ry(v), x + 12, ry(v), C.g, 3) end
	line(g, x - 18, ry(rne), x + 18, ry(rne), C.g, 3)
	local yy = ry(dd)
	local inRng = dd > rmin and dd < rmax
	poly(g, { { x - 30, yy - 11 }, { x - 14, yy }, { x - 30, yy + 11 } }, inRng and C.r or C.w, true)
	text(g, km(rmax), x, ry(rmax) - 18, C.gd, 20, "center")
	if inRng and floor(self.time * 4) % 2 == 0 then text(g, dd < rne and "NOESC" or "SHOOT", x, y1 + 24, C.r, 20, "center") end
end

-- ------------------------------------------------------- situation map
function Mfd:sa(g, Wd, H, ac, world, info)
	local hdg = atan2(ac.forward.x, ac.forward.y)
	local ch, sh = cos(hdg), sin(hdg)
	local cx, cy = Wd / 2, H * 0.66
	local enemies = {}
	for _, t in ipairs(world.aircraft) do if t.alive and t.team ~= ac.team then enemies[#enemies + 1] = t end end
	local nearest = math.huge
	for _, t in ipairs(enemies) do nearest = min(nearest, len(sub(t.pos, ac.pos))) end
	local toZone = info.zone and sqrt((info.zone.x - ac.pos.x) ^ 2 + (info.zone.y - ac.pos.y) ^ 2) or 0
	local range = 40000
	if nearest < 14000 then range = 20000 elseif nearest > 40000 and toZone > 38000 then range = 80000 end
	local k = (H * 0.58) / range
	local function toS(p)
		local rx, ry = p.x - ac.pos.x, p.y - ac.pos.y
		return cx + (rx * ch - ry * sh) * k, cy - (rx * sh + ry * ch) * k
	end
	-- (the display's frame clips what is drawn outside of it)
	circle(g, cx, cy, range * k, C.gd, 3); circle(g, cx, cy, range * k / 2, C.gd, 2.5)
	for a = 0, 330, 30 do
		local ang = a * DEG - hdg
		local r0 = range * k
		local r1 = r0 - (a % 90 ~= 0 and 10 or 18)
		line(g, cx + sin(ang) * r0, cy - cos(ang) * r0, cx + sin(ang) * r1, cy - cos(ang) * r1, C.gd, 2)
		if a % 90 == 0 then text(g, string.sub("ÉKDN", 1, 0) .. ({ "É", "K", "D", "N" })[a / 90 + 1], cx + sin(ang) * (r0 - 34), cy - cos(ang) * (r0 - 34), C.gd, 22, "center") end
	end
	if info.base then
		local bx, by = toS(info.base)
		circle(g, bx, by, info.base.r * k, { 98, 217, 255, 0.55 }, 2.5)
		g:fillRect(bx - 4, by - 16, 8, 32, C.c)
		text(g, "BÁZIS", bx + 12, by - 18, C.c, 20)
	end
	if info.zone then
		local zx, zy = toS(info.zone)
		circle(g, zx, zy, info.zone.r * k, { 255, 75, 59, 0.7 }, 3)
		text(g, "HARCI ZÓNA", zx, zy, { 255, 75, 59, 0.85 }, 20, "center")
	end
	-- contacts: radar tracks filled, the rest of the picture (datalink) hollow
	for _, t in ipairs(enemies) do
		local x, y = toS(t.pos)
		local th = atan2(t.forward.x, t.forward.y) - hdg
		local tri = {}
		for _, p in ipairs({ { 0, -14 }, { 10, 10 }, { -10, 10 } }) do
			tri[#tri + 1] = { x + p[1] * cos(th) - p[2] * sin(th), y + p[1] * sin(th) + p[2] * cos(th) }
		end
		local tracked = ac.radar.contacts[t] ~= nil or ac.radar.locked == t
		poly(g, tri, C.r, tracked)
		local vx, vy = sin(th), -cos(th)
		line(g, x + vx * 14, y + vy * 14, x + vx * 34, y + vy * 34, C.r, 2)
		text(g, string.format("%.0f", t.pos.z / 1000), x + 14, y + 14, C.r, 18)
		if ac.radar.locked == t then box(g, x - 20, y - 20, 40, 40, C.w, 2.5) end
	end
	-- missiles: ours cyan, the ones coming at us red
	local blink = floor(self.time * 6) % 2 == 0
	for _, m in ipairs(world.missiles) do
		if m.alive then
			local x, y = toS(m.pos)
			if m.shooter == ac then g:fillCircle(x, y, 5, C.c)
			elseif (m.guidedTarget == ac or m.intended == ac) and blink then text(g, "M", x, y, C.r, 26, "center") end
		end
	end
	-- RWR bearings on the outer ring
	for _, t in ipairs(ac.rwr.threats) do
		local r0 = range * k + 2
		local col = t.level == "launch" and C.r or t.level == "lock" and C.a or C.gd
		line(g, cx + sin(t.bearing) * r0, cy - cos(t.bearing) * r0, cx + sin(t.bearing) * (r0 - 24), cy - cos(t.bearing) * (r0 - 24), col, 5)
	end
	-- own aircraft
	poly(g, { { cx, cy - 18 }, { cx + 12, cy + 12 }, { cx, cy + 5 }, { cx - 12, cy + 12 } }, C.w, true)
	box(g, Wd / 2 - 46, 6, 92, 40, C.g, 2.5)
	text(g, pad3(headingDeg(ac.forward)), Wd / 2, 27, C.w, 30, "center")
	text(g, (range / 1000) .. " KM", 12, 27, C.gd, 22)
	text(g, #enemies .. " BANDITA", Wd - 12, 27, #enemies > 0 and C.r or C.gd, 22, "right")
	local rows = {}
	if info.zone then rows[#rows + 1] = { "ZÓNA " .. pad3(bearingTo(ac, info.zone)) .. "° " .. km(max(0, toZone - info.zone.r)) .. " KM", toZone < info.zone.r and C.r or C.a } end
	if info.base then rows[#rows + 1] = { "BÁZIS " .. pad3(bearingTo(ac, info.base)) .. "° " .. km(sqrt((info.base.x - ac.pos.x) ^ 2 + (info.base.y - ac.pos.y) ^ 2)) .. " KM", C.c } end
	for i, r in ipairs(rows) do text(g, r[1], i > 1 and Wd - 12 or 12, H - 76, r[2], 21, i > 1 and "right" or "left") end
end

-- ----------------------------------------------------------------- stores
function Mfd:sms(g, Wd, H, ac, world, info)
	local sp, sel = ac.spec, ac.selected
	text(g, "SMS", 14, 26, C.g, 30)
	box(g, Wd - 196, 8, 184, 36, C.g, 2.5)
	text(g, "MASTER ARM", Wd - 104, 27, C.w, 22, "center")
	-- planform from the spec's dimensions, stations at their real spanwise positions
	local span = sp.wingSpan
	local sx, cx, cy = (Wd - 60) / span, Wd / 2, 190
	local half = span / 2 * sx
	local lenPx = min(sp.length * sx * 0.62, 230)
	poly(g, { { cx, cy - lenPx * 0.62 }, { cx + 16, cy - lenPx * 0.3 }, { cx + half, cy + 18 }, { cx + half, cy + 34 }, { cx + 22, cy + 40 },
		{ cx + 70, cy + lenPx * 0.42 }, { cx + 16, cy + lenPx * 0.38 }, { cx, cy + lenPx * 0.42 }, { cx - 16, cy + lenPx * 0.38 },
		{ cx - 70, cy + lenPx * 0.42 }, { cx - 22, cy + 40 }, { cx - half, cy + 34 }, { cx - half, cy + 18 }, { cx - 16, cy - lenPx * 0.3 } }, C.gd)
	for _, st in ipairs(ac.stations) do
		local p = sp.stations[st.number]
		local x = cx + p[1] * sx
		local y = cy + 34 + (abs(p[1]) < 1.5 and 30 or 0)
		local is9 = st.spec.guidance == IR
		local col = not st.loaded and C.gdd or st.key == sel and C.w or C.g
		if st.loaded then g:fillRect(x - 15, y, 30, 54, col) else box(g, x - 15, y, 30, 54, col, 2) end
		text(g, is9 and "9" or "120", x, y + 70, st.loaded and col or C.gdd, is9 and 22 or 18, "center")
		text(g, tostring(st.number), x, y - 14, C.gd, 18, "center")
		if not st.loaded and st.reload ~= nil then text(g, tostring(math.ceil(st.reload)), x, y + 27, C.a, 18, "center") end
	end
	local rows = {}
	for _, key in ipairs(ac:weaponKeys()) do
		local total = 0
		for _, s in ipairs(ac.stations) do if s.key == key then total = total + 1 end end
		rows[#rows + 1] = { (key == sel and ">" or " ") .. " " .. padR(key, 9) .. " " .. ac:missileCount(key) .. " / " .. total, key == sel and C.w or C.g }
	end
	rows[#rows + 1] = { "  GUN " .. sp.gun.name .. "  " .. ac.gun.ammo .. " RDS", ac.gun.ammo > 0 and C.g or C.a }
	rows[#rows + 1] = { "  FLARE " .. ac.flares .. "   CHAFF " .. ac.chaff, ac.flares > 0 and C.g or C.a }
	local s = ac.selectedSpec
	local status, col = "", C.g
	if s and s.guidance == IR then
		local sk = ac.irSeeker
		status = sk.locked and "AIM-9M: LOCK" or sk.candidate and "AIM-9M: HŐFORRÁS (F)" or "AIM-9M: KERESÉS"
		col = sk.locked and C.w or sk.candidate and C.a or C.gd
	elseif s and s.guidance == ARH then
		local lock = ac.radar.mode == STT
		status = lock and "AIM-120A: RADAR LOCK OK" or "AIM-120A: NINCS LOCK (T)"
		col = lock and C.w or C.a
	end
	rows[#rows + 1] = { "  " .. status, col }
	for i, r in ipairs(rows) do text(g, r[1], 18, 318 + (i - 1) * 30, r[2], 23) end
end

-- ---------------------------------------------------- engines, fuel, performance
function Mfd:eng(g, Wd, H, ac, world, info)
	local fm, sp = ac.fm, ac.spec
	local n = sp.engines or 1
	local e = fm.engine
	local ab, dry = clamp((e - 1) / 0.1, 0, 1), min(e, 1)
	local rpm = e > 1 and 100 + 2 * ab or 64 + 36 * dry ^ 0.7
	local noz = e > 1 and 25 + 75 * ab or 8 + 30 * (1 - dry)
	local egt = 420 + 430 * dry ^ 1.6 + 40 * ab
	local title = "ENG  F110-GE-129"
	if n > 1 then title = ({ f22 = "ENG  F119-PW-100 ×2", f15 = "ENG  F110-GE-129 ×2" })[sp.id] or "ENG  F414-GE-400 ×2" end
	text(g, title, 14, 26, C.g, 26)
	local colW = n > 1 and 112 or 150
	for k = 0, n - 1 do
		local x, top, bh = 30 + k * colW, 64, 180
		text(g, n > 1 and ({ "BAL", "JOBB" })[k + 1] or "RPM", x + 30, top, C.gd, 20, "center")
		box(g, x + 10, top + 18, 40, bh, C.gd, 2)
		local f = clamp((rpm - 50) / 55, 0, 1)
		g:fillRect(x + 12, top + 20 + bh * (1 - f), 36, max(0, bh * f - 4), e > 1 and C.a or C.g)
		text(g, round(rpm) .. "%", x + 30, top + bh + 40, e > 1 and C.a or C.w, 24, "center")
		text(g, "NOZ " .. round(noz), x + 30, top + bh + 70, C.g, 19, "center")
	end
	local ff, thr = fm.fuelFlow * 3600 / n, fm.thrust / n / 1000
	local L = {
		{ "EGT " .. round(egt) .. "°C", egt > 870 and C.a or C.g },
		{ "FF  " .. round(ff) .. " KG/H" .. (n > 1 and " ×2" or ""), C.g },
		{ "THR " .. fix(thr) .. " KN" .. (n > 1 and " ×2" or ""), C.g },
		{ e > 1 and ("AB  " .. round(ab * 100) .. "%") or "AB  KI", e > 1 and C.a or C.gd },
	}
	local xl = n > 1 and 262 or 210
	for i, l in ipairs(L) do text(g, l[1], xl, 82 + (i - 1) * 34, l[2], 23) end
	local mass = fm.mass
	local tw = fm.thrust / (mass * 9.81)
	local ps = fm.vel.z + dot(fm.vel, fm.accel) / 9.81
	local toBase = info.base and sqrt((info.base.x - ac.pos.x) ^ 2 + (info.base.y - ac.pos.y) ^ 2) or 0
	local perKm = sp.fuelFlowDry * 0.35 / 0.23
	local bingo = toBase / 1000 * perKm + sp.internalFuel * 0.08
	local minutes = fm.fuelFlow > 0.01 and fm.fuel / fm.fuelFlow / 60 or 99
	local R = {
		{ "T/W " .. fix(tw, 2), tw >= 1 and C.w or C.g },
		{ "PS  " .. (ps >= 0 and "+" or "") .. round(ps) .. " M/S", ps >= 0 and C.g or C.a },
		{ "D   " .. string.format("%.0f", fm.drag / 1000) .. " KN", C.g },
		{ "M " .. fix(fm.mach, 2) .. "  " .. round(fm.ias * 3.6) .. " KM/H", C.g },
		{ "AOA " .. fix(fm.alpha / DEG) .. "° / " .. sp.alphaLimit .. "°", fm.alpha / DEG > sp.alphaLimit * 0.8 and C.a or C.g },
		{ "G " .. fix(fm.gLoad) .. "  (+" .. fix(self.gHi) .. " / " .. fix(self.gLo) .. ")", fm.gLoad > sp.gMax * 0.85 and C.a or C.g },
	}
	for i, l in ipairs(R) do text(g, l[1], xl, 222 + (i - 1) * 27, l[2], 22) end
	local fy = H - 112
	local frac = clamp(fm.fuel / sp.internalFuel, 0, 1)
	local low = fm.fuel < bingo
	box(g, 14, fy - 14, Wd - 28, 26, C.gd, 2)
	g:fillRect(16, fy - 12, (Wd - 32) * frac, 22, low and C.r or frac < 0.3 and C.a or C.g)
	text(g, "FUEL " .. round(fm.fuel) .. " KG   " .. (minutes < 99 and (floor(minutes) .. " PERC") or ""), 14, fy + 32, low and C.r or C.w, 23)
	text(g, "BINGO " .. round(bingo), Wd - 14, fy + 32, low and C.r or C.gd, 21, "right")
	text(g, "TÖMEG " .. fix(mass / 1000) .. " T", Wd - 14, 26, C.gd, 21, "right")
end

-- -------------------------------------------------------------------- RWR
function Mfd:rwr(g, Wd, H, ac, world, info, d, mini)
	local cx = Wd / 2
	local cy = mini and H / 2 or H * 0.42
	local R = mini and min(Wd, H) * 0.44 or Wd * 0.34
	circle(g, cx, cy, R, C.gd, mini and 2 or 2.5); circle(g, cx, cy, R * 0.5, C.gdd, 2)
	for k = 0, 11 do
		local a = k * pi / 6
		line(g, cx + sin(a) * R, cy - cos(a) * R, cx + sin(a) * R * 0.9, cy - cos(a) * R * 0.9, C.gd, 2)
	end
	poly(g, { { cx, cy - 10 }, { cx + 8, cy + 8 }, { cx - 8, cy + 8 } }, C.g)
	if not mini then text(g, "RWR  ALR-67", 14, 26, C.g, 26) end
	local blink = floor(self.time * 6) % 2 == 0
	for _, t in ipairs(ac.rwr.threats) do
		local rad, col = R * 0.8, C.g
		local skip = false
		if t.level == "launch" then
			rad, col = R * 0.3, C.r
			if not blink then skip = true end
		elseif t.level == "lock" then rad, col = R * 0.55, C.a end
		if not skip then
			local x, y = cx + sin(t.bearing) * rad, cy - cos(t.bearing) * rad
			text(g, t.symbol, x, y, col, mini and 26 or 34, "center")
			if t.level ~= "search" then circle(g, x, y, mini and 18 or 26, col, 3) end
		end
	end
	if mini then return end
	local rows = {}
	for _, e in ipairs(ac.rwr.incoming) do
		local m, dist = e.missile, e.dist
		local closing = dot(sub(m.vel, ac.vel), norm(sub(ac.pos, m.pos)))
		local tti = closing > 1 and dist / closing or nil
		rows[#rows + 1] = { "RAKÉTA " .. m.spec.name .. " " .. km(dist) .. " KM" .. ((tti ~= nil and tti < 60) and ("  " .. string.format("%.0f", tti) .. " S") or ""), C.r }
	end
	if #rows == 0 then
		local n = #ac.rwr.threats
		rows[1] = { n > 0 and (n .. " RADAR FIGYEL") or "NINCS FENYEGETÉS", n > 0 and C.a or C.gd }
	end
	rows[#rows + 1] = { "FLARE " .. ac.flares .. "   CHAFF " .. ac.chaff .. "   (X)", C.g }
	for i = 1, min(4, #rows) do text(g, rows[i][1], 18, H * 0.42 + R + 36 + (i - 1) * 30, rows[i][2], 22) end
end
function Mfd:rwrmini(g, Wd, H, ac, world, info, d) self:rwr(g, Wd, H, ac, world, info, d, true) end

-- ----------------------------------------------- data line (DED / UFCD)
function Mfd:ded(g, Wd, H, ac, world, info)
	local fm = ac.fm
	local rows = {}
	local toZone = info.zone and sqrt((info.zone.x - ac.pos.x) ^ 2 + (info.zone.y - ac.pos.y) ^ 2) or 0
	local toBase = info.base and sqrt((info.base.x - ac.pos.x) ^ 2 + (info.base.y - ac.pos.y) ^ 2) or 0
	local where = nil
	if info.base and toBase < info.base.r then where = { "BÁZIS: BIZTONSÁGI ZÓNA", C.c }
	elseif info.zone and toZone < info.zone.r then where = { "HARCI ZÓNÁBAN", C.r } end
	if info.zone then rows[#rows + 1] = { "ZÓNA " .. pad3(bearingTo(ac, info.zone)) .. "° " .. padL(km(max(0, toZone - info.zone.r)), 4) .. "  BÁZ " .. pad3(bearingTo(ac, info.base)) .. "° " .. km(toBase), C.g } end
	local perKm = ac.spec.fuelFlowDry * 0.35 / 0.23
	local bingo = toBase / 1000 * perKm + ac.spec.internalFuel * 0.08
	rows[#rows + 1] = { "FUEL " .. padL(round(fm.fuel), 5) .. "  BINGO " .. round(bingo), fm.fuel < bingo and C.r or C.g }
	local parts = {}
	for _, k in ipairs(ac:weaponKeys()) do parts[#parts + 1] = (k == "AIM-9M" and "9M" or "120") .. "×" .. ac:missileCount(k) end
	rows[#rows + 1] = { table.concat(parts, " ") .. "  GUN " .. ac.gun.ammo, C.g }
	rows[#rows + 1] = where or { "HULLÁM " .. (info.wave or 0) .. "  BANDITA " .. (info.enemies or 0), C.gd }
	if H > Wd * 0.6 then                       -- the Hornet's taller UFCD: flight data and fuel endurance too
		local minutes = fm.fuelFlow > 0.01 and floor(fm.fuel / fm.fuelFlow / 60) or 99
		table.insert(rows, 2, { "ALT " .. round(ac.pos.z) .. "  M" .. fix(fm.mach, 2) .. "  G" .. fix(fm.gLoad), C.w })
		table.insert(rows, 4, { "IDŐ " .. minutes .. " PERC  FF " .. round(fm.fuelFlow * 3600), C.g })
		rows[#rows + 1] = { "FLARE " .. ac.flares .. "  CHAFF " .. ac.chaff, C.gd }
	end
	local lh = H / (#rows + 0.4)
	local fs = min(floor(lh * 0.66), floor(Wd / 19))
	for i, r in ipairs(rows) do text(g, r[1], 12, lh * (i - 0.3), r[2], fs) end
end

return D
