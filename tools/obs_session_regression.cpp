#include <globals.h>
#include <atomic>
#include <thread>
#include <condition_variable>
#define private public
#include <managers/obs_manager.h>
#undef private
#include <cstdio>
#include <managers/non_vocal_manager.h>

// 测试只检查协议发布，不控制真实歌曲音量。
NonVocalManager& GetNonVocalManager() { static NonVocalManager manager; return manager; }
// 隔离测试没有绑定歌曲，不请求静音。
bool NonVocalManager::IsNonVocalApplied() { return false; }

// 所有协议字段保持原格式，重复帧必须跳过编码；变化仍立即发布。
bool VerifyPublishChanges() {
    ObsManager manager;
    manager.Publish();
    manager.request = "重复帧哨兵";
    manager.Publish();
    if (manager.request != "重复帧哨兵") return false;
    manager.title = "测试曲目";
    manager.Publish();
    if (manager.request.find("e6b58be8af95e69bb2e79bae") == std::string::npos) return false;
    for (int field = 0; field < 7; ++field) {
        const auto previous = manager.request;
        if (field == 0) ++manager.session.epoch;
        if (field == 1) manager.session.pvid = 261;
        if (field == 2) manager.session.active = true;
        if (field == 3) { manager.enabled = true; manager.autoRecord = true; }
        if (field == 4) ++manager.testCounter;
        if (field == 5) manager.nonVocal = true;
        if (field == 6) manager.enabled = false;
        manager.Publish();
        if (manager.request == previous) return false;
        const auto current = manager.request;
        manager.Publish();
        if (manager.request != current) return false;
    }
    return true;
}

// 按现场单曲结束序列回放真实管理器，检查冻结时钟与错误的播放标记不会重启录制。
bool VerifySinglePvEnd() {
    PvSelector selector{};
    DivaPlaybackStatus clock{};
    DivaPlaybackStatus2 playing{};
    PVWaitScreenInfoStruct info{};
    selector.PVID = 805;
    selector.gameModeIndex = 0x0101;
    playing.isPlaying = 1;
    info.Name = "ロストワンの号哭";
    pvsel = &selector;
    playbackStatus = &clock;
    playbackStatus2 = &playing;
    PVWaitScreenInfo = &info;
    ObsManager manager;
    manager.initialized = true;
    manager.enabled = manager.autoRecord = true;
    manager.OnGameState("PV POST PROCESS TASK");
    manager.OnFrame();
    clock.currentPlaybackTime = 0.1f;
    manager.OnFrame();
    if (!manager.session.active) return false;
    const auto firstEpoch = manager.session.epoch;
    // 人工暂停只冻结时钟，当前文件继续保持录制。
    clock.currentPlaybackTime = 11.7773f;
    manager.OnGameState("PAUSE_MENU_SWITCH");
    playing.isPlaying = 0;
    manager.OnFrame();
    if (!manager.session.active || manager.session.epoch != firstEpoch) return false;
    playing.isPlaying = 1;
    clock.currentPlaybackTime = 218.339f;
    manager.OnFrame();
    const auto recordingSnapshot = manager.request;
    manager.OnGameState("GameResultTask");
    const auto endedSnapshot = manager.request;
    if (manager.session.active || manager.session.prepared || endedSnapshot == recordingSnapshot) return false;
    for (int frame = 0; frame < 600; ++frame) manager.OnFrame();
    if (manager.session.active || manager.request != endedSnapshot) return false;
    // 结果画面里的残余时钟继续增长也不能重新认领同一会话。
    clock.currentPlaybackTime += 1.0f;
    manager.OnFrame();
    if (manager.session.active || manager.session.epoch != firstEpoch) return false;
    manager.OnGameState("GameResultTask");
    if (manager.request != endedSnapshot) return false;
    std::ofstream output("artifacts/obs-single-end/session-snapshots.txt");
    output << "正常录制快照：" << recordingSnapshot << "自然结束快照：" << endedSnapshot;
    if (!output) return false;
    // 用户重播同曲建立独立文件；列表下一首亦使用相同准备流程。
    clock.currentPlaybackTime = 0.0f;
    manager.OnGameState("PV POST PROCESS TASK");
    manager.OnFrame();
    clock.currentPlaybackTime = 0.1f;
    manager.OnFrame();
    if (!manager.session.active || manager.session.epoch == firstEpoch) return false;
    manager.OnGameState("GameResultTask");
    selector.PVID = 249;
    info.Name = "アゲアゲアゲイン";
    clock.currentPlaybackTime = 0.0f;
    manager.OnGameState("PV POST PROCESS TASK");
    manager.OnFrame();
    clock.currentPlaybackTime = 0.1f;
    manager.OnFrame();
    const bool nextStarted = manager.session.active && manager.session.pvid == 249;
    pvsel = nullptr;
    playbackStatus = nullptr;
    playbackStatus2 = nullptr;
    PVWaitScreenInfo = nullptr;
    return nextStarted;
}

// 检查核心会话边界；失败时只输出中文，不访问真实游戏或 OBS。
int main() {
    SetConsoleOutputCP(CP_UTF8);
    if (!VerifyPublishChanges()) { puts("OBS 快照去重失败。"); return 12; }
    std::filesystem::create_directories("artifacts/obs-single-end");
    if (!VerifySinglePvEnd()) { puts("单曲自然结束、结束锁定或重播回归失败。"); return 13; }
    if (ObsPvSession::IsEndState("PAUSE_MENU_SWITCH") || ObsPvSession::IsEndState(nullptr)) return 14;
    ObsPvSession session;
    session.OnState("PV POST PROCESS TASK", 424);
    session.OnFrame(true, 424, true, 0.0f);
    if (session.active) return 1;
    session.OnFrame(true, 424, true, 0.1f);
    if (!session.active) return 2;
    auto first = session.epoch;
    session.OnFrame(true, 424, true, 100.0f);
    session.OnState("PAUSE_MENU_SWITCH", 424);
    session.OnFrame(true, 424, false, 100.0f);
    if (!session.active || session.epoch != first) return 3;
    // 不返回 PVsel 的不同歌曲连续切换。
    session.OnSongLoaded();
    if (session.active) return 4;
    session.OnFrame(true, 824, true, 100.0f);
    if (session.active || session.prepared) return 5;
    session.OnState("PV POST PROCESS TASK", 824);
    session.OnFrame(true, 824, true, 0.0f);
    session.OnFrame(true, 824, true, 0.1f);
    if (!session.active || session.pvid != 824 || session.epoch == first) return 6;
    // 没有再次发出准备事件时，同曲加载必须等时钟归零再开始。
    session.OnFrame(true, 824, true, 100.0f);
    first = session.epoch;
    session.OnSongLoaded();
    session.OnFrame(true, 824, true, 100.1f);
    if (session.active) return 7;
    session.OnFrame(true, 824, true, 0.0f);
    session.OnFrame(true, 824, true, 0.1f);
    if (!session.active || session.epoch == first) return 8;
    // 不发歌曲加载或准备事件，仍能识别同曲播放中的时钟重置。
    session.OnFrame(true, 824, true, 100.0f);
    first = session.epoch;
    session.OnFrame(true, 824, true, 0.0f);
    session.OnFrame(true, 824, true, 0.1f);
    if (!session.active || session.epoch == first) return 9;
    session.OnState("PVsel", -1);
    session.OnFrame(false, -1, false, 0.0f);
    if (session.active || session.prepared) return 10;
    session.OnFrame(true, 424, true, 50.0f);
    if (session.active) return 11;
    puts("OBS 会话回归通过：连续切歌、同曲循环、旧时钟保护、暂停及退出；未运行游戏。");
    puts("OBS 快照回归通过：重复帧跳过编码，全部协议字段变化仍立即发布。");
    puts("单曲结束回归通过：现场 PV805 结果状态、600 帧结尾停钟、播放标记仍为真、重播与下一首；人工暂停继续录制。");
    return 0;
}
