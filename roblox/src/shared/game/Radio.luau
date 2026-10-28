--!nonstrict
-- The radio: the port of web/js/radio.js (the calls and what the other side answers).  You talk to the tower, your wingman and
-- the AWACS with the real brevity words ("FOX TWO", "SPLASH", "BINGO" ...): type them, or pick one from the numbered list.  The
-- other side answers in the radio log (subtitles; Roblox cannot synthesise speech).  There is no speech recognition either.
-- The unidentified-intruder calls (interrogate, follow me ...) belong to the air-policing missions of the browser career and are left out.
-- Written in the common subset of Lua 5.4 and Luau, so it is tested outside of Roblox (roblox/tests).
local M = require(script.Parent.Parent.sim.SimMath)
local V, sub, len, norm, dot, DEG = M.V, M.sub, M.len, M.norm, M.dot, M.DEG
local atan2 = M.atan2

local Radio = {}
Radio.__index = Radio

-- id, what to say, other ways to say it, who to, the lesson that teaches it, what it means (Hungarian)
local CALLS = {
	-- tower
	{ id = "radio_check", say = "RADIO CHECK", alt = { "HOW DO YOU READ", "COMM CHECK" }, to = "tower", lesson = "radio1", hu = "rádiópróba – hallanak-e" },
	{ id = "request_taxi", say = "REQUEST TAXI", alt = { "READY TO TAXI", "TAXI" }, to = "tower", lesson = "radio1", hu = "gurulási engedélyt kérsz" },
	{ id = "ready_takeoff", say = "READY FOR TAKEOFF", alt = { "REQUEST TAKEOFF", "READY FOR DEPARTURE", "HOLDING SHORT", "READY" }, to = "tower", lesson = "radio1", hu = "felszállásra kész vagy, engedélyt kérsz" },
	{ id = "airborne", say = "AIRBORNE", alt = { "DEPARTING", "WHEELS UP" }, to = "tower", lesson = "radio1", hu = "a levegőben vagy" },
	{ id = "inbound", say = "INBOUND FOR LANDING", alt = { "REQUEST LANDING", "INBOUND", "RETURNING FOR LANDING", "FULL STOP" }, to = "tower", lesson = "radio2", hu = "leszállni jössz" },
	{ id = "gear_down", say = "GEAR DOWN", alt = { "THREE GREEN", "GEAR DOWN AND LOCKED" }, to = "tower", lesson = "radio2", hu = "a futómű kint és bezárva" },
	{ id = "clear_runway", say = "CLEAR OF RUNWAY", alt = { "RUNWAY VACATED", "CLEAR OF THE RUNWAY" }, to = "tower", lesson = "radio2", hu = "leszálltál, elhagytad a kifutót" },
	{ id = "emergency", say = "MAYDAY", alt = { "EMERGENCY", "PAN PAN" }, to = "tower", lesson = "radio2", hu = "vészhelyzet" },
	-- flight (between the lead and the wingman)
	{ id = "ack", say = "COPY", alt = { "TWO", "ROGER", "WILCO", "ACKNOWLEDGED", "AFFIRMATIVE" }, to = "flight", lesson = "radio3", hu = "vettem (a 2-es így nyugtáz: „TWO”)" },
	{ id = "visual", say = "VISUAL", alt = { "VISUAL ON LEAD", "I HAVE YOU" }, to = "flight", lesson = "radio3", hu = "látom a saját gépet (vezért / kísérőt)" },
	{ id = "blind", say = "BLIND", alt = { "NO VISUAL", "LOST YOU" }, to = "flight", lesson = "radio3", hu = "nem látom a saját gépet" },
	{ id = "tally", say = "TALLY", alt = { "TALLY HO", "TALLY BANDIT" }, to = "flight", lesson = "radio4", hu = "látom az ellenséget" },
	{ id = "no_joy", say = "NO JOY", alt = { "NO TALLY" }, to = "flight", lesson = "radio4", hu = "nem látom az ellenséget" },
	{ id = "fox2", say = "FOX TWO", alt = { "FOX 2" }, to = "flight", lesson = "radio4", hu = "hőkövető rakétát indítottam" },
	{ id = "fox3", say = "FOX THREE", alt = { "FOX 3" }, to = "flight", lesson = "radio4", hu = "aktív radaros rakétát indítottam" },
	{ id = "guns", say = "GUNS GUNS", alt = { "GUNS" }, to = "flight", lesson = "radio4", hu = "gépágyúval lövök" },
	{ id = "splash", say = "SPLASH ONE", alt = { "SPLASH", "KILL", "BANDIT DOWN" }, to = "flight", lesson = "radio4", hu = "lelőttem" },
	{ id = "defending", say = "DEFENDING", alt = { "DEFENSIVE", "MISSILE INBOUND", "SPIKED", "NOTCHING" }, to = "flight", lesson = "radio4", hu = "rakéta jön rám, védekezem" },
	{ id = "bingo", say = "BINGO", alt = { "BINGO FUEL", "JOKER" }, to = "flight", lesson = "radio5", hu = "kevés az üzemanyag – haza kell indulni" },
	{ id = "winchester", say = "WINCHESTER", alt = { "OUT OF MISSILES", "NO WEAPONS" }, to = "flight", lesson = "radio5", hu = "elfogyott a fegyver" },
	{ id = "rtb", say = "RTB", alt = { "RETURNING TO BASE", "RETURN TO BASE", "HEADING HOME" }, to = "flight", lesson = "radio5", hu = "visszatérek a bázisra" },
	-- orders to the wingman
	{ id = "engage", say = "ENGAGE", alt = { "CLEARED HOT", "ATTACK", "TWO ENGAGE", "ENGAGE BANDIT", "CLEARED TO ENGAGE" }, to = "wing", lesson = "radio6", hu = "parancs a kísérőnek: támadj" },
	{ id = "cover", say = "COVER ME", alt = { "COVER", "CHECK SIX", "CHECK MY SIX" }, to = "wing", lesson = "radio6", hu = "parancs: védd a hátamat" },
	{ id = "rejoin", say = "REJOIN", alt = { "FORM UP", "JOIN UP", "RETURN TO FORMATION" }, to = "wing", lesson = "radio6", hu = "parancs: gyere vissza alakzatba" },
	{ id = "break", say = "BREAK LEFT", alt = { "BREAK RIGHT", "BREAK" }, to = "wing", lesson = "radio6", hu = "figyelmeztetés: rakéta / ellenség – kitörés" },
	-- AWACS (the airborne radar: who is where)
	{ id = "picture", say = "PICTURE", alt = { "REQUEST PICTURE", "BOGEY DOPE", "DECLARE", "BRAA" }, to = "awacs", lesson = "radio5", hu = "hol vannak az ellenséges gépek? (irány, táv, magasság)" },
	{ id = "checking_in", say = "CHECKING IN", alt = { "ON STATION", "CHECK IN" }, to = "awacs", lesson = "radio5", hu = "bejelentkezel az AWACS-hoz" },
}
Radio.CALLS = CALLS

local NUM = { [0] = "ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE" }
local FIX = { FOCKS = "FOX", FOCUS = "FOX", FOXTROT = "FOX", TOO = "TWO", TO = "TWO", FOR = "FOUR", TALLEY = "TALLY", TELLY = "TALLY", TALLIES = "TALLY",
	SPLASHED = "SPLASH", BINGE = "BINGO", RTV = "RTB", ARE = "R", TEA = "T", BEE = "B", VISUALS = "VISUAL", PICTURES = "PICTURE",
	WINCHESTERS = "WINCHESTER", ENGAGED = "ENGAGE", ENGAGING = "ENGAGE", DEFENSIVE = "DEFENDING", GUN = "GUNS", TAXIING = "TAXI" }

-- "Fox 2!" -> "FOX TWO"
function Radio.normalise(text)
	local t = string.upper(tostring(text))
	t = string.gsub(t, "TAKE[%- ]?OFF", "TAKEOFF")
	t = string.gsub(t, "[^A-Z0-9 ]", " ")
	t = string.gsub(t, "%d", function(d) return " " .. NUM[tonumber(d)] .. " " end)
	local words = {}
	for w in string.gmatch(t, "%S+") do words[#words + 1] = FIX[w] or w end
	return table.concat(words, " ")
end
local normalise = Radio.normalise

-- does the phrase occur in the words (in order, other words allowed in between: callsigns, "tower", ...)?
local function occurs(words, phrase)
	local p = {}
	for w in string.gmatch(phrase, "%S+") do p[#p + 1] = w end
	local i = 1
	for _, w in ipairs(words) do
		if w == p[i] then
			i = i + 1
			if i > #p then return true end
		end
	end
	return false
end

-- -> the best matching call (the longest phrase wins: "FOX TWO" over "TWO"), or nil
function Radio.recognise(text, allowed)
	allowed = allowed or CALLS
	local words = {}
	for w in string.gmatch(normalise(text), "%S+") do words[#words + 1] = w end
	local best, bestLen = nil, 0
	for _, c in ipairs(allowed) do
		local phrases = { c.say }
		for _, a in ipairs(c.alt) do phrases[#phrases + 1] = a end
		for _, ph in ipairs(phrases) do
			local n = normalise(ph)
			if occurs(words, n) and #n > bestLen then best, bestLen = c, #n end
		end
	end
	return best
end

Radio.NAMES = { tower = "TORONY", awacs = "AWACS „MAGIC”", wing = "KÍSÉRŐ", lead = "VEZÉR", instructor = "OKTATÓ", you = "TE" }

local MAX_LOG = 5

-- g: the match (player, wingman, world, terrain, hud)
function Radio.new(g)
	local self = setmetatable({}, Radio)
	self.g = g
	self.log = {}                                       -- { who, text, t } newest last
	self.version = 0                                    -- grows whenever the log changes
	self.listeners = {}
	self.callsign = (g.opts and g.opts.callsign) or "VIPER 1-1"
	self.unlocked = nil                                 -- nil: everything (free play); else a set of lesson ids
	self.cleared = { taxi = false, takeoff = false, land = false }
	self.time, self.pending = 0, {}
	return self
end

function Radio:reset()
	self.cleared = { taxi = false, takeoff = false, land = false }
end

function Radio:onCall(fn)
	table.insert(self.listeners, fn)
	return function()
		for i, f in ipairs(self.listeners) do
			if f == fn then table.remove(self.listeners, i) break end
		end
	end
end

-- the calls that make sense right now
function Radio:available()
	local g, p = self.g, self.g.player
	local out = {}
	for _, c in ipairs(CALLS) do
		local ok = true
		if self.unlocked and not self.unlocked[c.lesson] then ok = false end
		if c.to == "wing" then ok = ok and g.wingman ~= nil and g.wingman.alive end
		if c.to == "awacs" then ok = ok and (p == nil or not p.onGround) end
		if ok then out[#out + 1] = c end
	end
	return out
end

-- a line in the radio log; delay: seconds until it appears
function Radio:say(who, text, delay)
	if delay and delay > 0 then
		self.pending[#self.pending + 1] = { t = self.time + delay, who = who, text = text }
		return
	end
	self.log[#self.log + 1] = { who = who, text = text, t = self.time }
	while #self.log > MAX_LOG do table.remove(self.log, 1) end
	self.version = self.version + 1
end

function Radio:update(dt)
	self.time = self.time + dt
	local i = 1
	while i <= #self.pending do
		local l = self.pending[i]
		if l.t <= self.time then
			table.remove(self.pending, i)
			self:say(l.who, l.text)
		else
			i = i + 1
		end
	end
end

local PREFIX = { tower = "TOWER, ", awacs = "MAGIC, ", wing = "TWO, ", flight = "" }

-- text: what the player typed / picked.  -> true if understood
function Radio:transmit(text, how)
	if not text or string.match(text, "^%s*$") then return false end
	local call = Radio.recognise(text, self:available())
	local hud = self.g.hud
	if not call then
		local locked = self.unlocked and Radio.recognise(text, CALLS)
		self:say("you", string.upper(text))
		hud:message(locked and ("Ezt még nem tanultad: " .. locked.say .. " (" .. locked.hu .. ")") or "Ezt nem értik a rádión – nézd meg a listát (I)", "warn", 3, "mic")
		return false
	end
	self:say("you", (PREFIX[call.to] or "") .. self.callsign .. ", " .. call.say)
	self:respond(call)
	for _, fn in ipairs(self.listeners) do fn(call, how) end
	return true
end

local function rdelay() return 0.9 + math.random() * 0.7 end

function Radio:homeBearing()
	local p, f = self.g.player, self.g.terrain.airfield
	if not p then return "000" end
	return string.format("%03d", math.floor(((atan2(f.x - p.pos.x, f.y - p.pos.y) / DEG) + 360) % 360 + 0.5) % 360)
end

-- BRAA: bearing, range (nautical miles), altitude (angels = thousands of feet) and aspect of the nearest group
function Radio:picture(short)
	local g, p, cs = self.g, self.g.player, self.callsign
	if not p then return cs .. ", Magic, picture clean." end
	local foes = {}
	for _, a in ipairs(g.world.aircraft) do
		if a.alive and a.team ~= p.team then foes[#foes + 1] = a end
	end
	if #foes == 0 then return cs .. ", Magic, picture clean." end
	local nearest = foes[1]
	for _, a in ipairs(foes) do
		if len(sub(a.pos, p.pos)) < len(sub(nearest.pos, p.pos)) then nearest = a end
	end
	local group = 0
	for _, a in ipairs(foes) do
		if len(sub(a.pos, nearest.pos)) < 8000 then group = group + 1 end
	end
	local rel = sub(nearest.pos, p.pos)
	local brg = math.floor(((atan2(rel.x, rel.y) / DEG) + 360) % 360 + 0.5) % 360
	local nm = math.max(1, math.floor(len(rel) / 1852 + 0.5))
	local angels = math.max(1, math.floor(nearest.pos.z * 3.281 / 1000 + 0.5))
	local asp = dot(norm(nearest.vel), norm(sub(p.pos, nearest.pos)))
	local aspect = asp > 0.7 and "hot" or (asp < -0.5 and "cold" or "flanking")
	local count = ""
	if group > 1 then count = (group == 2 and "two contacts" or (group .. " contacts")) .. ", " end
	local more = ""
	if #foes > group and not short then more = " " .. (#foes - group) .. " more further out." end
	return string.format("%s, Magic, %s BRAA %03d, %d miles, angels %d, %s, %shostile.%s", cs, #foes > group and "lead group" or "single group", brg, nm, angels, aspect, count, more)
end

-- what the other side answers
function Radio:respond(call)
	local g, p, cs = self.g, self.g.player, self.callsign
	local rwy = "36"
	local function R(who, text) self:say(who, text, rdelay()) end
	local id = call.id
	if id == "radio_check" then R("tower", cs .. ", Tower, loud and clear.")
	elseif id == "request_taxi" then
		self.cleared.taxi = true
		R("tower", cs .. ", taxi to runway " .. rwy .. ", hold short.")
	elseif id == "ready_takeoff" then
		-- in training the order matters: taxi clearance first
		if self.unlocked and not self.cleared.taxi and p and p.onGround then R("tower", cs .. ", request taxi first.")
		else
			self.cleared.takeoff = true
			R("tower", cs .. ", wind calm, runway " .. rwy .. ", cleared for takeoff.")
		end
	elseif id == "airborne" then R("tower", cs .. ", radar contact, climb and maintain angels one five. Contact Magic.")
	elseif id == "inbound" then R("tower", cs .. ", runway " .. rwy .. ", report gear down.")
	elseif id == "gear_down" then
		if p and p.fm.gearPos > 0.9 then
			self.cleared.land = true
			R("tower", cs .. ", check gear down, wind calm, runway " .. rwy .. ", cleared to land.")
		else R("tower", cs .. ", negative, your gear is not down! Go around.") end
	elseif id == "clear_runway" then R("tower", cs .. ", taxi to parking. Welcome home.")
	elseif id == "emergency" then R("tower", cs .. ", roger your mayday, runway " .. rwy .. " is yours, crash crews standing by.")
	elseif id == "picture" then R("awacs", self:picture(false))
	elseif id == "checking_in" then R("awacs", cs .. ", Magic, radar contact. " .. self:picture(true))
	elseif id == "engage" or id == "cover" or id == "rejoin" or id == "break" then
		local w = g.wingman
		if not w or not w.alive then R("awacs", cs .. ", your wingman is not on frequency.")
		else
			if w.pilot and w.pilot.order ~= nil then w.pilot.order = id == "break" and "engage" or id end
			R("wing", ({ engage = "Two, engaging.", cover = "Two, in your six.", rejoin = "Two, rejoining.", ["break"] = "Two, breaking, defending!" })[id])
		end
	elseif id == "bingo" then
		if g.wingman and g.wingman.alive then R("wing", "Two, copy bingo, RTB.")
		else R("awacs", cs .. ", Magic, copy, vector " .. self:homeBearing() .. " for home.") end
	elseif id == "rtb" then R("awacs", cs .. ", Magic copies, home plate bearing " .. self:homeBearing() .. ".")
	elseif id == "defending" then
		if g.wingman and g.wingman.alive then
			R("wing", "Two, coming to help!")
			if g.wingman.pilot then g.wingman.pilot.order = "engage" end
		end
	elseif id == "splash" then
		if g.wingman and g.wingman.alive then R("wing", "Two, good kill!")
		else R("awacs", cs .. ", Magic, copy splash.") end
	end
end

-- the game's own events (missile launched, kill ...): an automatic call from the wingman
function Radio:event(kind)
	local w = self.g.wingman
	if not (w and w.alive) then return end
	if kind == "wing_fox" then self:say("wing", "Two, fox three!", 0.3)
	elseif kind == "wing_splash" then self:say("wing", "Two, splash one!", 0.3)
	elseif kind == "wing_defending" then self:say("wing", "Two, defending, missile inbound!", 0.2) end
end

return Radio
