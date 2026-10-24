#pragma once
#include <Windows.h>
#include <winmeta.h>
#include <TraceLoggingProvider.h>
#pragma comment(lib, "advapi32.lib")

// 仅在 WPR 显式启用此提供程序时发送事件；普通运行没有落盘或后台采样。
TRACELOGGING_DECLARE_PROVIDER(g_divaPerformanceProvider);

// 用高精度时钟标记一个生产调用区间，供 ETL 对照函数采样和单次长帧。
class DivaPerformanceScope {
    const char* section;
    LARGE_INTEGER started{};
    bool enabled;
public:
    // 未采集时仅检查提供程序开关，不读取时钟或分配内存。
    explicit DivaPerformanceScope(const char* name) : section(name),
        enabled(TraceLoggingProviderEnabled(g_divaPerformanceProvider, WINEVENT_LEVEL_VERBOSE, 0)) {
        if (enabled) QueryPerformanceCounter(&started);
    }
    // 在调用结束处记录区间耗时，文件写入由独立 ETW 记录器负责。
    ~DivaPerformanceScope() {
        if (!enabled) return;
        LARGE_INTEGER ended, frequency;
        QueryPerformanceCounter(&ended);
        QueryPerformanceFrequency(&frequency);
        TraceLoggingWrite(g_divaPerformanceProvider, "ModSection",
            TraceLoggingLevel(WINEVENT_LEVEL_VERBOSE), TraceLoggingString(section, "section"),
            TraceLoggingFloat64((ended.QuadPart - started.QuadPart) * 1000000.0 / frequency.QuadPart, "duration_us"));
    }
};

// 在既有歌词索引通知处标记换句，避免为分析增加新的游戏 Hook。
inline void TraceDivaLyricChange(int pvid, int index, float playbackSeconds, bool showLyrics) {
    TraceLoggingWrite(g_divaPerformanceProvider, "LyricChange",
        TraceLoggingInt32(pvid, "pvid"), TraceLoggingInt32(index, "index"),
        TraceLoggingFloat32(playbackSeconds, "playback_seconds"), TraceLoggingBool(showLyrics, "show_lyrics"));
}
