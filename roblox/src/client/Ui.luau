--!nonstrict
-- Small helpers to build the screens in code (no hand-made GUI objects to keep in sync).
local Ui = {}

function Ui.make(class: string, props: { [string]: any }?, children: { Instance }?): Instance
	local o = Instance.new(class)
	local parent = nil
	for k, v in props or {} do
		if k == "Parent" then parent = v else o[k] = v end
	end
	for _, c in children or {} do c.Parent = o end
	if parent then o.Parent = parent end
	return o
end

function Ui.corner(r: number?): UICorner
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, r or 6)
	return c
end

function Ui.padding(p: number): UIPadding
	local u = Instance.new("UIPadding")
	u.PaddingTop, u.PaddingBottom, u.PaddingLeft, u.PaddingRight = UDim.new(0, p), UDim.new(0, p), UDim.new(0, p), UDim.new(0, p)
	return u
end

function Ui.label(parent: Instance, text: string, props: { [string]: any }?): TextLabel
	local l = Ui.make("TextLabel", {
		BackgroundTransparency = 1, Text = text, TextColor3 = Color3.fromRGB(230, 240, 235), Font = Enum.Font.GothamMedium,
		TextSize = 16, TextXAlignment = Enum.TextXAlignment.Left, Size = UDim2.new(1, 0, 0, 20),
	})
	for k, v in props or {} do l[k] = v end
	l.Parent = parent
	return l
end

function Ui.button(parent: Instance, text: string, props: { [string]: any }?, onClick: (() -> ())?): TextButton
	local b = Ui.make("TextButton", {
		Text = text, Font = Enum.Font.GothamBold, TextSize = 16, TextColor3 = Color3.fromRGB(16, 22, 20),
		BackgroundColor3 = Color3.fromRGB(255, 200, 64), AutoButtonColor = true, Size = UDim2.new(0, 140, 0, 38),
	}, { Ui.corner(6) })
	for k, v in props or {} do b[k] = v end
	b.Parent = parent
	if onClick then b.Activated:Connect(onClick) end
	return b
end

Ui.Green = Color3.fromRGB(107, 255, 133)
Ui.Amber = Color3.fromRGB(255, 200, 64)
Ui.Red = Color3.fromRGB(255, 90, 70)
Ui.Panel = Color3.fromRGB(18, 26, 30)
Ui.RarityColor = {
	C = Color3.fromRGB(159, 176, 191), R = Color3.fromRGB(90, 176, 255), E = Color3.fromRGB(197, 139, 255), L = Color3.fromRGB(255, 200, 64),
}

return Ui
