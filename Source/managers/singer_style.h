#pragma once
#include <imgui.h>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

// 每个歌手独立保留未唱/已唱的填充、描边和阴影，四色为核心、阴影兼容现有功能。
struct SingerPalette {
    ImVec4 beforeFill, beforeStroke, beforeShadow;
    ImVec4 afterFill, afterStroke, afterShadow;
};

// 一层文字的颜色，以及跨整行共享的合唱渐变端点。
struct KtvTextStyle {
    ImVec4 fill, stroke, shadow;
    std::vector<ImVec4> fillStops, strokeStops, shadowStops;
    float gradientX = 0.0f, gradientWidth = 0.0f;
    // 上下渐变按每次文本绘制的实际字形高度取色；旧横向模式仍可切换。
    bool verticalGradient = false;
};

// 将色彩限制到有限合法范围，防止损坏配置生成非法顶点颜色。
inline ImVec4 ClampSingerColor(ImVec4 color) {
    float* values = &color.x;
    for (int i = 0; i < 4; ++i) values[i] = std::isfinite(values[i]) ? (std::max)(0.0f, (std::min)(1.0f, values[i])) : 1.0f;
    return color;
}

// 两端保持原色，中间按指定比例柔和过渡；横向30%、上下20%，多人沿相邻颜色扩展。
inline ImVec4 SampleSingerGradient(const std::vector<ImVec4>& stops, float position, float transition = 0.30f) {
    if (stops.empty()) return ImVec4(1, 1, 1, 1);
    if (stops.size() == 1) return stops[0];
    const float scaled = (std::max)(0.0f, (std::min)(1.0f, position)) * (float)(stops.size() - 1);
    const size_t left = (std::min)((size_t)scaled, stops.size() - 2);
    transition = (std::max)(0.01f, (std::min)(1.0f, transition));
    float t = (scaled - (float)left - (0.5f - transition * 0.5f)) / transition;
    t = (std::max)(0.0f, (std::min)(1.0f, t));
    t = t * t * (3.0f - 2.0f * t);
    const ImVec4& a = stops[left]; const ImVec4& b = stops[left + 1];
    return ImVec4(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t, a.w + (b.w - a.w) * t);
}

// 只给本次字形新增的顶点着色，保留纹理UV和字体覆盖率；不依赖字体格式。
inline void ApplySingerVertexGradient(ImDrawList* list, int firstVertex, const std::vector<ImVec4>& stops, float origin, float width, float opacity) {
    if (stops.size() < 2 || width <= 0) return;
    for (int i = firstVertex; i < list->VtxBuffer.Size; ++i) {
        ImDrawVert& vertex = list->VtxBuffer[i];
        ImVec4 color = ClampSingerColor(SampleSingerGradient(stops, (vertex.pos.x - origin) / width));
        color.w *= opacity;
        vertex.col = ImGui::ColorConvertFloat4ToU32(color);
    }
}

// 关闭渐变时平均融合全部参与者的同一颜色层，不能只取三人组合的中间歌手。
inline ImVec4 BlendSingerColors(const std::vector<ImVec4>& colors) {
    if (colors.empty()) return ImVec4(1, 1, 1, 1);
    ImVec4 result(0, 0, 0, 0);
    for (const auto& color : colors) { result.x += color.x; result.y += color.y; result.z += color.z; result.w += color.w; }
    const float count = (float)colors.size();
    return ImVec4(result.x / count, result.y / count, result.z / count, result.w / count);
}

// 歌手身份限定为安全的简短ASCII标识；可扩展自定义角色，而不限定六人。
inline bool IsSingerIdentity(const std::string& name) {
    if (name.empty() || name.size() > 32 || name[0] < 'A' || name[0] > 'Z') return false;
    for (char ch : name) if (!(ch >= 'A' && ch <= 'Z') && !(ch >= '0' && ch <= '9') && ch != '_') return false;
    return true;
}

// 为常见角色提供辨识明显的默认色，其他身份采用通用紫色而非写死曲目或槽位。
inline SingerPalette DefaultSingerPalette(const std::string& identity) {
    ImVec4 accent(0.65f, 0.4f, 1.0f, 1.0f);
    if (identity == "MIK") accent = ImVec4(0.12f, 0.88f, 0.76f, 1);
    else if (identity == "RIN") accent = ImVec4(1.0f, 0.64f, 0.10f, 1);
    else if (identity == "LEN") accent = ImVec4(1.0f, 0.88f, 0.10f, 1);
    else if (identity == "KAI") accent = ImVec4(0.22f, 0.55f, 1.0f, 1);
    else if (identity == "LUK") accent = ImVec4(1.0f, 0.42f, 0.66f, 1);
    else if (identity == "MEI") accent = ImVec4(1.0f, 0.23f, 0.23f, 1);
    return { ImVec4(0.85f + accent.x * 0.15f, 0.85f + accent.y * 0.15f, 0.85f + accent.z * 0.15f, 1),
        ImVec4(accent.x * 0.16f, accent.y * 0.16f, accent.z * 0.16f, 1), ImVec4(0, 0, 0, 0.5f),
        accent, ImVec4(1, 1, 1, 1), ImVec4(accent.x * 0.2f, accent.y * 0.2f, accent.z * 0.2f, 0.75f) };
}

// 用中文显示常见身份，未知身份仍显示原标识，便于多角色扩展。
inline const char* SingerDisplayName(const std::string& identity) {
    if (identity == "MIK") return u8"初音";
    if (identity == "RIN") return u8"镜音铃";
    if (identity == "LEN") return u8"镜音连";
    if (identity == "KAI") return "KAITO";
    if (identity == "LUK") return u8"巡音";
    if (identity == "MEI") return "MEIKO";
    return identity.c_str();
}

// 根据行内身份组合构建单人或合唱样式；未标记行直接沿用旧配色。
inline KtvTextStyle ResolveSingerStyle(const std::vector<std::string>& identities, const std::map<std::string, SingerPalette>& palettes, bool after, bool gradient, const KtvTextStyle& fallback, float x, float width, bool vertical = false) {
    KtvTextStyle style = fallback;
    style.verticalGradient = vertical;
    std::vector<std::string> seen;
    for (const auto& identity : identities) {
        if (std::find(seen.begin(), seen.end(), identity) != seen.end()) continue;
        seen.push_back(identity);
        const auto found = palettes.find(identity);
        const SingerPalette palette = found != palettes.end() ? found->second : DefaultSingerPalette(identity);
        style.fillStops.push_back(after ? palette.afterFill : palette.beforeFill);
        style.strokeStops.push_back(after ? palette.afterStroke : palette.beforeStroke);
        style.shadowStops.push_back(after ? palette.afterShadow : palette.beforeShadow);
    }
    if (seen.empty()) return fallback;
    style.fill = BlendSingerColors(style.fillStops);
    style.stroke = BlendSingerColors(style.strokeStops);
    style.shadow = BlendSingerColors(style.shadowStops);
    style.gradientX = x; style.gradientWidth = width;
    if (!gradient || seen.size() < 2) { style.fillStops.clear(); style.strokeStops.clear(); style.shadowStops.clear(); }
    return style;
}

// 数字必须完整解析，拒绝带后缀的行号和时间，确保旁路格式严格。
inline long ParseSingerInteger(const std::string& value) {
    size_t consumed = 0;
    const long number = std::stol(value, &consumed);
    if (consumed != value.size()) throw std::runtime_error("歌手旁路数字格式无效");
    return number;
}

// 严格绑定全部行的时间和全文；任一不匹配整份旁路失效，避免歌词串曲或错行染色。
template<class Line> inline bool ReadSingerSidecar(std::istream& input, int pvId, std::vector<Line>& lines, std::vector<std::string>& available) {
    std::string record;
    if (!std::getline(input, record)) return false;
    if (!record.empty() && record.back() == '\r') record.pop_back();
    std::stringstream header(record);
    std::string marker, version, trailing; int identity = -1; size_t count = 0;
    if (!(header >> marker >> version >> identity >> count) || marker != "#" || version != "singers-v1" || (header >> trailing)) return false;
    if (identity != pvId || count != lines.size()) return false;
    std::vector<std::vector<std::string>> parsed(lines.size());
    std::vector<bool> seen(lines.size(), false);
    std::vector<std::string> roles;
    try {
        while (std::getline(input, record)) {
            if (!record.empty() && record.back() == '\r') record.pop_back();
            if (record.empty()) continue;
            if (record.rfind("# performer\t", 0) == 0) {
                const size_t last = record.find_last_of('\t');
                const std::string role = record.substr(last + 1);
                if (!IsSingerIdentity(role)) return false;
                if (std::find(roles.begin(), roles.end(), role) == roles.end()) roles.push_back(role);
                continue;
            }
            if (record[0] == '#') continue;
            std::vector<std::string> fields; size_t start = 0;
            for (int column = 0; column < 4; ++column) {
                const size_t tab = record.find('\t', start);
                if (tab == std::string::npos) return false;
                fields.push_back(record.substr(start, tab - start)); start = tab + 1;
            }
            const size_t number = (size_t)ParseSingerInteger(fields[0]);
            if (!number || number > lines.size() || seen[number - 1]) return false;
            const Line& line = lines[number - 1];
            if (ParseSingerInteger(fields[1]) != line.startMs || ParseSingerInteger(fields[2]) != line.endMs || record.substr(start) != line.text) return false;
            seen[number - 1] = true;
            if (fields[3] == "-") continue;
            std::stringstream names(fields[3]); std::string name;
            while (std::getline(names, name, ',')) {
                if (!IsSingerIdentity(name)) return false;
                if (std::find(parsed[number - 1].begin(), parsed[number - 1].end(), name) == parsed[number - 1].end()) parsed[number - 1].push_back(name);
                if (std::find(roles.begin(), roles.end(), name) == roles.end()) roles.push_back(name);
            }
        }
    } catch (const std::exception&) { return false; }
    if (std::find(seen.begin(), seen.end(), false) != seen.end()) return false;
    for (size_t i = 0; i < lines.size(); ++i) lines[i].singers = parsed[i];
    available = roles;
    return true;
}
