--!nonstrict
-- Jets, guns, missiles, flares, damage and kills: everything that decides who hits whom lives on the server.
-- Every jet belongs to a room (attribute RoomId) and a team (Team); only members of the same room see and hit each
-- other, and in a team-fight room only the other team is hostile.  A two-seat jet (Seats = 2) carries a second
-- player in the rear seat (WsoId) who fires missiles, drops flares and marks targets for the pilot.
local Debris = game:GetService("Debris")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local JetBuilder = require(Shared.JetBuilder)
local Data = require(script.Parent.Data)
local Rooms = require(script.Parent.Rooms)
local World = require(script.Parent.World)

local Combat = {}
local remotes = nil
local rng = Random.new()

local jets = {}      -- [Player] = Model: the jet a player flies
local rear = {}      -- [Player] = Model: the jet whose rear seat a player holds
local lastShot, lastMissile, lastFlare = {}, {}, {}
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

-- the jet a player is in (and "pilot" or "wso")
function Combat.seatOf(player: Player)
	local j = jets[player]
	if j and j.Parent then return j, "pilot" end
	local r = rear[player]
	if r and r.Parent then return r, "wso" end
	return nil, nil
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

-- everybody in a jet: the pilot and the rear seat
local function occupants(model: Model): { Player }
	local out = {}
	local pid, wid = model:GetAttribute("OwnerId"), model:GetAttribute("WsoId")
	if pid then
		local p = Players:GetPlayerByUserId(pid)
		if p then table.insert(out, p) end
	end
	if wid and wid ~= 0 then
		local p = Players:GetPlayerByUserId(wid)
		if p then table.insert(out, p) end
	end
	return out
end
Combat.occupants = occupants

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

-- tracer lines are shown only to the members of the room
local function tracer(roomId: number, from: Vector3, to: Vector3, color: Color3, except: Player?)
	local room = Rooms.byId(roomId)
	if not room then return end
	for p in room.members do
		if p ~= except then remotes.Tracer:FireClient(p, from, to, color) end
	end
end
Combat.tracer = tracer

-- is `target` an enemy of `attacker` (a jet)?  Same room; the AI is hostile to everybody, a jet only in a team fight
function Combat.hostile(attacker: Model, target: Model): boolean
	local room = attacker:GetAttribute("RoomId")
	if not room or target:GetAttribute("RoomId") ~= room then return false end
	if target.Parent == workspace.Enemies then return true end
	if target.Parent == workspace.Jets and target ~= attacker then
		local r = Rooms.byId(room)
		return r ~= nil and r.mode == "pvp" and target:GetAttribute("Team") ~= attacker:GetAttribute("Team")
	end
	return false
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
	remotes.Mark.OnServerEvent:Connect(function(player, target) Combat.mark(player, target) end)
	remotes.Crashed.OnServerEvent:Connect(function(player)
		local j = Combat.jetOf(player)
		if j then Combat.destroy(j, nil, "Lezuhantál") end
	end)
	remotes.JoinSeat.OnServerInvoke = function(player, pilotUserId) return Combat.joinSeat(player, pilotUserId) end
	remotes.LeaveSeat.OnServerInvoke = function(player) Combat.leaveSeat(player) return true end

	-- a member leaves the room: the jet goes with them (the rear seat just empties)
	Rooms.hooks.left = function(player)
		Combat.removeJet(player)
	end
	-- nobody changes team in the air
	Rooms.hooks.canSwitch = function(player)
		return Combat.seatOf(player) == nil
	end
	Players.PlayerRemoving:Connect(function(player)
		Combat.removeJet(player)
		lastShot[player], lastMissile[player], lastFlare[player] = nil, nil, nil
	end)
end

-- ------------------------------------------------------------------ the jets
-- a new jet for a player (twoSeat: with a rear seat that a team mate can take), in the air over the island
function Combat.spawnPlayerJet(player: Player, twoSeat: boolean?)
	local room = Rooms.get(player)
	if not room then return nil end
	Combat.removeJet(player)
	local p = Data.get(player)
	local team = room.team[player] or "A"
	local pos, look = World.spawnPoint(team, room.mode == "pvp", rng)
	local model = JetBuilder.build(p and p.airOn, p and p.pilotOn, false, twoSeat == true, nil, p and p.jetOn)
	model.Name = "Jet_" .. player.Name
	model:SetAttribute("Health", Config.Jet.Health)
	model:SetAttribute("MaxHealth", Config.Jet.Health)
	model:SetAttribute("OwnerId", player.UserId)
	model:SetAttribute("RoomId", room.id)
	model:SetAttribute("Team", team)
	model:SetAttribute("Seats", twoSeat and 2 or 1)
	model:SetAttribute("WsoId", 0)
	model:SetAttribute("SeatOpen", twoSeat == true)
	model:SetAttribute("Missiles", Config.Jet.Missiles)
	model:SetAttribute("Flares", Config.Jet.Flares)
	model:SetAttribute("FlareUntil", 0)
	model:SetAttribute("MarkUid", 0)
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
	Rooms.push(room)
	return model
end

-- the rear seat of somebody's two-seat jet (same room, same team)
function Combat.joinSeat(player: Player, pilotUserId)
	if Combat.seatOf(player) then return false, "Már repülsz" end
	local room = Rooms.get(player)
	local pilot = typeof(pilotUserId) == "number" and Players:GetPlayerByUserId(pilotUserId)
	local jet = pilot and Combat.jetOf(pilot)
	if not room or not jet then return false, "Ez a gép már nincs a levegőben" end
	if jet:GetAttribute("RoomId") ~= room.id then return false, "Másik szoba" end
	if jet:GetAttribute("Seats") ~= 2 or jet:GetAttribute("WsoId") ~= 0 or not jet:GetAttribute("SeatOpen") then return false, "A hátsó ülés foglalt" end
	if jet:GetAttribute("Team") ~= (room.team[player] or "A") then return false, "Ez a másik csapat gépe" end
	local d = Data.get(player)
	jet:SetAttribute("WsoId", player.UserId)
	JetBuilder.addPilot(jet, d and d.pilotOn, 2, true)
	rear[player] = jet
	remotes.Seat:FireClient(player, jet)
	toast(pilot, player.DisplayName .. " beült a hátsó ülésre", "good")
	Rooms.push(room)
	return true, "Beültél"
end

function Combat.leaveSeat(player: Player)
	local jet = rear[player]
	rear[player] = nil
	if jet and jet.Parent then
		if jet:GetAttribute("WsoId") == player.UserId then
			jet:SetAttribute("WsoId", 0)
			JetBuilder.removeSeat(jet, 2)
			local pilot = Players:GetPlayerByUserId(jet:GetAttribute("OwnerId") or 0)
			toast(pilot, player.DisplayName .. " kiszállt a hátsó ülésből", "warn")
		end
	end
	if player.Parent then remotes.Seat:FireClient(player, nil) end
end

-- takes a player out of whatever jet they are in (a pilot's jet is removed, with the rear seat's passenger)
function Combat.removeJet(player: Player)
	local jet = jets[player]
	jets[player] = nil
	if jet and jet.Parent then
		for _, p in occupants(jet) do
			if p ~= player then
				rear[p] = nil
				remotes.Seat:FireClient(p, nil)
				remotes.Died:FireClient(p, "A pilóta kilépett")
			end
		end
		jet:Destroy()
	end
	if rear[player] then Combat.leaveSeat(player) end
end

-- the rear seat marks an enemy: the pilot's display shows it and the pilot's lock prefers it
function Combat.mark(player: Player, target)
	local jet, role = Combat.seatOf(player)
	if not jet or role ~= "wso" then return end
	if typeof(target) ~= "Instance" or not target:IsA("Model") or not target.Parent or not Combat.hostile(jet, target) then
		jet:SetAttribute("MarkUid", 0)
		return
	end
	local uid = target:GetAttribute("Uid")
	if not uid then
		Combat.uidCounter = (Combat.uidCounter or 0) + 1
		uid = Combat.uidCounter
		target:SetAttribute("Uid", uid)
	end
	jet:SetAttribute("MarkUid", uid)
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

-- the coins and the score of a kill; the other seat of the shooter's jet shares in it
local function award(attacker: Player, amount: number, text: string)
	local jet = Combat.seatOf(attacker)
	Data.addKill(attacker)
	Data.addCoins(attacker, amount)
	toast(attacker, text .. " +" .. amount .. " érme", "good")
	if jet then
		for _, p in occupants(jet) do
			if p ~= attacker then
				Data.addCoins(p, math.floor(amount / 2))
				toast(p, text .. " +" .. math.floor(amount / 2) .. " érme", "good")
			end
		end
	end
end

function Combat.destroy(model: Model, attacker: Player?, how: string?)
	if not model.Parent then return end
	model:SetAttribute("Health", 0)
	local pos = model:GetPivot().Position
	explode(pos, 18)
	local ownerId = model:GetAttribute("OwnerId")
	if ownerId then
		-- a player's jet: everybody in it is out
		for _, victim in occupants(model) do
			jets[victim] = nil
			rear[victim] = nil
			remotes.MissileAlert:FireClient(victim, false)
			remotes.Seat:FireClient(victim, nil)
			remotes.Died:FireClient(victim, how or "Lelőttek")
		end
		if attacker then
			local room = Rooms.byId(model:GetAttribute("RoomId"))
			award(attacker, Config.Rooms.PvpKillCoins, "Lelőtted az ellenfelet!")
			if room then
				local team = room.team[attacker]
				if team then Rooms.score(room, team) end
				Rooms.push(room)
			end
		end
	else
		if attacker then award(attacker, Config.Coins.PerKill, "Lelőttél egy ellenséget!") end
		killedEvent:Fire(model, attacker)
	end
	model:Destroy()
end

-- ------------------------------------------------------------------ guns
-- the closest enemy on the line of fire (a sphere round each jet), or nil
local function lineTarget(origin: Vector3, look: Vector3, range: number, radius: number, jet: Model)
	local best, bestT = nil, range
	local function consider(m: Model)
		if not m:IsA("Model") or not Combat.hostile(jet, m) then return end
		local c = m:GetPivot().Position
		local v = c - origin
		local t = v:Dot(look)
		if t > 0 and t < bestT then
			local perp = (v - look * t).Magnitude
			if perp < radius + t * 0.004 then best, bestT = m, t end
		end
	end
	for _, m in workspace.Enemies:GetChildren() do consider(m) end
	for _, m in workspace.Jets:GetChildren() do consider(m) end
	return best, bestT
end

function Combat.fireGun(player: Player)
	local jet = Combat.jetOf(player)               -- only the pilot has the gun
	if not jet then return end
	local now = os.clock()
	if now - (lastShot[player] or 0) < 1 / (Config.Gun.Rate + 2) then return end
	lastShot[player] = now
	local body = jet.PrimaryPart
	local look = body.CFrame.LookVector
	local origin = body.Position + look * 12
	local G = Config.Gun
	local target, t = lineTarget(origin, look, G.Range, G.Radius, jet)
	local dest = origin + look * (target and t or G.Range)
	tracer(jet:GetAttribute("RoomId"), origin, dest, Color3.fromRGB(255, 240, 140), player)
	if target then Combat.damage(target, G.Damage, player, "gépágyú") end
end

-- ------------------------------------------------------------------ missiles
local function launchMissile(owner: Player?, origin: CFrame, target: Model, damage: number, roomId: number)
	local part = Instance.new("Part")
	part.Name = "Missile"
	part.Size = Vector3.new(0.8, 0.8, 5)
	part.Color = Color3.fromRGB(255, 190, 90)
	part.Material = Enum.Material.Neon
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CFrame = origin
	part:SetAttribute("RoomId", roomId)
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
	local m = { part = part, dir = origin.LookVector, target = target, owner = owner, damage = damage, age = 0, judged = false, lost = false, victims = {} }
	table.insert(missiles, m)
	if target:GetAttribute("OwnerId") then
		for _, victim in occupants(target) do
			table.insert(m.victims, victim)
			remotes.MissileAlert:FireClient(victim, true)
		end
	end
	return m
end
Combat.launchMissile = launchMissile

local function endMissile(m)
	m.part:Destroy()
	m.dead = true
	for _, v in m.victims do
		if v.Parent then remotes.MissileAlert:FireClient(v, false) end
	end
end

-- a missile from the pilot (the target must be in front of the nose) or from the rear seat (a wide cone)
function Combat.playerMissile(player: Player, target)
	local jet, role = Combat.seatOf(player)
	if not jet or typeof(target) ~= "Instance" or not target:IsA("Model") or not target.Parent then return end
	if not Combat.hostile(jet, target) then return end
	local now = os.clock()
	if now - (lastMissile[jet] or 0) < 0.8 then return end
	local n = jet:GetAttribute("Missiles") or 0
	if n <= 0 then return end
	local body = jet.PrimaryPart
	local to = target:GetPivot().Position - body.Position
	local dist = to.Magnitude
	if dist > Config.Missile.Range or dist < 80 then return end
	local cone = role == "wso" and 80 or Config.Missile.Cone + 6
	if to.Unit:Dot(body.CFrame.LookVector) < math.cos(math.rad(cone)) then return end
	lastMissile[jet] = now
	jet:SetAttribute("Missiles", n - 1)
	local startCF = CFrame.lookAt(body.Position + to.Unit * 9, body.Position + to.Unit * 20)
	if role == "pilot" then startCF = body.CFrame * CFrame.new(0, -1, -8) end
	launchMissile(player, startCF, target, Config.Missile.Damage, jet:GetAttribute("RoomId"))
	task.delay(Config.Jet.MissileReload, function()
		if jet.Parent then jet:SetAttribute("Missiles", math.min(Config.Jet.Missiles, (jet:GetAttribute("Missiles") or 0) + 1)) end
	end)
end

function Combat.flare(player: Player)
	local jet = Combat.seatOf(player)
	if not jet then return end
	local now = os.clock()
	if now - (lastFlare[jet] or 0) < Config.Jet.FlareCooldown then return end
	local n = jet:GetAttribute("Flares") or 0
	if n <= 0 then return end
	lastFlare[jet] = now
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
				endMissile(m)
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
							if m.owner then toast(m.owner, "Kicselezték a rakétádat!", "warn") end
							for _, v in m.victims do toast(v, "Kicselezted a rakétát!", "good") end
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
							endMissile(m)
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
