#include <managers/obs_manager.h>
#include <managers/non_vocal_manager.h>
#include <chrono>
#include <cmath>

// 保持进程级生命周期；本项目不支持运行时热卸载 DLL。
ObsManager& GetObsManager() {
    static ObsManager* instance = new ObsManager();
    return *instance;
}

// 读取与旧配置隔离的开关，损坏配置保持默认关闭。
void ObsManager::Load() {
    enabled = false;
    autoRecord = false;
    try {
        auto path = FullPathInDllFolder(L"obs-tools.toml");
        if (std::filesystem::exists(path)) {
            auto cfg = toml::parse(path);
            enabled = toml::find_or<bool>(cfg, "enabled", false);
            autoRecord = toml::find_or<bool>(cfg, "auto_record_pv", false);
        }
    } catch (...) {
        status = "OBS 配置读取失败；联动保持关闭";
    }
}

// UTF-8 配置仅保存联动开关，密码保留在 Helper 专用配置中。
void ObsManager::Save() {
    std::ofstream out(std::filesystem::path(FullPathInDllFolder(L"obs-tools.toml")), std::ios::trunc);
    if (out) {
        out << "# OBS 游戏内联动；认证密码由独立 Helper 管理\n"
            << "enabled = " << (enabled ? "true" : "false") << "\n"
            << "auto_record_pv = " << (autoRecord ? "true" : "false") << "\n";
    }
    else {
        std::lock_guard<std::mutex> lock(guard);
        status = "OBS 开关保存失败";
    }
}

// 初始化后才允许后台线程运行。
void ObsManager::Init() {
    std::lock_guard<std::mutex> lifecycleLock(lifecycleGuard);
    if (initialized) return;
    Load();
    initialized = true;
    Publish();
    if (enabled) EnsureWorker();
}

// 启动一条常驻后台线程，实例与 DLL 均保持进程级生命周期。
void ObsManager::EnsureWorker() {
    if (!workerStarted.exchange(true))
        std::thread(&ObsManager::Worker, this).detach();
}

// 中文曲名编码成十六进制，避免空格、换行和管道协议分隔符冲突。
void ObsManager::Publish() {
    std::ostringstream out;
    out << "v2 " << GetCurrentProcessId() << " " << session.epoch << " "
        << (enabled && autoRecord ? 1 : 0) << " " << (session.active ? 1 : 0)
        << " " << session.pvid << " " << testCounter << " " << (nonVocal ? 1 : 0) << " ";
    const char* digits = "0123456789abcdef";
    if (title.empty()) out << "-";
    else for (unsigned char byte : title) out << digits[byte >> 4] << digits[byte & 15];
    out << "\n";
    std::lock_guard<std::mutex> lock(guard);
    request = out.str();
}

// 游戏线程只排队，后台落盘；每秒采样一次，并立即记录边界事件。
void ObsManager::Trace(const char* reason) {
    if (!enabled) return;
    std::ostringstream out;
    out << "事件：" << reason << "；状态：" << gameState
        << "；PV：" << (pvsel ? static_cast<int>(pvsel->PVID) : -1)
        << "；模式：" << (pvsel ? pvsel->gameModeIndex : 0)
        << "；时钟：" << (playbackStatus ? playbackStatus->currentPlaybackTime : -1.0f)
        << "；播放：" << (playbackStatus2 ? playbackStatus2->isPlaying : 0)
        << "；会话：" << session.epoch << "；准备：" << session.prepared << "；录制：" << session.active
        << "；曲名：" << title << "；人声静音：" << nonVocal << "\n";
    std::lock_guard<std::mutex> lock(guard);
    if (diagnostics.size() < 128) diagnostics.push_back(out.str());
}

// 观察已有歌曲加载事件，补齐不返回选曲界面的连续切歌与同曲循环。
void ObsManager::OnSongAudio(const std::string& path) {
    std::lock_guard<std::mutex> lifecycleLock(lifecycleGuard);
    if (!initialized) return;
    std::string normalized = path;
    std::replace(normalized.begin(), normalized.end(), '\\', '/');
    if (normalized.find("sound/song/") == std::string::npos && normalized.find("pv_") == std::string::npos) return;
    session.OnSongLoaded();
    Trace("歌曲加载");
    Publish();
}

// 已有 PV 进入/选曲事件不新增签名或 hook。
void ObsManager::OnGameState(const char* state) {
    std::lock_guard<std::mutex> lifecycleLock(lifecycleGuard);
    if (!initialized || !state) return;
    gameState = state;
    session.OnState(state, pvsel ? static_cast<int>(pvsel->PVID) : -1);
    if (strcmp(state, "PV POST PROCESS TASK") == 0) {
        title = PVWaitScreenInfo ? PVWaitScreenInfo->Name : std::string();
        // 标题沿用游戏当前生效的数据；过长或无标题时由 Helper 使用 PVID 后备。
        if (title.size() > 1000) title.clear();
    }
    Trace("状态切换");
    Publish();
}

// 播放暂停不结束录制；重新开始或更换 PV 则生成新的会话。
void ObsManager::OnFrame() {
    std::lock_guard<std::mutex> lifecycleLock(lifecycleGuard);
    if (!initialized) return;
    const bool viewer = pvsel && static_cast<int>(pvsel->PVID) > 0 &&
        (pvsel->gameModeIndex == 0x0101 || pvsel->gameModeIndex == 0x010101);
    const auto oldEpoch = session.epoch;
    const bool wasActive = session.active;
    session.OnFrame(viewer, viewer ? static_cast<int>(pvsel->PVID) : -1,
        playbackStatus2 && playbackStatus2->isPlaying,
        playbackStatus ? playbackStatus->currentPlaybackTime : -1.0f);
    if (session.epoch != oldEpoch) Trace("曲目变化或回到开头");
    if (!wasActive && session.active) {
        // 在首帧递增时固定真实静音状态，录制中开关变化不重命名已有文件。
        nonVocal = NonVocalManager_Inst.IsNonVocalApplied();
        title = PVWaitScreenInfo ? PVWaitScreenInfo->Name : std::string();
        if (title.size() > 1000) title.clear();
        Trace("开始播放");
    }
    const auto tick = GetTickCount64();
    if (enabled && tick - lastSampleTick >= 1000) {
        lastSampleTick = tick;
        Trace("每秒采样");
    }
    Publish();
}

// 所有等待限定在后台线程，事件完成或超时都回收资源。
std::string ObsManager::Exchange(const std::string& message) {
    HANDLE pipe = CreateFileW(L"\\\\.\\pipe\\DivaKaraokeObsV1", GENERIC_READ | GENERIC_WRITE,
        0, nullptr, OPEN_EXISTING, FILE_FLAG_OVERLAPPED, nullptr);
    if (pipe == INVALID_HANDLE_VALUE) return "Helper 未连接；请运行 obs_helper.py";
    OVERLAPPED operation{};
    operation.hEvent = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    if (!operation.hEvent) { CloseHandle(pipe); return "Helper 通信资源不足"; }
    DWORD count = 0;
    BOOL ok = WriteFile(pipe, message.data(), static_cast<DWORD>(message.size()), &count, &operation);
    if (!ok && GetLastError() == ERROR_IO_PENDING) {
        if (WaitForSingleObject(operation.hEvent, 1500) == WAIT_OBJECT_0)
            ok = GetOverlappedResult(pipe, &operation, &count, FALSE);
    }
    char reply[2048] = {};
    if (ok) {
        ResetEvent(operation.hEvent);
        operation.Internal = operation.InternalHigh = 0;
        ok = ReadFile(pipe, reply, sizeof(reply) - 1, &count, &operation);
        if (!ok && GetLastError() == ERROR_IO_PENDING) {
            if (WaitForSingleObject(operation.hEvent, 4000) == WAIT_OBJECT_0)
                ok = GetOverlappedResult(pipe, &operation, &count, FALSE);
        }
    }
    if (!ok) {
        CancelIoEx(pipe, &operation);
        // OVERLAPPED 内存只能在取消完成后释放；等待仍然只发生于后台。
        GetOverlappedResult(pipe, &operation, &count, TRUE);
    }
    CloseHandle(operation.hEvent);
    CloseHandle(pipe);
    return ok ? std::string(reply, count) : "Helper 通信超时；游戏继续运行";
}

// 变化立即发送，未变化时每秒心跳，游戏退出后由 Helper 看门狗收尾。
void ObsManager::Worker() {
    std::string previous;
    auto last = std::chrono::steady_clock::now() - std::chrono::seconds(2);
    for (;;) {
        std::string current;
        std::vector<std::string> pendingDiagnostics;
        { std::lock_guard<std::mutex> lock(guard); current = request; pendingDiagnostics.swap(diagnostics); }
        if (!pendingDiagnostics.empty()) {
            std::ofstream log(std::filesystem::path(FullPathInDllFolder(L"obs-runtime.log")), std::ios::app);
            for (const auto& line : pendingDiagnostics) log << line;
        }
        const auto now = std::chrono::steady_clock::now();
        if (current != previous || now - last >= std::chrono::seconds(1)) {
            const std::string reply = Exchange(current);
            { std::lock_guard<std::mutex> lock(guard); status = reply; }
            previous = current;
            last = std::chrono::steady_clock::now();
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(40));
    }
}

// 联动与自动录制分别可关闭；关闭时停止本功能拥有的录制。
void ObsManager::OnImGUI() {
    std::lock_guard<std::mutex> lifecycleLock(lifecycleGuard);
    ImGui::Separator();
    ImGui::TextUnformatted("OBS 录制");
    bool changed = ImGui::Checkbox("启用 OBS 联动", &enabled);
    changed = ImGui::Checkbox("PV / 播放列表自动录制（持续待命）", &autoRecord) || changed;
    if (changed) {
        Publish();
        if (enabled) EnsureWorker();
    }
    if (ImGui::Button("保存 OBS 开关")) Save();
    ImGui::SameLine();
    if (ImGui::Button("测试 OBS 连接")) { ++testCounter; Publish(); EnsureWorker(); }
    std::string current;
    { std::lock_guard<std::mutex> lock(guard); current = status; }
    ImGui::TextWrapped("状态：%s", current.c_str());
    ImGui::TextWrapped("每首按游戏曲名及 On Vocal / Non Vocal 命名，录完继续待命。暂停 PV 仍继续录制。");
}
