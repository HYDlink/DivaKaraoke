#pragma once
#include <globals.h>
#include <managers/font_manager.h>
#include <srtparser/srtparser.h>
#include <managers/singer_style.h>
#include <managers/ktv_timing.h>
#include <managers/ktv_geometry.h>
#include <array>

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
    // 本行参与的不同歌手身份；空集合使用原来的默认颜色。
    std::vector<std::string> singers;
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
    std::string songAudioName;

    int lyricIndex = 0;
    std::vector<LyricLine> lyricTimeline;
    // 曲内固定布局仅在时间线或预告设置变化时重算。
    std::vector<KtvLineLayout> renderLayouts;
    int renderPreCueMs = -1;
    // 行几何按字体版本、输出尺寸及实际布局设置缓存，避免逐帧测量正文和 Ruby。
    std::vector<KtvLineGeometry> renderGeometries;
    std::vector<bool> renderGeometryReady;
    std::vector<int> renderGeometryLanes;
    std::array<float, 12> renderGeometrySettings{};
    ImFont* renderFont = nullptr;
    unsigned long long renderFontRevision = 0;
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
    // 加载与本曲字幕逐行时间、全文严格匹配的歌手标记。
    bool LoadSingerSidecar(const std::wstring& filename);
    // 返回应用偏移后的当前播放时间（毫秒）。
    long CurrentTimestampMs();
    // 在时间线上查找当前正在显示的歌词行。
    const LyricLine* FindCurrentLyric(long timestampMs) const;
    // 在时间线上查找下一条尚未开始的歌词行。
    const LyricLine* FindNextLyric(long timestampMs) const;
    // 从当前启用的数据源中查找正在显示的歌词行。
    const LyricLine* FindCurrentActiveLyric(long timestampMs) const;
    // 从当前启用的数据源中查找下一条歌词行。
    const LyricLine* FindNextActiveLyric(long timestampMs) const;
public:
    // 取得本曲固定轨道布局，并在用户改变预告设置时失效旧几何。
    const std::vector<KtvLineLayout>& GetRenderLayouts();
    // 缓存实际时间线行的几何，预览行仍由共享测量算法直接计算。
    KtvLineGeometry GetRenderGeometry(const LyricLine& line, int lane);
    // 在切歌或退出时清除显示缓存，不保留前一曲的数据。
    void ClearRenderCache();
    // 身份键控配色支持任意数量歌手，不将第二槽位写死为特定角色。
    std::map<std::string, SingerPalette> singerPalettes;
    // 当前歌曲去重后的歌手身份，复制角色合并为一个身份。
    std::vector<std::string> currentSingerIds;
    // 启用逐行歌手配色；未标记时保留原默认配色。
    bool singerColorsEnabled = true;
    // 多歌手组合采用横向柔和渐变，关闭时使用融合纯色。
    bool singerChorusGradient = true;
    // 合唱默认试用上下双色，用户可随时切回整句横向渐变。
    bool singerChorusVertical = true;
    // 从独立配置读取歌手配色，不修改用户既有歌词配置字段。
    void LoadSingerSettings();
    // 原子保存独立歌手配色配置，避免影响旧配置、歌词和字体。
    bool SaveSingerSettings();
    // 在歌词颜色面板展示当前角色的完整配色及合唱预览。
    void DrawSingerColorPanel();
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
    void SetSongAudio(const char* src);

    void OnLyricsBegin();
    void OnLyricsEnd();

    void OnFrame();
    void OnImGUI();
};

// 首次使用时创建歌词管理器，避免 DLL 装载期构造 STL 容器。
LyricManager& GetLyricManager();
// 在安全渲染入口预热透明合成资源，不在歌词到达时编译 shader。
void PrepareKtvCompositeResources(const ImVec2& viewportSize);
#define LyricManager_Inst GetLyricManager()
