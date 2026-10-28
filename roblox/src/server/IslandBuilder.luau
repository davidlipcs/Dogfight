--!nonstrict
-- Builds the game's real island as Roblox terrain, from the height grid and the ground colours of the browser game
-- (IslandData + the simulation's own SimTerrain, so what you see is what the flight model collides with).  It takes a few
-- minutes, so do it ONCE in Studio (see roblox/README.md): the terrain is saved with the place.  In the Command Bar (View > Command Bar) run:
--   require(game.ServerScriptService.Server.IslandBuilder).build()
-- The terrain is a thin shell (three voxels) over the sea bed: nothing is dug, so it stays light.
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local IslandData = require(Shared.IslandData)
local SimTerrain = require(Shared.sim.SimTerrain)

local IslandBuilder = {}

local MATERIAL = {
	[0] = Enum.Material.Sand,
	[1] = Enum.Material.Grass,
	[2] = Enum.Material.LeafyGrass,
	[3] = Enum.Material.Ground,
	[4] = Enum.Material.Rock,
	[5] = Enum.Material.Sand,
	[6] = Enum.Material.Snow,
}

function IslandBuilder.build(progress: ((number) -> ())?)
	local data = IslandData.load()
	local sim = SimTerrain.new(data)
	local terrain = workspace.Terrain
	terrain:Clear()
	local V = Config.Island.Voxel
	local half = Config.World.Half
	local nv = math.floor(half * 2 / V)              -- voxels per side
	local S = Config.Island.StudsPerMeter
	local cell = data.size / data.res
	local field = data.airfield
	local fieldX, fieldZ, fieldY = field.x * S, -field.y * S, field.elevation * S
	local SLAB = 16
	local t0 = os.clock()
	local slabsPerSide = math.ceil(nv / SLAB)
	local total, done = slabsPerSide * slabsPerSide, 0

	for sx = 0, slabsPerSide - 1 do
		for sz = 0, slabsPerSide - 1 do
			local vx0, vz0 = sx * SLAB, sz * SLAB
			local w, d = math.min(SLAB, nv - vx0), math.min(SLAB, nv - vz0)
			-- the ground of every column of the slab
			local surf, mat = {}, {}
			local lo, hi = math.huge, -math.huge
			for x = 1, w do
				surf[x], mat[x] = {}, {}
				for z = 1, d do
					local X = (vx0 + x - 0.5) * V - half
					local Z = (vz0 + z - 0.5) * V - half
					local mx, my = X / S, -Z / S                     -- the game's metres
					local y = sim:height(mx, my) * S
					surf[x][z] = y
					local m = 0
					if y > 0.5 then
						local gi = math.clamp(math.floor((mx + data.size / 2) / cell + 0.5), 0, data.res)
						local gj = math.clamp(math.floor((my + data.size / 2) / cell + 0.5), 0, data.res)
						m = IslandData.material(data, gi, gj)
					end
					mat[x][z] = m
					local top = math.floor(y / V)
					if top < lo then lo = top end
					if top > hi then hi = top end
				end
			end
			if hi > -1 or lo < 0 then
				local vyLo = math.min(lo - 2, -2)
				local vyHi = math.max(hi, 0)
				local h = vyHi - vyLo + 1
				local materials, occupancy = {}, {}
				for x = 1, w do
					materials[x], occupancy[x] = {}, {}
					for y = 1, h do
						materials[x][y], occupancy[x][y] = {}, {}
						for z = 1, d do
							materials[x][y][z] = Enum.Material.Air
							occupancy[x][y][z] = 0
						end
					end
					for z = 1, d do
						local y = surf[x][z]
						local m = MATERIAL[mat[x][z]]
						if y > 0.5 then
							local k = math.floor(y / V)
							for vy = k - 2, k do
								local idx = vy - vyLo + 1
								materials[x][idx][z] = m
								occupancy[x][idx][z] = vy == k and math.max(0.2, (y - k * V) / V) or 1
							end
						else
							-- the sea bed and a layer of water over it, round the coast
							local bed = -2 - vyLo + 1
							materials[x][bed][z] = Enum.Material.Sand
							occupancy[x][bed][z] = 1
							materials[x][bed + 1][z] = Enum.Material.Water
							occupancy[x][bed + 1][z] = 1
						end
					end
				end
				local region = Region3.new(
					Vector3.new(vx0 * V - half, vyLo * V, vz0 * V - half),
					Vector3.new((vx0 + w) * V - half, (vyHi + 1) * V, (vz0 + d) * V - half))
				terrain:WriteVoxels(region, V, materials, occupancy)
			end
			done += 1
			if done % 40 == 0 then
				if progress then progress(done / total) end
				task.wait()
			end
		end
	end
	workspace:SetAttribute("IslandBuilt", true)
	print(string.format("Dogfight Plus: the island is built (%.0f s). Save the place now (File > Save).", os.clock() - t0))
end

return IslandBuilder
