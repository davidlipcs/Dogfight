--!nonstrict
-- Jets, guns, missiles, flares, damage and kills: everything that decides who hits whom lives on the server.
local Debris = game:GetService("Debris")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local JetBuilder = require(Shared.JetBuilder)
local Data = require(script.Parent.Data)

local Combat = {}
local remotes = nil
local rng = Random.new()

local jets = {}      -- [Player] = Model
local lastShot = {}  -- [Player] = os.clock()
local lastMissile = {}
local lastFlare = {}
local missiles = {}  -- active missile tables
local killedEvent = Instance.new("BindableEvent")
Combat.EnemyKilled = killedEvent.Event      -- fires (enemyModel, attackerPlayer or nil)

local function folder(name: string): Folder
	local f = workspace:FindFirstChild(name)
	if not f then
		f = Instance.new("Folder")
		f.Name = name
		f.Parent = workspace
	end
	return f
end

function Combat.jetOf(player: Player): Model?
	local j = jets[player]
	if j and j.Parent then return j end
	return nil
end

local function toast(player: Player?, text: string, kind: string?)
	if player and player.Parent and remotes then remotes.Toast:FireClient(player, text, kind or "info") end
end
Combat.toast = toast

local function velocityOf(model: Model): Vector3
	local v = model:GetAttribute("Vel")
	if typeof(v) == "Vector3" then return v end
	local body = model.PrimaryPart
	if body then return body.AssemblyLinearVelocity end
	return Vector3.zero
end

local function explode(pos: Vector3, size: number?)
	local e = Instance.new("Explosion")
	e.Position = pos
	e.BlastRadius = size or 10
	e.BlastPressure = 0
	e.DestroyJointRadiusPercent = 0
	e.Parent = workspace
	Debris:AddItem(e, 4)
end

function Combat.init(r)
	remotes = r
	folder("Jets")
	folder("Enemies")
	folder("Missiles")
	folder("Effects")

	remotes.Fire.OnServerEvent:Connect(function(player) Combat.fireGun(player) end)
	remotes.FireMissile.OnServerEvent:Connect(function(player, target) Combat.playerMissile(player, target) end)
	remotes.Flare.OnServerEvent:Connect(function(player) Combat.flare(player) end)
	remotes.Crashed.OnServerEvent:Connect(function(player)
		local j = Combat.jetOf(player)
		if j then Combat.destroy(j, nil, "Lezuhantál") end
	end)
	Players.PlayerRemoving:Connect(function(player)
		local j = jets[player]
		if j then j:Destroy() end
		jets[player] = nil
		lastShot[player], lastMissile[player], lastFlare[player] = nil, nil, nil
	end)
end

-- a new jet for a player, in the air over the island and flying
function Combat.spawnPlayerJet(player: Player)
	local old = jets[player]
	if old then old:Destroy() end
	local p = Data.get(player)
	local W = Config.World
	local a = rng:NextNumber(0, math.pi * 2)
	local pos = Vector3.new(math.cos(a) * W.SpawnRadius, W.SpawnHeight + rng:NextNumber(-60, 60), math.sin(a) * W.SpawnRadius)
	local look = Vector3.new(-pos.X, 0, -pos.Z).Unit
	local model = JetBuilder.build(p and p.airOn, p and p.pilotOn, false)
	model.Name = "Jet_" .. player.Name
	model:SetAttribute("Health", Config.Jet.Health)
	model:SetAttribute("MaxHealth", Config.Jet.Health)
	model:SetAttribute("OwnerId", player.UserId)
	model:SetAttribute("Missiles", Config.Jet.Missiles)
	model:SetAttribute("Flares", Config.Jet.Flares)
	model:SetAttribute("FlareUntil", 0)
	model:PivotTo(CFrame.lookAt(pos, pos + look))
	model.Parent = workspace.Jets
	local body = model.PrimaryPart
	-- a force that cancels gravity: the player's own flight code moves the jet
	local att = Instance.new("Attachment")
	att.Parent = body
	local vf = Instance.new("VectorForce")
	vf.Attachment0 = att
	vf.RelativeTo = Enum.ActuatorRelativeTo.World
	vf.ApplyAtCenterOfMass = true
	vf.Force = Vector3.new(0, body.AssemblyMass * workspace.Gravity, 0)
	vf.Parent = body
	body.AssemblyLinearVelocity = look * Config.Jet.StartSpeed
	pcall(function() body:SetNetworkOwner(player) end)
	jets[player] = model
	return model
end

-- ------------------------------------------------------------------ damage
function Combat.damage(model: Model, amount: number, attacker: Player?, how: string?)
	if not model or not model.Parent then return end
	local hp = model:GetAttribute("Health")
	if not hp or hp <= 0 then return end
	hp -= amount
	model:SetAttribute("Health", hp)
	if hp <= 0 then Combat.destroy(model, attacker, how) end
end

function Combat.destroy(model: Model, attacker: Player?, how: string?)
	if not model.Parent then return end
	model:SetAttribute("Health", 0)
	local pos = model:GetPivot().Position
	explode(pos, 18)
	local ownerId = model:GetAttribute("OwnerId")
	if ownerId then
		local victim = Players:GetPlayerByUserId(ownerId)
		if victim then
			jets[victim] = nil
			remotes.MissileAlert:FireClient(victim, false)
			remotes.Died:FireClient(victim, how or "Lelőttek")
		end
	else
		if attacker then
			Data.addKill(attacker)
			Data.addCoins(attacker, Config.Coins.PerKill)
			toast(attacker, "Lelőttél egy ellenséget! +" .. Config.Coins.PerKill .. " érme", "good")
		end
		killedEvent:Fire(model, attacker)
	end
	model:Destroy()
end

-- ------------------------------------------------------------------ guns
-- the closest enemy on the line of fire (a sphere round each jet), or nil
local function lineTarget(origin: Vector3, look: Vector3, range: number, radius: number, hostile: (Model) -> boolean)
	local best, bestT = nil, range
	local function consider(m: Model)
		if not m:IsA("Model") or not hostile(m) then return end
		local c = m:GetPivot().Position
		local v = c - origin
		local t = v:Dot(look)
		if t > 0 and t < bestT then
			local perp = (v - look * t).Magnitude
			if perp < radius + t * 0.004 then best, bestT = m, t end
		end
	end
	for _, m in workspace.Enemies:GetChildren() do consider(m) end
	if Config.PvP then for _, m in workspace.Jets:GetChildren() do consider(m) end end
	return best, bestT
end

function Combat.fireGun(player: Player)
	local jet = Combat.jetOf(player)
	if not jet then return end
	local now = os.clock()
	if now - (lastShot[player] or 0) < 1 / (Config.Gun.Rate + 2) then return end
	lastShot[player] = now
	local body = jet.PrimaryPart
	local look = body.CFrame.LookVector
	local origin = body.Position + look * 12
	local G = Config.Gun
	local target, t = lineTarget(origin, look, G.Range, G.Radius, function(m) return m ~= jet end)
	local dest = origin + look * (target and t or G.Range)
	for _, p in Players:GetPlayers() do
		if p ~= player then remotes.Tracer:FireClient(p, origin, dest, Color3.fromRGB(255, 240, 140)) end
	end
	if target then Combat.damage(target, G.Damage, player, "gépágyú") end
end

-- ------------------------------------------------------------------ missiles
local function launchMissile(owner: Player?, origin: CFrame, target: Model, damage: number)
	local part = Instance.new("Part")
	part.Name = "Missile"
	part.Size = Vector3.new(0.8, 0.8, 5)
	part.Color = Color3.fromRGB(255, 190, 90)
	part.Material = Enum.Material.Neon
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CFrame = origin
	local a0, a1 = Instance.new("Attachment"), Instance.new("Attachment")
	a0.Position = Vector3.new(0, 0.35, 2.4)
	a1.Position = Vector3.new(0, -0.35, 2.4)
	a0.Parent, a1.Parent = part, part
	local trail = Instance.new("Trail")
	trail.Attachment0, trail.Attachment1 = a0, a1
	trail.Lifetime = 0.9
	trail.Color = ColorSequence.new(Color3.fromRGB(255, 200, 120), Color3.fromRGB(120, 120, 120))
	trail.Transparency = NumberSequence.new(0.1, 1)
	trail.Parent = part
	part.Parent = workspace.Missiles
	local m = { part = part, dir = origin.LookVector, target = target, owner = owner, damage = damage, age = 0, judged = false, lost = false }
	table.insert(missiles, m)
	local ownerId = target:GetAttribute("OwnerId")
	if ownerId then
		local victim = Players:GetPlayerByUserId(ownerId)
		if victim then
			m.victim = victim
			remotes.MissileAlert:FireClient(victim, true)
		end
	end
	return m
end
Combat.launchMissile = launchMissile

local function endMissile(m, hit: boolean)
	m.part:Destroy()
	m.dead = true
	if m.victim and m.victim.Parent then remotes.MissileAlert:FireClient(m.victim, false) end
end

function Combat.playerMissile(player: Player, target)
	local jet = Combat.jetOf(player)
	if not jet or typeof(target) ~= "Instance" or not target:IsA("Model") or not target.Parent then return end
	local hostile = target.Parent == workspace.Enemies or (Config.PvP and target.Parent == workspace.Jets and target ~= jet)
	if not hostile then return end
	local now = os.clock()
	if now - (lastMissile[player] or 0) < 0.8 then return end
	local n = jet:GetAttribute("Missiles") or 0
	if n <= 0 then return end
	local body = jet.PrimaryPart
	local to = target:GetPivot().Position - body.Position
	local dist = to.Magnitude
	if dist > Config.Missile.Range or dist < 80 then return end
	if to.Unit:Dot(body.CFrame.LookVector) < math.cos(math.rad(Config.Missile.Cone + 6)) then return end
	lastMissile[player] = now
	jet:SetAttribute("Missiles", n - 1)
	launchMissile(player, body.CFrame * CFrame.new(0, -1, -8), target, Config.Missile.Damage)
	task.delay(Config.Jet.MissileReload, function()
		if jet.Parent then jet:SetAttribute("Missiles", math.min(Config.Jet.Missiles, (jet:GetAttribute("Missiles") or 0) + 1)) end
	end)
end

function Combat.flare(player: Player)
	local jet = Combat.jetOf(player)
	if not jet then return end
	local now = os.clock()
	if now - (lastFlare[player] or 0) < Config.Jet.FlareCooldown then return end
	local n = jet:GetAttribute("Flares") or 0
	if n <= 0 then return end
	lastFlare[player] = now
	jet:SetAttribute("Flares", n - 1)
	jet:SetAttribute("FlareUntil", now + Config.Jet.FlareTime)
	local body = jet.PrimaryPart
	for i = 1, 3 do
		local f = Instance.new("Part")
		f.Name = "Flare"
		f.Shape = Enum.PartType.Ball
		f.Size = Vector3.new(1.4, 1.4, 1.4)
		f.Color = Color3.fromRGB(255, 220, 140)
		f.Material = Enum.Material.Neon
		f.CanCollide = false
		f.CanQuery = false
		f.CFrame = body.CFrame * CFrame.new(rng:NextNumber(-2, 2), -2, 9)
		f.Parent = workspace.Effects
		f.AssemblyLinearVelocity = body.AssemblyLinearVelocity * 0.6 + Vector3.new(rng:NextNumber(-25, 25), -20, rng:NextNumber(-25, 25))
		local light = Instance.new("PointLight")
		light.Color = f.Color
		light.Range = 14
		light.Parent = f
		Debris:AddItem(f, 3)
	end
end

-- the missiles fly: they steer at the target (limited turn), a flare burst can shake them off, the fuse goes
-- off close to the target
function Combat.step(dt: number)
	local M = Config.Missile
	local now = os.clock()
	for i = #missiles, 1, -1 do
		local m = missiles[i]
		if m.dead then
			table.remove(missiles, i)
		else
			m.age += dt
			local target = m.target
			local pos = m.part.Position
			if m.age > M.Life or pos.Y < -5 or not m.part.Parent then
				endMissile(m, false)
			else
				local alive = target and target.Parent and (target:GetAttribute("Health") or 0) > 0
				if alive and not m.lost then
					local tpos = target:GetPivot().Position
					local dist = (tpos - pos).Magnitude
					-- the last moment: flares (a player) or the pilot's skill (an enemy) can shake the missile off, once
					if not m.judged and dist < 450 then
						m.judged = true
						local isPlayer = target:GetAttribute("OwnerId") ~= nil
						local shaken
						if isPlayer then
							shaken = (target:GetAttribute("FlareUntil") or 0) > now and rng:NextNumber() < 0.6
						else
							shaken = rng:NextNumber() < Config.Enemy.FlareChance
						end
						if shaken then
							m.lost = true
							if m.owner then toast(m.owner, "Az ellenség kicselezte a rakétát!", "warn") end
							if m.victim then toast(m.victim, "Kicselezted a rakétát!", "good") end
						end
					end
					if not m.lost then
						local lead = tpos + velocityOf(target) * math.clamp(dist / M.Speed, 0, 1.5)
						local want = (lead - pos)
						if want.Magnitude > 0.1 then
							want = want.Unit
							local ang = math.acos(math.clamp(m.dir:Dot(want), -1, 1))
							local maxTurn = M.TurnRate * dt
							if ang <= maxTurn then m.dir = want else m.dir = m.dir:Lerp(want, maxTurn / ang).Unit end
						end
						if dist < M.FuseRadius then
							explode(pos, 12)
							Combat.damage(target, m.damage, m.owner, "rakéta")
							endMissile(m, true)
						end
					end
				end
				if not m.dead then
					local np = pos + m.dir * M.Speed * dt
					m.part.CFrame = CFrame.lookAt(np, np + m.dir)
				end
			end
		end
	end
end

return Combat
