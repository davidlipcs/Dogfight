--!nonstrict
-- The shop: skins for coins, and coin packs / the double-coins pass for Robux.
local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared.Config)
local Catalog = require(Shared.Catalog)
local Data = require(script.Parent.Data)

local Shop = {}

local function ownsPass(player: Player): boolean
	if Config.DoubleCoinsPass == 0 then return false end
	local ok, has = pcall(function() return MarketplaceService:UserOwnsGamePassAsync(player.UserId, Config.DoubleCoinsPass) end)
	return ok and has == true
end

-- called when a player's data is in: the pass is checked once per visit
function Shop.onLoaded(player: Player)
	local p = Data.get(player)
	if p and ownsPass(player) then
		p.double = true
		Data.push(player)
	end
end

function Shop.start(remotes)
	Shop.remotes = remotes
	remotes.GetProfile.OnServerInvoke = function(player)
		return Data.view(player, true)
	end

	remotes.BuyAir.OnServerInvoke = function(player, id)
		local p = Data.get(player)
		local skin = typeof(id) == "string" and Catalog.AirById[id]
		if not p or not skin then return false, "Ismeretlen festés" end
		if p.air[id] then return false, "Ez már a tiéd" end
		if not Data.spend(player, skin.price) then return false, "Nincs elég érméd" end
		p.air[id] = true
		p.airOn = id
		Data.push(player)
		return true, skin.name .. " megvéve!"
	end

	remotes.BuyPilot.OnServerInvoke = function(player, id)
		local p = Data.get(player)
		local skin = typeof(id) == "string" and Catalog.PilotById[id]
		if not p or not skin then return false, "Ismeretlen ruha" end
		if p.pilot[id] then return false, "Ez már a tiéd" end
		if not Data.spend(player, skin.price) then return false, "Nincs elég érméd" end
		p.pilot[id] = true
		p.pilotOn = id
		Data.push(player)
		return true, skin.name .. " megvéve!"
	end

	remotes.EquipJet.OnServerInvoke = function(player, key)
		local p = Data.get(player)
		if not p then return false end
		if key == nil or key == "" then p.jetOn = nil
		else
			local ok = false
			for _, j in Config.JetModels do if j.key == key then ok = true end end
			if not ok then return false end
			p.jetOn = key
		end
		Data.push(player)
		return true
	end

	remotes.EquipAir.OnServerInvoke = function(player, id)
		local p = Data.get(player)
		if not p then return false end
		if id == nil or id == "" then p.airOn = nil
		elseif typeof(id) == "string" and p.air[id] then p.airOn = id
		else return false end
		Data.push(player)
		return true
	end

	remotes.EquipPilot.OnServerInvoke = function(player, id)
		local p = Data.get(player)
		if not p then return false end
		if id == nil or id == "" then p.pilotOn = nil
		elseif typeof(id) == "string" and p.pilot[id] then p.pilotOn = id
		else return false end
		Data.push(player)
		return true
	end

	-- a skin for Robux: the price is the skin's tier (Config.SkinRobux, 500 Ft at most); the pick is remembered until the receipt
	remotes.BuySkinRobux.OnServerInvoke = function(player, kind, id)
		local p = Data.get(player)
		if not p or (kind ~= "air" and kind ~= "pilot") then return false, "Hiba" end
		local skin = typeof(id) == "string" and (kind == "air" and Catalog.AirById[id] or Catalog.PilotById[id])
		if not skin then return false, "Ismeretlen skin" end
		if (kind == "air" and p.air or p.pilot)[id] then return false, "Ez már a tiéd" end
		local product = Config.SkinProducts[skin.rarity]
		if not product or product == 0 then return false, "A Robux-vásárlás még nincs beállítva" end
		p.pending = { kind = kind, id = id, rarity = skin.rarity }
		task.spawn(Data.save, player)
		MarketplaceService:PromptProductPurchase(player, product)
		return true, tostring(Config.SkinRobux[skin.rarity]) .. " Robux"
	end

	-- Robux: the client asks, the server opens the purchase window (only for an id that is in the Config)
	remotes.BuyProduct.OnServerInvoke = function(player, index)
		local prod = typeof(index) == "number" and Config.Products[index]
		if not prod or prod.id == 0 then return false end
		MarketplaceService:PromptProductPurchase(player, prod.id)
		return true
	end
	remotes.BuyPass.OnServerInvoke = function(player)
		if Config.DoubleCoinsPass == 0 then return false end
		MarketplaceService:PromptGamePassPurchase(player, Config.DoubleCoinsPass)
		return true
	end
	MarketplaceService.PromptGamePassPurchaseFinished:Connect(function(player, passId, purchased)
		if purchased and passId == Config.DoubleCoinsPass then
			local p = Data.get(player)
			if p then p.double = true; Data.push(player) end
		end
	end)

	-- the receipt of a developer product: the coins are given once per purchase
	MarketplaceService.ProcessReceipt = function(info)
		local player = Players:GetPlayerByUserId(info.PlayerId)
		if not player then return Enum.ProductPurchaseDecision.NotProcessedYet end
		local p = Data.get(player)
		if not p then return Enum.ProductPurchaseDecision.NotProcessedYet end
		local rid = tostring(info.PurchaseId)
		if p.receipts[rid] then return Enum.ProductPurchaseDecision.PurchaseGranted end
		-- a skin: the four rarity products
		for rarity, pid in Config.SkinProducts do
			if pid ~= 0 and pid == info.ProductId then
				p.receipts[rid] = true
				local pend = p.pending
				if pend and pend.rarity == rarity then
					(pend.kind == "air" and p.air or p.pilot)[pend.id] = true
					if pend.kind == "air" then p.airOn = pend.id else p.pilotOn = pend.id end
					if Shop.remotes then Shop.remotes.Toast:FireClient(player, "Megvetted: " .. pend.id, "good") end
				else
					p.coins += Config.TierCoins[rarity]       -- the pick was lost (a restart): the same value in coins
				end
				p.pending = nil
				Data.push(player)
				task.spawn(Data.save, player)
				return Enum.ProductPurchaseDecision.PurchaseGranted
			end
		end
		for _, prod in Config.Products do
			if prod.id == info.ProductId then
				p.receipts[rid] = true
				p.coins += prod.coins          -- bought coins are not doubled
				Data.push(player)
				task.spawn(Data.save, player)
				return Enum.ProductPurchaseDecision.PurchaseGranted
			end
		end
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end
end

return Shop
