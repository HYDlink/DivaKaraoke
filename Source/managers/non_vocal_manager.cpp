#include <managers/non_vocal_manager.h>
#include <Psapi.h>

namespace {
    using PairVolumeFunction = int (__fastcall*)(void*, int, int);
    PairVolumeFunction originalPairVolume = nullptr;

    // 转发音频请求；原函数始终执行，保留伴奏以及游戏音频内部同步行为。
    int __fastcall SetPairVolumeHook(void* music, int pair, int value) {
        return NonVocalManager_Inst.OnVolumeRequest(music, pair, value);
    }

    // 检查歌曲对象可读；生命周期另外由歌曲加载和 PVsel 通知约束。
    bool IsReadableMusic(void* music) {
        MEMORY_BASIC_INFORMATION region{};
        if (!music || !VirtualQuery(music, &region, sizeof(region)) || region.State != MEM_COMMIT ||
            (region.Protect & (PAGE_GUARD | PAGE_NOACCESS)))
            return false;
        return reinterpret_cast<uintptr_t>(music) + 0x2C <=
            reinterpret_cast<uintptr_t>(region.BaseAddress) + region.RegionSize;
    }

    // 使用本机已反汇编验证的完整前段签名查找音量函数，不依赖固定地址。
    void* FindPairVolumeFunction() {
        const char* signature = "\x48\x89\x5C\x24\x08\x57\x48\x83\xEC\x20\xF6\x01\x04\x48\x8B\xD9\x48\x63\xFA\x75\x10\xB8\xFE\xFF\xFF\xFF\x48\x8B\x5C\x24\x30\x48\x83\xC4\x20\x5F\xC3\x66\x41\x0F\x6E\xC0\x0F\x5B\xC0\xF3\x0F\x59\x05";
        MODULEINFO module{};
        if (!GetModuleInformation(GetCurrentProcess(), GetModuleHandle(nullptr), &module, sizeof(module)) ||
            module.SizeOfImage < 92)
            return nullptr;
        auto base = reinterpret_cast<unsigned char*>(module.lpBaseOfDll);
        auto end = base + module.SizeOfImage;
        // 只检查足以容纳完整函数的起点，保护尾部语义校验与版本不匹配路径。
        auto candidate = reinterpret_cast<unsigned char*>(sigScan(signature,
            "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", 49, base, module.SizeOfImage - 92 + 1));
        if (!candidate || candidate + 92 > end)
            return nullptr;
        auto rest = candidate + 1;
        if (end - rest >= 92 && sigScan(signature,
            "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", 49, rest,
            static_cast<size_t>(end - rest - 92 + 1)))
            return nullptr;
        // 再核对函数尾部：歌曲 OGG wrapper +0xE8 与声道增益调用，拒绝仅前段相似的函数。
        const unsigned char suffix[] = { 0x48, 0x8B, 0x8B, 0xE8, 0x00, 0x00, 0x00 };
        if (!candidate || memcmp(candidate + 0x3A, suffix, sizeof(suffix)) != 0 ||
            candidate[0x4A] != 0xE8 || candidate[0x5B] != 0xC3)
            return nullptr;
        return candidate;
    }
}

// 通过函数局部静态对象提供延迟初始化。
NonVocalManager& GetNonVocalManager() {
    static NonVocalManager instance;
    return instance;
}

// 配置或可选 Hook 失败只停用音频功能，歌词基线继续运行。
void NonVocalManager::Init() {
    std::lock_guard<std::mutex> lock(mutex);
    if (installed)
        return;
    try {
        const auto path = FullPathInDllFolder(L"audio-tools.toml");
        if (std::filesystem::exists(path)) {
            const auto settings = toml::parse(path);
            enabled = toml::find_or<bool>(settings, "non_vocal_enabled", false);
        }
    } catch (...) {
        enabled = false;
        LOG(L"音频配置读取失败，已默认关闭人声静音。");
    }
    originalPairVolume = reinterpret_cast<PairVolumeFunction>(FindPairVolumeFunction());
    if (!originalPairVolume) {
        status = "音频签名未匹配，功能不可用";
        LOG(L"未找到已验证的歌曲声道音量函数，已跳过人声静音 Hook。");
        return;
    }
    LONG error = DetourTransactionBegin();
    if (error == NO_ERROR)
        error = DetourUpdateThread(GetCurrentThread());
    if (error == NO_ERROR)
        error = DetourAttach(reinterpret_cast<PVOID*>(&originalPairVolume), SetPairVolumeHook);
    if (error != NO_ERROR) {
        DetourTransactionAbort();
        originalPairVolume = nullptr;
        status = "音频 Hook 安装失败，功能不可用";
        LOG(L"人声静音 Hook 安装失败，错误码：%ld。", error);
        return;
    }
    error = DetourTransactionCommit();
    installed = error == NO_ERROR;
    status = installed ? "已就绪，等待歌曲；游戏听感待验收" : "音频 Hook 提交失败，功能不可用";
    LOG(L"人声静音 Hook 初始化结果：%s；错误码：%ld。", installed ? L"成功" : L"失败", error);
}

// 只绑定歌曲加载 Hook 提供的对象，初始增益来自已验证的游戏自身字段。
void NonVocalManager::OnSongAudio(void* music, const char* path) {
    std::lock_guard<std::mutex> lock(mutex);
    songMusic = nullptr;
    applied = false;
    if (!installed || !path || !*path || !IsReadableMusic(music))
        return;
    // 只接受歌曲路径，避免将标题、菜单或 SE 使用的音乐对象纳入控制。
    std::string songPath(path);
    std::replace(songPath.begin(), songPath.end(), '\\', '/');
    if (songPath.find("sound/song/") == std::string::npos && songPath.find("pv_") == std::string::npos)
        return;
    songMusic = music;
    const auto bytes = reinterpret_cast<const unsigned char*>(music);
    for (int pair = 0; pair < 4; ++pair) {
        // 0x0C 的曲目增益与 0x1C 的声道主增益由本机 map 反汇编证实，非猜测字段。
        int gain = 0;
        int master = 0;
        memcpy(&gain, bytes + 0x0C + pair * sizeof(int), sizeof(int));
        memcpy(&master, bytes + 0x1C + pair * sizeof(int), sizeof(int));
        requestedGain[pair] = static_cast<int>((static_cast<float>(gain) * master) * 0.01f);
    }
    pending = enabled;
    ApplyLocked();
    LOG(L"人声静音已绑定歌曲音频：%S。", path);
}

// 退回歌曲选择或主菜单即丢弃对象；下次加载重新建立关联。
void NonVocalManager::OnGameState(const char* state) {
    if (!state || (strcmp(state, "PVsel") != 0 && strcmp(state, "MENU") != 0 && strcmp(state, "STARTUP") != 0))
        return;
    std::lock_guard<std::mutex> lock(mutex);
    if (applied && IsReadableMusic(songMusic)) {
        originalPairVolume(songMusic, 1, requestedGain[1]);
        originalPairVolume(songMusic, 3, requestedGain[3]);
    }
    songMusic = nullptr;
    pending = false;
    applied = false;
}

// 保存原始请求而不是固定恢复 100%，因此 miss gate 和淡出仍可恢复游戏状态。
int NonVocalManager::OnVolumeRequest(void* music, int pair, int value) {
    std::lock_guard<std::mutex> lock(mutex);
    if (music == songMusic && pair >= 0 && pair < 4) {
        requestedGain[pair] = value;
        if (enabled && (pair == 1 || pair == 3)) {
            value = 0;
            applied = true;
        }
    }
    return originalPairVolume(music, pair, value);
}

// 只补应用开关，不逐帧覆盖伴奏或游戏的增益逻辑。
void NonVocalManager::ApplyLocked() {
    if (!pending || !installed || !songMusic || !IsReadableMusic(songMusic))
        return;
    originalPairVolume(songMusic, 1, enabled ? 0 : requestedGain[1]);
    originalPairVolume(songMusic, 3, enabled ? 0 : requestedGain[3]);
    applied = enabled;
    pending = false;
}

// 帧入口应用来自 ImGui 的开关变化。
void NonVocalManager::OnFrame() {
    std::lock_guard<std::mutex> lock(mutex);
    ApplyLocked();
}

// 返回歌曲实际静音状态，只读访问不改变音频行为。
bool NonVocalManager::IsNonVocalApplied() {
    std::lock_guard<std::mutex> lock(mutex);
    return installed && songMusic && enabled && applied;
}

// 独立 TOML 不修改历史歌词配置，默认关闭。
bool NonVocalManager::SaveSettings() {
    std::ofstream output(FullPathInDllFolder(L"audio-tools.toml"), std::ios::binary | std::ios::trunc);
    if (!output)
        return false;
    output << "# 人声静音：仅对标准伴奏/人声分轨歌曲有效。\nnon_vocal_enabled = "
        << (enabled ? "true" : "false") << "\n";
    return static_cast<bool>(output);
}

// 显示真实 Hook 状态，并明确立体声混音无法独立去人声。
void NonVocalManager::OnImGUI() {
    std::lock_guard<std::mutex> lock(mutex);
    ImGui::TextUnformatted("音频");
    ImGui::BeginDisabled(!installed);
    if (ImGui::Checkbox("伴奏模式 / 关闭人声", &enabled))
        pending = true;
    ImGui::EndDisabled();
    ImGui::TextUnformatted(status.c_str());
    ImGui::TextUnformatted(songMusic ? (enabled ? "当前歌曲：人声静音已请求" : "当前歌曲：使用游戏原始增益") : "当前没有绑定歌曲");
    ImGui::TextWrapped("适用于标准分轨音频。已混入伴奏的人声无法去除；部分 Mod 曲可能没有人声分轨。");
    if (ImGui::Button("保存音频设置"))
        status = SaveSettings() ? "音频设置已保存" : "音频设置保存失败";
}
