#include <globals.h>
#include <managers/font_manager.h>

// 将 Windows 本地路径规范化为 TOML 可安全保存、跨平台可读取的正斜杠形式。
std::string NormalizeFontConfigPath(std::string path) {
	std::replace(path.begin(), path.end(), '\\', '/');
	return path;
}

// 根据已部署 TTC 文件选择目标字形，避免集合默认字体与 UI 标注不一致。
int ResolveFontFaceIndex(const std::string& path) {
	const std::string fileName = FileNameFromPath(path);
	return fileName == "01-dfp-heisei-maru-gothic-w4.ttc" || fileName == "02-dfp-maru-gothic-sb.ttc" ? 2 : 0;
}
void FontManager::Init(Config& cfg) {
	if (!isInit) {
		RefreshFontList();
		if (fontsAvailable.size() > 0) {
			fontnameWithCharset = &fontsAvailable[0];
			fontnameDefault = &fontsAvailable[fontsAvailable.size() - 1];
			// Assign default fonts by alphabetical order
			// 优先选择部署的日文卡拉 OK 字体，避免默认 Arial 影响日文歌词外观。
			for (int i = 0; i < fontsAvailable.size(); i++) {
				if (FileNameFromPath(fontsAvailable[i]) == "00-dfg-heisei-gothic-w5.ttc") {
					fontnameDefault = &fontsAvailable[i];
					fontnameWithCharset = &fontsAvailable[i];
					break;
				}
			}
		}
		FromConfig(cfg);
		isInit = true;
	}
}

Config& FontManager::FromConfig(Config& cfg) {
	// Fonts should be available. If not, fallback values are used.
	for (int i = 0; i < fontsAvailable.size(); i++) {
		if (NormalizeFontConfigPath(fontsAvailable[i]) == NormalizeFontConfigPath(cfg.fontnameDefault)) fontnameDefault = &fontsAvailable[i];
		if (NormalizeFontConfigPath(fontsAvailable[i]) == NormalizeFontConfigPath(cfg.fontnameWithCharset)) fontnameWithCharset = &fontsAvailable[i];
	}
	// Font Styles
	fontSize = (std::max)(10.0f, (std::min)(100.0f, cfg.fontSize));
	// 限制界面字体图集尺寸，避免误设大字号后 DX11 无法创建字体纹理。
	fontSizeImGui = (std::max)(10.0f, (std::min)(24.0f, cfg.fontSizeImGui));
	isBold = cfg.isBold;
	isItalic = cfg.isItalic;
	ImGui::GetIO().FontGlobalScale = cfg.FontGlobalScale;
	fillColor = cfg.fillColor;
	strokeColor = cfg.strokeColor;
	shadowColor = cfg.shadowColor;
	strokeSize = cfg.strokeSize;
	shadowOffset = cfg.shadowOffset;
	showGUI = cfg.showFontManagerGUI;
	return cfg;
}
Config& FontManager::ToConfig(Config& cfg) {
	// Fonts are saved with filenames
	cfg.fontnameDefault = NormalizeFontConfigPath(*fontnameDefault);
	cfg.fontnameWithCharset = NormalizeFontConfigPath(*fontnameWithCharset);
	// Font Styles
	cfg.fontSize = fontSize;
	cfg.fontSizeImGui = fontSizeImGui;
	cfg.isBold = isBold;
	cfg.isItalic = isItalic;
	cfg.FontGlobalScale = ImGui::GetIO().FontGlobalScale;
	cfg.fillColor = fillColor;
	cfg.strokeColor = strokeColor;
	cfg.shadowColor = shadowColor;
	cfg.strokeSize = strokeSize;
	cfg.shadowOffset = shadowOffset;
	cfg.showFontManagerGUI = showGUI;
	return cfg;
}

/* Build charset containing every character the renderer could ever display.
- This will APPEND all unique characters of the string to the charset.
- Normally it should contain the pv_db.txt from any lyrics mod you're using
- Otherwise, it would use a fallback charset which would cover most Japanese characters & Romal characters
*/
int FontManager::UpdateCharset(std::wstring chars) {
	size_t size_before = charset.size();
	for (auto& c : chars) if (c) charset[c] = 1;
	return (int)(charset.size() - size_before);
}

/* Retrives all available fonts under the fonts\ directroy. Results are alphabetically sorted. */
std::vector<std::string>& FontManager::RefreshFontList() {
	fontsAvailable.clear();
	try {
		for (auto file : std::filesystem::directory_iterator(to_utf8(FullPathInDllFolder(L"fonts\\")))) {
			std::wstring path = file.path();
			const std::wstring fileName = file.path().filename().wstring();
			// DFG POP Mix W5 字间距过紧，不纳入模组字体选择列表。
			if (fileName.find(L"DFGPOPMix-W5") != std::wstring::npos || fileName.find(L"DFPPOPMix-W5") != std::wstring::npos)
				continue;
			std::wstring ext = path.substr(path.length() - 3);
			if (ext == L"ttf" || ext == L"otf" || ext == L"ttc") {
				fontsAvailable.push_back(to_utf8(path));
			}
		}
		std::sort(fontsAvailable.begin(), fontsAvailable.end());
	}
	catch (std::filesystem::filesystem_error e) {
		MessageBoxW(
			window,
			FONTS_FOLDER_NOT_FOUND,
			MESSAGEBOX_TITLE,
			MB_ICONEXCLAMATION
		);
	}
	return fontsAvailable;
}

/* Build atlas based on current charset and fonts.
- Fonts DO NOT get re-rendered on every frame. Including styles, etc.
- They get put on a texture here ONCE and would not change unless this function is called again.
- which will update the fonts based on current settings.
- TL;DR: If you made any change to the settings and want to see in on screen, this function MUST be called afterwards.
- And do it outside ImGui's NewFrame() scope. In our instance just set `reloadFonts` to true
-
- NOTE : Do not use offical DearImGui repo to build since it does not contain some new features I introduced to
-        this version of ImGui.
*/
void FontManager::RebuildFonts() {
	ImGuiIO& io = ImGui::GetIO();
	io.Fonts->Clear();
	// Default font will still be usable
	ImFontConfig config;
	config.SizePixels = fontSizeImGui;
	io.Fonts->AddFontDefault(&config);
	// 新增中文工具面板使用系统雅黑字形，只合并到固定字号的界面字体。
	if (std::filesystem::exists(L"C:\\Windows\\Fonts\\msyh.ttc")) {
		ImFontConfig uiConfig;
		uiConfig.MergeMode = true;
		// 常用中文范围不含所有工具文字，补齐两项模块的中文字符，避免显示问号。
		ImFontGlyphRangesBuilder uiBuilder;
		uiBuilder.AddRanges(io.Fonts->GetGlyphRangesChineseSimplifiedCommon());
		uiBuilder.AddText(u8"逐行歌手颜色启用合唱柔和渐变关闭融合纯本曲标记未识别使用默认其他初音镜铃连巡填充描边已阴影恢复此保存重新读取即时预览包含四色上下取消整句横向");
		uiBuilder.AddText(u8"一下不与专丢中为主义乐事于交人仅仍以件会伴似体使例供依保信修停允先免入关具内再准凑出函分则初别到制前功加动化匹单即卸历原去及反发取受变口另只可台史号同名后听启周命和回因固在地址均坏基增声复外失奏始字存安完定实容密对将就尾局工已帧常并序应延建开异弃式当录径待心快态恢感戏成或户所才执找护拒拥择持损换接控提播支收改放效数整新无既旧时明是显暂曲更有期未本机束条来果查标校核检模次歌止此步段每求汇没法测消淡混游源点热然照版状狗独猜理生用由界留的益盖目相看真知码确示离秒程立等签管紧约级纳线终绑结绝继绪续编置而联能自菜行补装覆认许设证词试话语误请读调象败资赏赖起超足路跳身轨转载辑边过运进连迟退送适选逐通逻道避部都配释重量鉴错门闭限除隔静非音项频题驻验默" );
		static ImVector<ImWchar> uiRanges;
		uiBuilder.BuildRanges(&uiRanges);
		io.Fonts->AddFontFromFileTTF("C:\\Windows\\Fonts\\msyh.ttc", fontSizeImGui,
			&uiConfig, uiRanges.Data);

	}
	// Setting up styles
	if (isBold) config.FontBuilderFlags |= ImGuiFreeTypeBuilderFlags_Bold;
	if (isItalic) config.FontBuilderFlags |= ImGuiFreeTypeBuilderFlags_Oblique;
	LOG(L"正在重建字体图集，请稍候。");
	// 歌词图集按当前输出分辨率生成；ImGui 控制面板仍保持固定字号。
	const float lyricAtlasFontSize = fontSize * lyricAtlasScale;
	if (fontnameDefault) {
		config.FontNo = ResolveFontFaceIndex(*fontnameDefault);
		io.Fonts->AddFontFromFileTTF(
			fontnameDefault->c_str(),
			lyricAtlasFontSize,
			&config, // Merge into this font.
			io.Fonts->GetGlyphRangesDefault()
		);
		config.MergeMode = true;
	}
	ImVector<ImWchar> ranges;
	ImFontGlyphRangesBuilder builder;
	if (charset.size() > 0) {
		std::wstring charset_buffer;
		for (auto& c : charset) charset_buffer.push_back(c.first);
		builder.AddText(to_utf8(charset_buffer).c_str());
	}
	else {
		LOG(L"使用基础字符集等待歌词字符进入图集，避免高分辨率下构建完整日文图集。");
		builder.AddRanges(io.Fonts->GetGlyphRangesDefault());
	}
	builder.BuildRanges(&ranges);
	if (fontnameWithCharset) {
		config.FontNo = ResolveFontFaceIndex(*fontnameWithCharset);
		font = io.Fonts->AddFontFromFileTTF(
			fontnameWithCharset->c_str(),
			lyricAtlasFontSize,
			&config,
			&ranges[0]
		);
	}
	io.Fonts->Build();
	++atlasRevision;
	LOG(L"字体图集重建完成。");
}

/* 以 1080p 为基准确定歌词物理字号，分辨率改变时安排下一帧重建高分辨率图集。 */
void FontManager::UpdateKtvResolutionScale(const ImVec2& viewportSize) {
	if (viewportSize.y <= 0.0f)
		return;
	const float targetScale = (std::max)(0.75f, (std::min)(2.0f, viewportSize.y / 1080.0f));
	if (fabsf(targetScale - lyricAtlasScale) < 0.01f)
		return;
	lyricAtlasScale = targetScale;
	reloadFonts = true;
	LOG(L"歌词字体图集将按 %.2fx 输出倍率重建。", lyricAtlasScale);
}

/* Called by DX Hook's OnFrame. Do not override.*/
void FontManager::OnFrame() {
	UpdateKtvResolutionScale(ImGui::GetIO().DisplaySize);
	if (reloadFonts) {
		// 字体图集改变前仅释放 DX11 后端对象，保留 ImGui 上下文与窗口状态。
		ImGui_ImplDX11_InvalidateDeviceObjects();
		RebuildFonts();
		// 下一帧的 ImGui_ImplDX11_NewFrame 会自动上传新图集纹理。
		reloadFonts = false;
	}
}

/* Called by DX Hook's OnFrame. Do not override.*/
void FontManager::OnImGUI() {
	if (!showGUI) return;
	ImGui::SetNextWindowBgAlpha(0.5);
	ImGui::Begin("Fonts [Ctrl+F]");
	ImGui::Text("Note : The settings here don't reflect automatically. You need to apply it first.");
	ImGui::Text("Current charset size : %d", charset.size());
	ImGui::Text("Fonts");
	if (fontsAvailable.size() > 0) {
		if (ImGui::BeginCombo("Default (w/ Romal & Japanese charset)", FileNameFromPath(*fontnameDefault).c_str())) {
			for (int i = 0; i < fontsAvailable.size(); i++) {
				std::string* font = &fontsAvailable[i];
				const bool isSelected = (font == fontnameDefault);
				if (ImGui::Selectable(FileNameFromPath(*font).c_str(), isSelected)) {
					fontnameDefault = font;
				}
				if (isSelected) {
					ImGui::SetItemDefaultFocus();
				}
			}
			ImGui::EndCombo();
		}

		if (ImGui::BeginCombo("Fallback (w/ Custom Charset)", FileNameFromPath(*fontnameWithCharset).c_str())) {
			for (int i = 0; i < fontsAvailable.size(); i++) {
				std::string* font = &fontsAvailable[i];
				const bool isSelected = (font == fontnameWithCharset);
				if (ImGui::Selectable(FileNameFromPath(*font).c_str(), isSelected)) {
					fontnameWithCharset = font;
				}
				if (isSelected) {
					ImGui::SetItemDefaultFocus();
				}
			}
			ImGui::EndCombo();
		}
		ImGui::Separator();
	}
	else {
		ImGui::TextColored(ImVec4(1.0f, 0.0f, 0.0f, 1.0f), "WARNING : No fonts available!");
	}
	if (ImGui::Button("Refresh List")) RefreshFontList();
	ImGui::Text("Font Size");
	ImGui::TextColored(ImVec4(1.0f, 0.0f, 0.0f, 1.0f), "WARNING : Going for a large font size might crash the texture creation procedure!");
	ImGui::SliderFloat("Font Size", &fontSize, 10, 100, "%.1f");
	ImGui::SliderFloat("ImGui Font Size", &fontSizeImGui, 10, 24, "%.1f");
	ImGui::SliderInt("Stroke Size", &strokeSize, 0, 10);

	ImGui::Separator();
	ImGui::Text("Shadows");
	ImGui::SliderFloat("X", &shadowOffset.x, -10, 10);
	ImGui::SliderFloat("Y", &shadowOffset.y, -10, 10);
	shadowOffset.x = ceilf(shadowOffset.x);
	shadowOffset.y = ceilf(shadowOffset.y);
	ImGui::Separator();
	ImGui::Text("Font Colors & Misc");
	ImGui::ColorEdit4("Fill", (float*)&fillColor);
	ImGui::ColorEdit4("Stroke", (float*)&strokeColor);
	ImGui::ColorEdit4("Shadow", (float*)&shadowColor);
	ImGui::Checkbox("Bold", &isBold);
	ImGui::SameLine();
	ImGui::Checkbox("Italic", &isItalic);
	ImGui::Text("Scaling: %.1f", ImGui::GetIO().FontGlobalScale);
	if (ImGui::Button("Scale+")) ImGui::GetIO().FontGlobalScale += 0.1f;
	ImGui::SameLine();
	if (ImGui::Button("Scale-")) ImGui::GetIO().FontGlobalScale -= 0.1f;
	ImGui::Separator();
	SHOW_WINDOW_SAVE_SELECTOR;
	ImGui::SameLine();
	if (ImGui::Button("Save & Apply")) {
		// Only possible outside NewFrame()
		Config::SaveGlobalConfig();
		reloadFonts = true;
	}
	ImGui::End();
}
// 延后字体管理器的实际构造，确保它不在 Windows loader lock 内运行。
FontManager& GetFontManager() {
	static FontManager manager;
	return manager;
}

