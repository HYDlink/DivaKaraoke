#pragma once
#include <globals.h>

// 在歌曲音量层控制人声声道对，不修改音符判定或歌词运行时。
class NonVocalManager {
public:
    // 在加载器 Init 阶段读取独立配置并安装可选音频 Hook。
    void Init();
    // 在安全帧补应用开关变化，维持游戏请求的原始增益。
    void OnFrame();
    // 在调用者已经打开的 ImGui 窗口中绘制音频配置。
    void OnImGUI();
    // 在原歌曲加载函数返回后绑定该歌曲对象，避免影响其它声音。
    void OnSongAudio(void* music, const char* path);
    // 离开 PV 时清除歌曲对象，避免跨生命周期使用旧指针。
    void OnGameState(const char* state);
    // 拦截歌曲原始增益请求并只对人声声道对执行静音。
    int OnVolumeRequest(void* music, int pair, int value);
    // 只读获取当前歌曲实际应用的人声静音状态，供录像文件命名。
    bool IsNonVocalApplied();
private:
    // 把独立音频设置写入模组目录，保存失败时保留当前运行状态。
    bool SaveSettings();
    // 根据最近的原始请求应用当前开关，关闭时恢复原始增益。
    void ApplyLocked();
    std::mutex mutex;
    void* songMusic = nullptr;
    int requestedGain[4] = {};
    bool enabled = false;
    bool installed = false;
    bool pending = false;
    bool applied = false;
    std::string status;
};

// 首次 Init 后才创建管理器，避免 DLL 装载期间初始化业务对象。
NonVocalManager& GetNonVocalManager();
#define NonVocalManager_Inst GetNonVocalManager()
