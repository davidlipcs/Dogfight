--!nonstrict
-- From the devices to the jet: the port of applyInput / flyStick of web/js/game.js.  Outside the mouse moves the aim circle and the
-- jet points its nose there; in the cockpit the mouse is the control stick itself (push = nose down, pull = nose up, sideways =
-- roll).  Keys: W/S pitch, A/D roll, Q/E rudder, Shift/Z throttle, B air brake, X flares, left mouse = gun.
-- input: { dx, dy (mouse travel this frame, px), held(name) -> bool, mouse = { [0]=left, [1]=middle, [2]=right }, locked (bool) }
-- Common subset of Lua 5.4 and Luau.
local Cam = require(script.Parent.Camera)
local M = require(script.Parent.Parent.sim.SimMath)
local clamp = M.clamp

local K = {}

local function axis(held, pos, neg)
	local p, n = held(pos), held(neg)
	if p and not n then return 1 end
	if n and not p then return -1 end
	return nil
end

-- Mouse joystick for the cockpit.  The stick stays exactly where you put it - nothing pulls it back to the middle, so a slow turn
-- or a long hard break can be held as long as you want.  A small dead zone makes neutral easy to find.
local function flyStick(match, cam, dx, dy)
	local s = match.stick
	local inv = cam.invertY and -1 or 1
	local k = Cam.SENS_BASE * cam.stickSens * Cam.STICK_GAIN
	s.x = clamp(s.x + dx * k, -1, 1)
	s.y = clamp(s.y + dy * k * inv, -1, 1)
end

-- returns nothing; sets the controls of the match's player
function K.apply(match, cam, input, dt)
	local p = match.player
	local held = input.held
	local joystick = cam.cockpit and not cam.freeLook
	if joystick then flyStick(match, cam, input.dx, input.dy)
	else cam:mouseDelta(input.dx, input.dy) end
	if input.pad then                          -- right stick: the aim circle (or the head, with the left stick pressed in)
		cam:setFreeLook(input.pad.l3 == true)
		cam:rotate(-input.pad.rx * 110 * dt, -input.pad.ry * 80 * dt * (cam.invertY and -1 or 1))
	end
	local pitch, roll, yaw = axis(held, "s", "w"), axis(held, "d", "a"), axis(held, "e", "q")      -- S = nose up (pull), W = nose down (push)
	if joystick then
		local dz = function(v) return math.abs(v) < Cam.STICK_DEADZONE and 0 or (v - M.sign(v) * Cam.STICK_DEADZONE) / (1 - Cam.STICK_DEADZONE) end
		if pitch == nil then pitch = dz(match.stick.y) end
		if roll == nil then roll = dz(match.stick.x) end
	else
		match.stick.x, match.stick.y = 0, 0
	end
	if input.pad then                          -- a controller: the left stick flies the jet directly (stick back = nose up)
		if input.pad.lx ~= 0 or input.pad.ly ~= 0 then
			if axis(held, "s", "w") == nil then pitch = input.pad.ly end
			if axis(held, "d", "a") == nil then roll = input.pad.lx end
		end
	end
	local manual = pitch ~= nil or roll ~= nil
	-- flying with the keys: the mouse aim point rides on the nose, so letting go does not yank the jet back
	if manual then cam.aim = M.qlook(p.forward) end
	match:applyInput(dt, {
		aim = cam:aimDirection(), pitch = pitch, roll = roll, yaw = yaw,
		throttleUp = held("shift") or (input.pad and input.pad.rt), throttleDown = held("z") or held("control") or (input.pad and input.pad.lt),
		brake = held("b") or (input.pad and input.pad.down), trigger = input.mouse[0] or (input.pad and input.pad.rb) or false,
		flare = held("x") or (input.pad and input.pad.lb) or false,
	})
	if not (input.pad and input.pad.l3) then cam:setFreeLook(held("c") or input.mouse[2] or false) end
	cam.stick = joystick and match.stick or nil
end

return K
