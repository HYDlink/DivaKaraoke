#include <globals.h>
#include <managers/font_manager.h>
#include <srtparser/srtparser.h>
// 仅在测试中检查时间线内容；实际加载与状态切换仍调用生产实现。
#define private public
#include <managers/lyric_manager.h>
#undef private

// 回归不创建图形设备，只替换字体管理器的字符集收集依赖。
FontManager& GetFontManager() {
    static FontManager manager{};
    return manager;
}

// 测试字体依赖记录真实歌词与 Ruby 字符，不加载字体文件。
int FontManager::UpdateCharset(std::wstring chars) {
    int added = 0;
    for (wchar_t ch : chars) added += charset.emplace(ch, 1).second ? 1 : 0;
    return added;
}

// 回归不操作配置文件；若误调用界面保存路径则立即报错。
void Config::SaveGlobalConfig() {
    throw std::runtime_error("回归不应保存用户配置");
}

// 回归不操作配置文件；若误调用界面加载路径则立即报错。
void Config::LoadGlobalConfig() {
    throw std::runtime_error("回归不应读取用户配置");
}

// 写入隔离目录中的 UTF-8 测试歌词，不触碰用户缓存。
void WriteFixture(const std::filesystem::path& file, const std::string& text) {
    std::ofstream output(file, std::ios::binary | std::ios::trunc);
    output << text;
    if (!output) throw std::runtime_error("测试歌词写入失败");
}

// 断言失败时输出可定位的中文说明。
void Require(bool condition, const char* description) {
    if (!condition) throw std::runtime_error(description);
}

// 检查缓存与共享算法一致，并覆盖调字号、切换轨道、重建字体及曲内预告变化。
void VerifyRenderCache(LyricManager& manager) {
    ImGui::CreateContext();
    auto& io = ImGui::GetIO();
    io.IniFilename = nullptr;
    io.DisplaySize = ImVec2(1920, 1080);
    FontManager_Inst.font = io.Fonts->AddFontDefault();
    io.Fonts->Build();
    io.DeltaTime = 1.0f / 60;
    ImGui::NewFrame();
    manager.ktvPreCueMs = 3000;
    manager.ktvCurrentColumnX = 0.04f; manager.ktvNextColumnX = 0.96f;
    manager.ktvCurrentRowY = 0.66f; manager.ktvNextRowY = 0.81f;
    FontManager_Inst.fontSize = 90;
    FontManager_Inst.strokeSize = 4;
    FontManager_Inst.shadowOffset = ImVec2(3, 3);
    const auto& layouts = manager.GetRenderLayouts();
    Require(layouts.size() == manager.lyricTimeline.size(), "缓存布局行数不正确");
    const auto* layoutData = layouts.data();
    Require(manager.GetRenderLayouts().data() == layoutData, "未修改设置时重建了布局");
    const LyricLine& line = manager.lyricTimeline.front();
    for (int step = 0; step < 6; ++step) {
        if (step == 1) FontManager_Inst.fontSize = 75;
        if (step == 2) { FontManager_Inst.lyricAtlasScale = 2; manager.ktvNextColumnX = 0.8f; }
        if (step == 3) { ++FontManager_Inst.atlasRevision; manager.lyricWindowOpacity = 0.5f; }
        if (step == 4) { manager.ktvCurrentRowY = 0.7f; manager.ktvPreCueMs = 6000; manager.GetRenderLayouts(); }
        for (int lane : { 0, 1, 0 }) {
            const KtvGeometryStyle style = { FontManager_Inst.fontSize, FontManager_Inst.strokeSize,
                FontManager_Inst.shadowOffset, manager.lyricWindowOpacity > 0 ? 18.0f : 0.0f, FontManager_Inst.lyricAtlasScale };
            const auto expected = GetKtvLineGeometry(FontManager_Inst.font, style.referenceFontSize * style.displayScale,
                line, style, lane, 1920 * manager.ktvCurrentColumnX, 1920 * manager.ktvNextColumnX,
                1080 * (lane == 0 ? manager.ktvCurrentRowY : manager.ktvNextRowY));
            const auto actual = manager.GetRenderGeometry(line, lane);
            Require(actual.fontSize == expected.fontSize && actual.position.x == expected.position.x &&
                actual.position.y == expected.position.y && actual.bounds.z == expected.bounds.z &&
                actual.textSize.x == expected.textSize.x, "几何缓存设置失效后与原算法不一致");
        }
    }
    manager.ClearRenderCache();
    Require(manager.renderLayouts.empty() && manager.renderGeometries.empty(), "清理后仍保留前一曲显示缓存");
    ImGui::EndFrame();
    ImGui::DestroyContext();
    FontManager_Inst.font = nullptr;
    std::cout << "通过：布局复用及字体版本、字号、倍率、安全区、轨道和背景的几何缓存失效。\n";
}

// 用真实歌词管理器及 SRT/Ruby parser 验证不经过选曲界面的连续切歌。
int main(int argc, char** argv) {
    SetConsoleOutputCP(CP_UTF8);
    try {
        const auto root = std::filesystem::absolute("artifacts/lyric-playlist-build/fixtures");
        std::filesystem::create_directories(root / "lyrics");
        wcscpy_s(DllFilePathBuffer, (root / "DivaKaraoke.dll").c_str());
        WriteFixture(root / "lyrics/PV900001.srt", "1\n00:00:00,000 --> 00:00:02,000\n前曲\n\n");
        WriteFixture(root / "lyrics/PV900001.ruby.tsv", "1\t0:2:ぜんきょく\n");
        WriteFixture(root / "lyrics/PV900001.singers.tsv", "# singers-v1\t900001\t1\n# performer\t0\tMIK\n# performer\t1\tRIN\n1\t0\t2000\tMIK,RIN\t前曲\n");
        WriteFixture(root / "lyrics/PV900002.srt", "1\n00:00:00,000 --> 00:00:02,000\n次曲\n\n");
        WriteFixture(root / "lyrics/PV900002.ruby.tsv", "1\t0:2:じきょく\n");
        WriteFixture(root / "lyrics/PV900002.singers.tsv", "# singers-v1\t900002\t1\n# performer\t0\tLEN\n# performer\t1\tKAI\n1\t0\t2000\tLEN,KAI\t次曲\n");
        // 明确保持下一首无歌词，用于验证缺失文件不会留下旧时间线。
        std::filesystem::remove(root / "lyrics/PV900003.srt");
        WriteFixture(root / "lyrics/PV900004.srt", "这不是有效的 SRT\n");
        PvSelector selector{};
        DivaPlaybackStatus clock{};
        DivaPlaybackStatus2 playing{};
        pvsel = &selector;
        playbackStatus = &clock;
        playbackStatus2 = &playing;
        clock.currentPlaybackTime = 0.5f;
        playing.isPlaying = 1;
        LyricManager manager{};
        manager.useExternalLyrics = true;
        selector.PVID = 900001;
        manager.UpdateGameState("PV POST PROCESS TASK");
        manager.OnFrame();
        Require(manager.shouldShowLyrics() && manager.GetCurrentLyricLine() == "前曲", "第一首歌词未加载");
        Require(manager.lyricTimeline.at(0).rubySpans.at(0).ruby == "ぜんきょく", "第一首 Ruby 未加载");
        Require(manager.lyricTimeline.at(0).singers == std::vector<std::string>({ "MIK", "RIN" }), "第一首合唱身份未加载");

        selector.PVID = 900002;
        Require(!manager.shouldShowLyrics(), "PVID 已切换时仍允许渲染旧歌词");
        // 不经过 PVsel/PV_STAGE，直接准备下一首，覆盖原问题的触发路径。
        manager.UpdateGameState("PV POST PROCESS TASK");
        Require(manager.GetCurrentLyricLine() == "次曲", "直接切歌仍沿用上一首歌词");
        Require(manager.lyricTimeline.at(0).rubySpans.at(0).ruby == "じきょく", "下一首仍沿用旧 Ruby");
        Require(manager.currentSingerIds == std::vector<std::string>({ "LEN", "KAI" }), "下一首仍沿用旧歌手身份");
        std::cout << "通过：两首连续播放正确切换歌词与 Ruby。\n";

        selector.PVID = 900001;
        manager.OnFrame();
        Require(manager.lyricTimeline.empty() && manager.GetCurrentLyricLine().empty(), "切歌首帧未清空旧时间线");
        manager.UpdateGameState("PV_STAGE");
        manager.UpdateGameState("PV POST PROCESS TASK");
        Require(manager.GetCurrentLyricLine() == "前曲", "加载状态后未绑定新曲");
        manager.UpdateGameState("PV_STAGE");
        Require(!manager.shouldShowLyrics() && manager.lyricTimeline.empty(), "加载界面仍保留旧歌词");
        manager.UpdateGameState("PV POST PROCESS TASK");
        // 同曲循环时文件更新也必须重新读取，不能只比较 PVID。
        manager.UpdateLyricIndex(99);
        WriteFixture(root / "lyrics/PV900001.srt", "1\n00:00:00,000 --> 00:00:02,000\n循环新词\n\n");
        manager.UpdateGameState("PV POST PROCESS TASK");
        Require(manager.GetCurrentLyricLine() == "循环新词" && manager.lyricIndex == 0, "同曲循环未重建歌词状态");
        Require(manager.lyricTimeline.at(0).singers.empty() && manager.currentSingerIds.empty(), "全文已改变仍使用旧歌手文件");
        // 持久化使用隔离模组目录，验证四色及阴影、开关和自定义第三歌手。
        manager.LoadSingerSettings();
        manager.singerPalettes["CUSTOM_THIRD"] = DefaultSingerPalette("CUSTOM_THIRD");
        manager.singerPalettes["RIN"].beforeStroke = ImVec4(0.11f, 0.22f, 0.33f, 0.44f);
        manager.singerPalettes["RIN"].afterFill = ImVec4(0.45f, 0.56f, 0.67f, 0.78f);
        manager.singerColorsEnabled = false; manager.singerChorusGradient = false; manager.singerChorusVertical = false;
        Require(manager.SaveSingerSettings(), "独立歌手配置保存失败");
        manager.singerChorusVertical = true;
        manager.singerPalettes.clear(); manager.LoadSingerSettings();
        Require(!manager.singerChorusVertical,"横向模式没有独立持久化");
        Require(manager.singerPalettes.count("CUSTOM_THIRD") && !manager.singerColorsEnabled && !manager.singerChorusGradient, "配置未保存自定义身份与开关");
        Require(std::fabs(manager.singerPalettes.at("RIN").beforeStroke.w - 0.44f) < 0.001f && std::fabs(manager.singerPalettes.at("RIN").afterFill.y - 0.56f) < 0.001f, "未唱描边或已唱填充没有独立持久化");
        std::cout << "通过：歌手旁路切歌、全文强绑定、四种颜色及自定义第三歌手持久化。\n";
        VerifyRenderCache(manager);
        manager.OnFrame();
        playing.isPlaying = 0;
        manager.OnFrame();
        Require(manager.shouldShowLyrics() && manager.GetCurrentLyricLine() == "循环新词", "暂停错误清除了当前歌词");
        manager.UpdateGameState(nullptr);
        std::cout << "通过：提前切换 PVID、加载清理、同曲循环、暂停与空状态。\n";

        selector.PVID = 900003;
        manager.UpdateGameState("PV POST PROCESS TASK");
        Require(manager.lyricTimeline.empty() && manager.GetCurrentLyricLine().empty(), "缺少歌词文件时保留了上一首");
        selector.PVID = 900004;
        manager.UpdateGameState("PV POST PROCESS TASK");
        Require(manager.lyricTimeline.empty(), "无效 SRT 未清空时间线");
        manager.UpdateGameState("PVsel");
        Require(!manager.shouldShowLyrics() && manager.loadedPvid == -1, "退出选曲未释放曲目绑定");
        pvsel = nullptr;
        manager.UpdateGameState("PV POST PROCESS TASK");
        Require(!manager.shouldShowLyrics(), "无有效选曲时不应展示歌词");
        std::cout << "通过：缺失/无效 SRT、退出选曲与无选曲指针。\n";
        // 使用实际生产SRT及本轮生成旁路，验证六首完整行号与全文匹配。
        pvsel = &selector;
        for (int id : { 41, 62, 728, 802, 611, 268 }) {
            char stem[32]; sprintf_s(stem, "PV%03d", id);
            const auto filename = std::string(stem);
            std::filesystem::copy_file(std::filesystem::path("artifacts/furigana-official-alignment/cache") / (filename + ".srt"), root / "lyrics" / (filename + ".srt"), std::filesystem::copy_options::overwrite_existing);
            std::filesystem::copy_file(std::filesystem::path("artifacts/singer-mvp/cache") / (filename + ".singers.tsv"), root / "lyrics" / (filename + ".singers.tsv"), std::filesystem::copy_options::overwrite_existing);
            selector.PVID = id; manager.OnLyricsBegin();
            Require(!manager.currentSingerIds.empty(), "实际歌曲歌手旁路没有通过生产字幕全文绑定");
            if (id == 802) {
                Require(manager.lyricTimeline.at(38).singers == std::vector<std::string>({"MIK", "LUK"}), "用户已校对的愛Dee第39句身份不符");
                Require(manager.lyricTimeline.at(41).singers == std::vector<std::string>({"MIK", "LUK"}), "用户已校对的愛Dee第42句身份不符");
            }
            if (id == 268) for (const auto& line : manager.lyricTimeline)
                Require(line.singers == std::vector<std::string>({"MIK"}), "六个初音复制角色产生了假合唱");
        }
        std::cout << "通过：六首真实字幕歌手强绑定、愛Dee人工校对样本及六初音身份归并。\n";
        // 按真实批量目录动态加载全部歌手旁路，不用固定PV名单决定验收范围。
        if (argc > 1) {
            const std::filesystem::path batch(argv[1]);
            size_t checked = 0;
            for (const auto& file : std::filesystem::directory_iterator(batch)) {
                const std::string name = file.path().filename().string();
                const std::string suffix = ".singers.tsv";
                if (!file.is_regular_file() || name.size() <= suffix.size() || name.substr(name.size()-suffix.size()) != suffix) continue;
                const std::string stem = name.substr(0,name.size()-suffix.size());
                const int id = std::stoi(stem.substr(2));
                std::filesystem::copy_file(batch/(stem+".srt"),root/"lyrics"/(stem+".srt"),std::filesystem::copy_options::overwrite_existing);
                std::filesystem::copy_file(file.path(),root/"lyrics"/name,std::filesystem::copy_options::overwrite_existing);
                selector.PVID = id; manager.OnLyricsBegin();
                Require(!manager.currentSingerIds.empty(),(std::string("真实批量旁路未通过生产SRT绑定：")+stem).c_str());
                ++checked;
            }
            Require(checked > 0,"真实批量目录中没有歌手旁路");
            std::cout << "通过：生产C++加载器动态验证" << checked << "首批量歌手旁路与实际SRT。\n";
        }
        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "歌词播放列表回归失败：" << error.what() << '\n';
        return 1;
    }
}
