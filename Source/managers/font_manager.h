#pragma once
#include <globals.h>

#define VEC4_TO_COL32(name) IM_COL32(name.x*255,name.y*255,name.z*255,name.w*255)

class FontManager {

private:
    std::vector<std::string> fontsAvailable;
    std::string* fontnameDefault = NULL;
    std::string* fontnameWithCharset = NULL;
    
public:
    bool isInit = false;
    // Current combined font used for lyrics renderer
    ImFont* font;
    // Flag for triggering a font reload on next frame
    bool reloadFonts = false;
    // Current Charset buffer
    std::map<wchar_t, int> charset;
    // PVDB & Charset buffer
    std::map<int, std::string> PVDB_Buffer;
    std::map<int, std::map<wchar_t, int>> PVDB_Charset_Buffer;
    // Configurable
    float fontSize;
    float fontSizeImGui;
    bool isBold;
    bool isItalic;
    ImVec4 fillColor;
    ImVec4 strokeColor;
    ImVec4 shadowColor;
    ImVec2 shadowOffset;
    int strokeSize;
    // 相对于 1080p 的歌词字体图集缩放倍率；界面字体不随此倍率变化。
    float lyricAtlasScale = 1.0f;
    bool showGUI = true;
    void Init(Config& cfg);

    Config& FromConfig(Config& cfg);
    Config& ToConfig(Config& cfg);

    std::vector<std::string>& RefreshFontList();

    int UpdateCharset(std::wstring chars);
    // 根据当前渲染窗口高度更新歌词图集倍率，并在下一帧安全重建图集。
    void UpdateKtvResolutionScale(const ImVec2& viewportSize);
    void RebuildFonts();
    void OnFrame();
    void OnImGUI();

};

// 首次使用时创建字体管理器，避免 DLL 装载期构造 STL 容器。
FontManager& GetFontManager();
#define FontManager_Inst GetFontManager()
