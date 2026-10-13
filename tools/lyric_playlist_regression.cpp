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

// 用真实歌词管理器及 SRT/Ruby parser 验证不经过选曲界面的连续切歌。
int main() {
    SetConsoleOutputCP(CP_UTF8);
    try {
        const auto root = std::filesystem::absolute("artifacts/lyric-playlist-build/fixtures");
        std::filesystem::create_directories(root / "lyrics");
        wcscpy_s(DllFilePathBuffer, (root / "MMFreeLyrics.dll").c_str());
        WriteFixture(root / "lyrics/PV900001.srt", "1\n00:00:00,000 --> 00:00:02,000\n前曲\n\n");
        WriteFixture(root / "lyrics/PV900001.ruby.tsv", "1\t0:2:ぜんきょく\n");
        WriteFixture(root / "lyrics/PV900002.srt", "1\n00:00:00,000 --> 00:00:02,000\n次曲\n\n");
        WriteFixture(root / "lyrics/PV900002.ruby.tsv", "1\t0:2:じきょく\n");
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

        selector.PVID = 900002;
        Require(!manager.shouldShowLyrics(), "PVID 已切换时仍允许渲染旧歌词");
        // 不经过 PVsel/PV_STAGE，直接准备下一首，覆盖原问题的触发路径。
        manager.UpdateGameState("PV POST PROCESS TASK");
        Require(manager.GetCurrentLyricLine() == "次曲", "直接切歌仍沿用上一首歌词");
        Require(manager.lyricTimeline.at(0).rubySpans.at(0).ruby == "じきょく", "下一首仍沿用旧 Ruby");
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
        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "歌词播放列表回归失败：" << error.what() << '\n';
        return 1;
    }
}
