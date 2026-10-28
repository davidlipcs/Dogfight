--!nonstrict
-- The "Napi" tab of the lobby: the daily reward, the three daily missions and the top list (server/Daily.luau).
local Ui = require(script.Parent.Ui)

local DailyUi = {}

function DailyUi.build(parent, remotes)
	local list = Ui.make("ScrollingFrame", {
		BackgroundTransparency = 1, BorderSizePixel = 0, ScrollBarThickness = 8, CanvasSize = UDim2.new(0, 0, 0, 0), AutomaticCanvasSize = Enum.AutomaticSize.Y,
		Size = UDim2.new(1, 0, 1, 0), Visible = false, Parent = parent,
	}, { Ui.make("UIListLayout", { Padding = UDim.new(0, 10), SortOrder = Enum.SortOrder.LayoutOrder }) })
	local msg = Ui.label(list, "", { Size = UDim2.new(1, -10, 0, 22), TextSize = 15, LayoutOrder = 0 })
	local function section(title, order)
		local f = Ui.make("Frame", { BackgroundColor3 = Color3.fromRGB(24, 34, 40), BorderSizePixel = 0, Size = UDim2.new(1, -12, 0, 10), AutomaticSize = Enum.AutomaticSize.Y, LayoutOrder = order, Parent = list }, {
			Ui.corner(8), Ui.padding(10), Ui.make("UIListLayout", { Padding = UDim.new(0, 6), SortOrder = Enum.SortOrder.LayoutOrder }),
		})
		Ui.label(f, title, { Size = UDim2.new(1, 0, 0, 22), TextSize = 18, Font = Enum.Font.GothamBold, TextColor3 = Ui.Amber, LayoutOrder = 0 })
		return f
	end
	local daily, missions, board = section("Napi jutalom", 1), section("Napi feladatok", 2), section("A legjobb pilóták", 3)
	local function clear(f)
		for _, c in f:GetChildren() do
			if c:IsA("GuiObject") and c.LayoutOrder ~= 0 then c:Destroy() end
		end
	end
	local function say(text, good)
		msg.Text = text or ""
		msg.TextColor3 = good and Ui.Green or Ui.Amber
	end
	local function refresh()
		local ok, data = pcall(function() return remotes.GetMissions:InvokeServer() end)
		if not ok or not data then return end
		clear(daily)
		local d = data.daily
		local row = Ui.make("Frame", { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, 40), LayoutOrder = 1, Parent = daily }, {
			Ui.make("UIListLayout", { FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 6) }),
		})
		for i, n in d.rewards do
			local on = i <= d.streak
			Ui.label(row, tostring(n), { Size = UDim2.new(0, 54, 0, 36), TextSize = 14, TextXAlignment = Enum.TextXAlignment.Center, Font = Enum.Font.GothamBold,
				BackgroundTransparency = 0, BackgroundColor3 = on and Color3.fromRGB(60, 110, 70) or Color3.fromRGB(40, 54, 60), TextColor3 = on and Ui.Green or Color3.fromRGB(200, 215, 210) })
		end
		Ui.button(daily, d.available and "Átveszem a mai jutalmat" or "Ma már átvetted", { Size = UDim2.new(0, 260, 0, 36), TextSize = 15, LayoutOrder = 2,
			BackgroundColor3 = d.available and Ui.Green or Color3.fromRGB(70, 80, 84) }, function()
			local ok2, good, text = pcall(function() return remotes.ClaimDaily:InvokeServer() end)
			say(ok2 and text or "Hiba", ok2 and good)
			refresh()
		end)
		clear(missions)
		for i, m in data.missions do
			local f = Ui.make("Frame", { BackgroundTransparency = 1, Size = UDim2.new(1, 0, 0, 34), LayoutOrder = i, Parent = missions })
			Ui.label(f, m.text, { Size = UDim2.new(1, -250, 0, 34), TextSize = 14, TextWrapped = true })
			Ui.label(f, m.progress .. " / " .. m.target, { Position = UDim2.new(1, -240, 0, 0), Size = UDim2.new(0, 70, 0, 34), TextSize = 14, TextColor3 = m.done and Ui.Green or Color3.fromRGB(200, 215, 210) })
			Ui.button(f, m.claimed and "Átvéve" or ("+" .. m.reward .. " érme"), { Position = UDim2.new(1, -160, 0, 3), Size = UDim2.new(0, 150, 0, 28), TextSize = 13,
				BackgroundColor3 = (m.done and not m.claimed) and Ui.Amber or Color3.fromRGB(70, 80, 84) }, function()
				if m.claimed or not m.done then return end
				local ok2, good, text = pcall(function() return remotes.ClaimMission:InvokeServer(m.id) end)
				say(ok2 and text or "Hiba", ok2 and good)
				refresh()
			end)
		end
		local ok3, top = pcall(function() return remotes.GetLeaderboard:InvokeServer() end)
		clear(board)
		if ok3 and top and #top > 0 then
			for i, e in top do
				Ui.label(board, string.format("%d.  %s  –  %d pont", e.rank, e.name, e.score), { Size = UDim2.new(1, 0, 0, 20), TextSize = 14, LayoutOrder = i })
			end
		else
			Ui.label(board, "Még nincs eredmény.", { Size = UDim2.new(1, 0, 0, 20), TextSize = 14, LayoutOrder = 1 })
		end
	end
	return { frame = list, refresh = refresh }
end

return DailyUi
