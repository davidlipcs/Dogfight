--!nonstrict
-- Aircraft, missile, radar and gun data (SpecData.luau, generated from web/js/specs.js) and the three helpers of specs.js.
local D = require(script.Parent.SpecData)

local S = {}
for k, v in pairs(D) do S[k] = v end

local function named(set, n)
	if not n then return set end
	local function with(base, name)
		local m = {}
		for k, v in pairs(base) do m[k] = v end
		m.name = name
		return m
	end
	return { ["AIM-9M"] = with(set["AIM-9M"], n[1]), ["AIM-120A"] = with(set["AIM-120A"], n[2]) }
end

-- the missile set a jet carries (the player's are better than the enemies')
function S.missilesFor(spec, enemy)
	local nation = spec.nation
	if not nation and spec.id and string.sub(spec.id, 1, 2) == "su" then nation = "ru" end
	local n = nation and D.NAMES[nation] or nil
	return named(enemy and D.BANDIT_MISSILES or D.PLAYER_MISSILES, n)
end

-- station layout for n9 AIM-9s and n120 AIM-120s: every weapon takes the stations only it can use first, then the shared ones
-- in its order of preference.  Returns layout ({ station = weapon }) and left (what did not fit)
function S.buildLoadout(spec, n9, n120)
	local layout, want = {}, { ["AIM-9M"] = n9, ["AIM-120A"] = n120 }
	for _, pass in ipairs({ "own", "shared" }) do
		for _, key in ipairs({ "AIM-120A", "AIM-9M" }) do
			for _, st in ipairs(spec.prefer[key]) do
				if want[key] <= 0 then break end
				local ok = spec.pylons[st] or {}
				local has = false
				for _, k in ipairs(ok) do if k == key then has = true end end
				if not (layout[st] or not has or ((pass == "own") ~= (#ok == 1))) then
					layout[st] = key
					want[key] = want[key] - 1
				end
			end
		end
	end
	return { layout = layout, left = want }
end

function S.loadoutLimits(spec)
	local function n(k)
		local c = 0
		for _, p in pairs(spec.pylons) do
			for _, kk in ipairs(p) do if kk == k then c = c + 1 end end
		end
		return c
	end
	local total = 0
	for _ in pairs(spec.pylons) do total = total + 1 end
	return { ["AIM-9M"] = n("AIM-9M"), ["AIM-120A"] = n("AIM-120A"), total = total }
end

return S
