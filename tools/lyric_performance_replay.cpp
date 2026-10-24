#define IMGUI_DEFINE_MATH_OPERATORS
#include <globals.h>
#include <chrono>
#include <iomanip>
#include <stdexcept>
// 只读检查生产时间线，不将测试入口加入游戏 DLL。
#define private public
#include <managers/lyric_manager.h>
#undef private

// 回放期间禁止保存或重载真实配置。
void Config::SaveGlobalConfig() { throw std::runtime_error("性能回放不能保存用户配置"); }
// 回放期间禁止重载真实配置。
void Config::LoadGlobalConfig() { throw std::runtime_error("性能回放不能重载用户配置"); }

// 返回高精度单调时间，所有测量使用同一时钟。
double ReplayNowUs() {
    return std::chrono::duration<double, std::micro>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

// 条件失败立即结束测试，避免把缺少字形或设备的结果当作有效性能数据。
void ReplayRequire(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

// 保存真实生产绘制的 RGBA 数据，用于逐像素对照两版正文、注音和淡出。
void SaveReplayPixels(ID3D11Texture2D* texture, const std::filesystem::path& path, UINT width, UINT height) {
    D3D11_TEXTURE2D_DESC description{};
    texture->GetDesc(&description);
    description.Usage = D3D11_USAGE_STAGING;
    description.BindFlags = 0;
    description.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ID3D11Texture2D* staging = nullptr;
    ReplayRequire(SUCCEEDED(g_pd3dDevice->CreateTexture2D(&description, nullptr, &staging)), "读回纹理创建失败");
    g_pd3dDeviceContext->CopyResource(staging, texture);
    D3D11_MAPPED_SUBRESOURCE mapped{};
    ReplayRequire(SUCCEEDED(g_pd3dDeviceContext->Map(staging, 0, D3D11_MAP_READ, 0, &mapped)), "读回纹理失败");
    std::ofstream output(path, std::ios::binary);
    for (UINT row = 0; row < height; ++row)
        output.write(reinterpret_cast<const char*>(mapped.pData) + row * mapped.RowPitch, width * 4);
    g_pd3dDeviceContext->Unmap(staging, 0);
    staging->Release();
}

// 用真实安装字体及 PV261 时间线离屏回放；不启动游戏、不修改游戏文件。
int wmain(int argc, wchar_t** argv) {
    SetConsoleOutputCP(CP_UTF8);
    try {
        ReplayRequire(argc == 2, "用法：lyric_performance_replay 结果目录");
        const auto outputRoot = std::filesystem::absolute(argv[1]);
        std::filesystem::create_directories(outputRoot);
        const std::filesystem::path modRoot = L"E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics";
        wcscpy_s(DllFilePathBuffer, (modRoot / L"MMFreeLyrics.dll").c_str());
        ImGui::CreateContext();
        ImGui::GetIO().IniFilename = nullptr;
        auto& cfg = GlobalConfig_Inst;
        cfg.LoadDefault();
        ReplayRequire(cfg.Load(), "真实用户配置读取失败");
        auto& lyrics = LyricManager_Inst;
        auto& fonts = FontManager_Inst;
        lyrics.Init(cfg);
        fonts.Init(cfg);
        lyrics.showGUI = false;
        fonts.showGUI = false;
        PvSelector selector{};
        DivaPlaybackStatus clock{};
        DivaPlaybackStatus2 playing{};
        pvsel = &selector; playbackStatus = &clock; playbackStatus2 = &playing;
        selector.PVID = 261; playing.isPlaying = 1;
        lyrics.loadedPvid = 261;
        // 显式置为正在播放；枚举本身保持生产类的原私有可见性。
        lyrics.lyricDisplayStatus = static_cast<decltype(lyrics.lyricDisplayStatus)>(1);
        ReplayRequire(lyrics.LoadExternalLyrics((modRoot / L"lyrics/PV261.srt").wstring()), "PV261 字幕加载失败");
        lyrics.LoadRubySidecar((modRoot / L"lyrics/PV261.ruby.tsv").wstring());
        ReplayRequire(lyrics.lyricTimeline.size() == 38, "PV261 时间线行数异常");
        ReplayRequire(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, nullptr, 0,
            D3D11_SDK_VERSION, &g_pd3dDevice, nullptr, &g_pd3dDeviceContext)), "硬件 DX11 设备创建失败");
        ImGui_ImplDX11_Init(g_pd3dDevice, g_pd3dDeviceContext);
        D3D11_QUERY_DESC queryDescription = { D3D11_QUERY_EVENT, 0 };
        ID3D11Query* completed = nullptr;
        ReplayRequire(SUCCEEDED(g_pd3dDevice->CreateQuery(&queryDescription, &completed)), "图形同步查询创建失败");
        std::ofstream csv(outputRoot / "frames.csv");
        csv << "height,show_lyrics,time_ms,cpu_us,font_us,draw_us,submit_us,vertices,font_rebuilt\n" << std::fixed << std::setprecision(3);
        for (UINT height : { 1080U, 2160U }) {
            const UINT width = height * 16 / 9;
            ImGui::GetIO().DisplaySize = ImVec2((float)width, (float)height);
            ImGui::GetIO().DeltaTime = 1.0f / 60;
            fonts.OnFrame();
#ifndef PERFORMANCE_LEGACY_NATIVE
            PrepareKtvCompositeResources(ImGui::GetIO().DisplaySize);
#endif
            D3D11_TEXTURE2D_DESC description{};
            description.Width = width; description.Height = height;
            description.MipLevels = description.ArraySize = description.SampleDesc.Count = 1;
            description.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
            description.BindFlags = D3D11_BIND_RENDER_TARGET;
            ID3D11Texture2D* texture = nullptr;
            ID3D11RenderTargetView* target = nullptr;
            ReplayRequire(SUCCEEDED(g_pd3dDevice->CreateTexture2D(&description, nullptr, &texture)) &&
                SUCCEEDED(g_pd3dDevice->CreateRenderTargetView(texture, nullptr, &target)), "离屏画布创建失败");
            for (bool show : { false, true }) {
                lyrics.showLyrics = show;
                double maximum = 0, sum = 0;
                int frames = 0, capturedLine = -1;
                std::vector<long> timestamps;
                for (long time = 0; time <= 245500; time += 100) timestamps.push_back(time);
                for (const auto& line : lyrics.lyricTimeline)
                    for (long delta : { -16L, 0L, 16L, 250L, 500L }) timestamps.push_back((std::max)(0L, line.startMs + delta));
                std::sort(timestamps.begin(), timestamps.end());
                timestamps.erase(std::unique(timestamps.begin(), timestamps.end()), timestamps.end());
                for (long time : timestamps) {
                    clock.currentPlaybackTime = time / 1000.0f;
                    const double start = ReplayNowUs();
#ifdef PERFORMANCE_LEGACY_NATIVE
                    const auto* native = lyrics.FindCurrentLyric(time);
                    if (native && capturedLine != (int)(native - lyrics.lyricTimeline.data())) {
                        capturedLine = (int)(native - lyrics.lyricTimeline.data());
                        lyrics.SetLyricLine(true, native->text.c_str());
                    }
#endif
                    lyrics.OnFrame();
                    const bool fontRebuilt = fonts.reloadFonts;
                    fonts.OnFrame();
                    const double fontEnd = ReplayNowUs();
                    ImGui_ImplDX11_NewFrame();
                    ImGui::NewFrame();
                    lyrics.OnImGUI();
                    ImGui::Render();
                    const double drawEnd = ReplayNowUs();
                    const float clear[4] = { 0.12f, 0.24f, 0.36f, 1 };
                    g_pd3dDeviceContext->ClearRenderTargetView(target, clear);
                    g_pd3dDeviceContext->OMSetRenderTargets(1, &target, nullptr);
                    ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
                    const double submitEnd = ReplayNowUs();
                    const double elapsed = submitEnd - start;
                    maximum = (std::max)(maximum, elapsed); sum += elapsed; ++frames;
                    csv << height << ',' << show << ',' << time << ',' << elapsed << ',' << fontEnd - start << ','
                        << drawEnd - fontEnd << ',' << submitEnd - drawEnd << ',' << ImGui::GetDrawData()->TotalVtxCount << ',' << fontRebuilt << '\n';
                    // 每帧等 GPU 完成放在计时之外，避免无 Present 的回放积压几千帧。
                    g_pd3dDeviceContext->End(completed);
                    while (g_pd3dDeviceContext->GetData(completed, nullptr, 0, 0) == S_FALSE) SwitchToThread();
                    if (show && (time == 12500 || time == 13300 || time == 20500 || time == 31700))
                        SaveReplayPixels(texture, outputRoot / (std::to_string(height) + "-" + std::to_string(time) + ".rgba"), width, height);
                }
                std::cout << "回放完成：高度=" << height << "；显示歌词=" << show << "；帧数=" << frames
                    << "；平均 CPU 微秒=" << sum / frames << "；最大 CPU 微秒=" << maximum << '\n';
            }
            target->Release(); texture->Release();
        }
        completed->Release();
        ImGui_ImplDX11_Shutdown();
        ImGui::DestroyContext();
        g_pd3dDeviceContext->Release(); g_pd3dDevice->Release();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "性能回放失败：" << error.what() << '\n';
        return 1;
    }
}
