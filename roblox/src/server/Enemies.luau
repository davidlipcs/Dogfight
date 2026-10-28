--!nonstrict
-- The enemy jets (flown by the server) and the waves.  They chase the nearest player, shoot when they are lined
-- up and fire a missile now and then - the flares and a hard turn are the answer.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local JetBuilder = require(Shared.JetBuilder)
local Data = require(script.Parent.Data)
local Combat = require(script.Parent.Combat)

local Enemies = {}
local remotes = nil
local rng = Random.new()

local list = {}          -- enemy tables
local wave = 0
local pending = 0        -- enemies of this wave that have not come in yet
local waveTimer = 3
local spawnTimer = 0
local idleTime = 0

function Enemies.wave(): number
	return wave
end
function Enemies.count(): number
	return #list + pending
end

local function flyingPlayers()
	local out = {}
	for _, p in Players:GetPlayers() do
		local j = Combat.jetOf(p)
		if j then table.insert(out, { player = p, jet = j }) end
	end
	return out
end

local function spawnOne()
	local E, W = Config.Enemy, Config.World
	local a = rng:NextNumber(0, math.pi * 2)
	local pos = Vector3.new(math.cos(a) * W.EnemyRing, rng:NextNumber(350, 800), math.sin(a) * W.EnemyRing)
	local look = (Vector3.new(0, 400, 0) - pos).Unit
	local model = JetBuilder.build(nil, nil, true)
	model.Name = "Enemy"
	model:SetAttribute("Health", E.Health + math.min(wave, 10) * 4)
	model:SetAttribute("MaxHealth", E.Health + math.min(wave, 10) * 4)
	model.PrimaryPart.Anchored = true
	model:PivotTo(CFrame.lookAt(pos, pos + look))
	model.Parent = workspace.Enemies
	table.insert(list, {
		model = model, pos = pos, look = look, bank = 0, speed = E.Speed,
		gunT = 0, missT = rng:NextNumber(4, E.MissileCooldown), phase = rng:NextNumber(0, 6.28),
	})
end

local function startWave()
	wave += 1
	local n = Config.Enemy.WaveBase + wave
	pending = n
	spawnTimer = 0
	for _, f in flyingPlayers() do Combat.toast(f.player, "HULLÁM " .. wave .. " – " .. n .. " ellenség jön", "warn") end
end

function Enemies.init(r)
	remotes = r
	Combat.EnemyKilled:Connect(function(model, attacker)
		for i = #list, 1, -1 do
			if list[i].model == model then table.remove(list, i) end
		end
		if #list == 0 and pending == 0 then
			waveTimer = Config.Enemy.WaveDelay
			local bonus = Config.Coins.WaveBonus * math.min(wave, 10)
			for _, f in flyingPlayers() do
				Data.addCoins(f.player, bonus)
				Combat.toast(f.player, "HULLÁM " .. wave .. " KÉSZ! +" .. bonus .. " érme", "good")
			end
		end
	end)
end

local function nearestTarget(pos: Vector3)
	local best, bestD = nil, math.huge
	for _, f in flyingPlayers() do
		local d = (f.jet:GetPivot().Position - pos).Magnitude
		if d < bestD then best, bestD = f.jet, d end
	end
	return best, bestD
end

local function steer(e, dt: number, wish: Vector3, rate: number)
	local look = e.look
	local ang = math.acos(math.clamp(look:Dot(wish), -1, 1))
	local maxTurn = rate * dt
	local nl = look
	if ang <= maxTurn then nl = wish elseif ang > 1e-4 then nl = look:Lerp(wish, maxTurn / ang).Unit end
	-- bank into the turn (looks right, costs nothing)
	local side = look:Cross(nl).Y
	local want = math.clamp(side / math.max(dt, 1e-3) * 1.4, -1.2, 1.2)
	e.bank += (want - e.bank) * math.min(1, dt * 4)
	e.look = nl
	return ang
end

function Enemies.step(dt: number)
	local E, W = Config.Enemy, Config.World
	local fliers = flyingPlayers()
	if #fliers == 0 then
		-- nobody is flying: the wave stops, the leftovers go away after a while
		idleTime += dt
		if idleTime > 10 and (#list > 0 or pending > 0) then
			for _, e in list do e.model:Destroy() end
			list = {}
			pending = 0
			wave = math.max(0, wave - 1)
			waveTimer = 3
		end
		return
	end
	idleTime = 0

	-- waves
	if #list == 0 and pending == 0 then
		waveTimer -= dt
		if waveTimer <= 0 then startWave() end
	end
	if pending > 0 then
		spawnTimer -= dt
		if spawnTimer <= 0 and #list < E.MaxActive then
			spawnOne()
			pending -= 1
			spawnTimer = 2.5
		end
	end

	for i = #list, 1, -1 do
		local e = list[i]
		if not e.model.Parent then
			table.remove(list, i)
		else
			local target, dist = nearestTarget(e.pos)
			local wish = e.look
			if target then
				local tpos = target:GetPivot().Position
				local tvel = target.PrimaryPart and target.PrimaryPart.AssemblyLinearVelocity or Vector3.zero
				local lead = tpos + tvel * math.clamp(dist / 900, 0, 1.2)
				wish = (lead - e.pos)
				if wish.Magnitude < 1 then wish = e.look else wish = wish.Unit end
				-- hold the course instead of a head-on pass: swing out a little when very close
				if dist < 250 then wish = (wish + Vector3.new(math.sin(e.phase), 0.25, math.cos(e.phase)) * 0.8).Unit end
			else
				wish = (Vector3.new(0, 500, 0) - e.pos).Unit
			end
			-- the edges of the field and the ground
			if math.abs(e.pos.X) > W.Half - 300 or math.abs(e.pos.Z) > W.Half - 300 then
				wish = (Vector3.new(-e.pos.X, 450 - e.pos.Y, -e.pos.Z)).Unit
			end
			if e.pos.Y < 120 and wish.Y < 0.2 then wish = Vector3.new(wish.X, 0.35, wish.Z).Unit end
			if e.pos.Y > 1600 and wish.Y > -0.1 then wish = Vector3.new(wish.X, -0.3, wish.Z).Unit end
			steer(e, dt, wish, E.TurnRate)
			e.pos += e.look * e.speed * dt
			local up = Vector3.new(0, 1, 0)
			if math.abs(e.look.Y) > 0.98 then up = Vector3.new(0, 0, 1) end
			e.model:PivotTo(CFrame.lookAt(e.pos, e.pos + e.look, up) * CFrame.Angles(0, 0, e.bank))
			e.model:SetAttribute("Vel", e.look * e.speed)
			e.phase += dt * 0.7

			-- weapons
			if target then
				local aimOk = target:GetPivot().Position - e.pos
				local aim = math.acos(math.clamp(e.look:Dot(aimOk.Unit), -1, 1))
				e.gunT -= dt
				if dist < E.GunRange and aim < 0.1 and e.gunT <= 0 then
					e.gunT = 0.2
					local hitChance = 0.45
					local from = e.pos + e.look * 12
					local to = target:GetPivot().Position
					for _, p in Players:GetPlayers() do remotes.Tracer:FireClient(p, from, from + (to - from).Unit * math.min(dist, E.GunRange), Color3.fromRGB(255, 90, 70)) end
					if rng:NextNumber() < hitChance then Combat.damage(target, E.GunDamage, nil, "ellenséges ágyú") end
				end
				e.missT -= dt
				if e.missT <= 0 and dist < E.MissileRange and dist > 700 and aim < 0.45 then
					e.missT = E.MissileCooldown * rng:NextNumber(0.8, 1.3)
					Combat.launchMissile(nil, CFrame.lookAt(e.pos + e.look * 10, e.pos + e.look * 20), target, Config.Missile.Damage * 0.8)
				end
			end
		end
	end
end

return Enemies
