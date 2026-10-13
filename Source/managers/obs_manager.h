#pragma once
#include <globals.h>
#include <atomic>
#include <thread>
#include <managers/obs_session.h>

// OBS 联动只向独立 Helper 发送生命周期；网络与认证不会进入游戏帧线程。
class ObsManager {
private:
    bool initialized = false;
    bool enabled = false;
    bool autoRecord = false;
    ObsPvSession session;
    unsigned long long testCounter = 0;
    std::string title;
    bool nonVocal = false;
    std::string gameState;
    std::vector<std::string> diagnostics;
    unsigned long long lastSampleTick = 0;
    // 将完整播放快照放入有界队列，由后台线程写入中文诊断日志。
    void Trace(const char* reason);
    // 生命周期由游戏事件与渲染线程共享，始终先持有此锁再访问快照锁。
    std::mutex lifecycleGuard;
    std::mutex guard;
    std::string request;
    std::string status = "未启用；请先启动 OBS Helper";
    std::atomic<bool> workerStarted{ false };
    // 加载独立配置，默认关闭，避免影响既有歌词配置。
    void Load();
    // 保存两个联动开关到模组自身目录。
    void Save();
    // 创建后台 IPC 工作线程，禁止在 DLL 装载期启动。
    void EnsureWorker();
    // 在后台发送快照和心跳；超时或 Helper 缺失不会阻塞游戏。
    void Worker();
    // 以有界超时完成一次 Named Pipe 收发。
    std::string Exchange(const std::string& message);
    // 发布生命周期快照，供后台线程读取。
    void Publish();
public:
    // 在游戏与 ImGui 初始化完成后加载独立设置。
    void Init();
    // 复用现有游戏状态事件，PVsel 是已证实的退出边界。
    void OnGameState(const char* state);
    // 复用成功的歌曲音频加载通知，在播放列表加载下一曲时结束旧会话。
    void OnSongAudio(const std::string& path);
    // 仅在 PV 鉴赏且播放时钟开始递增时启动一个新录制会话。
    void OnFrame();
    // 在调用方 PV 工具面板中绘制可编辑开关与状态。
    void OnImGUI();
};

// 首次使用时创建管理器，避开 DLL 装载期 STL 和线程初始化。
ObsManager& GetObsManager();
#define ObsManager_Inst GetObsManager()
