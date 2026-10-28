--!nonstrict
-- The rear seat of a two-seat jet: you do not fly, you look around from behind the jet (the cursor turns the view),
-- lock enemies in a wide cone, fire the jet's missiles, drop flares and mark a target for the pilot.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")

local Config = require(ReplicatedStorage:WaitForChild("Shared").Config)
local State = require(script.Parent.State)

local Wso = {}

local camera = workspace.CurrentCamera
local active = false
local jet, remotes, onLeave
local lockTarget = nil
local yaw, pitch = 0, 0.15
Wso.state = { wso = true }

local function findLock(origin: Vector3, look: Vector3)
	local best, bestAng = nil, math.rad(40)
	local function consider(m: Instance)
		if not m:IsA("Model") or not State.hostile(m) then return end
		local to = m:GetPivot().Position - origin
		local d = to.Magnitude
		if d < Config.Missile.Range and d > 60 then
			local ang = math.acos(math.clamp(look:Dot(to.Unit), -1, 1))
			if ang < bestAng then best, bestAng = m, ang end
		end
	end
	for _, m in workspace.Enemies:GetChildren() do consider(m) end
	for _, m in workspace.Jets:GetChildren() do consider(m) end
	return best
end

local function step(dt: number)
	if not active then return end
	if not jet or not jet.Parent then return end
	camera = workspace.CurrentCamera
	camera.CameraType = Enum.CameraType.Scriptable
	local cf = jet:GetPivot()
	-- the cursor turns the view round the jet
	local m = UserInputService:GetMouseLocation()
	local size = camera.ViewportSize
	local dx = math.clamp((m.X - size.X / 2) / (size.X / 2), -1, 1)
	local dy = math.clamp((m.Y - size.Y / 2) / (size.Y / 2), -1, 1)
	local ty, tp = -dx * 2.6, 0.12 - dy * 0.7
	yaw += (ty - yaw) * math.min(1, dt * 6)
	pitch += (tp - pitch) * math.min(1, dt * 6)
	local rotView = cf.Rotation * CFrame.Angles(0, yaw, 0) * CFrame.Angles(pitch, 0, 0)
	local camPos = cf.Position + rotView * Vector3.new(0, 4, 34)
	camera.CFrame = CFrame.lookAt(camPos, cf.Position)
	camera.FieldOfView = 70
	local look = (cf.Position - camPos).Unit                       -- where the view is aimed
	lockTarget = findLock(cf.Position, look)

	local body = jet.PrimaryPart
	local vel = body and body.AssemblyLinearVelocity or Vector3.zero
	local s = Wso.state
	s.speed, s.alt, s.throttle, s.ab, s.stall, s.edge, s.lock = vel.Magnitude, cf.Position.Y, 0, false, false, false, lockTarget
	s.pos, s.look, s.mouse = camPos, look, false
end

function Wso.init(r, leave)
	remotes = r
	onLeave = leave
	RunService:BindToRenderStep("DogfightWso", Enum.RenderPriority.Camera.Value + 1, step)
	local function act()
		if lockTarget and lockTarget.Parent then remotes.FireMissile:FireServer(lockTarget) end
	end
	UserInputService.InputBegan:Connect(function(input, processed)
		if not active then return end
		if input.UserInputType == Enum.UserInputType.MouseButton2 and not processed then act() return end
		if input.UserInputType == Enum.UserInputType.MouseButton3 then remotes.Mark:FireServer(lockTarget) return end
		if processed then return end
		local k = input.KeyCode
		if k == Enum.KeyCode.X or k == Enum.KeyCode.Space or k == Enum.KeyCode.ButtonX then act()
		elseif k == Enum.KeyCode.G or k == Enum.KeyCode.ButtonB then remotes.Flare:FireServer()
		elseif k == Enum.KeyCode.T or k == Enum.KeyCode.ButtonY then remotes.Mark:FireServer(lockTarget)
		elseif k == Enum.KeyCode.Z then if onLeave then onLeave() end end
	end)
end

function Wso.start(model: Model)
	jet = model
	active = true
	yaw, pitch = 0, 0.15
end

function Wso.stop()
	active = false
	jet = nil
end

function Wso.isActive(): boolean
	return active
end

return Wso
