#pragma once
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <imgui.h>
#include <imgui_internal.h>

// 测量与绘制共用的装饰尺寸，字号只作用于单句，不修改字体配置或图集。
struct KtvGeometryStyle {
    // 用户设置的基准字号，用于同比缩放描边和阴影。
    float referenceFontSize;
    // 基准字号下的描边像素。
    int strokeSize;
    // 基准字号下的阴影偏移。
    ImVec2 shadowOffset;
    // 启用背景时为正文两侧保留的基准像素。
    float backgroundPadding;
    // 输出分辨率相对 1080p 的倍率。
    float displayScale;
};

// 一行在当前字体及安全区下的最终几何信息，预告和演唱复用同一算法。
struct KtvLineGeometry {
    // 该句临时使用的有效字号。
    float fontSize;
    // 字形推进宽度与正文高度，用于整句ワイプ。
    ImVec2 textSize;
    // 正文绘制起点。
    ImVec2 position;
    // 包含正文、Ruby、描边、阴影及背景的相对包围盒。
    ImVec4 bounds;
};

// 合并两个相对包围盒，包含字形向左或向右伸出的部分。
inline ImVec4 UnionKtvBounds(const ImVec4& a, const ImVec4& b) {
    return ImVec4((std::min)(a.x, b.x), (std::min)(a.y, b.y),
        (std::max)(a.z, b.z), (std::max)(a.w, b.w));
}

// 按 ImGui 实际字形及推进距离测量文本，包括斜体字形的越界边缘。
inline ImVec4 MeasureKtvTextBounds(ImFont* font, float fontSize, const char* text) {
    const ImVec2 nominal = font->CalcTextSizeA(fontSize, FLT_MAX, 0.0f, text);
    ImVec4 result(0, 0, nominal.x, nominal.y);
    const float scale = fontSize / font->FontSize;
    float x = 0, y = 0;
    const char* end = text + strlen(text);
    while (text < end) {
        unsigned int character;
        const int bytes = ImTextCharFromUtf8(&character, text, end);
        if (bytes <= 0) break;
        text += bytes;
        if (character == '\r') continue;
        if (character == '\n') { x = 0; y += fontSize; continue; }
        const ImFontGlyph* glyph = font->FindGlyph((ImWchar)character);
        if (!glyph) continue;
        if (glyph->Visible)
            result = UnionKtvBounds(result, ImVec4(x + glyph->X0 * scale, y + glyph->Y0 * scale,
                x + glyph->X1 * scale, y + glyph->Y1 * scale));
        x += glyph->AdvanceX * scale;
    }
    return result;
}

// 加入与实际绘制一致的描边整数取整和阴影偏移。
inline ImVec4 DecorateKtvBounds(const ImVec4& ink, float fontSize, const KtvGeometryStyle& style, bool ruby) {
    const float scale = fontSize / style.referenceFontSize;
    const float outline = (float)(std::max)(1, (int)roundf(style.strokeSize * scale * (ruby ? 0.5f : 1.0f)));
    const float shadowScale = scale * (ruby ? 0.45f : 1.0f);
    const float dx = style.shadowOffset.x * shadowScale;
    const float dy = style.shadowOffset.y * shadowScale;
    return UnionKtvBounds(ImVec4(ink.x - outline, ink.y - outline, ink.z + outline, ink.w + outline),
        ImVec4(ink.x + dx, ink.y + dy, ink.z + dx, ink.w + dy));
}

// 将旁路 Ruby 的 UTF-16 字符下标定位到 UTF-8 边界，不在代理对中间拆字符。
inline const char* FindKtvUtf8Boundary(const char* text, size_t utf16Index) {
    size_t index = 0;
    const char* end = text + strlen(text);
    while (text < end && index < utf16Index) {
        unsigned int character;
        const int bytes = ImTextCharFromUtf8(&character, text, end);
        if (bytes <= 0) return nullptr;
        index += character > 0xffff ? 2 : 1;
        text += bytes;
    }
    return index == utf16Index ? text : nullptr;
}

// 按所属汉字词组的实际推进宽度计算 Ruby，测量和绘制共享这一结果。
template<class Span>
bool GetKtvRubyGeometry(ImFont* font, float baseFontSize, const char* text, const Span& span,
    const KtvGeometryStyle& style, ImVec2& position, float& fontSize, float& groupWidth) {
    if (!span.length || span.ruby.empty()) return false;
    const char* begin = FindKtvUtf8Boundary(text, span.start);
    const char* end = FindKtvUtf8Boundary(text, span.start + span.length);
    if (!begin || !end) return false;
    const float prefixWidth = font->CalcTextSizeA(baseFontSize, FLT_MAX, 0, text, begin).x;
    groupWidth = font->CalcTextSizeA(baseFontSize, FLT_MAX, 0, begin, end).x;
    const float desiredSize = baseFontSize * 0.42f;
    const float desiredWidth = font->CalcTextSizeA(desiredSize, FLT_MAX, 0, span.ruby.c_str()).x;
    if (groupWidth <= 0 || desiredWidth <= 0) return false;
    fontSize = desiredSize * (std::min)(1.0f, groupWidth / desiredWidth);
    position = ImVec2(prefixWidth, -fontSize - 6.0f * baseFontSize / style.referenceFontSize);
    return true;
}

// 测量整句与全部振假名的装饰包围盒，预留背景的实际左右边缘。
template<class Line>
ImVec4 MeasureKtvLineBounds(ImFont* font, float fontSize, const Line& line, const KtvGeometryStyle& style) {
    ImVec4 bounds = DecorateKtvBounds(MeasureKtvTextBounds(font, fontSize, line.text.c_str()), fontSize, style, false);
    for (const auto& span : line.rubySpans) {
        ImVec2 rubyPosition;
        float rubySize, groupWidth;
        if (!GetKtvRubyGeometry(font, fontSize, line.text.c_str(), span, style, rubyPosition, rubySize, groupWidth)) continue;
        const ImVec4 ink = MeasureKtvTextBounds(font, rubySize, span.ruby.c_str());
        const float naturalWidth = font->CalcTextSizeA(rubySize, FLT_MAX, 0, span.ruby.c_str()).x;
        // Ruby 可以在词组内分布，保守覆盖整个词组并包含首尾字形的伸出。
        const ImVec4 groupInk((std::min)(0.0f, ink.x), ink.y,
            groupWidth + (std::max)(0.0f, ink.z - naturalWidth), ink.w);
        ImVec4 decorated = DecorateKtvBounds(groupInk, rubySize, style, true);
        decorated.x += rubyPosition.x; decorated.z += rubyPosition.x;
        decorated.y += rubyPosition.y; decorated.w += rubyPosition.y;
        bounds = UnionKtvBounds(bounds, decorated);
    }
    if (style.backgroundPadding > 0) {
        const ImVec2 nominal = font->CalcTextSizeA(fontSize, FLT_MAX, 0, line.text.c_str());
        const float padding = style.backgroundPadding * fontSize / style.referenceFontSize;
        bounds.x = (std::min)(bounds.x, -padding);
        bounds.z = (std::max)(bounds.z, nominal.x + padding);
    }
    return bounds;
}

// 根据安全区为单句临时缩字号，普通句保持原字号，上下轨共享相同宽度上限。
template<class Line>
KtvLineGeometry GetKtvLineGeometry(ImFont* font, float requestedFontSize, const Line& line,
    const KtvGeometryStyle& style, int lane, float safeLeftX, float safeRightX, float rowY) {
    KtvLineGeometry result = {};
    const float inset = (std::max)(1.0f, style.displayScale);
    const float availableWidth = safeRightX - safeLeftX - 2 * inset;
    if (!font || requestedFontSize <= 0 || style.referenceFontSize <= 0 || availableWidth <= 0) return result;
    result.fontSize = requestedFontSize;
    for (int attempt = 0; attempt < 8; attempt++) {
        result.bounds = MeasureKtvLineBounds(font, result.fontSize, line, style);
        const float width = result.bounds.z - result.bounds.x;
        if (width <= availableWidth) break;
        result.fontSize *= availableWidth / width * 0.999f;
    }
    result.bounds = MeasureKtvLineBounds(font, result.fontSize, line, style);
    result.textSize = font->CalcTextSizeA(result.fontSize, FLT_MAX, 0, line.text.c_str());
    result.position = ImVec2(lane == 0 ? safeLeftX + inset - result.bounds.x
        : safeRightX - inset - result.bounds.z, rowY);
    return result;
}
