--!nonstrict
-- The simulation's frame (metres: x east, y north, z up) <-> the Roblox world (studs: X east, Y up, Z south).
-- The island is Config.Island.StudsPerMeter studs per metre.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage:WaitForChild("Shared").Config)

local C = {}
local S = Config.Island.StudsPerMeter
C.S = S

function C.pos(p) return Vector3.new(p.x * S, p.z * S, -p.y * S) end
function C.posXYZ(x, y, z) return Vector3.new(x * S, z * S, -y * S) end
-- a direction or velocity (m/s -> studs/s)
function C.vec(v) return Vector3.new(v.x * S, v.z * S, -v.y * S) end
function C.dir(v) return Vector3.new(v.x, v.z, -v.y) end
-- a point of the Roblox world back to the simulation's frame (x, y, z numbers)
function C.fromWorld(v) return v.X / S, -v.Z / S, v.Y / S end

-- the rotation of a sim quaternion (body: x right, y forward, z up) as the Roblox CFrame of a model whose
-- RIGHT is +X, UP is +Y and LOOK is -Z (a model built facing forward = -Z)
function C.cframe(p, q)
	local x, y, z, w = q.x, q.y, q.z, q.w
	-- the rotation matrix of the quaternion, columns = the body axes in the sim's frame
	local r00, r01, r02 = 1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)
	local r10, r11, r12 = 2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)
	local r20, r21, r22 = 2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)
	-- body right = (r00, r10, r20), body forward = (r01, r11, r21), body up = (r02, r12, r22) in sim coordinates
	local R = Vector3.new(r00, r20, -r10)
	local F = Vector3.new(r01, r21, -r11)
	local U = Vector3.new(r02, r22, -r12)
	-- CFrame.fromMatrix(pos, right, up, back)
	return CFrame.fromMatrix(C.pos(p), R, U, -F)
end

return C
