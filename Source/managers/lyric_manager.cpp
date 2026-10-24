#define IMGUI_DEFINE_MATH_OPERATORS
#include <globals.h>
#include <managers/lyric_manager.h>
#include <managers/ktv_timing.h>
#include <managers/ktv_composite.h>
#include <imgui/imgui_internal.h>
#include <managers/ktv_geometry.h>
#include <managers/singer_render.h>
#include <utils/performance_trace.h>

bool ImGui_CursorButton(const char* ID, ImGuiMouseCursor cursor, bool flipX = false, bool flipY = false) {
	ImVec2 offset, size;
	ImVec2 out_uv_border[2]; // TODO : Render borders as well
	ImVec2 out_uv_fill[2];
	ImTextureID texId = ImGui::GetIO().Fonts->TexID;
	ImGui::GetIO().Fonts->GetMouseCursorTexData(cursor, &offset, &size, out_uv_border, out_uv_fill);
	if (flipX) std::swap(out_uv_border[0].x, out_uv_border[1].x);
	if (flipY) std::swap(out_uv_border[0].y, out_uv_border[1].y);
	ImGui::PushID(ID);
	const bool pressed = ImGui::ImageButton(texId, size, out_uv_border[0], out_uv_border[1]);
	ImGui::PopID();
	return pressed;
}

// 将 ImGui 浮点颜色转换为可直接绘制的颜色，并按需降低透明度。
ImU32 ToOverlayColor(const ImVec4& color, float opacity = 1.0f) {
	return IM_COL32(
		(int)(color.x * 255.0f),
		(int)(color.y * 255.0f),
		(int)(color.z * 255.0f),
		(int)(color.w * opacity * 255.0f)
	);
}

// 统一使用共享歌手渲染入口，正文、描边、阴影和注音遵循相同的合唱规则。
void AddStyledKtvText(ImDrawList* list, ImFont* font, float size, const ImVec2& position,
    const char* text, const KtvTextStyle& style, int layer, float opacity) {
    AddSingerStyledText(list, font, size, position, text, style, layer, opacity);
}

// 绘制一层带阴影和描边的 KTV 歌词文本。
void DrawKtvText(
	ImDrawList* drawList,
	ImFont* font,
	float fontSize,
	const ImVec2& position,
	const char* text,
	const KtvTextStyle& style,
	float opacity
) {
	const float decorationScale = fontSize / FontManager_Inst.fontSize;
	const ImVec2 shadowPosition = position + FontManager_Inst.shadowOffset * decorationScale;
	AddStyledKtvText(drawList, font, fontSize, shadowPosition, text, style, 2, opacity);

	const int outlineSize = (std::max)(1, (int)roundf(FontManager_Inst.strokeSize * decorationScale));
	for (int offsetY = -outlineSize; offsetY <= outlineSize; offsetY++) {
		for (int offsetX = -outlineSize; offsetX <= outlineSize; offsetX++) {
			if (offsetX == 0 && offsetY == 0)
				continue;
			AddStyledKtvText(drawList, font, fontSize, position + ImVec2((float)offsetX, (float)offsetY), text, style, 1, opacity);
		}
	}
	AddStyledKtvText(drawList, font, fontSize, position, text, style, 0, opacity);
}

// 已唱与未唱颜色各占独立裁剪区域，避免透明合成时两种颜色重叠。
void DrawKtvWipeText(
	ImDrawList* drawList,
	ImFont* font,
	float fontSize,
	const ImVec2& position,
	const ImVec2& textSize,
	const char* text,
	const KtvTextStyle& beforeStyle,
	const KtvTextStyle& afterStyle,
	float progress,
	float opacity = 1.0f
) {
	if (progress <= 0.0f || progress >= 1.0f) {
		DrawKtvText(drawList, font, fontSize, position, text, progress >= 1.0f ? afterStyle : beforeStyle, opacity);
		return;
	}
	const float clipX = position.x + textSize.x * progress;
	const ImVec2 clipMin = drawList->GetClipRectMin();
	const ImVec2 clipMax = drawList->GetClipRectMax();
	drawList->PushClipRect(clipMin, ImVec2(clipX, clipMax.y), true);
	DrawKtvText(drawList, font, fontSize, position, text, afterStyle, opacity);
	drawList->PopClipRect();
	drawList->PushClipRect(ImVec2(clipX, clipMin.y), clipMax, true);
	DrawKtvText(drawList, font, fontSize, position, text, beforeStyle, opacity);
	drawList->PopClipRect();
}

// 按 Ruby 自身字号绘制一个细描边字符，避免沿用主歌词粗描边而淹没平假名。
void DrawSingleRubyCharacter(
	ImDrawList* drawList,
	ImFont* font,
	float fontSize,
	const ImVec2& position,
	const char* text,
	const KtvTextStyle& style,
	float opacity = 1.0f
) {
	const float decorationScale = fontSize / FontManager_Inst.fontSize;
	const int outlineSize = (std::max)(1, (int)roundf(FontManager_Inst.strokeSize * decorationScale * 0.5f));
	const ImVec2 shadowPosition = position + FontManager_Inst.shadowOffset * (0.45f * decorationScale);
	AddStyledKtvText(drawList, font, fontSize, shadowPosition, text, style, 2, opacity);
	for (int offsetY = -outlineSize; offsetY <= outlineSize; offsetY++) {
		for (int offsetX = -outlineSize; offsetX <= outlineSize; offsetX++) {
			if (offsetX != 0 || offsetY != 0)
				AddStyledKtvText(drawList, font, fontSize, position + ImVec2((float)offsetX, (float)offsetY), text, style, 1, opacity);
		}
	}
	AddStyledKtvText(drawList, font, fontSize, position, text, style, 0, opacity);
}

// 绘制词组 Ruby：短读音在底字组内等距分布，长读音保持缩放后的居中布局。
void DrawRubyText(
	ImDrawList* drawList,
	ImFont* font,
	float fontSize,
	const ImVec2& position,
	float groupWidth,
	const char* text,
	const KtvTextStyle& style,
	float opacity = 1.0f
) {
	const int characterCount = ImTextCountCharsFromUtf8(text, nullptr);
	const float naturalWidth = font->CalcTextSizeA(fontSize, FLT_MAX, 0.0f, text).x;
	if (characterCount <= 1 || naturalWidth >= groupWidth) {
		DrawSingleRubyCharacter(drawList, font, fontSize, ImVec2(position.x + (groupWidth - naturalWidth) * 0.5f, position.y), text, style, opacity);
		return;
	}
	float glyphWidthSum = 0.0f;
	const char* end = text + strlen(text);
	for (const char* cursor = text; cursor < end;) {
		unsigned int character;
		const int bytes = ImTextCharFromUtf8(&character, cursor, end);
		if (bytes <= 0) break;
		glyphWidthSum += font->CalcTextSizeA(fontSize, FLT_MAX, 0.0f, cursor, cursor + bytes).x;
		cursor += bytes;
	}
	const float freeWidth = (std::max)(0.0f, groupWidth - glyphWidthSum);
	const float edgeSpacing = freeWidth / (2.0f * (float)characterCount);
	const float innerSpacing = edgeSpacing * 2.0f;
	float x = position.x + edgeSpacing;
	for (const char* cursor = text; cursor < end;) {
		unsigned int character;
		const int bytes = ImTextCharFromUtf8(&character, cursor, end);
		if (bytes <= 0) break;
		// 单个 UTF-8 字符最长四字节，栈缓冲避免每帧逐字分配字符串。
		char glyph[5] = {};
		memcpy(glyph, cursor, bytes);
		DrawSingleRubyCharacter(drawList, font, fontSize, ImVec2(x, position.y), glyph, style, opacity);
		x += font->CalcTextSizeA(fontSize, FLT_MAX, 0.0f, glyph).x + innerSpacing;
		cursor += bytes;
	}
}

// 计算一个 Ruby 词组的位置；读音过宽时缩小并保持在所属汉字组的水平范围内。
bool GetRubyPosition(
	ImFont* font,
	float baseFontSize,
	const ImVec2& basePosition,
	const std::string& text,
	const RubySpan& span,
	ImVec2& rubyPosition,
	float& rubyFontSize,
	float& rubyGroupWidth
) {
	const KtvGeometryStyle style = { FontManager_Inst.fontSize, FontManager_Inst.strokeSize,
		FontManager_Inst.shadowOffset, 0, FontManager_Inst.lyricAtlasScale };
	if (!GetKtvRubyGeometry(font, baseFontSize, text.c_str(), span, style, rubyPosition, rubyFontSize, rubyGroupWidth))
		return false;
	rubyPosition += basePosition;
	return true;
}

// 绘制一行的全部 Ruby，并在当前演唱行按同一横向裁剪使用已唱配色。
void DrawKtvRubySpans(
	ImDrawList* drawList,
	ImFont* font,
	float baseFontSize,
	const ImVec2& basePosition,
	const LyricLine* line,
	const KtvTextStyle& beforeStyle,
	const KtvTextStyle& afterStyle,
	float wipeProgress,
	float lineWidth,
	float opacity = 1.0f
) {
	if (!line || line->rubySpans.empty())
		return;
	const ImVec2 clipMin = drawList->GetClipRectMin();
	const ImVec2 clipMax = drawList->GetClipRectMax();
	const float clipX = basePosition.x + lineWidth * wipeProgress;
	for (int pass = 0; pass < 2; pass++) {
		const bool sung = pass == 0;
		if ((sung && wipeProgress <= 0.0f) || (!sung && wipeProgress >= 1.0f)) continue;
		const bool clipped = wipeProgress > 0.0f && wipeProgress < 1.0f;
		if (clipped)
			drawList->PushClipRect(sung ? clipMin : ImVec2(clipX, clipMin.y), sung ? ImVec2(clipX, clipMax.y) : clipMax, true);
		for (const RubySpan& span : line->rubySpans) {
			ImVec2 rubyPosition;
			float rubyFontSize, rubyGroupWidth;
			if (GetRubyPosition(font, baseFontSize, basePosition, line->text, span, rubyPosition, rubyFontSize, rubyGroupWidth))
				DrawRubyText(drawList, font, rubyFontSize, rubyPosition, rubyGroupWidth, span.ruby.c_str(), sung ? afterStyle : beforeStyle, opacity);
		}
		if (clipped) drawList->PopClipRect();
	}
}

// 在歌词空档绘制放大并带描边的逐秒圆点，末尾圆点随时间淡出。
void DrawGapCountdownDots(
	ImDrawList* drawList,
	const ImVec2& viewportSize,
	long remainingMs,
	float anchorX,
	float anchorY,
	const ImVec4& color,
	float displayScale
) {
	const int maximumDots = 8;
	const float radius = 12.0f * displayScale;
	const float spacing = 42.0f * displayScale;
	if (remainingMs <= 0)
		return;
	const int dotCount = (std::min)(maximumDots, (int)((remainingMs + 999) / 1000));
	const long activeSecondMs = remainingMs % 1000;
	const float fadingOpacity = activeSecondMs == 0 ? 1.0f : (float)activeSecondMs / 1000.0f;
	const float firstX = viewportSize.x * anchorX;
	const float y = viewportSize.y * anchorY;
	for (int index = 0; index < dotCount; index++) {
		const float opacity = index == dotCount - 1 ? fadingOpacity : 1.0f;
		const ImVec2 center(firstX + spacing * index, y);
		drawList->AddCircleFilled(center, radius + 2.0f * displayScale, IM_COL32(0, 0, 0, (int)(230.0f * opacity)));
		drawList->AddCircleFilled(center, radius, ToOverlayColor(color, opacity));
	}
}

// 延迟创建可复用的整行透明合成画布。
KtvCompositeLayer& GetKtvCompositeLayer() {
	static KtvCompositeLayer layer;
	return layer;
}

// 资源只在设备或分辨率改变时创建，其余帧是固定字段比较。
void PrepareKtvCompositeResources(const ImVec2& viewportSize) {
	if (viewportSize.x > 0 && viewportSize.y > 0)
		GetKtvCompositeLayer().Prepare(g_pd3dDevice, (UINT)viewportSize.x, (UINT)viewportSize.y);
}

// 在实际 DX11 绘制阶段开始整行合成，失败时保留普通绘制并记录一次诊断。
void BeginKtvComposite(const ImDrawList*, const ImDrawCmd*) {
	static bool warned = false;
	if (!GetKtvCompositeLayer().Begin(g_pd3dDevice, g_pd3dDeviceContext) && !warned) {
		LOG(L"歌词整体透明画布创建失败，暂时使用普通绘制。");
		warned = true;
	}
}

// 回调参数存储固定精度透明度，避免引用下一帧可能失效的局部变量。
void EndKtvComposite(const ImDrawList*, const ImDrawCmd* command) {
	const float opacity = (float)(uintptr_t)command->UserCallbackData / 65535.0f;
	GetKtvCompositeLayer().End(g_pd3dDeviceContext, opacity);
}

// 根据当前窗口、字体及用户安全边距计算该句的临时字号与位置。
KtvLineGeometry GetRuntimeKtvLineGeometry(const LyricLine& line, int lane) {
	return LyricManager_Inst.GetRenderGeometry(line, lane);
}

// 切歌后重置布局及几何；容量可复用，但不能复用上一曲的结果。
void LyricManager::ClearRenderCache() {
	renderLayouts.clear();
	renderGeometries.clear();
	renderGeometryReady.clear();
	renderGeometryLanes.clear();
	renderPreCueMs = -1;
	renderFont = nullptr;
}

// 布局只依赖整首时间线和预告阈值，播放时钟改变不会使其失效。
const std::vector<KtvLineLayout>& LyricManager::GetRenderLayouts() {
	if (renderPreCueMs != ktvPreCueMs || renderLayouts.size() != lyricTimeline.size()) {
		renderLayouts = BuildKtvLineLayouts(lyricTimeline, ktvPreCueMs);
		renderPreCueMs = ktvPreCueMs;
		renderGeometryReady.assign(lyricTimeline.size(), false);
	}
	return renderLayouts;
}

// 字体、装饰、安全区、分辨率或轨道位置改变时重新测量，其余帧直接复用几何。
KtvLineGeometry LyricManager::GetRenderGeometry(const LyricLine& line, int lane) {
	const ImVec2 viewport = ImGui::GetMainViewport()->Size;
	const KtvGeometryStyle style = { FontManager_Inst.fontSize, FontManager_Inst.strokeSize,
		FontManager_Inst.shadowOffset, lyricWindowOpacity > 0 ? 18.0f : 0.0f,
		FontManager_Inst.lyricAtlasScale };
	const std::array<float, 12> settings = { viewport.x, viewport.y, style.referenceFontSize,
		(float)style.strokeSize, style.shadowOffset.x, style.shadowOffset.y, style.backgroundPadding,
		style.displayScale, ktvCurrentColumnX, ktvNextColumnX, ktvCurrentRowY, ktvNextRowY };
	// 两条轨道可以交替查询，轨道编号由每行独立保存，不参与全局失效。
	if (renderFont != FontManager_Inst.font || renderFontRevision != FontManager_Inst.atlasRevision ||
		renderGeometrySettings != settings || renderGeometries.size() != lyricTimeline.size()) {
		renderFont = FontManager_Inst.font;
		renderFontRevision = FontManager_Inst.atlasRevision;
		renderGeometrySettings = settings;
		renderGeometries.resize(lyricTimeline.size());
		renderGeometryReady.assign(lyricTimeline.size(), false);
		renderGeometryLanes.assign(lyricTimeline.size(), -1);
	}
	// 预览行不属于时间线，避免对无关对象执行指针相减。
	const auto address = reinterpret_cast<uintptr_t>(&line);
	const auto begin = reinterpret_cast<uintptr_t>(lyricTimeline.data());
	const bool inTimeline = address >= begin && address - begin < lyricTimeline.size() * sizeof(LyricLine)
		&& (address - begin) % sizeof(LyricLine) == 0;
	const size_t index = inTimeline ? (address - begin) / sizeof(LyricLine) : 0;
	if (inTimeline && renderGeometryReady[index] && renderGeometryLanes[index] == lane)
		return renderGeometries[index];
	const KtvLineGeometry geometry = GetKtvLineGeometry(FontManager_Inst.font,
		style.referenceFontSize * style.displayScale, line, style, lane,
		viewport.x * ktvCurrentColumnX, viewport.x * ktvNextColumnX,
		viewport.y * (lane == 0 ? ktvCurrentRowY : ktvNextRowY));
	if (inTimeline) {
		renderGeometries[index] = geometry;
		renderGeometryReady[index] = true;
		renderGeometryLanes[index] = lane;
	}
	return geometry;
}

// 主歌词、振假名和背景使用同一个合成层，淡出时保留已唱进度。
void DrawKtvLine(ImDrawList* drawList, const LyricLine& line, int lane, float progress, float opacity) {
	if (opacity <= 0.0f) return;
	const KtvLineGeometry geometry = GetRuntimeKtvLineGeometry(line, lane);
	if (geometry.fontSize <= 0) return;
	const float fontSize = geometry.fontSize;
	ImFont* font = FontManager_Inst.font;
	const ImVec2 size = geometry.textSize;
	const ImVec2 position = geometry.position;
	const KtvTextStyle defaultBefore = { LyricManager_Inst.ktvBeforeFillColor, LyricManager_Inst.ktvBeforeStrokeColor, LyricManager_Inst.ktvBeforeShadowColor };
	const KtvTextStyle defaultAfter = { LyricManager_Inst.ktvAfterFillColor, LyricManager_Inst.ktvAfterStrokeColor, LyricManager_Inst.ktvAfterShadowColor };
	const std::vector<std::string> identities = LyricManager_Inst.singerColorsEnabled ? line.singers : std::vector<std::string>();
	const KtvTextStyle before = ResolveSingerStyle(identities, LyricManager_Inst.singerPalettes, false, LyricManager_Inst.singerChorusGradient, defaultBefore, position.x, size.x, LyricManager_Inst.singerChorusVertical);
	const KtvTextStyle after = ResolveSingerStyle(identities, LyricManager_Inst.singerPalettes, true, LyricManager_Inst.singerChorusGradient, defaultAfter, position.x, size.x, LyricManager_Inst.singerChorusVertical);
	const bool composite = opacity < 1.0f;
	if (composite) drawList->AddCallback(BeginKtvComposite, nullptr);
	const float decorationScale = fontSize / FontManager_Inst.fontSize;
	if (LyricManager_Inst.lyricWindowOpacity > 0.0f)
		drawList->AddRectFilled(position - ImVec2(18, 10) * decorationScale, position + size + ImVec2(18, 10) * decorationScale,
			IM_COL32(0, 0, 0, (int)(LyricManager_Inst.lyricWindowOpacity * 220.0f)), 8.0f);
	DrawKtvWipeText(drawList, font, fontSize, position, size, line.text.c_str(), before, after, progress);
	DrawKtvRubySpans(drawList, font, fontSize, position, &line, before, after, progress, size.x);
	if (composite) {
		drawList->AddCallback(EndKtvComposite, (void*)(uintptr_t)(opacity * 65535.0f));
		drawList->AddCallback(ImDrawCallback_ResetRenderState, nullptr);
	}
}

void LyricManager::Init(Config& cfg) {
	if (!isInit) {
		FromConfig(cfg);
		ResetDefaultCharset();
		FontManager_Inst.reloadFonts = true;
		isInit = true;
	}
}

Config& LyricManager::FromConfig(Config& cfg) {
	lyricWindowOpacity = cfg.lyricWindowOpacity;
	showGUI = cfg.showLyricsManagerGUI;
	useExternalLyrics = cfg.useExternalLyrics;
	showInternalLyrics = cfg.showInternalLyrics;
	showLyrics = cfg.showLyrics;
	lyricDockingStyle = (LyricDockingStyle)cfg.lyricDockingStyle;
	lyricPivotStyle = (LyricPivotStyle)cfg.lyricPivotStyle;
	lyricPivotOffset = cfg.lyricPivotOffset;
	lyricFormat = cfg.lyricFormat;
	ktvBeforeFillColor = cfg.ktvBeforeFillColor;
	ktvBeforeStrokeColor = cfg.ktvBeforeStrokeColor;
	ktvBeforeShadowColor = cfg.ktvBeforeShadowColor;
	ktvAfterFillColor = cfg.ktvAfterFillColor;
	ktvAfterStrokeColor = cfg.ktvAfterStrokeColor;
	ktvAfterShadowColor = cfg.ktvAfterShadowColor;
	ktvCurrentColumnX = cfg.ktvCurrentColumnX;
	// 右侧轨道始终由左侧安全边距镜像推导，避免两侧留白不一致。
	ktvNextColumnX = 1.0f - ktvCurrentColumnX;
	ktvCurrentRowY = cfg.ktvCurrentRowY;
	ktvNextRowY = cfg.ktvNextRowY;
	ktvPreCueMs = cfg.ktvPreCueMs;
	ktvNativeWipeEstimateMs = cfg.ktvNativeWipeEstimateMs;
	ktvWipeEnabled = cfg.ktvWipeEnabled;
	ktvPreviewEnabled = cfg.ktvPreviewEnabled;
	ImGui::GetStyle().WindowBorderSize = cfg.WindowBorderSize;
	ImGui::GetStyle().WindowRounding = cfg.WindowRounding;
	LoadSingerSettings();
	return cfg;
}

Config& LyricManager::ToConfig(Config& cfg) {
	cfg.lyricWindowOpacity = lyricWindowOpacity;
	cfg.showLyricsManagerGUI = showGUI;
	cfg.useExternalLyrics = useExternalLyrics;
	cfg.showInternalLyrics = showInternalLyrics;
	cfg.showLyrics = showLyrics;
	cfg.lyricDockingStyle = lyricDockingStyle;
	cfg.lyricPivotStyle = lyricPivotStyle;
	cfg.lyricPivotOffset = lyricPivotOffset;
	cfg.lyricFormat = lyricFormat;
	cfg.ktvBeforeFillColor = ktvBeforeFillColor;
	cfg.ktvBeforeStrokeColor = ktvBeforeStrokeColor;
	cfg.ktvBeforeShadowColor = ktvBeforeShadowColor;
	cfg.ktvAfterFillColor = ktvAfterFillColor;
	cfg.ktvAfterStrokeColor = ktvAfterStrokeColor;
	cfg.ktvAfterShadowColor = ktvAfterShadowColor;
	cfg.ktvCurrentColumnX = ktvCurrentColumnX;
	// 持久化镜像值，保证旧配置与新版运行时布局保持兼容。
	cfg.ktvNextColumnX = 1.0f - ktvCurrentColumnX;
	cfg.ktvCurrentRowY = ktvCurrentRowY;
	cfg.ktvNextRowY = ktvNextRowY;
	cfg.ktvPreCueMs = ktvPreCueMs;
	cfg.ktvNativeWipeEstimateMs = ktvNativeWipeEstimateMs;
	cfg.ktvWipeEnabled = ktvWipeEnabled;
	cfg.ktvPreviewEnabled = ktvPreviewEnabled;
	cfg.WindowBorderSize = ImGui::GetStyle().WindowBorderSize;
	cfg.WindowRounding = ImGui::GetStyle().WindowRounding;
	SaveSingerSettings();
	return cfg;
}

/* Should the lyric be on screen? */
bool LyricManager::shouldShowLyrics() {
	return lyricDisplayStatus != Ended && pvsel && loadedPvid == static_cast<int>(pvsel->PVID);
}

/* The timestamp of the Ryhthm Game / PV Session in seconds. */
float LyricManager::TimeElapsed() {
	return playbackStatus->currentPlaybackTime;
}

/* Current line of lyrics being displayed. */
std::string LyricManager::GetCurrentLyricLine() {
	const LyricLine* current = FindCurrentActiveLyric(CurrentTimestampMs());
	if (current)
		return current->text;
	return {};
}

/* 将公开 SRT parser 的结果复制到项目自有时间线。 */
bool LyricManager::LoadExternalLyrics(const std::wstring& filename) {
	lyricTimeline.clear();
	currentSingerIds.clear();
	SubtitleParserFactory subParserFactory(to_utf8(filename));
	SubtitleParser* parser = subParserFactory.getParser();
	if (!parser)
		return false;

	const std::vector<SubtitleItem*> subtitles = parser->getSubtitles();
	std::wstring charsetBuffer;
	for (const SubtitleItem* subtitle : subtitles) {
		if (!subtitle)
			continue;
		LyricLine line = {
			subtitle->getStartTime(),
			subtitle->getEndTime(),
			subtitle->getText()
		};
		if (line.text.empty() || line.endMs < line.startMs)
			continue;
		charsetBuffer += to_wstr(line.text);
		lyricTimeline.push_back(line);
	}
	delete parser;

	if (lyricTimeline.empty())
		return false;
	ClearRenderCache();
	ResetDefaultCharset();
	if (FontManager_Inst.UpdateCharset(charsetBuffer))
		FontManager_Inst.reloadFonts = true;
	return true;
}

/* 读取 Ruby TSV：每条记录按 SRT 行号绑定 Unicode 字符范围与平假名读音。 */
bool LyricManager::LoadRubySidecar(const std::wstring& filename) {
	std::ifstream input(to_utf8(filename), std::ios::binary);
	if (!input.is_open())
		return false;
	std::wstring rubyCharset;
	std::string record;
	int loadedSpanCount = 0;
	while (std::getline(input, record)) {
		if (!record.empty() && record.back() == '\r')
			record.pop_back();
		if (record.empty() || record[0] == '#')
			continue;
		const size_t tab = record.find('\t');
		if (tab == std::string::npos)
			continue;
		int lineNumber = 0;
		try {
			lineNumber = std::stoi(record.substr(0, tab));
		}
		catch (const std::exception&) {
			continue;
		}
		if (lineNumber < 1 || (size_t)lineNumber > lyricTimeline.size())
			continue;
		LyricLine& lyric = lyricTimeline[(size_t)lineNumber - 1];
		const std::wstring wideText = to_wstr(lyric.text);
		std::stringstream spans(record.substr(tab + 1));
		std::string spanRecord;
		while (std::getline(spans, spanRecord, ';')) {
			const size_t firstColon = spanRecord.find(':');
			const size_t secondColon = spanRecord.find(':', firstColon == std::string::npos ? 0 : firstColon + 1);
			if (firstColon == std::string::npos || secondColon == std::string::npos)
				continue;
			try {
				RubySpan span = {
					(size_t)std::stoul(spanRecord.substr(0, firstColon)),
					(size_t)std::stoul(spanRecord.substr(firstColon + 1, secondColon - firstColon - 1)),
					spanRecord.substr(secondColon + 1)
				};
				if (span.length == 0 || span.start + span.length > wideText.size() || span.ruby.empty())
					continue;
				lyric.rubySpans.push_back(span);
				rubyCharset += to_wstr(span.ruby);
				loadedSpanCount++;
			}
			catch (const std::exception&) {
				continue;
			}
		}
	}
	if (FontManager_Inst.UpdateCharset(rubyCharset))
		FontManager_Inst.reloadFonts = true;
	LOG(L"已加载 Ruby 旁路文件：%d 个汉字词组标注。", loadedSpanCount);
	return loadedSpanCount > 0;
}

// 读取强绑定字幕时间及全文的歌手旁路，错误时不保留上一首的身份集合。
bool LyricManager::LoadSingerSidecar(const std::wstring& filename) {
    currentSingerIds.clear();
    for (auto& line : lyricTimeline) line.singers.clear();
    std::ifstream input(std::filesystem::path(filename), std::ios::binary);
    if (!input || !ReadSingerSidecar(input, loadedPvid, lyricTimeline, currentSingerIds)) return false;
    for (const auto& identity : currentSingerIds)
        if (!singerPalettes.count(identity)) singerPalettes.emplace(identity, DefaultSingerPalette(identity));
    LOG(L"已加载歌手旁路：%zu 个不同身份，%zu 行绑定完成。", currentSingerIds.size(), lyricTimeline.size());
    return true;
}

// 歌手配色使用独立文件，兼容旧配置并逐项拒绝不合法的新颜色。
void LyricManager::LoadSingerSettings() {
    singerColorsEnabled = true; singerChorusGradient = true; singerChorusVertical = true;
    singerPalettes.clear();
    for (const auto* identity : { "MIK", "RIN", "LEN", "KAI", "LUK", "MEI" })
        singerPalettes.emplace(identity, DefaultSingerPalette(identity));
    const auto path = FullPathInDllFolder(L"singer-colors.toml");
    if (!std::filesystem::exists(path)) return;
    try {
        const auto config = toml::parse(path);
        if (config.contains("enabled") && config.at("enabled").is_boolean()) singerColorsEnabled = config.at("enabled").as_boolean();
        if (config.contains("chorus_gradient") && config.at("chorus_gradient").is_boolean()) singerChorusGradient = config.at("chorus_gradient").as_boolean();
        if (config.contains("chorus_vertical") && config.at("chorus_vertical").is_boolean()) singerChorusVertical = config.at("chorus_vertical").as_boolean();
        if (!config.contains("palettes") || !config.at("palettes").is_table()) return;
        for (const auto& entry : config.at("palettes").as_table()) {
            if (!IsSingerIdentity(entry.first) || !entry.second.is_table()) continue;
            SingerPalette palette = DefaultSingerPalette(entry.first);
            ImVec4* colors[] = { &palette.beforeFill, &palette.beforeStroke, &palette.beforeShadow, &palette.afterFill, &palette.afterStroke, &palette.afterShadow };
            const char* keys[] = { "before_fill", "before_stroke", "before_shadow", "after_fill", "after_stroke", "after_shadow" };
            for (int i = 0; i < 6; ++i) {
                if (!entry.second.contains(keys[i]) || !entry.second.at(keys[i]).is_array()) continue;
                const auto& values = entry.second.at(keys[i]).as_array();
                if (values.size() != 4) continue;
                bool valid = true; float channels[4];
                for (int j = 0; j < 4; ++j) {
                    valid = valid && (values[j].is_floating() || values[j].is_integer());
                    if (valid) channels[j] = values[j].is_floating() ? (float)values[j].as_floating() : (float)values[j].as_integer();
                }
                if (valid) *colors[i] = ClampSingerColor(ImVec4(channels[0], channels[1], channels[2], channels[3]));
            }
            singerPalettes[entry.first] = palette;
        }
    } catch (const std::exception&) { LOG(L"歌手配色配置无效，使用默认歌手配色。"); }
}

// 保存歌手专用配置到临时文件后原子替换，旧歌词配置与字体设置保持独立。
bool LyricManager::SaveSingerSettings() {
    const std::wstring path = FullPathInDllFolder(L"singer-colors.toml");
    const std::wstring temporary = path + L".tmp";
    try {
        toml::value config(toml::table{});
        config["enabled"] = singerColorsEnabled; config["chorus_gradient"] = singerChorusGradient;
        config["chorus_vertical"] = singerChorusVertical;
        toml::value palettes(toml::table{});
        for (const auto& entry : singerPalettes) {
            if (!IsSingerIdentity(entry.first)) continue;
            const SingerPalette& palette = entry.second;
            const ImVec4 colors[] = { palette.beforeFill, palette.beforeStroke, palette.beforeShadow, palette.afterFill, palette.afterStroke, palette.afterShadow };
            const char* keys[] = { "before_fill", "before_stroke", "before_shadow", "after_fill", "after_stroke", "after_shadow" };
            toml::value record(toml::table{});
            for (int i = 0; i < 6; ++i) {
                const ImVec4 color = ClampSingerColor(colors[i]);
                record[keys[i]] = toml::array{ toml::value((double)color.x), toml::value((double)color.y), toml::value((double)color.z), toml::value((double)color.w) };
            }
            palettes[entry.first] = record;
        }
        config["palettes"] = palettes;
        std::ofstream output(std::filesystem::path(temporary), std::ios::binary | std::ios::trunc);
        output << toml::format(config); output.close();
        if (!output || !MoveFileExW(temporary.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
            throw std::runtime_error("保存失败");
        return true;
    } catch (const std::exception&) { LOG(L"无法保存歌手配色配置，请检查模组目录权限。"); return false; }
}

// 显示当前第一、第二及更多歌手的完整配色，提供同一生产绘制路径的即时合唱预览。
void LyricManager::DrawSingerColorPanel() {
    ImGui::Separator();
    ImGui::TextUnformatted(u8"逐行歌手颜色");
    ImGui::Checkbox(u8"启用歌手配色", &singerColorsEnabled);
    ImGui::Checkbox(u8"合唱柔和渐变（关闭为融合纯色）", &singerChorusGradient);
    if (singerChorusGradient) ImGui::Checkbox(u8"上下双色（取消为整句横向渐变）", &singerChorusVertical);
    size_t marked = 0;
    for (const auto& line : lyricTimeline) if (!line.singers.empty()) ++marked;
    ImGui::Text(u8"本曲标记：%zu / %zu 行；未识别行使用默认颜色", marked, lyricTimeline.size());
    std::vector<std::string> identities = currentSingerIds;
    if (identities.empty()) identities = { "MIK", "RIN" };
    const size_t currentCount = identities.size();
    for (const auto& entry : singerPalettes)
        if (std::find(identities.begin(), identities.end(), entry.first) == identities.end()) identities.push_back(entry.first);
    for (size_t index = 0; index < identities.size(); ++index) {
        const std::string& identity = identities[index];
        if (!singerPalettes.count(identity)) singerPalettes[identity] = DefaultSingerPalette(identity);
        std::string label = index < currentCount ? std::string(u8"歌手 ") + std::to_string(index + 1) + " · " : std::string(u8"其他歌手 · ");
        label += SingerDisplayName(identity); label += " (" + identity + ")";
        ImGui::PushID(identity.c_str());
        if (ImGui::CollapsingHeader(label.c_str(), index < 2 ? ImGuiTreeNodeFlags_DefaultOpen : 0)) {
            SingerPalette& palette = singerPalettes[identity];
            ImGui::ColorEdit4(u8"未唱填充", &palette.beforeFill.x);
            ImGui::ColorEdit4(u8"未唱描边", &palette.beforeStroke.x);
            ImGui::ColorEdit4(u8"已唱填充", &palette.afterFill.x);
            ImGui::ColorEdit4(u8"已唱描边", &palette.afterStroke.x);
            ImGui::ColorEdit4(u8"未唱阴影", &palette.beforeShadow.x);
            ImGui::ColorEdit4(u8"已唱阴影", &palette.afterShadow.x);
            if (ImGui::Button(u8"恢复此歌手默认色")) palette = DefaultSingerPalette(identity);
        }
        ImGui::PopID();
    }
    if (ImGui::Button(u8"保存歌手配色")) SaveSingerSettings();
    ImGui::SameLine();
    if (ImGui::Button(u8"重新读取歌手配色")) LoadSingerSettings();
    if (!FontManager_Inst.font) return;
    ImGui::TextUnformatted(u8"即时预览（包含未唱与已唱四色）");
    const std::vector<std::vector<std::string>> combinations = { { identities[0] }, { identities.size() > 1 ? identities[1] : identities[0] }, { identities[0], identities.size() > 1 ? identities[1] : identities[0] } };
    const char* samples[] = { u8"歌手一", u8"歌手二", u8"合唱" };
    for (int i = 0; i < 3; ++i) {
        const ImVec2 position = ImGui::GetCursorScreenPos();
        const float size = 28.0f;
        const ImVec2 textSize = FontManager_Inst.font->CalcTextSizeA(size, FLT_MAX, 0, samples[i]);
        const KtvTextStyle fallbackBefore = { ktvBeforeFillColor, ktvBeforeStrokeColor, ktvBeforeShadowColor };
        const KtvTextStyle fallbackAfter = { ktvAfterFillColor, ktvAfterStrokeColor, ktvAfterShadowColor };
        const std::vector<std::string> ids = singerColorsEnabled ? combinations[i] : std::vector<std::string>();
        const auto before = ResolveSingerStyle(ids, singerPalettes, false, singerChorusGradient, fallbackBefore, position.x, textSize.x, singerChorusVertical);
        const auto after = ResolveSingerStyle(ids, singerPalettes, true, singerChorusGradient, fallbackAfter, position.x, textSize.x, singerChorusVertical);
        DrawKtvWipeText(ImGui::GetWindowDrawList(), FontManager_Inst.font, size, position, textSize, samples[i], before, after, 0.56f);
        ImGui::Dummy(ImVec2(textSize.x + 12, size + 10));
    }
}

/* 返回应用外部字幕偏移后的播放时间。 */
long LyricManager::CurrentTimestampMs() {
	return (long)(TimeElapsed() * 1000) + exSubOffset;
}

/* 查找当前处于起止时间范围内的歌词行。 */
const LyricLine* LyricManager::FindCurrentLyric(long timestampMs) const {
	for (const LyricLine& line : lyricTimeline) {
		if (line.startMs <= timestampMs && timestampMs <= line.endMs)
			return &line;
	}
	return NULL;
}

/* 查找第一条尚未开始的歌词行。 */
const LyricLine* LyricManager::FindNextLyric(long timestampMs) const {
	for (const LyricLine& line : lyricTimeline) {
		if (line.startMs > timestampMs)
			return &line;
	}
	return NULL;
}

/* 按当前配置选择外部 SRT 或原生事件时间线。 */
const LyricLine* LyricManager::FindCurrentActiveLyric(long timestampMs) const {
	// KTV Overlay 只使用已加载的完整外部时间线，禁止回退到仅含当前句的原生事件。
	return useExternalLyrics && !lyricTimeline.empty() ? FindCurrentLyric(timestampMs) : NULL;
}

/* 按当前配置选择外部 SRT 或原生事件时间线中的下一句。 */
const LyricLine* LyricManager::FindNextActiveLyric(long timestampMs) const {
	// 没有完整缓存时不猜测下一句，防止原生事件回退破坏预告和空档状态机。
	return useExternalLyrics && !lyricTimeline.empty() ? FindNextLyric(timestampMs) : NULL;
}

/* Copies audio file name into our own buffer */
void LyricManager::SetSongAudio(const char* src) {
	if (src) songAudioName.assign(src);
}

/* Set current index of lyric and flag for line updates. */
void LyricManager::UpdateLyricIndex(int index) {
	if (lyricIndex != index)
		TraceDivaLyricChange(pvsel ? static_cast<int>(pvsel->PVID) : -1, index,
			playbackStatus ? playbackStatus->currentPlaybackTime : -1.0f, showLyrics);
	lyricIndex = index;
}

// 每次 PV 准备完成都重新绑定歌词，播放列表切歌不要求先返回选曲界面。
void LyricManager::UpdateGameState(const char* state) {
	if (!state) return;
	if (strcmp(state, "PV POST PROCESS TASK") == 0) {
		OnLyricsBegin();
	}
	else if (displayStatus == OnScreen &&
		(strcmp(state, "PVsel") == 0 || strcmp(state, "PV_STAGE") == 0 ||
		 strcmp(state, "PV_WATCH") == 0 || strcmp(state, "MAINMENU_SWITCH") == 0 ||
		 strcmp(state, "MENU") == 0 || strcmp(state, "STARTUP") == 0)) {
		OnLyricsEnd();
	}
}

void LyricManager::ResetDefaultCharset() {
	FontManager_Inst.charset.clear();
	FontManager_Inst.UpdateCharset(to_wstr(LYRIC_PLACEHOLDER_MESSAGE));
	FontManager_Inst.UpdateCharset(to_wstr(lyricFormat));
	FontManager_Inst.UpdateCharset(to_wstr(u8"歌手一歌手二合唱"));
}

// 记录每次进入 PV 时外部缓存的实际查找结果，避免仅凭画面推测 PVID 或文件命名问题。
void WriteRuntimeLyricLoadDiagnostic(int pvid, const std::wstring& filename, const char* result, size_t lineCount) {
	std::ofstream diagnostic(to_utf8(FullPathInDllFolder(L"freelyrics-runtime.log")), std::ios::app);
	if (!diagnostic.is_open())
		return;
	diagnostic << "pvid=" << pvid
		<< " result=" << result
		<< " lines=" << lineCount
		<< " path=" << to_utf8(filename)
		<< "\n";
}

// 为本次 PV 重建 SRT 与 Ruby 时间线，同曲循环也不能继承上次播放状态。
void LyricManager::OnLyricsBegin() {
	if (!pvsel || static_cast<int>(pvsel->PVID) < 0) {
		OnLyricsEnd();
		return;
	}
	loadedPvid = static_cast<int>(pvsel->PVID);
	LOG(L"开始加载 PV%d 的歌词", loadedPvid);
	lyricIndex = 0;
	lyricTimeline.clear();
	ClearRenderCache();
	currentSingerIds.clear();
	displayStatus = OnScreen;
	lyricDisplayStatus = Ready;
	if (useExternalLyrics) {
		// 只按本次准备的曲目查找外部歌词。
		wchar_t buffer[64] = { 0 };
		swprintf_s(buffer, L"PV%03d", pvsel->PVID);
		LOG(L"尝试加载外部歌词 lyrics\\%s.srt", buffer);
		std::wstring filename = FullPathInDllFolder(L"lyrics\\" + std::wstring(buffer) + L".srt");
		LOG(L"加载路径：%s", filename.c_str());
		if (!std::filesystem::exists(filename)) {
			LOG(L"未找到外部歌词文件，本首不显示外部歌词。");
			WriteRuntimeLyricLoadDiagnostic(pvsel->PVID, filename, "file_missing", 0);
		}
		else if (LoadExternalLyrics(filename)) {
			LOG(L"外部歌词已加载，共 %zu 行。", lyricTimeline.size());
			WriteRuntimeLyricLoadDiagnostic(pvsel->PVID, filename, "loaded", lyricTimeline.size());
			const std::wstring rubyFilename = FullPathInDllFolder(L"lyrics\\" + std::wstring(buffer) + L".ruby.tsv");
			if (!LoadRubySidecar(rubyFilename))
				LOG(L"未找到或未加载 Ruby 旁路文件，将仅显示主歌词。");
			const std::wstring singerFilename = FullPathInDllFolder(L"lyrics\\" + std::wstring(buffer) + L".singers.tsv");
			if (!LoadSingerSidecar(singerFilename))
				LOG(L"未加载有效歌手标记，本首未标记行使用默认颜色。");
			return;
		}
		else {
			LOG(L"外部歌词文件中没有可用的歌词行。");
			WriteRuntimeLyricLoadDiagnostic(pvsel->PVID, filename, "invalid_srt", 0);
		}
	}
	else {
		WriteRuntimeLyricLoadDiagnostic(pvsel->PVID, L"", "external_disabled", 0);
	}
	// 缺少完整缓存时不显示 KTV，无需采集游戏数据库或逐句补建图集。
}

// 在进入加载或选曲界面时清除本首歌词与曲目绑定。
void LyricManager::OnLyricsEnd() {
	currentSingerIds.clear();
	lyricTimeline.clear();
	ClearRenderCache();
	displayStatus = NoLyric;
	lyricDisplayStatus = Ended;
	lyricIndex = 0;
	loadedPvid = -1;
	LOG(L"本次 PV 歌词已清除。");
}

// PVID 可能早于加载状态改变，逐帧清除不属于当前曲目的旧时间线。
void LyricManager::OnFrame() {
	if (displayStatus == OnScreen && (!pvsel || loadedPvid != static_cast<int>(pvsel->PVID))) {
		OnLyricsEnd();
		return;
	}
	if (lyricDisplayStatus != Ended) {
		if (playbackStatus2->isPlaying) {
			lyricDisplayStatus = Progressing;
		}
		else if (lyricDisplayStatus != Ready)
			lyricDisplayStatus = Paused;
	}
}

/* Called by DX Hook's OnFrame. Do not override.*/
void LyricManager::OnImGUI() {
	if (showGUI) {
		ImGui::SetNextWindowBgAlpha(0.5);
		ImGui::Begin("Lyric [Ctrl+G]");
		ImGui::Text("Performance Metrics : %.1f FPS (%.3f ms)", ImGui::GetIO().Framerate, 1000.0f / ImGui::GetIO().Framerate);

		ImGui::Separator();
		if (shouldShowLyrics()) {
			ImGui::Text("Now Playing PVID: PV%03d (on %s)", pvsel->PVID, pvsel->getGameDifficultyString());
			ImGui::PushFont(FontManager_Inst.font);
			ImGui::Text("%s", PVWaitScreenInfo->Name.c_str());
			ImGui::PopFont();
			ImGui::Separator();
			ImGui::Text("Music/%s MV/%s Lyrics/%s",
				PVWaitScreenInfo->Music.c_str(),
				PVWaitScreenInfo->MusicVideo.c_str(),
				PVWaitScreenInfo->Lyrics.c_str()
			);
			ImGui::Text("Arranger/%s Manipulator/%s PV/%s Guitar/%s",
				PVWaitScreenInfo->Arranger.c_str(),
				PVWaitScreenInfo->Manipulator.c_str(),
				PVWaitScreenInfo->PV.c_str(),
				PVWaitScreenInfo->GuitarPlayer.c_str()
			);
			ImGui::Separator();
			ImGui::Text(
				"Audio %s",
				songAudioName.c_str()
			);
			ImGui::Text(
				"LyricId:%d Evt:%d Type:%s Time:%.2f s",
				lyricIndex,
				playbackStatus->evtNumber,
				pvsel->getGameModeString(),
				TimeElapsed()
			);
			if (!lyricTimeline.empty()) {
				ImGui::Text(
					"Using External Lyrics (%d lines)",
					lyricTimeline.size()
				);
				ImGui::Separator();
				ImGui::SliderInt("Time Offset (ms)", (int*)&exSubOffset, -5000, 5000);
			}
		}
		else {
			ImGui::Text("No Lyric");
		}
		ImGui::Separator();
		ImGui::Text("Window Styling");
		ImGui::SliderFloat("Opacity", &lyricWindowOpacity, 0.0f, 1.0f, "%.1f");
		ImGuiStyle& style = ImGui::GetStyle();
		ImGui::Text("Borders");
		ImGui::SliderFloat("WindowBorderSize", &style.WindowBorderSize, 0.0f, 10.0f, "%.0f");
		ImGui::Text("Rounding");
		ImGui::SliderFloat("WindowRounding", &style.WindowRounding, 0.0f, 12.0f, "%.0f");
		ImGui::Separator();
		ImGui::Checkbox("Attempt to load (and use) external SubRip Lyrics (applies on song start)", &useExternalLyrics);
		ImGui::Checkbox("Show game lyrics", &showInternalLyrics);
		ImGui::SameLine();
		ImGui::Checkbox("Show lyrics", &showLyrics);
		ImGui::Separator();
		ImGui::Text("KTV Wipe Style");
		ImGui::Checkbox("Enable left-to-right wipe", &ktvWipeEnabled);
		ImGui::Checkbox("Show fixed KTV layout preview (no PV required)", &ktvPreviewEnabled);
		ImGui::SliderInt("Native wipe estimate (ms)", &ktvNativeWipeEstimateMs, 500, 10000);
		ImGui::SliderFloat("Side margin X (mirrored)", &ktvCurrentColumnX, 0.0f, 0.45f, "%.2f");
		ktvNextColumnX = 1.0f - ktvCurrentColumnX;
		ImGui::SliderFloat("Upper lane Y", &ktvCurrentRowY, 0.0f, 1.0f, "%.2f");
		ImGui::SliderFloat("Lower lane Y", &ktvNextRowY, 0.0f, 1.0f, "%.2f");
		ImGui::ColorEdit4("Before fill", (float*)&ktvBeforeFillColor);
		ImGui::ColorEdit4("Before stroke", (float*)&ktvBeforeStrokeColor);
		ImGui::ColorEdit4("Before shadow", (float*)&ktvBeforeShadowColor);
		ImGui::ColorEdit4("After fill", (float*)&ktvAfterFillColor);
		ImGui::ColorEdit4("After stroke", (float*)&ktvAfterStrokeColor);
		ImGui::ColorEdit4("After shadow", (float*)&ktvAfterShadowColor);
		DrawSingerColorPanel();
		ImGui::Separator();
		ImGui::Text("Lyric Format");
		ImGui::PushFont(FontManager_Inst.font);
		ImGui::InputText("##", &lyricFormat);
		ImGui::PopFont();
		if (ImGui::Button("Force Build Font For Format"))
			if (FontManager_Inst.UpdateCharset(to_wstr(lyricFormat)))
				FontManager_Inst.reloadFonts = true;
		ImGui::Text("Docking (Automatic Alignment)");
		if (ImGui::Button("Free")) {
			lyricDockingStyle = Free;
			lyricPivotStyle = NotSet;
		}
		ImGui::SameLine();
		if (ImGui::Button("H.Center"))
			lyricDockingStyle |= HorizontallyCentered;
		ImGui::SameLine();
		if (ImGui::Button("V.Center"))
			lyricDockingStyle |= VerticallyCentered;
		ImGui::Separator();
		if (lyricDockingStyle == Free) {
			ImGui::Text("Pivioting");
			int prev = lyricPivotStyle;
			ImGui::Separator();
			if (ImGui_CursorButton("Top Left", ImGuiMouseCursor_ResizeNESW, true, false))
				lyricPivotStyle = TopLeft;
			ImGui::SameLine();
			if (ImGui_CursorButton("Top Right", ImGuiMouseCursor_ResizeNESW, false, false))
				lyricPivotStyle = TopRight;
			if (ImGui_CursorButton("Bottom Left", ImGuiMouseCursor_ResizeNESW, true, true))
				lyricPivotStyle = BottomLeft;
			ImGui::SameLine();
			if (ImGui_CursorButton("Bottom Right", ImGuiMouseCursor_ResizeNESW, false, true))
				lyricPivotStyle = BottomRight;
			if (prev != lyricPivotStyle) lyricPivotOffset = ImVec2();
			ImGui::Separator();
		}
		SHOW_WINDOW_SAVE_SELECTOR;
		ImGui::End();
	}
	if (showLyrics && shouldShowLyrics() && FontManager_Inst.font) {
		const long timestampMs = CurrentTimestampMs();
		ImDrawList* drawList = ImGui::GetForegroundDrawList();
		const LyricLine* current = FindCurrentActiveLyric(timestampMs);
		const LyricLine* next = FindNextActiveLyric(timestampMs);
		const std::vector<KtvLineLayout>& layouts = GetRenderLayouts();
		if (next && !layouts.empty() && ShouldDrawKtvCountdown(current != nullptr, next->startMs - timestampMs)) {
			const int nextLane = layouts[(size_t)(next - lyricTimeline.data())].lane;
			const ImVec2 viewport = ImGui::GetMainViewport()->Size;
			const ImVec2 nextPosition = GetRuntimeKtvLineGeometry(*next, nextLane).position;
			const float dotsX = GetKtvCountdownFirstX(nextPosition.x, viewport.x * ktvCurrentColumnX,
				viewport.x * ktvNextColumnX, FontManager_Inst.lyricAtlasScale);
			DrawGapCountdownDots(drawList, ImGui::GetMainViewport()->Size, next->startMs - timestampMs,
				dotsX / viewport.x, GetKtvCountdownRowY(nextLane, ktvCurrentRowY, ktvNextRowY),
				ktvBeforeFillColor, FontManager_Inst.lyricAtlasScale);
		}
		// 每条歌词按自己的时间窗口绘制，不再在“当前句”变化时替换旧句或重置颜色。
		if (useExternalLyrics) {
			for (size_t index = 0; index < lyricTimeline.size(); index++) {
				const LyricLine& line = lyricTimeline[index];
				const KtvLineLayout& layout = layouts[index];
				const float opacity = GetLyricFadeOpacity(timestampMs, layout.fadeInStartMs, line.endMs, layout.nextSameLaneStartMs);
				if (opacity <= 0.0f) continue;
				const float progress = ktvWipeEnabled ? GetKtvWipeProgress(timestampMs, line.startMs, line.endMs) : 0.0f;
				DrawKtvLine(drawList, line, layout.lane, progress, opacity);
			}
		}
		// 只有没有真实歌词缓存时使用示例，长伴奏段不插入预览歌词。
		if (ktvPreviewEnabled && (!useExternalLyrics || lyricTimeline.empty())) {
			const LyricLine previewCurrent = { 0, 1, u8"ここから始まる歌", {} };
			const LyricLine previewNext = { 0, 1, u8"やっぱ１番好き", {} };
			DrawKtvLine(drawList, previewCurrent, 0, ktvWipeEnabled ? 0.56f : 0.0f, 1.0f);
			DrawKtvLine(drawList, previewNext, 1, 0.0f, 1.0f);
		}
	}
}
// 延后歌词管理器的实际构造，确保它不在 Windows loader lock 内运行。
LyricManager& GetLyricManager() {
	static LyricManager manager;
	return manager;
}
