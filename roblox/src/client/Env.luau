--!nonstrict
-- The time of day (Napszak): the presets day / sunset / overcast / night of web/js/render.js (TIMES) as Roblox lighting.  The sea,
-- sky and island are built once by the server (World.luau); this only changes the light, the haze and the clouds.
local Lighting = game:GetService("Lighting")

local Env = {}

local PRESETS = {
	day = { clock = 14, brightness = 3, outdoor = Color3.fromRGB(120, 130, 150), ambient = Color3.fromRGB(70, 78, 92), top = Color3.fromRGB(255, 244, 224),
		atmo = { density = 0.22, offset = 0.2, color = Color3.fromRGB(190, 205, 225), decay = Color3.fromRGB(150, 170, 200), haze = 1.2, glare = 0.1 },
		cloud = Color3.fromRGB(255, 255, 255), cover = 0.55, exposure = 0, sea = Color3.fromRGB(28, 96, 150) },
	sunset = { clock = 17.9, brightness = 2.6, outdoor = Color3.fromRGB(150, 110, 100), ambient = Color3.fromRGB(95, 70, 70), top = Color3.fromRGB(255, 164, 101),
		atmo = { density = 0.3, offset = 0.25, color = Color3.fromRGB(250, 168, 107), decay = Color3.fromRGB(170, 100, 90), haze = 2.2, glare = 0.6 },
		cloud = Color3.fromRGB(255, 207, 174), cover = 0.6, exposure = 0.1, sea = Color3.fromRGB(45, 61, 87) },
	overcast = { clock = 13, brightness = 1.3, outdoor = Color3.fromRGB(150, 156, 160), ambient = Color3.fromRGB(120, 125, 130), top = Color3.fromRGB(223, 229, 234),
		atmo = { density = 0.45, offset = 0.1, color = Color3.fromRGB(178, 186, 194), decay = Color3.fromRGB(150, 156, 160), haze = 2.4, glare = 0 },
		cloud = Color3.fromRGB(195, 200, 205), cover = 0.95, exposure = 0, sea = Color3.fromRGB(60, 80, 92) },
	night = { clock = 0.4, brightness = 1, outdoor = Color3.fromRGB(35, 45, 70), ambient = Color3.fromRGB(20, 26, 44), top = Color3.fromRGB(159, 180, 255),
		atmo = { density = 0.25, offset = 0, color = Color3.fromRGB(20, 28, 44), decay = Color3.fromRGB(10, 14, 24), haze = 0.6, glare = 0 },
		cloud = Color3.fromRGB(52, 60, 74), cover = 0.4, exposure = -0.1, sea = Color3.fromRGB(10, 20, 36) },
}
Env.names = { "day", "sunset", "overcast", "night" }

function Env.set(name)
	local p = PRESETS[name] or PRESETS.day
	Lighting.ClockTime = p.clock
	Lighting.Brightness = p.brightness
	Lighting.OutdoorAmbient = p.outdoor
	Lighting.Ambient = p.ambient
	Lighting.ColorShift_Top = p.top
	Lighting.ExposureCompensation = p.exposure
	local a = Lighting:FindFirstChildOfClass("Atmosphere") or Instance.new("Atmosphere")
	a.Density, a.Offset, a.Color, a.Decay, a.Haze, a.Glare = p.atmo.density, p.atmo.offset, p.atmo.color, p.atmo.decay, p.atmo.haze, p.atmo.glare
	a.Parent = Lighting
	local clouds = workspace.Terrain:FindFirstChildOfClass("Clouds")
	if not clouds then
		clouds = Instance.new("Clouds")
		clouds.Parent = workspace.Terrain
	end
	clouds.Color, clouds.Cover, clouds.Density = p.cloud, p.cover, 0.6
	local sea = workspace:FindFirstChild("Sea")
	if sea then sea.Color = p.sea end
end

return Env
