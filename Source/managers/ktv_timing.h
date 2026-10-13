#pragma once
#include <algorithm>
#include <climits>
#include <vector>

constexpr long KTV_POST_LINE_HOLD_MS = 1500;
constexpr long KTV_LINE_FADE_MS = 500;
constexpr long KTV_GAP_PREVIEW_MS = 6000;

// 通常保留 1.5 秒；密集短句给同轨新句的淡出和淡入各留半秒，避免漏句。
inline long GetKtvFadeOutStart(long endMs, long nextSameLaneStartMs = LONG_MAX) {
    const long hold = nextSameLaneStartMs == LONG_MAX ? KTV_POST_LINE_HOLD_MS
        : (std::max)(0L, (std::min)(KTV_POST_LINE_HOLD_MS, nextSameLaneStartMs - endMs - 2 * KTV_LINE_FADE_MS));
    return endMs + hold;
}

// 从播放时间计算整行透明度，淡入淡出都只改变透明度，不改变已唱颜色。
inline float GetLyricFadeOpacity(long timestampMs, long fadeInStartMs, long endMs, long nextSameLaneStartMs = LONG_MAX) {
    const long fadeOutStart = GetKtvFadeOutStart(endMs, nextSameLaneStartMs);
    if (timestampMs < fadeInStartMs || timestampMs >= fadeOutStart + KTV_LINE_FADE_MS) return 0.0f;
    const float fadeIn = (float)(timestampMs - fadeInStartMs) / KTV_LINE_FADE_MS;
    const float fadeOut = (float)(fadeOutStart + KTV_LINE_FADE_MS - timestampMs) / KTV_LINE_FADE_MS;
    return (std::min)(1.0f, (std::min)(fadeIn, fadeOut));
}

// 连续两句一起预显示；同轨旧句淡出完成后，才开始新句的半秒淡入。
inline long GetKtvFadeInStart(long startMs, bool nearbyPrevious, long previousFadeInStart,
    bool hasSameLanePrevious, long sameLanePreviousEndMs) {
    long result = nearbyPrevious ? previousFadeInStart : (std::max)(0L, startMs - KTV_GAP_PREVIEW_MS);
    if (hasSameLanePrevious)
        result = (std::max)(result, GetKtvFadeOutStart(sameLanePreviousEndMs, startMs) + KTV_LINE_FADE_MS);
    return result;
}

// 仅在空档最后六秒绘制提示点，短空档沿用原有逐秒提示。
inline bool ShouldDrawKtvCountdown(bool hasCurrent, long remainingMs) {
    return !hasCurrent && remainingMs > 0 && remainingMs <= KTV_GAP_PREVIEW_MS;
}

// 已结束的歌词保持完全已唱状态，淡出不会重新显示未唱颜色。
inline float GetKtvWipeProgress(long timestampMs, long startMs, long endMs) {
    if (endMs <= startMs) return timestampMs >= startMs ? 1.0f : 0.0f;
    return (std::max)(0.0f, (std::min)(1.0f, (float)(timestampMs - startMs) / (float)(endMs - startMs)));
}

// 预告六秒与旧句两秒的显示窗口不相交时，按长间奏划分新的歌词段落。
inline bool IsKtvParagraphBreak(long startMs, long previousEndMs) {
    return startMs - previousEndMs >= KTV_GAP_PREVIEW_MS + KTV_POST_LINE_HOLD_MS + KTV_LINE_FADE_MS;
}

// 每句布局由完整时间线推导，倒放或跳转不依赖前一帧的轨道状态。
struct KtvLineLayout {
    // 0 为左上轨，1 为右下轨。
    int lane;
    // 开始整体淡入的时间。
    long fadeInStartMs;
    // 下一条占用同一轨道的歌词起唱时间。
    long nextSameLaneStartMs;
};

// 时间线提供每句起止毫秒；相邻阈值只控制预显示衔接，长间奏后首句固定回上轨。
template<class Line>
std::vector<KtvLineLayout> BuildKtvLineLayouts(const std::vector<Line>& timeline, long nearbyThresholdMs) {
    std::vector<KtvLineLayout> layouts;
    layouts.reserve(timeline.size());
    const size_t missing = timeline.size();
    size_t previousInLane[2] = { missing, missing };
    for (size_t index = 0; index < timeline.size(); index++) {
        const bool paragraphStart = index == 0 || IsKtvParagraphBreak(timeline[index].startMs, timeline[index - 1].endMs);
        const int lane = paragraphStart ? 0 : 1 - layouts.back().lane;
        const size_t sameLanePrevious = previousInLane[lane];
        const bool nearby = !paragraphStart && timeline[index].startMs - timeline[index - 1].endMs <= nearbyThresholdMs;
        const long fadeInStart = GetKtvFadeInStart(timeline[index].startMs, nearby,
            index > 0 ? layouts.back().fadeInStartMs : 0, sameLanePrevious != missing,
            sameLanePrevious != missing ? timeline[sameLanePrevious].endMs : 0);
        if (sameLanePrevious != missing)
            layouts[sameLanePrevious].nextSameLaneStartMs = timeline[index].startMs;
        layouts.push_back({ lane, fadeInStart, LONG_MAX });
        previousInLane[lane] = index;
    }
    return layouts;
}

// 提示点位于待唱歌词的同一轨道上方，为振假名留出独立空间。
inline float GetKtvCountdownRowY(int lane, float upperRowY, float lowerRowY) {
    return (lane == 0 ? upperRowY : lowerRowY) - 0.065f;
}

// 提示点尽量对齐待唱行起点，并为六点完整倒计时保留左右安全边距。
inline float GetKtvCountdownFirstX(float lyricLeftX, float safeLeftX, float safeRightX, float displayScale) {
    const float radiusWithStroke = 14.0f * displayScale;
    const float minimum = safeLeftX + radiusWithStroke;
    const float maximum = (std::max)(minimum, safeRightX - radiusWithStroke - 5.0f * 42.0f * displayScale);
    return (std::max)(minimum, (std::min)(lyricLeftX, maximum));
}
