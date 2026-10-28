--!nonstrict
-- The flight: the player's own jet is flown here, on the client (it owns the physics of its jet, so the
-- controls are instant).  An arcade model: throttle and drag set the speed, the pitch / roll / yaw rates
-- grow with speed, a stall drops the nose.  The server checks the shooting, so nothing here can hurt anybody.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local TweenService = game:GetService("TweenService")
local Debris = game:GetService("Debris")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local JetBuilder = require(Shared.JetBuilder)
local State = require(script.Parent.State)

local Flight = {}

local J = Config.Jet
local player = Players.LocalPlayer
local camera = workspace.CurrentCamera

local active = false
local jet, body, remotes
local pos, rot, speed, throttle = Vector3.zero, CFrame.new(), 0, 0.7
local camRot = CFrame.new()
local cockpit = false
local firing = false
local lastShot = 0
local invertPitch = false
local mouseSteer = UserInputService.MouseEnabled and not UserInputService.TouchEnabled   -- M switches it
local touch = { roll = 0, pitch = 0, throttle = 0 }   -- set by the on-screen controls (Hud.luau)
local stallWarn, edgeWarn = false, false
local lockTarget = nil
local onCrash = nil

Flight.touch = touch
Flight.state = {}

local ignore = RaycastParams.new()
ignore.FilterType = Enum.RaycastFilterType.Exclude

-- ------------------------------------------------------------------ effects
local function beam(a: Vector3, b: Vector3, color: Color3)
	local len = (b - a).Magnitude
	if len < 1 then return end
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.Material = Enum.Material.Neon
	p.Color = color
	p.Size = Vector3.new(0.35, 0.35, len)
	p.CFrame = CFrame.lookAt((a + b) / 2, b)
	p.Parent = workspace
	TweenService:Create(p, TweenInfo.new(0.18), { Transparency = 1 }):Play()
	Debris:AddItem(p, 0.25)
end
Flight.beam = beam

-- ------------------------------------------------------------------ input
local function axis(pos_key: Enum.KeyCode, neg_key: Enum.KeyCode): number
	local v = 0
	if UserInputService:IsKeyDown(pos_key) then v += 1 end
	if UserInputService:IsKeyDown(neg_key) then v -= 1 end
	return v
end

local function readInput()
	local pitch, roll, yaw = 0, 0, 0
	-- keyboard: S / Down pulls up, W / Up pushes down; A / D (arrows) roll; Q / E rudder
	pitch += axis(Enum.KeyCode.S, Enum.KeyCode.W) + axis(Enum.KeyCode.Down, Enum.KeyCode.Up)
	roll += axis(Enum.KeyCode.D, Enum.KeyCode.A) + axis(Enum.KeyCode.Right, Enum.KeyCode.Left)
	yaw += axis(Enum.KeyCode.E, Enum.KeyCode.Q)
	-- mouse: the cursor steers (above the middle: nose up, right of the middle: bank right)
	if mouseSteer and UserInputService.MouseEnabled then
		local m = UserInputService:GetMouseLocation()
		local size = camera.ViewportSize
		local dx = (m.X - size.X / 2) / (size.X * 0.3)
		local dy = (m.Y - size.Y / 2) / (size.Y * 0.3)
		local function dead(v: number): number
			if math.abs(v) < 0.1 then return 0 end
			return math.clamp(v - math.sign(v) * 0.1, -1, 1)
		end
		roll += dead(dx)
		yaw += dead(dx) * 0.5
		pitch += -dead(dy)
	end
	-- gamepad
	for _, st in UserInputService:GetGamepadState(Enum.UserInputType.Gamepad1) do
		if st.KeyCode == Enum.KeyCode.Thumbstick1 then
			local p = st.Position
			if math.abs(p.X) > 0.12 then roll += p.X; yaw += p.X * 0.4 end
			if math.abs(p.Y) > 0.12 then pitch += -p.Y end
		elseif st.KeyCode == Enum.KeyCode.Thumbstick2 then
			if math.abs(st.Position.X) > 0.12 then yaw += st.Position.X end
		end
	end
	-- touch controls
	roll += touch.roll
	yaw += touch.roll * 0.5
	pitch += touch.pitch
	if invertPitch then pitch = -pitch end
	return math.clamp(pitch, -1, 1), math.clamp(roll, -1, 1), math.clamp(yaw, -1, 1)
end

local function readThrottle(dt: number)
	local d = 0
	if UserInputService:IsKeyDown(Enum.KeyCode.LeftShift) or UserInputService:IsKeyDown(Enum.KeyCode.R) then d += 1 end
	if UserInputService:IsKeyDown(Enum.KeyCode.LeftControl) or UserInputService:IsKeyDown(Enum.KeyCode.F) then d -= 1 end
	for _, st in UserInputService:GetGamepadState(Enum.UserInputType.Gamepad1) do
		if st.KeyCode == Enum.KeyCode.ButtonR2 then d += st.Position.Z end
		if st.KeyCode == Enum.KeyCode.ButtonL2 then d -= st.Position.Z end
	end
	d += touch.throttle
	throttle = math.clamp(throttle + d * 0.6 * dt, 0, 1)
end

-- the enemy in front of the nose that a missile can lock (the HUD draws the box); the one the rear seat marked comes first
local function findLock()
	local best, bestAng = nil, math.rad(Config.Missile.Cone)
	local look = rot.LookVector
	local function consider(m: Instance)
		if not m:IsA("Model") or not State.hostile(m) then return end
		local to = m:GetPivot().Position - pos
		local d = to.Magnitude
		if d < Config.Missile.Range and d > 80 then
			local ang = math.acos(math.clamp(look:Dot(to.Unit), -1, 1))
			if (Flight.markUid or 0) ~= 0 and m:GetAttribute("Uid") == Flight.markUid then ang *= 0.4 end
			if ang < bestAng then best, bestAng = m, ang end
		end
	end
	for _, m in workspace.Enemies:GetChildren() do consider(m) end
	for _, m in workspace.Jets:GetChildren() do consider(m) end
	return best
end

local function fireMissile()
	if lockTarget and lockTarget.Parent then remotes.FireMissile:FireServer(lockTarget) end
end

-- ------------------------------------------------------------------ the frame
local function step(dt: number)
	if not active or not jet or not jet.Parent then return end
	dt = math.min(dt, 0.1)
	local pitchIn, rollIn, yawIn = readInput()
	readThrottle(dt)

	-- control authority grows with speed: slow = mushy, fast = crisp
	local eff = math.clamp((speed - J.StallSpeed * 0.8) / (J.CornerSpeed - J.StallSpeed * 0.8), 0.15, 1.15)
	local dPitch = pitchIn * J.PitchRate * eff * dt
	local dRoll = rollIn * J.RollRate * dt
	local dYaw = yawIn * J.YawRate * dt

	-- a stall: the nose falls
	local stalled = speed < J.StallSpeed
	if stalled then
		dPitch -= (1 - speed / J.StallSpeed) * 0.9 * dt
	end
	stallWarn = stalled

	-- out of the field: the jet is turned back (the edge of the world)
	local W = Config.World
	local flat = Vector3.new(pos.X, 0, pos.Z)
	edgeWarn = flat.Magnitude > W.Half
	local forward = rot.LookVector
	local newLook = forward
	if edgeWarn then
		local want = (Vector3.new(-pos.X, 300 - pos.Y, -pos.Z)).Unit
		local ang = math.acos(math.clamp(forward:Dot(want), -1, 1))
		if ang > 0.01 then newLook = forward:Lerp(want, math.min(1, 0.9 * dt / ang)).Unit end
	end

	rot = rot * CFrame.Angles(dPitch, -dYaw, -dRoll)
	if edgeWarn then
		local up = rot.UpVector
		rot = CFrame.lookAt(Vector3.zero, newLook, up:Dot(newLook) > 0.98 and Vector3.new(0, 0, 1) or Vector3.new(0, 1, 0))
	end

	-- speed: thrust against drag, gravity along the climb
	local ab = throttle > 0.95
	local thrust = J.Accel * throttle * (ab and J.Afterburner or 1)
	local drag = J.Drag * speed * speed
	forward = rot.LookVector
	speed += (thrust - drag - workspace.Gravity * 0.5 * forward.Y) * dt
	speed = math.max(speed, 40)

	local vel = forward * speed
	if stalled then vel += Vector3.new(0, -(J.StallSpeed - speed) * 0.9, 0) end
	local nextPos = pos + vel * dt

	-- the ground and the sea: a crash
	ignore.FilterDescendantsInstances = { workspace.Jets, workspace.Enemies, workspace.Missiles, workspace.Effects }
	local hit = workspace:Raycast(pos, (nextPos - pos) + forward * 6, ignore)
	if hit or nextPos.Y < -2 then
		active = false
		remotes.Crashed:FireServer()
		if onCrash then onCrash() end
		return
	end
	pos = nextPos
	jet:PivotTo(CFrame.new(pos) * rot.Rotation)
	body.AssemblyLinearVelocity = vel
	body.AssemblyAngularVelocity = Vector3.zero
	JetBuilder.setFlame(jet, throttle)

	-- guns: held fire
	if firing and os.clock() - lastShot >= 1 / Config.Gun.Rate then
		lastShot = os.clock()
		remotes.Fire:FireServer()
		local origin = pos + forward * 12
		beam(origin, origin + forward * Config.Gun.Range * 0.5, Color3.fromRGB(255, 240, 140))
	end

	lockTarget = findLock()

	-- the camera: behind and above, lagging a little in the turns; V = from the cockpit
	camRot = camRot:Lerp(rot.Rotation, 1 - math.exp(-dt * 7))
	if cockpit then
		camera.CFrame = CFrame.new(pos) * rot.Rotation * CFrame.new(0, 1.9, -3.3)
		camera.FieldOfView = 78
	else
		local cp = pos + camRot.Rotation * Vector3.new(0, 6.5, 30)
		camera.CFrame = CFrame.lookAt(cp, pos + rot.LookVector * 90, camRot.UpVector)
		camera.FieldOfView = 68 + math.clamp((speed - 250) / 250, 0, 1) * 14
	end

	local s = Flight.state
	s.speed, s.alt, s.throttle, s.ab, s.stall, s.edge, s.lock, s.pos, s.look, s.mouse = speed, pos.Y, throttle, ab, stallWarn, edgeWarn, lockTarget, pos, rot.LookVector, mouseSteer
end

-- ------------------------------------------------------------------ public
function Flight.init(r)
	remotes = r
	UserInputService.InputBegan:Connect(function(input, processed)
		if not active then return end
		if input.UserInputType == Enum.UserInputType.MouseButton1 and not processed then firing = true; return end
		if processed then return end
		local k = input.KeyCode
		if k == Enum.KeyCode.Space or k == Enum.KeyCode.ButtonA then firing = true
		elseif k == Enum.KeyCode.M then mouseSteer = not mouseSteer
		elseif k == Enum.KeyCode.X or k == Enum.KeyCode.ButtonX then fireMissile()
		elseif k == Enum.KeyCode.G or k == Enum.KeyCode.ButtonB then remotes.Flare:FireServer()
		elseif k == Enum.KeyCode.V or k == Enum.KeyCode.ButtonY then cockpit = not cockpit; if Flight.onCockpit then Flight.onCockpit(cockpit) end
		elseif k == Enum.KeyCode.I then invertPitch = not invertPitch end
	end)
	UserInputService.InputEnded:Connect(function(input)
		if input.UserInputType == Enum.UserInputType.MouseButton1 or input.KeyCode == Enum.KeyCode.Space or input.KeyCode == Enum.KeyCode.ButtonA then firing = false end
	end)
	-- the right mouse button is a key code in InputBegan only for some set-ups: take it by input type too
	UserInputService.InputBegan:Connect(function(input, processed)
		if active and not processed and input.UserInputType == Enum.UserInputType.MouseButton2 then fireMissile() end
	end)
	RunService:BindToRenderStep("DogfightFlight", Enum.RenderPriority.Camera.Value + 1, step)
end

function Flight.start(model: Model, crashed: () -> ())
	jet = model
	body = model.PrimaryPart
	local cf = body.CFrame
	pos, rot = cf.Position, cf.Rotation
	speed, throttle = J.StartSpeed, 0.7
	camRot = rot
	cockpit, firing = false, false
	onCrash = crashed
	camera.CameraType = Enum.CameraType.Scriptable
	active = true
end

function Flight.stop()
	active = false
	firing = false
	if cockpit and Flight.onCockpit then Flight.onCockpit(false) end
	cockpit = false
end

function Flight.fireMissile() fireMissile() end
function Flight.setFiring(v: boolean) firing = v end
function Flight.flare() remotes.Flare:FireServer() end
function Flight.toggleCockpit() cockpit = not cockpit; if Flight.onCockpit then Flight.onCockpit(cockpit) end end
function Flight.isActive(): boolean return active end

return Flight
