--!nonstrict
-- The island's heights at any point (shared by the terrain builder, the world and the spawn code): the game's metres
-- become studs (Config.Island), the game's north (+y) is Roblox's -Z.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Island = require(Shared.Island)

local IslandMath = {}

local S, VS = Config.Island.StudsPerMeter, Config.Island.HeightScale
local heights = nil          -- [j][i] metres (j = rows from the south, i = columns from the west)
local mats = nil             -- the material digits (a string, row after row)

local alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
local lookup = {}
for i = 1, #alphabet do lookup[string.byte(alphabet, i)] = i - 1 end

-- base64 -> a list of bytes
local function decode(s: string)
	local out, n = {}, 0
	local acc, bits = 0, 0
	for i = 1, #s do
		local v = lookup[string.byte(s, i)]
		if v then
			acc = acc * 64 + v
			bits += 6
			if bits >= 8 then
				bits -= 8
				local div = 2 ^ bits
				local byte = math.floor(acc / div)
				acc -= byte * div
				n += 1
				out[n] = byte
			end
		end
	end
	return out
end

function IslandMath.load()
	if heights then return end
	local N = Island.N
	heights = {}
	local j = 0
	for _, name in { "IslandH1", "IslandH2", "IslandH3" } do
		local bytes = decode(require(ReplicatedStorage.Shared[name]))
		local k = 1
		for _ = 1, Island.HeightRows do
			j += 1
			local row = table.create(N)
			for i = 1, N do
				row[i] = (bytes[k] + bytes[k + 1] * 256) * Island.Unit - Island.Offset
				k += 2
			end
			heights[j] = row
		end
	end
	mats = require(ReplicatedStorage.Shared.IslandM)
end

-- metres of height at a point given as cell coordinates (fractional, 0 .. N-1)
local function cellHeight(fi: number, fj: number): number
	local N = Island.N
	fi = math.clamp(fi, 0, N - 1)
	fj = math.clamp(fj, 0, N - 1)
	local i0, j0 = math.floor(fi), math.floor(fj)
	local i1, j1 = math.min(i0 + 1, N - 1), math.min(j0 + 1, N - 1)
	local tx, ty = fi - i0, fj - j0
	local h = heights
	local a = h[j0 + 1][i0 + 1] * (1 - tx) + h[j0 + 1][i1 + 1] * tx
	local b = h[j1 + 1][i0 + 1] * (1 - tx) + h[j1 + 1][i1 + 1] * tx
	return a * (1 - ty) + b * ty
end

-- studs (X, Z) -> cell coordinates
function IslandMath.cellOf(X: number, Z: number)
	local cell = Island.SizeMeters / Island.N
	local mx, my = X / S, -Z / S
	return (mx + Island.SizeMeters / 2) / cell - 0.5, (my + Island.SizeMeters / 2) / cell - 0.5
end

-- the ground height in studs under (X, Z); the sea is 0
function IslandMath.height(X: number, Z: number): number
	IslandMath.load()
	local fi, fj = IslandMath.cellOf(X, Z)
	return math.max(cellHeight(fi, fj), 0) * VS
end

-- the ground material digit (1 grass, 2 leafy, 3 ground, 4 rock, 5 sand, 6 snow) of the cell under (X, Z)
function IslandMath.material(X: number, Z: number): number
	IslandMath.load()
	local fi, fj = IslandMath.cellOf(X, Z)
	local N = Island.N
	local i, j = math.clamp(math.floor(fi + 0.5), 0, N - 1), math.clamp(math.floor(fj + 0.5), 0, N - 1)
	return string.byte(mats, j * N + i + 1) - 48
end

-- the air base in studs: its centre on the ground, the runway runs north - south (along Z)
function IslandMath.airfield()
	local a = Island.Airfield
	local X, Z = a.x * S, -a.y * S
	return Vector3.new(X, a.elevation * VS, Z)
end

return IslandMath
