-- A mock of the part of the Roblox API that the project's client / server code uses, to run it headless under Lua 5.4 (lupa).  It is not a
-- Roblox: it makes the code run and logs what looks wrong (properties that do not exist, methods that are missing are Lua errors).
local M = { warnings = {}, log = {} }
local function warn_(msg) M.warnings[msg] = (M.warnings[msg] or 0) + 1 end
M.warn = warn_

function __it(x)
	if type(x) ~= "table" then return pairs({}) end
	if #x > 0 or next(x) == nil then return ipairs(x) end
	return pairs(x)
end

-- ----------------------------------------------------------------- value types
local function typed(name, mt)
	mt.__type = name
	return mt
end
function typeof(x)
	local mt = getmetatable(x)
	if mt and mt.__type then return mt.__type end
	return type(x)
end

local V3 = {}
V3.__type = "Vector3"
local function v3(x, y, z) return setmetatable({ X = x or 0, Y = y or 0, Z = z or 0 }, V3) end
V3.__index = function(t, k)
	if k == "Magnitude" then return math.sqrt(t.X * t.X + t.Y * t.Y + t.Z * t.Z) end
	if k == "Unit" then local m = math.sqrt(t.X * t.X + t.Y * t.Y + t.Z * t.Z); if m == 0 then return v3(0, 0, 0) end return v3(t.X / m, t.Y / m, t.Z / m) end
	if k == "Dot" then return function(a, b) return a.X * b.X + a.Y * b.Y + a.Z * b.Z end end
	if k == "Cross" then return function(a, b) return v3(a.Y * b.Z - a.Z * b.Y, a.Z * b.X - a.X * b.Z, a.X * b.Y - a.Y * b.X) end end
	if k == "Lerp" then return function(a, b, s) return v3(a.X + (b.X - a.X) * s, a.Y + (b.Y - a.Y) * s, a.Z + (b.Z - a.Z) * s) end end
	error("Vector3 has no member " .. tostring(k), 2)
end
V3.__add = function(a, b) return v3(a.X + b.X, a.Y + b.Y, a.Z + b.Z) end
V3.__sub = function(a, b) return v3(a.X - b.X, a.Y - b.Y, a.Z - b.Z) end
V3.__mul = function(a, b)
	if type(a) == "number" then return v3(b.X * a, b.Y * a, b.Z * a) end
	if type(b) == "number" then return v3(a.X * b, a.Y * b, a.Z * b) end
	return v3(a.X * b.X, a.Y * b.Y, a.Z * b.Z)
end
V3.__div = function(a, b) if type(b) == "number" then return v3(a.X / b, a.Y / b, a.Z / b) end return v3(a.X / b.X, a.Y / b.Y, a.Z / b.Z) end
V3.__unm = function(a) return v3(-a.X, -a.Y, -a.Z) end
V3.__eq = function(a, b) return a.X == b.X and a.Y == b.Y and a.Z == b.Z end
Vector3 = { new = v3, zero = v3(0, 0, 0), one = v3(1, 1, 1) }

local V2 = {}
V2.__type = "Vector2"
local function v2(x, y) return setmetatable({ X = x or 0, Y = y or 0 }, V2) end
V2.__index = function(t, k)
	if k == "Magnitude" then return math.sqrt(t.X * t.X + t.Y * t.Y) end
	error("Vector2 has no member " .. tostring(k), 2)
end
V2.__add = function(a, b) return v2(a.X + b.X, a.Y + b.Y) end
V2.__sub = function(a, b) return v2(a.X - b.X, a.Y - b.Y) end
V2.__mul = function(a, b) if type(b) == "number" then return v2(a.X * b, a.Y * b) end return v2(a.X * b.X, a.Y * b.Y) end
Vector2 = { new = v2, zero = v2(0, 0) }

local UD = { __type = "UDim" }
UD.__index = UD
UDim = { new = function(s, o) return setmetatable({ Scale = s or 0, Offset = o or 0 }, UD) end }
local U2 = { __type = "UDim2" }
U2.__index = U2
local function u2(xs, xo, ys, yo) return setmetatable({ X = UDim.new(xs, xo), Y = UDim.new(ys, yo) }, U2) end
UDim2 = { new = function(a, b, c, d)
	if type(a) == "table" then return u2(a.Scale, a.Offset, b.Scale, b.Offset) end
	return u2(a or 0, b or 0, c or 0, d or 0)
end, fromOffset = function(x, y) return u2(0, x, 0, y) end, fromScale = function(x, y) return u2(x, 0, y, 0) end }

local C3 = { __type = "Color3" }
C3.__index = C3
local function c3(r, g, b) return setmetatable({ R = r, G = g, B = b }, C3) end
Color3 = { new = c3, fromRGB = function(r, g, b) return c3(r / 255, g / 255, b / 255) end }
local CS = { __type = "ColorSequence" }
ColorSequence = { new = function(a, b) return setmetatable({ a = a, b = b }, CS) end }
NumberRange = { new = function(a, b) return setmetatable({ Min = a, Max = b or a }, { __type = "NumberRange" }) end }
NumberSequenceKeypoint = { new = function(t, v) return { Time = t, Value = v } end }
NumberSequence = { new = function(a, b)
	if type(a) == "table" and getmetatable(a) == nil then return setmetatable({ keys = a }, { __type = "NumberSequence" }) end
	return setmetatable({ keys = { { Time = 0, Value = a }, { Time = 1, Value = b or a } } }, { __type = "NumberSequence" })
end }
TweenInfo = { new = function() return {} end }
Font = { fromEnum = function(e) return { Family = e } end }
Rect = { new = function() return {} end }

-- CFrame: a position and three column vectors
local CF = { __type = "CFrame" }
local function cf(p, r, u, b) return setmetatable({ Position = p, R = r, U = u, B = b }, CF) end
local function ident() return cf(v3(0, 0, 0), v3(1, 0, 0), v3(0, 1, 0), v3(0, 0, 1)) end
local function rotv(c, v) return v3(c.R.X * v.X + c.U.X * v.Y + c.B.X * v.Z, c.R.Y * v.X + c.U.Y * v.Y + c.B.Y * v.Z, c.R.Z * v.X + c.U.Z * v.Y + c.B.Z * v.Z) end
CF.__index = function(t, k)
	if k == "LookVector" then return -t.B end
	if k == "RightVector" then return t.R end
	if k == "UpVector" then return t.U end
	if k == "X" then return t.Position.X end
	if k == "Y" then return t.Position.Y end
	if k == "Z" then return t.Position.Z end
	if k == "Rotation" then return cf(v3(0, 0, 0), t.R, t.U, t.B) end
	if k == "Inverse" then return function(c)
		local r = v3(c.R.X, c.U.X, c.B.X); local u = v3(c.R.Y, c.U.Y, c.B.Y); local b = v3(c.R.Z, c.U.Z, c.B.Z)
		local inv = cf(v3(0, 0, 0), r, u, b)
		inv.Position = -rotv(inv, c.Position)
		return inv
	end end
	if k == "ToEulerAnglesXYZ" then return function() return 0, 0, 0 end end
	error("CFrame has no member " .. tostring(k), 2)
end
CF.__mul = function(a, b)
	if getmetatable(b) == V3 then return a.Position + rotv(a, b) end
	return cf(a.Position + rotv(a, b.Position), rotv(a, b.R), rotv(a, b.U), rotv(a, b.B))
end
CF.__add = function(a, v) return cf(a.Position + v, a.R, a.U, a.B) end
CF.__sub = function(a, v) return cf(a.Position - v, a.R, a.U, a.B) end
CFrame = {
	new = function(x, y, z)
		if x == nil then return ident() end
		if getmetatable(x) == V3 then
			if y and getmetatable(y) == V3 then return CFrame.lookAt(x, y) end
			local c = ident(); c.Position = x; return c
		end
		local c = ident(); c.Position = v3(x, y, z); return c
	end,
	Angles = function(rx, ry, rz)
		local function rx_(a) return cf(v3(0, 0, 0), v3(1, 0, 0), v3(0, math.cos(a), math.sin(a)), v3(0, -math.sin(a), math.cos(a))) end
		local function ry_(a) return cf(v3(0, 0, 0), v3(math.cos(a), 0, -math.sin(a)), v3(0, 1, 0), v3(math.sin(a), 0, math.cos(a))) end
		local function rz_(a) return cf(v3(0, 0, 0), v3(math.cos(a), math.sin(a), 0), v3(-math.sin(a), math.cos(a), 0), v3(0, 0, 1)) end
		return rx_(rx or 0) * ry_(ry or 0) * rz_(rz or 0)
	end,
	lookAt = function(at, look, up)
		up = up or v3(0, 1, 0)
		local f = (look - at).Unit
		if f.Magnitude == 0 then return CFrame.new(at) end
		local r = f:Cross(up).Unit
		if r.Magnitude == 0 then r = v3(1, 0, 0) end
		local u = r:Cross(f)
		return cf(at, r, u, -f)
	end,
	fromMatrix = function(pos, r, u, b) return cf(pos, r, u, b or r:Cross(u)) end,
}
CFrame.identity = ident()

Enum = setmetatable({}, { __index = function(t, k)
	local cache = {}
	local e = setmetatable({}, { __index = function(_, v)
		if not cache[v] then cache[v] = { Name = v, EnumType = k, Value = (k == 'RenderPriority' and v == 'Camera') and 200 or 1 } end
		return cache[v]
	end })
	rawset(t, k, e)
	return e
end })

Random = { new = function(seed) local o = {}; function o:NextNumber(a, b) return (a or 0) + ((b or 1) - (a or 0)) * math.random() end; function o:NextInteger(a, b) return math.random(a, b) end; return o end }
function tick() return os.clock() end
time = os.clock
bit32 = bit32 or {
	band = function(a, b) return a & b end, bor = function(a, b) return a | b end, bxor = function(a, b) return a ~ b end,
	rshift = function(a, n) return (a & 0xFFFFFFFF) >> n end, lshift = function(a, n) return (a << n) & 0xFFFFFFFF end,
}
math.clamp = function(x, lo, hi) if x < lo then return lo elseif x > hi then return hi end return x end
math.sign = function(x) return x > 0 and 1 or x < 0 and -1 or 0 end
math.atan2 = function(y, x) return math.atan(y, x) end
table.clone = function(t) local o = {}; for k, v in pairs(t) do o[k] = v end return o end
table.find = function(t, v) for i, x in ipairs(t) do if x == v then return i end end return nil end
string.split = function(s, sep) local out = {}; for p in (s .. sep):gmatch("(.-)" .. sep:gsub("%p", "%%%0")) do out[#out + 1] = p end return out end
local lua_tostring = tostring

-- ----------------------------------------------------------------- signals
local function newSignal()
	local s = { handlers = {} }
	function s:Connect(f)
		local h = { f = f, connected = true }
		self.handlers[#self.handlers + 1] = h
		return { Disconnect = function() h.connected = false end, Connected = true }
	end
	function s:Once(f) return self:Connect(f) end
	function s:Fire(...)
		for _, h in ipairs(self.handlers) do if h.connected then h.f(...) end end
	end
	function s:Wait() return end
	return s
end
M.newSignal = newSignal

local EVENTS = {}
for n in ([[Activated MouseButton1Click InputBegan InputEnded InputChanged Changed ChildAdded ChildRemoved Heartbeat RenderStepped Stepped OnClientEvent
OnServerEvent PlayerAdded PlayerRemoving WindowFocusReleased GamepadConnected GamepadDisconnected MenuOpened MenuClosed Touched Died Ended Completed
FocusLost AncestryChanged DescendantAdded PromptGamePassPurchaseFinished PromptProductPurchaseFinished PromptPurchaseFinished]]):gmatch("%S+") do EVENTS[n] = true end

-- the properties the code may set (a name that is not here is logged: it may be a typo)
local KNOWN = {}
for n in ([[Name Parent Size Position AnchorPoint Rotation Visible Active ZIndex BackgroundColor3 BackgroundTransparency BorderSizePixel Text TextColor3
TextSize TextWrapped TextXAlignment TextYAlignment TextTransparency TextStrokeTransparency TextStrokeColor3 Font FontFace RichText AutomaticSize ClipsDescendants
LayoutOrder Image ImageColor3 ImageTransparency ScaleType AutoButtonColor TextScaled Color Thickness Transparency ApplyStrokeMode LineJoinMode CornerRadius
PaddingTop PaddingBottom PaddingLeft PaddingRight FillDirection Padding SortOrder HorizontalAlignment VerticalAlignment Wraps CellSize CellPadding Scale
ScrollBarThickness CanvasSize AutomaticCanvasSize CanvasPosition ScrollingDirection IgnoreGuiInset ResetOnSpawn DisplayOrder Enabled ZIndexBehavior
Anchored CanCollide CanQuery CanTouch Massless CastShadow Material Shape Reflectance Locked TopSurface BottomSurface CFrame Orientation PrimaryPart
MeshType Texture LightEmission LightInfluence EmissionDirection SpreadAngle RotSpeed LockedToPart ZOffset Rate Lifetime Speed Drag Acceleration
Looped Volume SoundId PlaybackSpeed TimePosition IsPlaying PlaybackRegionsEnabled PlaybackRegion LoopRegion RollOffMaxDistance
CameraType FieldOfView NearPlaneZ CameraSubject ViewportSize ClockTime Brightness OutdoorAmbient Ambient ColorShift_Top ExposureCompensation
Density Offset Decay Haze Glare Cover Gravity CharacterAutoLoads MouseBehavior MouseIconEnabled OnServerInvoke OnClientInvoke
Value Source DefaultValue PlaceId UserId DisplayName LocalPlayer Character ContrastValue Contrast Saturation TintColor Brightness Min Max
Rotation AbsoluteSize AbsolutePosition Modal MaxPlayers Archivable RobuxPrice PrimaryAxis ModelStreamingMode Fill EasingStyle Opacity
TextEditable ClearTextOnFocus PlaceholderText Selectable SelectionImageObject ImageRectOffset ImageRectSize SliceCenter BorderColor3 BorderMode
Color Transparency Length Cover ExtentsOffset StudsOffset Adornee AlwaysOnTop MaxDistance Face Axis EnableWindowFocusEvents WorldPosition WorldCFrame
Radius Height Mass AssemblyLinearVelocity Velocity Color3 CollisionGroup SurfaceGui SizeConstraint FillColor FillTransparency OutlineColor OutlineTransparency]]):gmatch("%S+") do KNOWN[n] = true end

local BASEPART = { Part = true, MeshPart = true, WedgePart = true, SpawnLocation = true, UnionOperation = true, Terrain = false }
local GUIOBJ = { Frame = true, TextLabel = true, TextButton = true, ImageLabel = true, ScrollingFrame = true, TextBox = true, ImageButton = true, ViewportFrame = true }
local BASES = { BasePart = BASEPART, GuiObject = GUIOBJ, GuiButton = { TextButton = true, ImageButton = true } }

M.DEFAULTS = { Transparency = 0, BackgroundTransparency = 0, TextTransparency = 0, Visible = true, Enabled = true, PlaybackSpeed = 1, Rotation = 0, Volume = 0.5, Looped = false,
	TimePosition = 0, Anchored = false, CanCollide = true, Text = '', ZIndex = 1, Size = nil }
local methods = {}
local function newInstance(class)
	local o = { __class = class, __p = {}, __kids = {}, __attrs = {}, __sig = {} }
	return setmetatable(o, M.IMT)
end
M.IMT = {}
M.IMT.__type = "Instance"
local function isA(o, c)
	if o.__class == c or c == "Instance" then return true end
	local b = BASES[c]
	if b and b[o.__class] then return true end
	if c == "GuiBase2d" and GUIOBJ[o.__class] then return true end
	if c == "LayerCollector" and (o.__class == "ScreenGui") then return true end
	if c == "PVInstance" and (BASEPART[o.__class] or o.__class == "Model") then return true end
	return false
end
M.IMT.__index = function(t, k)
	local m = methods[k]
	if m then return m end
	if k == "ClassName" then return t.__class end
	local p = rawget(t, "__p")
	if p[k] ~= nil then return p[k] end
	if EVENTS[k] then
		local s = t.__sig[k]
		if not s then s = newSignal(); t.__sig[k] = s end
		return s
	end
	for _, c in ipairs(t.__kids) do if c.__p.Name == k then return c end end
	if k == "Name" then return t.__class end
	local d = M.DEFAULTS[k]
	if d ~= nil then return d end
	if k == "AbsoluteSize" then return v2(1280, 720) end
	if k == "IsPlaying" then return false end
	if k == "ViewportSize" then return v2(1280, 720) end
	if k == "Position" and t.__p.CFrame then return t.__p.CFrame.Position end
	return nil
end
M.IMT.__newindex = function(t, k, v)
	if k == "Parent" then
		local old = t.__p.Parent
		if old then for i, c in ipairs(old.__kids) do if c == t then table.remove(old.__kids, i) break end end end
		t.__p.Parent = v
		if v then
			v.__kids[#v.__kids + 1] = t
			if v.__sig.ChildAdded then v.__sig.ChildAdded:Fire(t) end
		end
		return
	end
	if not KNOWN[k] and not EVENTS[k] and string.sub(k, 1, 2) ~= "__" then warn_("unknown property " .. tostring(k) .. " set on " .. t.__class) end
	if k == "CFrame" and t.__class ~= "Camera" then t.__p.Position = v.Position end
	t.__p[k] = v
end
M.IMT.__tostring = function(t) return t.__class .. ":" .. tostring(t.__p.Name or "") end

methods.Destroy = function(o) o.Parent = nil; o.__destroyed = true end
methods.ClearAllChildren = function(o) for i = #o.__kids, 1, -1 do o.__kids[i].Parent = nil end end
methods.GetChildren = function(o) local out = {}; for _, c in ipairs(o.__kids) do out[#out + 1] = c end return out end
local function desc(o, out) for _, c in ipairs(o.__kids) do out[#out + 1] = c; desc(c, out) end return out end
methods.GetDescendants = function(o) return desc(o, {}) end
methods.FindFirstChild = function(o, name, rec)
	for _, c in ipairs(o.__kids) do if c.__p.Name == name then return c end end
	if rec then for _, c in ipairs(desc(o, {})) do if c.__p.Name == name then return c end end end
	return nil
end
methods.FindFirstChildOfClass = function(o, class) for _, c in ipairs(o.__kids) do if c.__class == class then return c end end return nil end
methods.FindFirstChildWhichIsA = function(o, class) for _, c in ipairs(o.__kids) do if isA(c, class) then return c end end return nil end
methods.WaitForChild = function(o, name)
	local c = methods.FindFirstChild(o, name)
	if not c then error("WaitForChild would wait forever: " .. tostring(o) .. " has no child " .. tostring(name), 2) end
	return c
end
methods.IsA = isA
methods.IsDescendantOf = function(o, a) local p = o.__p.Parent; while p do if p == a then return true end p = p.__p.Parent end return false end
methods.SetAttribute = function(o, k, v) o.__attrs[k] = v end
methods.GetAttribute = function(o, k) return o.__attrs[k] end
methods.Clone = function(o)
	local c = newInstance(o.__class)
	for k, v in pairs(o.__p) do if k ~= "Parent" then c.__p[k] = v end end
	for k, v in pairs(o.__attrs) do c.__attrs[k] = v end
	for _, k in ipairs(o.__kids) do local kc = methods.Clone(k); kc.Parent = c end
	return c
end
methods.PivotTo = function(o, c) o.__p.CFrame = c; o.__p.Position = c.Position end
methods.GetPivot = function(o) return o.__p.CFrame or CFrame.new() end
methods.ScaleTo = function(o, s) o.__scale = s end
methods.GetBoundingBox = function(o) return CFrame.new(), v3(10, 4, 15) end
methods.Emit = function(o, n) o.__emitted = (o.__emitted or 0) + (n or 1) end
methods.Play = function(o) o.__p.IsPlaying = true end
methods.Stop = function(o) o.__p.IsPlaying = false end
methods.Pause = function(o) o.__p.IsPlaying = false end
methods.Resume = function(o) o.__p.IsPlaying = true end
methods.GetMouseDelta = function() return v2(0, 0) end
methods.IsKeyDown = function() return false end
methods.GetMouseLocation = function() return v2(640, 360) end
methods.SetCoreGuiEnabled = function() end
methods.Clear = function() end
methods.FillCylinder = function() end
methods.FillBall = function() end
methods.FillBlock = function() end
methods.WriteVoxels = function() end
methods.BulkMoveTo = function() end
methods.GetService = function(o, name) return M.service(name) end
methods.GetPlayers = function() return { M.localPlayer } end
methods.GetPlayerByUserId = function(o, id) return M.localPlayer end
methods.UserOwnsGamePassAsync = function() return false end
methods.PromptProductPurchase = function() end
methods.PromptGamePassPurchase = function() end
methods.GetProductInfo = function() return {} end
methods.BindToClose = function() end
methods.FilterStringAsync = function(o, t) return { GetNonChatStringForBroadcastAsync = function() return t end } end
methods.GetDataStore = function() return { GetAsync = function() return nil end, SetAsync = function() end } end
methods.WorldToViewportPoint = function() return v3(640, 360, 10), true end
methods.TweenSize = function() end

-- remotes
methods.FireServer = function(o, ...)
	local s = o.__sig.OnServerEvent
	if s then s:Fire(M.localPlayer, ...) end
	M.log[#M.log + 1] = "FireServer " .. tostring(o.__p.Name)
end
methods.FireClient = function(o, p, ...)
	local s = o.__sig.OnClientEvent
	if s then s:Fire(...) end
end
methods.FireAllClients = function(o, ...) local s = o.__sig.OnClientEvent if s then s:Fire(...) end end
methods.InvokeServer = function(o, ...)
	local f = o.__p.OnServerInvoke
	if not f then error("InvokeServer on " .. tostring(o.__p.Name) .. " has no OnServerInvoke (it would wait forever)", 2) end
	return f(M.localPlayer, ...)
end
-- run service
methods.BindToRenderStep = function(o, name, prio, fn) M.renderSteps[name] = fn end
methods.UnbindFromRenderStep = function(o, name) M.renderSteps[name] = nil end
methods.IsClient = function() return true end
methods.IsServer = function() return false end
methods.IsStudio = function() return true end
methods.IsRunning = function() return true end
M.renderSteps = {}

Instance = { new = function(class)
	local o = newInstance(class)
	o.__p.Name = class
	if class == "RemoteEvent" or class == "RemoteFunction" then o.__remote = true end
	return o
end }
local function instOf(class, name) local o = Instance.new(class); o.__p.Name = name or class; return o end
M.instOf = instOf

-- ----------------------------------------------------------------- services, the world
local services = {}
function M.service(name)
	if services[name] then return services[name] end
	local s = instOf(name, name)
	services[name] = s
	return s
end
local game = M.service("DataModel")
_G.game = game
_G.workspace = M.service("Workspace")
workspace.Terrain = nil
local terrain = instOf("Terrain", "Terrain"); terrain.Parent = workspace
local camera = instOf("Camera", "Camera"); camera.Parent = workspace
workspace.CurrentCamera = camera
local players = M.service("Players")
M.localPlayer = instOf("Player", "Player")
M.localPlayer.__p.UserId = 4242
M.localPlayer.__p.DisplayName = "Teszt"
local pg = instOf("PlayerGui", "PlayerGui"); pg.Parent = M.localPlayer
players.LocalPlayer = M.localPlayer
M.localPlayer.Parent = players
M.service("ReplicatedStorage"); M.service("ServerScriptService"); M.service("StarterPlayer"); M.service("Lighting")
M.service("UserInputService"); M.service("RunService"); M.service("SoundService"); M.service("StarterGui"); M.service("MarketplaceService")
M.service("DataStoreService"); M.service("TextService"); M.service("TweenService"); M.service("Debris"); M.service("GuiService"); M.service("ContextActionService")
M.service("HttpService")
M.service("Debris").AddItem = function() end
M.service("TweenService").Create = function() return { Play = function() end } end
M.service("RunService").Heartbeat = newSignal()
M.service("RunService").RenderStepped = newSignal()
M.service("MarketplaceService").ProcessReceipt = nil

-- tasks: coroutines; task.wait yields, M.pump(dt) lets time pass for the waiting ones
M.waiting = {}
M.clockT = 0
local function startThread(f, ...)
	local co = coroutine.create(f)
	local ok, r = coroutine.resume(co, ...)
	if not ok then M.log[#M.log + 1] = "task error: " .. tostring(r); error(r, 0) end
	if coroutine.status(co) == "suspended" then M.waiting[#M.waiting + 1] = { co = co, at = M.clockT + (type(r) == "number" and r or 0) } end
	return co
end
task = {
	spawn = function(f, ...) if type(f) == "function" then return startThread(f, ...) end end,
	defer = function(f, ...) return startThread(f, ...) end,
	delay = function(t, f, ...) local args = { ... }; return startThread(function() task.wait(t); f(table.unpack(args)) end) end,
	wait = function(t)
		if coroutine.isyieldable() then coroutine.yield(t or 0.03) end
		return t or 0.03
	end,
}
function M.pump(dt)
	M.clockT = M.clockT + dt
	local list = M.waiting
	M.waiting = {}
	for _, w in ipairs(list) do
		if w.at <= M.clockT then
			local ok, r = coroutine.resume(w.co)
			if not ok then M.log[#M.log + 1] = "task error: " .. tostring(r); error(r, 0) end
			if coroutine.status(w.co) == "suspended" then M.waiting[#M.waiting + 1] = { co = w.co, at = M.clockT + (type(r) == "number" and r or 0) } end
		else
			M.waiting[#M.waiting + 1] = w
		end
	end
end

-- ----------------------------------------------------------------- modules (translated from Luau by the driver)
M.modules = {}
local function moduleInstance(name, path)
	local o = instOf("ModuleScript", name)
	o.__file = path
	return o
end
M.moduleInstance = moduleInstance

function M.require(m)
	if type(m) ~= "table" or not m.__file then error("require: not a module: " .. tostring(m), 2) end
	if M.modules[m] ~= nil then return M.modules[m].value end
	local code = M.translate(m.__file)
	local env = setmetatable({ script = m }, { __index = _G })
	local f, e = load(code, "@" .. m.__file, "t", env)
	if not f then error(e, 0) end
	local slot = { value = nil }
	M.modules[m] = slot
	slot.value = f()
	return slot.value
end
function M.runScript(m)
	local code = M.translate(m.__file)
	local env = setmetatable({ script = m }, { __index = _G })
	local f, e = load(code, "@" .. m.__file, "t", env)
	if not f then error(e, 0) end
	return f()
end
_G.require = M.require

return M
