--!nonstrict
-- The math of the flight simulation: the port of web/js/util.js (vectors, quaternions, a seeded random).  World: +X east,
-- +Y north, +Z up, SI units, exactly like the browser game.  Written in the common subset of Lua 5.4 and Luau (no compound
-- assignment, no types), so the very same file can be tested against the JavaScript original outside of Roblox.
local M = {}

M.G = 9.80665
M.DEG = math.pi / 180
local DEG = M.DEG
local atan2 = math.atan2 or function(y, x) return math.atan(y, x) end
M.atan2 = atan2
local sqrt, abs, sin, cos, acos = math.sqrt, math.abs, math.sin, math.cos, math.acos

-- ------------------------------------------------------------------ vectors
local Vec = {}
Vec.__index = Vec
local function V(x, y, z) return setmetatable({ x = x or 0, y = y or 0, z = z or 0 }, Vec) end
M.V = V
Vec.__add = function(a, b) return V(a.x + b.x, a.y + b.y, a.z + b.z) end
Vec.__sub = function(a, b) return V(a.x - b.x, a.y - b.y, a.z - b.z) end
Vec.__mul = function(a, b)
	if type(a) == "number" then return V(b.x * a, b.y * a, b.z * a) end
	return V(a.x * b, a.y * b, a.z * b)
end
Vec.__unm = function(a) return V(-a.x, -a.y, -a.z) end
function Vec:clone() return V(self.x, self.y, self.z) end
-- in place (like THREE.Vector3)
function Vec:addScaled(v, s) self.x = self.x + v.x * s; self.y = self.y + v.y * s; self.z = self.z + v.z * s; return self end
function Vec:scale(s) self.x = self.x * s; self.y = self.y * s; self.z = self.z * s; return self end
function Vec:set(x, y, z) self.x = x; self.y = y; self.z = z; return self end

function M.add(a, b) return V(a.x + b.x, a.y + b.y, a.z + b.z) end
function M.sub(a, b) return V(a.x - b.x, a.y - b.y, a.z - b.z) end
function M.mul(a, s) return V(a.x * s, a.y * s, a.z * s) end
function M.dot(a, b) return a.x * b.x + a.y * b.y + a.z * b.z end
function M.cross(a, b) return V(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x) end
function M.len(a) return sqrt(a.x * a.x + a.y * a.y + a.z * a.z) end
function M.copy(a) return V(a.x, a.y, a.z) end
function M.norm(a, fallback)
	local l = M.len(a)
	if l > 1e-9 then return V(a.x / l, a.y / l, a.z / l) end
	if fallback then return M.copy(fallback) end
	return V(0, 1, 0)
end
local function clamp(x, lo, hi) if x < lo then return lo elseif x > hi then return hi else return x end end
M.clamp = clamp
function M.lerp(a, b, t) return a + (b - a) * t end
function M.smoothstep(e0, e1, x)
	local t = clamp((x - e0) / (e1 - e0), 0, 1)
	return t * t * (3 - 2 * t)
end
function M.sign(x) if x > 0 then return 1 elseif x < 0 then return -1 else return 0 end end
function M.angleBetween(a, b)
	local la, lb = M.len(a), M.len(b)
	if la < 1e-9 or lb < 1e-9 then return 0 end
	return acos(clamp(M.dot(a, b) / (la * lb), -1, 1))
end
-- table: a list of { x, y } pairs, 1-based
function M.interp(t, x)
	if x <= t[1][1] then return t[1][2] end
	for i = 1, #t - 1 do
		local x0, y0, x1, y1 = t[i][1], t[i][2], t[i + 1][1], t[i + 1][2]
		if x <= x1 then return y0 + (y1 - y0) * (x - x0) / (x1 - x0) end
	end
	return t[#t][2]
end

-- ------------------------------------------------------------------ quaternions (THREE.Quaternion: x, y, z, w)
local Quat = {}
Quat.__index = Quat
local function Q(x, y, z, w) return setmetatable({ x = x or 0, y = y or 0, z = z or 0, w = w or 1 }, Quat) end
M.Q = Q
function Quat:clone() return Q(self.x, self.y, self.z, self.w) end
function Quat:normalize()
	local l = sqrt(self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w)
	if l == 0 then self.x, self.y, self.z, self.w = 0, 0, 0, 1
	else l = 1 / l; self.x = self.x * l; self.y = self.y * l; self.z = self.z * l; self.w = self.w * l end
	return self
end
-- a * b (b is applied first)
local function qmul(a, b)
	return Q(a.x * b.w + a.w * b.x + a.y * b.z - a.z * b.y,
		a.y * b.w + a.w * b.y + a.z * b.x - a.x * b.z,
		a.z * b.w + a.w * b.z + a.x * b.y - a.y * b.x,
		a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z)
end
M.qmul = qmul
function M.qaxis(axis, angle)
	local a = M.norm(axis)
	local h = angle / 2
	local s = sin(h)
	return Q(a.x * s, a.y * s, a.z * s, cos(h))
end
local function xform(q, v)
	local x, y, z = v.x, v.y, v.z
	local qx, qy, qz, qw = q.x, q.y, q.z, q.w
	local ix = qw * x + qy * z - qz * y
	local iy = qw * y + qz * x - qx * z
	local iz = qw * z + qx * y - qy * x
	local iw = -qx * x - qy * y - qz * z
	return V(ix * qw + iw * -qx + iy * -qz - iz * -qy,
		iy * qw + iw * -qy + iz * -qx - ix * -qz,
		iz * qw + iw * -qz + ix * -qy - iy * -qx)
end
M.xform = xform
function M.toLocal(q, v) return xform(Q(-q.x, -q.y, -q.z, q.w), v) end
function M.fwdOf(q) return xform(q, V(0, 1, 0)) end
function M.upOf(q) return xform(q, V(0, 0, 1)) end
function M.rightOf(q) return xform(q, V(1, 0, 0)) end

-- orientation whose +Y axis points along forward and +Z as close to up as possible
function M.qlook(forward, up)
	up = up or V(0, 0, 1)
	local y = M.norm(forward)
	local u = up
	if abs(M.dot(y, u)) > 0.999 then
		if abs(y.z) > 0.5 then u = V(0, 1, 0) else u = V(0, 0, 1) end
	end
	local x = M.norm(M.cross(y, u))
	local z = M.cross(x, y)
	-- THREE.Matrix4.makeBasis(x, y, z) -> setFromRotationMatrix
	local m11, m12, m13 = x.x, y.x, z.x
	local m21, m22, m23 = x.y, y.y, z.y
	local m31, m32, m33 = x.z, y.z, z.z
	local trace = m11 + m22 + m33
	local q = Q()
	if trace > 0 then
		local s = 0.5 / sqrt(trace + 1)
		q.w = 0.25 / s; q.x = (m32 - m23) * s; q.y = (m13 - m31) * s; q.z = (m21 - m12) * s
	elseif m11 > m22 and m11 > m33 then
		local s = 2 * sqrt(1 + m11 - m22 - m33)
		q.w = (m32 - m23) / s; q.x = 0.25 * s; q.y = (m12 + m21) / s; q.z = (m13 + m31) / s
	elseif m22 > m33 then
		local s = 2 * sqrt(1 + m22 - m11 - m33)
		q.w = (m13 - m31) / s; q.x = (m12 + m21) / s; q.y = 0.25 * s; q.z = (m23 + m32) / s
	else
		local s = 2 * sqrt(1 + m33 - m11 - m22)
		q.w = (m21 - m12) / s; q.x = (m13 + m31) / s; q.y = (m23 + m32) / s; q.z = 0.25 * s
	end
	return q
end

-- compass heading (deg, clockwise from north) + pitch (deg) -> quaternion
function M.qheading(headingDeg, pitchDeg)
	pitchDeg = pitchDeg or 0
	return qmul(M.qaxis(V(0, 0, 1), -headingDeg * DEG), M.qaxis(V(1, 0, 0), pitchDeg * DEG))
end

function M.rotateTowards(cur, target, maxAngle)
	local ang = M.angleBetween(cur, target)
	if ang <= maxAngle or ang < 1e-6 then return M.copy(target) end
	local axis = M.cross(cur, target)
	if M.len(axis) < 1e-9 then
		if abs(cur.z) < 0.9 then axis = M.cross(cur, V(0, 0, 1)) else axis = M.cross(cur, V(1, 0, 0)) end
	end
	return M.norm(xform(M.qaxis(axis, maxAngle), cur))
end

-- closest approach of a relative position / velocity within dt: returns distance, time
function M.closestApproach(pRel, vRel, dt)
	local vv = M.dot(vRel, vRel)
	local t = 0
	if vv > 1e-9 then t = clamp(-M.dot(pRel, vRel) / vv, 0, dt) end
	return M.len(pRel + vRel * t), t
end

function M.headingDeg(v) return ((atan2(v.x, v.y) / DEG) % 360 + 360) % 360 end
function M.bankAngle(q)
	local r, u = M.rightOf(q), M.upOf(q)
	return atan2(-r.z, u.z)
end
function M.wrap(a)
	return ((((a + math.pi) % (2 * math.pi)) + 2 * math.pi) % (2 * math.pi)) - math.pi
end

-- ------------------------------------------------------------------ seeded random (mulberry32), 32-bit arithmetic by hand
local TWO32 = 4294967296
local function imul(a, b)                         -- the low 32 bits of a * b (unsigned 32 bit a, b)
	local ah, al = math.floor(a / 65536), a % 65536
	local bh, bl = math.floor(b / 65536), b % 65536
	return (al * bl + ((ah * bl + al * bh) % 65536) * 65536) % TWO32
end
local function bitop(a, b, f)
	local r, bit = 0, 1
	for _ = 1, 32 do
		if f(a % 2, b % 2) then r = r + bit end
		a = math.floor(a / 2); b = math.floor(b / 2); bit = bit * 2
	end
	return r
end
local function bxor(a, b) return bitop(a, b, function(x, y) return x ~= y end) end
local function bor(a, b) return bitop(a, b, function(x, y) return x == 1 or y == 1 end) end
local function rshift(a, n) return math.floor(a / 2 ^ n) end
-- rng(seed) returns r with r() in [0, 1), r.uniform(lo, hi), r.gauss(mu, sigma) - the same sequence as the JavaScript one
function M.rng(seed)
	local a = (seed or 1) % TWO32
	local function step()
		a = (a + 0x6d2b79f5) % TWO32
		local t = a
		t = imul(bxor(t, rshift(t, 15)), bor(t, 1))
		t = bxor(t, (t + imul(bxor(t, rshift(t, 7)), bor(t, 61))) % TWO32)
		return bxor(t, rshift(t, 14)) / TWO32
	end
	local obj = setmetatable({}, { __call = function() return step() end })
	function obj.uniform(lo, hi) return lo + (hi - lo) * step() end
	function obj.gauss(mu, sigma)
		mu = mu or 0
		sigma = sigma or 1
		local u = math.max(step(), 1e-12)
		local v = step()
		return mu + sigma * sqrt(-2 * math.log(u)) * cos(2 * math.pi * v)
	end
	return obj
end

return M
