#pragma once
#include <globals.h>
#include <managers/font_manager.h>
#include <srtparser/srtparser.h>

// 一个汉字词组对应的平假名 Ruby 标注，位置以原歌词的 Unicode 字符下标表示。
struct RubySpan {
    size_t start;
    size_t length;
    std::string ruby;
};

// 项目自有的行级歌词时间线项，避免渲染逻辑依赖外部 parser 的对象生命周期与查询 API。
struct LyricLine {
    long startMs;
    long endMs;
    std::string text;
    std::vector<RubySpan> rubySpans;
};

class LyricManager {

    enum DisplayStatus {
        OnScreen,
        NoLyric
    };
    enum LyricDisplayType {
        RyhthmGame,
        PVMode,
        None
    };
    enum LyricDisplayStatus {
        Ended,
        Progressing,
        Paused,
        Ready
    };
    enum LyricDockingStyle {
        Free = 0b0000,
        HorizontallyCentered = 0b0001,
        VerticallyCentered = 0b0010,
    };
    enum LyricPivotStyle {        
        NotSet,
        TopLeft,
        TopRight,
        BottomLeft,
        BottomRight
    };
private:
    std::string internalLyricLine;    
    std::string songAudioName;

    int lyricIndex = 0;
    std::vector<LyricLine> lyricTimeline;
    std::vector<LyricLine> nativeLyricTimeline;
    std::string activeNativeLyric;
    int nativeTimelinePvid = -1;
    // 当前时间线所属的曲目，切歌时禁止沿用上一首歌词。
    int loadedPvid = -1;

    DisplayStatus displayStatus = NoLyric;
    LyricDisplayType lyricDisplayType = None;
    LyricDisplayStatus lyricDisplayStatus = Ended;

    bool lyricWasMoved = false;
    ImVec2 lyricPosBeforeMove;

    long exSubOffset = 0;
    
    // 重置字体所需的基础字符集。
    void ResetDefaultCharset();
    // 将公开 SRT parser 的输出复制为项目自有时间线。
    bool LoadExternalLyrics(const std::wstring& filename);
    // 读取与 SRT 同名的 Ruby TSV，将汉字词组读音绑定到已加载的时间线行。
    bool LoadRubySidecar(const std::wstring& filename);
    // 返回应用偏移后的当前播放时间（毫秒）。
    long CurrentTimestampMs();
    // 在时间线上查找当前正在显示的歌词行。
    const LyricLine* FindCurrentLyric(long timestampMs) const;
    // 在时间线上查找下一条尚未开始的歌词行。
    const LyricLine* FindNextLyric(long timestampMs) const;
    // 记录游戏原生歌词事件，并用相邻事件闭合上一句的结束时间。
    void CaptureNativeLyric(const char* text);
    // 从当前启用的数据源中查找正在显示的歌词行。
    const LyricLine* FindCurrentActiveLyric(long timestampMs) const;
    // 从当前启用的数据源中查找下一条歌词行。
    const LyricLine* FindNextActiveLyric(long timestampMs) const;
public:
    bool isInit = false;
    // Configurable 
    int lyricDockingStyle = Free;
    int lyricPivotStyle = NotSet;
    ImVec2 lyricPivotOffset;
    std::string lyricFormat;

    // KTV ワイプ可配置项
    ImVec4 ktvBeforeFillColor;
    ImVec4 ktvBeforeStrokeColor;
    ImVec4 ktvBeforeShadowColor;
    ImVec4 ktvAfterFillColor;
    ImVec4 ktvAfterStrokeColor;
    ImVec4 ktvAfterShadowColor;
    float ktvCurrentColumnX;
    float ktvNextColumnX;
    float ktvCurrentRowY;
    float ktvNextRowY;
    int ktvPreCueMs;
    int ktvNativeWipeEstimateMs;
    bool ktvWipeEnabled;
    bool ktvPreviewEnabled;

    bool useExternalLyrics;
    float lyricWindowOpacity = 0.0f;
    bool showInternalLyrics;
    bool showLyrics;

    bool showGUI = true;
    
    bool shouldShowLyrics();

    void Init(Config& cfg);

    Config& FromConfig(Config& cfg);
    Config& ToConfig(Config& cfg);

    float TimeElapsed();
    std::string GetCurrentLyricLine();

    void UpdateLyricIndex(int index);
    void UpdateGameState(const char* state);
    void SetLyricLine(bool isLyric, const char* src);
    void SetSongAudio(const char* src);

    void OnLyricsBegin();
    void OnLyricsEnd();

    void OnFrame();
    void OnImGUI();
};

// 首次使用时创建歌词管理器，避免 DLL 装载期构造 STL 容器。
LyricManager& GetLyricManager();
#define LyricManager_Inst GetLyricManager()
