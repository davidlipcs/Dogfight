--!nonstrict
-- The height field and the home air base of the game: the port of web/js/terrain.js.  heights: a 1-based array of
-- (res+1)^2 numbers in metres, row after row (rows from the south, columns from the west), exactly the game's grid.
local M = require(script.Parent.SimMath)
local clamp, sqrt, atan = M.clamp, math.sqrt, math.atan

local T = {}
T.RUNWAY_LENGTH, T.RUNWAY_WIDTH, T.TAXIWAY_OFFSET, T.TAXIWAY_WIDTH = 3000, 45, 190, 23
T.APRON = { 260, 520, -350, 350 }

-- ------------------------------------------------------------------ the air base
local Airfield = {}
Airfield.__index = function(t, k)
	if k == "southThreshold" then return t.y - T.RUNWAY_LENGTH / 2 end
	return Airfield[k]
end
function T.newAirfield(x, y, elevation) return setmetatable({ x = x, y = y, elevation = elevation }, Airfield) end
function Airfield:onRunway(x, y, margin)
	margin = margin or 0
	return math.abs(x - self.x) <= T.RUNWAY_WIDTH / 2 + margin and math.abs(y - self.y) <= T.RUNWAY_LENGTH / 2 + margin
end
function Airfield:onPaved(x, y)
	local dx, dy = x - self.x, y - self.y
	if self:onRunway(x, y, 3) then return true end
	if math.abs(dx - T.TAXIWAY_OFFSET) <= T.TAXIWAY_WIDTH / 2 and math.abs(dy) <= T.RUNWAY_LENGTH / 2 then return true end
	for _, cy in ipairs({ -T.RUNWAY_LENGTH / 2 + 60, 0, T.RUNWAY_LENGTH / 2 - 60 }) do
		if dx >= 0 and dx <= T.TAXIWAY_OFFSET and math.abs(dy - cy) <= T.TAXIWAY_WIDTH / 2 then return true end
	end
	local x0, x1, y0, y1 = T.APRON[1], T.APRON[2], T.APRON[3], T.APRON[4]
	return dx >= x0 - 70 and dx <= x1 and dy >= y0 and dy <= y1
end
function Airfield:startPosition() return { self.x, self.southThreshold + 120, 0 } end

-- ------------------------------------------------------------------ the terrain
local Terrain = {}
Terrain.__index = Terrain

-- data: { size, res, heights (1-based, metres, (res+1)^2 values), airfield = { x, y, elevation } }
function T.new(data)
	local self = setmetatable({}, Terrain)
	self:load(data)
	return self
end

function Terrain:load(data)
	self.size = data.size
	self.res = data.res
	self.n = data.res + 1
	self.cell = self.size / self.res
	self.half = self.size / 2
	self.grid = data.heights
	local mx = -1e9
	for i = 1, #self.grid do if self.grid[i] > mx then mx = self.grid[i] end end
	self.maxHeight = mx
	local a = data.airfield
	self.airfield = T.newAirfield(a.x, a.y, a.elevation)
end

-- i, j are 0-based like the original
function Terrain:at(i, j) return self.grid[j * self.n + i + 1] end

function Terrain:rawHeight(x, y)
	local gx, gy = (x + self.half) / self.cell, (y + self.half) / self.cell
	if gx < 0 or gy < 0 or gx >= self.res or gy >= self.res then return -220 end
	local i, j = math.floor(gx), math.floor(gy)
	local fx, fy = gx - i, gy - j
	local n, g = self.n, self.grid
	local k = j * n + i + 1
	local h0 = g[k] + (g[k + 1] - g[k]) * fx
	local h1 = g[k + n] + (g[k + n + 1] - g[k + n]) * fx
	return h0 + (h1 - h0) * fy
end

function Terrain:height(x, y) return math.max(self:rawHeight(x, y), 0) end

function Terrain:slope(x, y, d)
	d = d or 6
	local gx = (self:height(x + d, y) - self:height(x - d, y)) / (2 * d)
	local gy = (self:height(x, y + d) - self:height(x, y - d)) / (2 * d)
	return atan(sqrt(gx * gx + gy * gy))
end

function Terrain:lineOfSight(a, b, samples)
	samples = samples or 12
	if a.z > self.maxHeight and b.z > self.maxHeight then return true end
	for k = 1, samples - 1 do
		local t = k / samples
		local z = a.z + (b.z - a.z) * t
		if z < self.maxHeight and z < self:height(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t) then return false end
	end
	return true
end

function Terrain:clampInside(x, y, margin)
	margin = margin or 8000
	local lim = self.half - margin
	return clamp(x, -lim, lim), clamp(y, -lim, lim)
end

return T
