--!nonstrict
-- The enemy jets (flown by the server) and the waves.  Every co-op room has its own waves: the enemies chase the
-- nearest jet of that room, shoot when they are lined up and fire a missile now and then - the flares and a hard
-- turn are the answer.  (A team-fight room has no AI.)
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local JetBuilder = require(Shared.JetBuilder)
local Data = require(script.Parent.Data)
local Combat = require(script.Parent.Combat)
local Rooms = require(script.Parent.Rooms)

local Enemies = {}
local remotes = nil
local rng = Random.new()

local state = {}         -- [roomId] = { list, wave, pending, waveTimer, spawnTimer, idle }

local function stateOf(room)
	local s = state[room.id]
	if not s then
		s = { list = {}, wave = 0, pending = 0, waveTimer = 3, spawnTimer = 0, idle = 0 }
		state[room.id] = s
	end
	return s
end

function Enemies.wave(room): number
	local s = state[room.id]
	return s and s.wave or 0
end
function Enemies.count(room): number
	local s = state[room.id]
	return s and (#s.list + s.pending) or 0
end

-- the room's jets in the air
local function flyers(room)
	local out = {}
	for _, p in Rooms.players(room) do
		local j = Combat.jetOf(p)
		if j then table.insert(out, { player = p, jet = j }) end
	end
	return out
end

local function clearRoom(id: number)
	local s = state[id]
	if not s then return end
	for _, e in s.list do e.model:Destroy() end
	state[id] = nil
end
Enemies.clearRoom = clearRoom

local function spawnOne(room, s)
	local E, W = Config.Enemy, Config.World
	local a = rng:NextNumber(0, math.pi * 2)
	local pos = Vector3.new(math.cos(a) * W.EnemyRing, rng:NextNumber(350, 800), math.sin(a) * W.EnemyRing)
	local look = (Vector3.new(0, 400, 0) - pos).Unit
	local model = JetBuilder.build(nil, nil, true)
	model.Name = "Enemy"
	local hp = E.Health + math.min(s.wave, 10) * 4
	model:SetAttribute("Health", hp)
	model:SetAttribute("MaxHealth", hp)
	model:SetAttribute("RoomId", room.id)
	model.PrimaryPart.Anchored = true
	model:PivotTo(CFrame.lookAt(pos, pos + look))
	model.Parent = workspace.Enemies
	table.insert(s.list, {
		model = model, pos = pos, look = look, bank = 0, speed = E.Speed,
		gunT = 0, missT = rng:NextNumber(4, E.MissileCooldown), phase = rng:NextNumber(0, 6.28),
	})
end

local function startWave(room, s, n)
	s.wave += 1
	s.pending = Config.Enemy.WaveBase + s.wave + math.max(0, n - 1)        -- one more for every extra jet in the air
	s.spawnTimer = 0
	for _, p in Rooms.players(room) do Combat.toast(p, "HULLÁM " .. s.wave .. " – " .. s.pending .. " ellenség jön", "warn") end
end

function Enemies.init(r)
	remotes = r
	Rooms.hooks.closed = function(room) clearRoom(room.id) end
	Combat.EnemyKilled:Connect(function(model, attacker)
		local id = model:GetAttribute("RoomId")
		local room = id and Rooms.byId(id)
		local s = id and state[id]
		if not s then return end
		for i = #s.list, 1, -1 do
			if s.list[i].model == model then table.remove(s.list, i) end
		end
		if room and #s.list == 0 and s.pending == 0 then
			s.waveTimer = Config.Enemy.WaveDelay
			local bonus = Config.Coins.WaveBonus * math.min(s.wave, 10)
			for _, f in flyers(room) do
				Data.addCoins(f.player, bonus)
				Combat.toast(f.player, "HULLÁM " .. s.wave .. " KÉSZ! +" .. bonus .. " érme", "good")
			end
		end
	end)
end

local function nearestTarget(room, pos: Vector3)
	local best, bestD = nil, math.huge
	for _, f in flyers(room) do
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

local function stepRoom(room, dt: number)
	local E, W = Config.Enemy, Config.World
	local s = stateOf(room)
	local fliers = flyers(room)
	if #fliers == 0 then
		-- nobody is flying: the wave stops, the leftovers go away after a while
		s.idle += dt
		if s.idle > 10 and (#s.list > 0 or s.pending > 0) then
			for _, e in s.list do e.model:Destroy() end
			s.list = {}
			s.pending = 0
			s.wave = math.max(0, s.wave - 1)
			s.waveTimer = 3
		end
		return
	end
	s.idle = 0

	-- waves
	if #s.list == 0 and s.pending == 0 then
		s.waveTimer -= dt
		if s.waveTimer <= 0 then startWave(room, s, #fliers) end
	end
	if s.pending > 0 then
		s.spawnTimer -= dt
		if s.spawnTimer <= 0 and #s.list < E.MaxActive then
			spawnOne(room, s)
			s.pending -= 1
			s.spawnTimer = 2.5
		end
	end

	for i = #s.list, 1, -1 do
		local e = s.list[i]
		if not e.model.Parent then
			table.remove(s.list, i)
		else
			local target, dist = nearestTarget(room, e.pos)
			local wish = e.look
			if target then
				local tpos = target:GetPivot().Position
				local tvel = target.PrimaryPart and target.PrimaryPart.AssemblyLinearVelocity or Vector3.zero
				local lead = tpos + tvel * math.clamp(dist / 900, 0, 1.2)
				wish = (lead - e.pos)
				if wish.Magnitude < 1 then wish = e.look else wish = wish.Unit end
				-- swing out a little when very close instead of a head-on pass
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
					local from = e.pos + e.look * 12
					local to = target:GetPivot().Position
					Combat.tracer(room.id, from, from + (to - from).Unit * math.min(dist, E.GunRange), Color3.fromRGB(255, 90, 70), nil)
					if rng:NextNumber() < 0.45 then Combat.damage(target, E.GunDamage, nil, "ellenséges ágyú") end
				end
				e.missT -= dt
				if e.missT <= 0 and dist < E.MissileRange and dist > 700 and aim < 0.45 then
					e.missT = E.MissileCooldown * rng:NextNumber(0.8, 1.3)
					Combat.launchMissile(nil, CFrame.lookAt(e.pos + e.look * 10, e.pos + e.look * 20), target, Config.Missile.Damage * 0.8, room.id)
				end
			end
		end
	end
end

function Enemies.step(dt: number)
	-- only co-op rooms with somebody in the air have waves
	for id, s in state do
		if not Rooms.byId(id) then clearRoom(id) end
	end
	for _, p in Players:GetPlayers() do
		local room = Rooms.get(p)
		if room and room.mode == "coop" and not room._stepped then
			room._stepped = true
			stepRoom(room, dt)
		end
	end
	for _, p in Players:GetPlayers() do
		local room = Rooms.get(p)
		if room then room._stepped = nil end
	end
end

return Enemies
