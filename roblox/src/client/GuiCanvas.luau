--!nonstrict
-- An immediate-mode 2D canvas made of pooled GUI objects, for the HUD (shared/game/Hud.luau draws on it exactly like the browser game
-- draws on its <canvas>).  Call begin() before a frame's drawing and finish() after it: the objects that were not used are hidden.
-- Colours are { r, g, b, a } (0..255, a 0..1).
local GuiCanvas = {}
GuiCanvas.__index = GuiCanvas

local MONO = Font.fromEnum(Enum.Font.RobotoMono)
local TITLE = Font.fromEnum(Enum.Font.Oswald)

local function newPool(make)
	return { list = {}, n = 0, make = make }
end
local function take(pool)
	pool.n += 1
	local o = pool.list[pool.n]
	if not o then
		o = pool.make()
		pool.list[pool.n] = o
	end
	return o
end
local function hideRest(pool)
	for i = pool.n + 1, #pool.list do
		local o = pool.list[i]
		if o.Visible then o.Visible = false end
	end
end

function GuiCanvas.new(player: Player)
	local self = setmetatable({}, GuiCanvas)
	local gui = Instance.new("ScreenGui")
	gui.Name = "HudCanvas"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.DisplayOrder = 5
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.Enabled = false
	gui.Parent = player:WaitForChild("PlayerGui")
	self.gui = gui
	local root = Instance.new("Frame")
	root.Name = "Root"
	root.BackgroundTransparency = 1
	root.Size = UDim2.fromScale(1, 1)
	root.Active = false
	root.Parent = gui
	self.root = root
	self.lw = 1.6

	local function frame(z)
		local f = Instance.new("Frame")
		f.BorderSizePixel = 0
		f.AnchorPoint = Vector2.new(0.5, 0.5)
		f.ZIndex = z
		f.Active = false
		f.Visible = false
		f.Parent = root
		return f
	end
	self.lines = newPool(function() return frame(3) end)
	self.fills = newPool(function() return frame(1) end)
	self.dots = newPool(function()
		local f = frame(1)
		local c = Instance.new("UICorner")
		c.CornerRadius = UDim.new(0.5, 0)
		c.Parent = f
		return f
	end)
	self.rects = newPool(function()
		local f = frame(2)
		f.BackgroundTransparency = 1
		local s = Instance.new("UIStroke")
		s.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
		s.LineJoinMode = Enum.LineJoinMode.Miter
		s.Parent = f
		return f
	end)
	self.rings = newPool(function()
		local f = frame(2)
		f.BackgroundTransparency = 1
		local c = Instance.new("UICorner")
		c.CornerRadius = UDim.new(0.5, 0)
		c.Parent = f
		local s = Instance.new("UIStroke")
		s.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
		s.Parent = f
		return f
	end)
	self.texts = newPool(function()
		local t = Instance.new("TextLabel")
		t.BackgroundTransparency = 1
		t.AutomaticSize = Enum.AutomaticSize.XY
		t.Size = UDim2.fromOffset(0, 0)
		t.TextStrokeTransparency = 0.45
		t.TextStrokeColor3 = Color3.new(0, 0, 0)
		t.FontFace = MONO
		t.ZIndex = 4
		t.Active = false
		t.Visible = false
		t.Parent = root
		return t
	end)
	self.edges = {}
	for i = 1, 8 do
		local f = frame(0)
		f.AnchorPoint = Vector2.new(0, 0)
		local g = Instance.new("UIGradient")
		g.Parent = f
		self.edges[i] = f
	end
	self.edgeN = 0
	self.fullFill = frame(0)
	self.fullFill.AnchorPoint = Vector2.new(0, 0)
	self.fullFill.Size = UDim2.fromScale(1, 1)
	self.fullFill.Position = UDim2.fromScale(0, 0)
	return self
end

function GuiCanvas:setEnabled(on) self.gui.Enabled = on end
function GuiCanvas:size()
	local s = self.root.AbsoluteSize
	return s.X, s.Y
end

function GuiCanvas:begin()
	for _, p in { self.lines, self.fills, self.dots, self.rects, self.rings, self.texts } do p.n = 0 end
	self.edgeN = 0
	self.fullFillOn = false
end
function GuiCanvas:finish()
	for _, p in { self.lines, self.fills, self.dots, self.rects, self.rings, self.texts } do hideRest(p) end
	for i = self.edgeN + 1, 8 do self.edges[i].Visible = false end
	self.fullFill.Visible = self.fullFillOn
end

local function col(c) return Color3.fromRGB(c[1], c[2], c[3]), 1 - (c[4] or 1) end

function GuiCanvas:lineWidth(w) self.lw = w end

function GuiCanvas:line(x1, y1, x2, y2, c)
	local dx, dy = x2 - x1, y2 - y1
	local len = math.sqrt(dx * dx + dy * dy)
	if len < 0.5 then return end
	local f = take(self.lines)
	local color, tr = col(c)
	f.Visible = true
	f.BackgroundColor3 = color
	f.BackgroundTransparency = tr
	f.Size = UDim2.fromOffset(len + self.lw * 0.5, self.lw)
	f.Position = UDim2.fromOffset((x1 + x2) / 2, (y1 + y2) / 2)
	f.Rotation = math.deg(math.atan2(dy, dx))
end

function GuiCanvas:dashed(x1, y1, x2, y2, c, on, off)
	local dx, dy = x2 - x1, y2 - y1
	local len = math.sqrt(dx * dx + dy * dy)
	if len < 1 then return end
	local ux, uy = dx / len, dy / len
	local step = math.max(on + off, 4)
	local d, n = 0, 0
	while d < len and n < 40 do
		local e = math.min(d + on, len)
		self:line(x1 + ux * d, y1 + uy * d, x1 + ux * e, y1 + uy * e, c)
		d += step
		n += 1
	end
end

function GuiCanvas:arc(x, y, r, c, a0, a1)
	if a0 == nil then
		if r < 0.5 then return end
		local f = take(self.rings)
		local color, tr = col(c)
		f.Visible = true
		f.Size = UDim2.fromOffset(r * 2, r * 2)
		f.Position = UDim2.fromOffset(x, y)
		local s = f:FindFirstChildOfClass("UIStroke")
		s.Color = color
		s.Transparency = tr
		s.Thickness = self.lw
		return
	end
	-- a part of a circle: short segments
	local span = a1 - a0
	local n = math.max(2, math.min(48, math.floor(math.abs(span) / (math.pi / 16)) + 1))
	local px, py = x + math.cos(a0) * r, y + math.sin(a0) * r
	for i = 1, n do
		local a = a0 + span * i / n
		local qx, qy = x + math.cos(a) * r, y + math.sin(a) * r
		self:line(px, py, qx, qy, c)
		px, py = qx, qy
	end
end

function GuiCanvas:strokeRect(x, y, w, h, c)
	local f = take(self.rects)
	local color, tr = col(c)
	f.Visible = true
	f.AnchorPoint = Vector2.new(0, 0)
	f.Size = UDim2.fromOffset(w, h)
	f.Position = UDim2.fromOffset(x, y)
	local s = f:FindFirstChildOfClass("UIStroke")
	s.Color = color
	s.Transparency = tr
	s.Thickness = self.lw
end

function GuiCanvas:fillRect(x, y, w, h, c)
	local f = take(self.fills)
	local color, tr = col(c)
	f.Visible = true
	f.AnchorPoint = Vector2.new(0, 0)
	f.BackgroundColor3 = color
	f.BackgroundTransparency = tr
	f.Size = UDim2.fromOffset(w, h)
	f.Position = UDim2.fromOffset(x, y)
end

function GuiCanvas:fillCircle(x, y, r, c)
	local f = take(self.dots)
	local color, tr = col(c)
	f.Visible = true
	f.BackgroundColor3 = color
	f.BackgroundTransparency = tr
	f.Size = UDim2.fromOffset(r * 2, r * 2)
	f.Position = UDim2.fromOffset(x, y)
end

-- size in pixels of a text (a mono font is 0.6 em per character)
function GuiCanvas:measure(str, size) return #str * size * 0.6 end

function GuiCanvas:text(str, x, y, c, size, align, font)
	if str == "" then return end
	local t = take(self.texts)
	local color, tr = col(c)
	t.Visible = true
	t.Text = str
	t.TextColor3 = color
	t.TextTransparency = tr
	t.TextSize = size
	t.FontFace = font == "title" and TITLE or MONO
	t.AnchorPoint = Vector2.new(align == "center" and 0.5 or align == "right" and 1 or 0, 0.5)
	t.Position = UDim2.fromOffset(x, y)
	t.TextXAlignment = align == "center" and Enum.TextXAlignment.Center or align == "right" and Enum.TextXAlignment.Right or Enum.TextXAlignment.Left
end

-- a darkening / reddening of the screen edges (G-LOC, damage): rgb colour, alpha at the very edge, inner (0..1: where it starts, from the
-- middle), extra (alpha of a flat cover over everything)
function GuiCanvas:vignette(rgb, alpha, inner, extra)
	local color = Color3.fromRGB(rgb[1], rgb[2], rgb[3])
	local depth = math.clamp(1 - inner, 0.1, 0.6)
	local function edge(pos, size, rotation)
		self.edgeN += 1
		local f = self.edges[self.edgeN]
		f.Visible = true
		f.BackgroundColor3 = color
		f.BackgroundTransparency = 0
		f.Position = pos
		f.Size = size
		local g = f:FindFirstChildOfClass("UIGradient")
		g.Rotation = rotation
		g.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1 - math.clamp(alpha, 0, 1)), NumberSequenceKeypoint.new(1, 1) })
	end
	edge(UDim2.fromScale(0, 0), UDim2.fromScale(depth, 1), 0)
	edge(UDim2.fromScale(1 - depth, 0), UDim2.fromScale(depth, 1), 180)
	edge(UDim2.fromScale(0, 0), UDim2.fromScale(1, depth), 90)
	edge(UDim2.fromScale(0, 1 - depth), UDim2.fromScale(1, depth), 270)
	if extra and extra > 0 then
		self.fullFillOn = true
		self.fullFill.BackgroundColor3 = color
		self.fullFill.BackgroundTransparency = 1 - math.clamp(extra, 0, 1)
	end
end

return GuiCanvas
