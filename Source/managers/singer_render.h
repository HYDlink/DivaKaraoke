#pragma once
#include "singer_style.h"
#include "ktv_geometry.h"

// 测量可见字形真实上下边界，排除字体行高空白；正文和每段注音独立测量。
inline ImVec2 GetSingerInkY(ImFont* font, float size, const char* text, float positionY) {
    float low = FLT_MAX, high = -FLT_MAX, lineY = std::floor(positionY);
    const float scale = size / font->FontSize;
    const char* end = text + strlen(text);
    while (text < end) {
        unsigned int character;
        const int bytes = ImTextCharFromUtf8(&character, text, end);
        if (bytes <= 0) break;
        text += bytes;
        if (character == '\n') { lineY += size; continue; }
        if (character == '\r') continue;
        const ImFontGlyph* glyph = font->FindGlyph((ImWchar)character);
        if (!glyph || !glyph->Visible) continue;
        low = (std::min)(low, lineY + glyph->Y0 * scale);
        high = (std::max)(high, lineY + glyph->Y1 * scale);
    }
    return ImVec2(low, high);
}

// 使用现有字体的精细裁剪生成不重叠色带，自动插值UV；中间20%以四段近似柔和过渡。
inline void AddSingerVerticalText(ImDrawList* list, ImFont* font, float size, const ImVec2& position,
    const char* text, const std::vector<ImVec4>& stops, float opacity) {
    const ImVec2 ink = GetSingerInkY(font, size, text, position.y);
    const float height = ink.y - ink.x;
    if (!(height > 0)) return;
    std::vector<float> boundaries = { 0.0f };
    const float pairs = (float)(stops.size() - 1);
    for (size_t pair = 0; pair + 1 < stops.size(); ++pair)
        for (int step = 0; step <= 4; ++step)
            boundaries.push_back(((float)pair + 0.40f + 0.05f * step) / pairs);
    boundaries.push_back(1.0f);
    const ImVec2 clipMin = list->GetClipRectMin(), clipMax = list->GetClipRectMax();
    for (size_t band = 1; band < boundaries.size(); ++band) {
        const ImVec4 clip(clipMin.x, (std::max)(clipMin.y, ink.x + height * boundaries[band - 1]),
            clipMax.x, (std::min)(clipMax.y, ink.x + height * boundaries[band]));
        if (clip.y >= clip.w || clip.x >= clip.z) continue;
        const int first = list->VtxBuffer.Size;
        list->AddText(font, size, position, IM_COL32_WHITE, text, nullptr, 0.0f, &clip);
        for (int index = first; index < list->VtxBuffer.Size; ++index) {
            ImDrawVert& vertex = list->VtxBuffer[index];
            ImVec4 color = ClampSingerColor(SampleSingerGradient(stops, (vertex.pos.y - ink.x) / height, 0.20f));
            color.w *= opacity;
            vertex.col = ImGui::ColorConvertFloat4ToU32(color);
        }
    }
}

// 三种文字层共享此入口：等色端点走原绘制，合唱按选择使用上下或整句横向渐变。
inline void AddSingerStyledText(ImDrawList* list, ImFont* font, float size, const ImVec2& position,
    const char* text, const KtvTextStyle& style, int layer, float opacity) {
    const ImVec4 color = layer == 0 ? style.fill : layer == 1 ? style.stroke : style.shadow;
    const auto& stops = layer == 0 ? style.fillStops : layer == 1 ? style.strokeStops : style.shadowStops;
    bool different = false;
    for (const auto& stop : stops)
        different = different || stop.x != stops.front().x || stop.y != stops.front().y || stop.z != stops.front().z || stop.w != stops.front().w;
    if (different && style.verticalGradient) {
        AddSingerVerticalText(list, font, size, position, text, stops, opacity);
        return;
    }
    const int first = list->VtxBuffer.Size;
    ImVec4 solid = ClampSingerColor(color); solid.w *= opacity;
    list->AddText(font, size, position, different ? IM_COL32_WHITE : ImGui::ColorConvertFloat4ToU32(solid), text);
    if (different) ApplySingerVertexGradient(list, first, stops, style.gradientX, style.gradientWidth, opacity);
}
