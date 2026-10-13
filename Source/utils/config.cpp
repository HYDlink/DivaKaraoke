#include <globals.h>
void Config::LoadDefault() {
	fontnameDefault = "";
	fontnameWithCharset = "";
	fontSize = 86.0f;
	fontSizeImGui = 13.0f;
	isBold = true;
	isItalic = false;
	strokeSize = 4;
	shadowOffset = ImVec2(3, 3);
	fillColor = ImVec4(1, 1, 1, 1);
	strokeColor = ImVec4(0, 0, 0, 1);
	shadowColor = ImVec4(0, 0, 0, 0.5);

	lyricWindowOpacity = 0.0f;
	lyricFormat = "%s";
	// 默认采用传统卡拉 OK 可读性预设：未唱白字黑边，已唱黄字白边。
	ktvBeforeFillColor = ImVec4(1, 1, 1, 1);
	ktvBeforeStrokeColor = ImVec4(0, 0, 0, 1);
	ktvBeforeShadowColor = ImVec4(0, 0, 0, 0.5);
	ktvAfterFillColor = ImVec4(1, 0.82f, 0.0f, 1);
	ktvAfterStrokeColor = ImVec4(1, 1, 1, 1);
	ktvAfterShadowColor = ImVec4(0.25f, 0.16f, 0.0f, 0.75f);
	ktvCurrentColumnX = 0.12f;
	ktvNextColumnX = 0.88f;
	ktvCurrentRowY = 0.76f;
	ktvNextRowY = 0.88f;
	ktvPreCueMs = 3000;
	ktvNativeWipeEstimateMs = 4000;
	ktvWipeEnabled = true;
	ktvPreviewEnabled = false;

	WindowBorderSize = 0.0f;
	WindowRounding = 12.0f;
	FontGlobalScale = 1.0f;
	ImGuiSettings = "";

	showFontManagerGUI = true;
	showLyricsManagerGUI = true;
	// 默认优先加载本地原生派生时间线；文件缺失时运行时会自动回退到游戏原生当前句。
	useExternalLyrics = true;
	showLyrics = true;
	showInternalLyrics = false;
	// 配置文件尚未保存时也必须提供确定的歌词布局默认值。
	lyricDockingStyle = 0;
	lyricPivotStyle = 0;
	lyricPivotOffset = ImVec2();
}

#pragma warning( disable : 4244 )
bool Config::Save() {
	config = toml::parse(FullPathInDllFolder(L"freelyrics.toml"));
	// 配置写入根级字段，避免 DivaModLoader 的旧 TOML 读取器跳过带自定义子表的 Mod。
	if (config.contains("freelyrics"))
		config.as_table().erase("freelyrics");
	toml::value& table = config;

	ASSIGN_TO_TABLE(fontnameDefault);
	ASSIGN_TO_TABLE(fontnameWithCharset);
	ASSIGN_TO_TABLE(fontSize);
	ASSIGN_TO_TABLE(fontSizeImGui);
	ASSIGN_TO_TABLE(isBold);
	ASSIGN_TO_TABLE(isItalic);
	ASSIGN_TO_TABLE(strokeSize);
	ASSIGN_TO_TABLE(lyricWindowOpacity);
	ASSIGN_TO_TABLE(WindowBorderSize);
	ASSIGN_TO_TABLE(WindowRounding);
	ASSIGN_TO_TABLE(FontGlobalScale);
	ASSIGN_TO_TABLE(ImGuiSettings);
	ASSIGN_TO_TABLE(showFontManagerGUI);
	ASSIGN_TO_TABLE(showLyricsManagerGUI);
	ASSIGN_TO_TABLE(useExternalLyrics);
	ASSIGN_TO_TABLE(showInternalLyrics);
	ASSIGN_TO_TABLE(showLyrics);
	ASSIGN_TO_TABLE(lyricDockingStyle);
	ASSIGN_TO_TABLE(lyricPivotStyle);
	ASSIGN_TO_TABLE(lyricFormat);
	ASSIGN_TO_TABLE(ktvCurrentColumnX);
	ASSIGN_TO_TABLE(ktvNextColumnX);
	ASSIGN_TO_TABLE(ktvCurrentRowY);
	ASSIGN_TO_TABLE(ktvNextRowY);
	ASSIGN_TO_TABLE(ktvPreCueMs);
	ASSIGN_TO_TABLE(ktvNativeWipeEstimateMs);
	ASSIGN_TO_TABLE(ktvWipeEnabled);
	ASSIGN_TO_TABLE(ktvPreviewEnabled);

	VEC2_TO_XY(lyricPivotOffset);
	ASSIGN_TO_TABLE(lyricPivotOffsetX);
	ASSIGN_TO_TABLE(lyricPivotOffsetY);

	VEC2_TO_XY(shadowOffset);
	ASSIGN_TO_TABLE(shadowOffsetX);
	ASSIGN_TO_TABLE(shadowOffsetY);

	VEC4_TO_RGBA(fillColor);
	ASSIGN_TO_TABLE(fillColorR);
	ASSIGN_TO_TABLE(fillColorG);
	ASSIGN_TO_TABLE(fillColorB);
	ASSIGN_TO_TABLE(fillColorA);
	VEC4_TO_RGBA(strokeColor);
	ASSIGN_TO_TABLE(strokeColorR);
	ASSIGN_TO_TABLE(strokeColorG);
	ASSIGN_TO_TABLE(strokeColorB);
	ASSIGN_TO_TABLE(strokeColorA);
	VEC4_TO_RGBA(shadowColor);
	ASSIGN_TO_TABLE(shadowColorR);
	ASSIGN_TO_TABLE(shadowColorG);
	ASSIGN_TO_TABLE(shadowColorB);
	ASSIGN_TO_TABLE(shadowColorA);

	VEC4_TO_RGBA(ktvBeforeFillColor);
	ASSIGN_TO_TABLE(ktvBeforeFillColorR);
	ASSIGN_TO_TABLE(ktvBeforeFillColorG);
	ASSIGN_TO_TABLE(ktvBeforeFillColorB);
	ASSIGN_TO_TABLE(ktvBeforeFillColorA);
	VEC4_TO_RGBA(ktvBeforeStrokeColor);
	ASSIGN_TO_TABLE(ktvBeforeStrokeColorR);
	ASSIGN_TO_TABLE(ktvBeforeStrokeColorG);
	ASSIGN_TO_TABLE(ktvBeforeStrokeColorB);
	ASSIGN_TO_TABLE(ktvBeforeStrokeColorA);
	VEC4_TO_RGBA(ktvBeforeShadowColor);
	ASSIGN_TO_TABLE(ktvBeforeShadowColorR);
	ASSIGN_TO_TABLE(ktvBeforeShadowColorG);
	ASSIGN_TO_TABLE(ktvBeforeShadowColorB);
	ASSIGN_TO_TABLE(ktvBeforeShadowColorA);
	VEC4_TO_RGBA(ktvAfterFillColor);
	ASSIGN_TO_TABLE(ktvAfterFillColorR);
	ASSIGN_TO_TABLE(ktvAfterFillColorG);
	ASSIGN_TO_TABLE(ktvAfterFillColorB);
	ASSIGN_TO_TABLE(ktvAfterFillColorA);
	VEC4_TO_RGBA(ktvAfterStrokeColor);
	ASSIGN_TO_TABLE(ktvAfterStrokeColorR);
	ASSIGN_TO_TABLE(ktvAfterStrokeColorG);
	ASSIGN_TO_TABLE(ktvAfterStrokeColorB);
	ASSIGN_TO_TABLE(ktvAfterStrokeColorA);
	VEC4_TO_RGBA(ktvAfterShadowColor);
	ASSIGN_TO_TABLE(ktvAfterShadowColorR);
	ASSIGN_TO_TABLE(ktvAfterShadowColorG);
	ASSIGN_TO_TABLE(ktvAfterShadowColorB);
	ASSIGN_TO_TABLE(ktvAfterShadowColorA);

	// Writing back to the file
	std::ofstream f(FullPathInDllFolder(L"freelyrics.toml"), std::ios::binary);
	if (!f.is_open()) {
		MessageBoxW(
			window,
			L"无法写入歌词配置文件 freelyrics.toml！",
			MESSAGEBOX_TITLE,
			MB_ICONEXCLAMATION
		);
		return false;
	}
	f << config;
	f.close();
	return true;
}

bool Config::Load() {
	try {
		config = toml::parse(FullPathInDllFolder(L"freelyrics.toml"));
	}
	catch (const std::exception&) {
		// 旁路设置文件缺失或损坏时保留默认值，不能在游戏启动期用模态窗口阻塞进程。
		LOG(L"无法解析 freelyrics.toml，已使用默认配置。");
		LoadDefault();
		return false;
	}
	{
		// 兼容旧版 freelyrics 子表，并优先支持加载器兼容的根级配置字段。
		toml::table freelyrics = config.contains("freelyrics")
			? toml::find<toml::table>(config, "freelyrics")
			: config.as_table();
		try {
			fontnameDefault = freelyrics["fontnameDefault"].as_string();
			fontnameWithCharset = freelyrics["fontnameWithCharset"].as_string();
			fontSize = freelyrics["fontSize"].as_floating();
			fontSizeImGui = freelyrics["fontSizeImGui"].as_floating();
			isBold = freelyrics["isBold"].as_boolean();
			isItalic = freelyrics["isItalic"].as_boolean();
			strokeSize = freelyrics["strokeSize"].as_integer();
			lyricWindowOpacity = freelyrics["lyricWindowOpacity"].as_floating();
			WindowBorderSize = freelyrics["WindowBorderSize"].as_floating();
			WindowRounding = freelyrics["WindowRounding"].as_floating();
			FontGlobalScale = freelyrics["FontGlobalScale"].as_floating();
			ImGuiSettings = freelyrics["ImGuiSettings"].as_string();
			showFontManagerGUI = freelyrics["showFontManagerGUI"].as_boolean();
			showLyricsManagerGUI = freelyrics["showLyricsManagerGUI"].as_boolean();
			useExternalLyrics = freelyrics["useExternalLyrics"].as_boolean();
			showInternalLyrics = freelyrics["showInternalLyrics"].as_boolean();
			showLyrics = freelyrics["showLyrics"].as_boolean();
			lyricDockingStyle = freelyrics["lyricDockingStyle"].as_integer();
			lyricPivotStyle = freelyrics["lyricPivotStyle"].as_integer();
			lyricFormat = freelyrics["lyricFormat"].as_string();
			// 新增 KTV 配置缺失时保持默认值，兼容旧版配置文件。
			if (freelyrics.find("ktvPreCueMs") != freelyrics.end()) {
				ktvCurrentColumnX = freelyrics["ktvCurrentColumnX"].as_floating();
				ktvNextColumnX = freelyrics["ktvNextColumnX"].as_floating();
				ktvCurrentRowY = freelyrics["ktvCurrentRowY"].as_floating();
				ktvNextRowY = freelyrics["ktvNextRowY"].as_floating();
				ktvPreCueMs = freelyrics["ktvPreCueMs"].as_integer();
				// 该字段在第一版 KTV 配置之后才加入，缺失时保留默认预估时长。
				if (freelyrics.find("ktvNativeWipeEstimateMs") != freelyrics.end())
					ktvNativeWipeEstimateMs = freelyrics["ktvNativeWipeEstimateMs"].as_integer();
				ktvWipeEnabled = freelyrics["ktvWipeEnabled"].as_boolean();
				if (freelyrics.find("ktvPreviewEnabled") != freelyrics.end())
					ktvPreviewEnabled = freelyrics["ktvPreviewEnabled"].as_boolean();
				ktvBeforeFillColor = ImVec4(freelyrics["ktvBeforeFillColorR"].as_floating(), freelyrics["ktvBeforeFillColorG"].as_floating(), freelyrics["ktvBeforeFillColorB"].as_floating(), freelyrics["ktvBeforeFillColorA"].as_floating());
				ktvBeforeStrokeColor = ImVec4(freelyrics["ktvBeforeStrokeColorR"].as_floating(), freelyrics["ktvBeforeStrokeColorG"].as_floating(), freelyrics["ktvBeforeStrokeColorB"].as_floating(), freelyrics["ktvBeforeStrokeColorA"].as_floating());
				ktvBeforeShadowColor = ImVec4(freelyrics["ktvBeforeShadowColorR"].as_floating(), freelyrics["ktvBeforeShadowColorG"].as_floating(), freelyrics["ktvBeforeShadowColorB"].as_floating(), freelyrics["ktvBeforeShadowColorA"].as_floating());
				ktvAfterFillColor = ImVec4(freelyrics["ktvAfterFillColorR"].as_floating(), freelyrics["ktvAfterFillColorG"].as_floating(), freelyrics["ktvAfterFillColorB"].as_floating(), freelyrics["ktvAfterFillColorA"].as_floating());
				ktvAfterStrokeColor = ImVec4(freelyrics["ktvAfterStrokeColorR"].as_floating(), freelyrics["ktvAfterStrokeColorG"].as_floating(), freelyrics["ktvAfterStrokeColorB"].as_floating(), freelyrics["ktvAfterStrokeColorA"].as_floating());
				ktvAfterShadowColor = ImVec4(freelyrics["ktvAfterShadowColorR"].as_floating(), freelyrics["ktvAfterShadowColorG"].as_floating(), freelyrics["ktvAfterShadowColorB"].as_floating(), freelyrics["ktvAfterShadowColorA"].as_floating());
			}
			lyricPivotOffset = ImVec2(
				freelyrics["lyricPivotOffsetX"].as_floating(),
				freelyrics["lyricPivotOffsetY"].as_floating()
			);

			shadowOffset = ImVec2(
				freelyrics["shadowOffsetX"].as_floating(),
				freelyrics["shadowOffsetY"].as_floating()
			);

			fillColor = ImVec4(
				freelyrics["fillColorR"].as_floating(),
				freelyrics["fillColorG"].as_floating(),
				freelyrics["fillColorB"].as_floating(),
				freelyrics["fillColorA"].as_floating()
			);
			strokeColor = ImVec4(
				freelyrics["strokeColorR"].as_floating(),
				freelyrics["strokeColorG"].as_floating(),
				freelyrics["strokeColorB"].as_floating(),
				freelyrics["strokeColorA"].as_floating()
			);
			shadowColor = ImVec4(
				freelyrics["shadowColorR"].as_floating(),
				freelyrics["shadowColorG"].as_floating(),
				freelyrics["shadowColorB"].as_floating(),
				freelyrics["shadowColorA"].as_floating()
			);
		}
		catch (const std::exception&) {
			// 单个旧字段不兼容时同样不能阻塞启动，改用完整默认配置继续运行。
			LOG(L"freelyrics.toml 字段不兼容，已使用默认配置。");
			LoadDefault();
			return false;
		}
		return true;
	}
}
#pragma warning( default : 4244 )
// 延后配置对象的实际构造，确保它不在 Windows loader lock 内运行。
Config& GetGlobalConfig() {
	static Config config;
	return config;
}
