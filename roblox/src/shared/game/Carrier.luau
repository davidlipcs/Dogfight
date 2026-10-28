--!nonstrict
-- The aircraft carrier ("USS Dogfight", CVN-80) anchored 15 km south of the home base: the port of web/js/carrier.js without the model.  Its flight
-- deck is part of the ground: terrain:height() returns the deck height over it, so landing, taxiing and taking off work with the normal flight
-- model.  Plus what only a carrier has: an angled landing deck with four arresting wires (a trap, or a bolter), two bow catapults and the
-- optical landing system (the meatball).  Real numbers: 333 m long, 77 m wide flight deck, 9 degree angled deck, deck ~19 m above the sea.
-- Common subset of Lua 5.4 and Luau.
local M = require(script.Parent.Parent.sim.SimMath)
local V = M.V
local sin, cos, abs, tan, pi = math.sin, math.cos, math.abs, math.tan, math.pi

local C = {}
C.DECK_Z = 19.5
local DECK_Z = C.DECK_Z
local ANGLE = -9 * pi / 180                            -- the landing deck points 9 degrees to port of the bow
-- deck outline in the carrier's frame (x starboard, y bow), metres
C.OUTLINE = { { 22, 166 }, { 24, 40 }, { 24, -150 }, { 12, -166 }, { -26, -166 }, { -47, 34 }, { -47, 70 }, { -30, 96 }, { -18, 166 } }
C.WIRES = { 52, 64, 76, 88 }                          -- distance of the wires from the stern, along the landing line
C.CATS = { { 9, 30, 160 }, { -9, 30, 160 } }          -- { x, start y, end y }
local OUTLINE, WIRES, CATS = C.OUTLINE, C.WIRES, C.CATS

local function inside(x, y)
	local c = false
	local j = #OUTLINE
	for i = 1, #OUTLINE do
		local xi, yi, xj, yj = OUTLINE[i][1], OUTLINE[i][2], OUTLINE[j][1], OUTLINE[j][2]
		if (yi > y) ~= (yj > y) and x < ((xj - xi) * (y - yi)) / (yj - yi) + xi then c = not c end
		j = i
	end
	return c
end

local Carrier = {}
Carrier.__index = function(t, k)
	if k == "landingHeading" then return t.heading + ANGLE * 180 / pi end
	return Carrier[k]
end

function C.new(terrain, x, y, heading)
	local self = setmetatable({}, Carrier)
	self.terrain, self.x, self.y, self.heading = terrain, x or 21000, y or -42000, heading or 0
	self.cos, self.sin = cos(self.heading * pi / 180), sin(self.heading * pi / 180)
	self.landStart, self.landDir = { -8, -166 }, { sin(ANGLE), cos(ANGLE) }
	self.active = true
	-- the deck becomes ground: wrap the terrain's height and the airfield's "paved" test
	local baseHeight = terrain.height
	local af = terrain.airfield
	local basePaved = af.onPaved
	terrain.height = function(t, px, py)
		if self:onDeck(px, py) then return DECK_Z end
		return baseHeight(t, px, py)
	end
	af.onPaved = function(a, px, py) return self:onDeck(px, py) or basePaved(a, px, py) end
	terrain.isWater = function(px, py) return (not self:onDeck(px, py)) and terrain:rawHeight(px, py) < 0 end
	terrain.carrier = self
	return self
end
-- world -> carrier frame
function Carrier:local_(px, py)
	local dx, dy = px - self.x, py - self.y
	return dx * self.cos - dy * self.sin, dx * self.sin + dy * self.cos
end
function Carrier:world(lx, ly, z)
	return V(self.x + lx * self.cos + ly * self.sin, self.y - lx * self.sin + ly * self.cos, z or DECK_Z)
end
function Carrier:onDeck(px, py)
	if not self.active then return false end
	if abs(px - self.x) > 200 or abs(py - self.y) > 200 then return false end
	local lx, ly = self:local_(px, py)
	return inside(lx, ly)
end
-- how far along the landing line from the stern, and how far off it (m)
function Carrier:landing(px, py)
	local lx, ly = self:local_(px, py)
	local sx, sy = self.landStart[1], self.landStart[2]
	local dx, dy = self.landDir[1], self.landDir[2]
	local rx, ry = lx - sx, ly - sy
	return rx * dx + ry * dy, rx * dy - ry * dx                      -- along, off
end
-- a point on the glide slope (3.5 degrees) behind the stern, for approaches and the meatball
function Carrier:glide(px, py, pz)
	local along, off = self:landing(px, py)
	local dist = 60 - along                                          -- aim at the third wire
	local want = DECK_Z + tan(3.5 * pi / 180) * dist
	return { dist = dist, off = off, high = pz - 2 - want, behind = dist > 0 }
end
-- a parking / catapult spot in the world: x, y, heading
function Carrier:catapult(k)
	local c = CATS[(k or 0) + 1]
	local p = self:world(c[1], c[2])
	return p.x, p.y, self.heading
end
function Carrier:onCatapult(px, py)
	local lx, ly = self:local_(px, py)
	for _, c in ipairs(CATS) do
		if abs(lx - c[1]) < 6 and ly > c[2] - 8 and ly < c[3] then return true end
	end
	return false
end
function Carrier:inWires(px, py)
	local along, off = self:landing(px, py)
	return abs(off) < 14 and along > WIRES[1] - 14 and along < WIRES[4] + 10
end
function Carrier:wireNumber(px, py)
	local along = self:landing(px, py)
	local best, bd = 1, 1e9
	for i, w in ipairs(WIRES) do
		local d = abs(along - w)
		if d < bd then bd, best = d, i end
	end
	return best
end

return C
