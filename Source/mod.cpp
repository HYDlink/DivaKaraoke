#include <globals.h>
#include <managers/font_manager.h>
#include <managers/lyric_manager.h>
#include <managers/non_vocal_manager.h>
#include <managers/obs_manager.h>
#include <utils/performance_trace.h>
#include <imgui/imgui_internal.h>
#pragma warning( disable : 26495 26812 )
// Signatures
SIG_SCAN
(
	sigChangeGameState,
	0x1402C9660,
	"\x4C\x8B\xC2\x41\xB9\x00\x00\x00\x00\x48\x8B\x15\x00\x00\x00\x00\x48\x8B\x52\x10\xE9\x00\x00\x00\x00",
	"xxxxx????xxx????xxxxx????"
)
SIG_SCAN
(
	sigRenderLyricAndTitle,
	0x14027B150,
	"\x48\x8B\xC4\x48\x89\x58\x08\x48\x89\x70\x10\x48\x89\x78\x18\x55\x48\x8D\x68\xD8\x48\x81\xEC\x00\x00\x00\x00\x0F\x29\x70\xE8\x0F\x29\x78\xD8\x48\x8B\x05\x00\x00\x00\x00\x48\x33\xC4\x48\x89\x45\xF0\x48\x8B\x5D\x50\x41\x8B\xF9\x41\x8B\xF0\x0F\x28\xF1\x0F\x28\xF8",
	"xxxxxxxxxxxxxxxxxxxxxxx????xxxxxxxxxxx????xxxxxxxxxxxxxxxxxxxxxxx"
)
SIG_SCAN
(
	sigLoadSongAudio,
	0x14023E2B0,
	"\x48\x89\x5C\x24\x00\x55\x56\x57\x48\x81\xEC\x00\x00\x00\x00\x0F\x29\xB4\x24\x00\x00\x00\x00\x48\x8B\x05\x00\x00\x00\x00\x48\x33\xC4\x48\x89\x84\x24\x00\x00\x00\x00",
	"xxxx?xxxxxx????xxxx????xxx????xxxxxxx????"
)
SIG_SCAN
(
	sigUpdateLyrics,
	0x140244CD0,
	"\x48\x89\x5C\x24\x00\x57\x48\x83\xEC\x50\x48\x8B\x05\x00\x00\x00\x00\x48\x33\xC4\x48\x89\x44\x24\x00\x48\x8B\xF9\x48\x8D\x99\x00\x00\x00\x00",
	"xxxx?xxxxxxxx????xxxxxxx?xxxxxx????"
)
SIG_SCAN
(
	sigGetInputState,
	0x1402AC960,
	"\x4C\x8B\x05\x00\x00\x00\x00\x4D\x85\xC0\x74\x35\x4C\x63\xC9\x48\xB8\x00\x00\x00\x00\x00\x00\x00\x00\x49\x8B\x48\x08\x49\x2B\x08\x48\xF7\xE9",
	"xxx????xxxxxxxxxx????????xxxxxxxxxx"
)
SIG_SCAN(
	sigDivaPlayback,
	0x14024EB40,
	"\x40\x53\x55\x41\x54\x41\x57\x48\x81\xEC\x00\x00\x00\x00\x0F\x29\x74\x24\x00\x48\x8B\x05\x00\x00\x00\x00\x48\x33\xC4\x48\x89\x44\x24\x00\x80\x39\x00\x45\x0F\xB6\xF9",
	"xxxxxxxxxx????xxxx?xxx????xxxxxxx?xxxxxxx"
)
SIG_SCAN(
	sigDivaPlayback2,
	0x14CC60620,
	"\x40\x53\x48\x83\xEC\x20\x65\x48\x8B\x04\x25\x00\x00\x00\x00\xBA\x00\x00\x00\x00\x48\x8B\x08\x8B\x04\x0A\x39\x05\x00\x00\x00\x00\x7F\x0D",
	"xxxxxxxxxxx????x????xxxxxxxx????xx"
)
SIG_SCAN(
	sigpv_selector_switch__PvSelector__applySel,
	0x1406EFA30,
	"\x40\x57\x48\x81\xEC\x00\x00\x00\x00\x80\xB9\x00\x00\x00\x00\x00\x48\x8B\xF9\x74\x0B\x33\xC0\x48\x81\xC4\x00\x00\x00\x00\x5F\xC3",
	"xxxxx????xx?????xxxxxxxxxx????xx"
)
SIG_SCAN(
	sigMegaMix__CreateTaskWaitScreen,
	0x140653EF0,
	"\x48\x89\x5C\x24\x00\x48\x89\x4C\x24\x00\x57\x48\x83\xEC\x20\x48\x8D\x3D\x00\x00\x00\x00\x48\x89\x7C\x24\x00\x48\x8B\xCF\xE8\x00\x00\x00\x00\x90\x48\x8D\x05\x00\x00\x00\x00\x48\x89\x05\x00\x00\x00\x00\x33\xDB\x48\x89\x1D\x00\x00\x00\x00\x48\x89\x1D\x00\x00\x00\x00\x48\xC7\x05\x00\x00\x00\x00\x00\x00\x00\x00\x48\x8D\x0D\x00\x00\x00\x00\xE8\x00\x00\x00\x00\x90\x48\x8D\x0D\x00\x00\x00\x00\xE8\x00\x00\x00\x00\x48\x89\x1D\x00\x00\x00\x00",
	"xxxx?xxxx?xxxxxxxx????xxxx?xxxx????xxxx????xxx????xxxxx????xxx????xxx????????xxx????x????xxxx????x????xxx????"
)
FUNCTION_PTR(DivaPlaybackStatus2*, __fastcall, getPlaybackStatus2, sigDivaPlayback2Addr);
FUNCTION_PTR(PvSelector*, __fastcall, getPvSelAddr, readRelCall16Address((uint64_t)sigpv_selector_switch__PvSelector__applySelAddr + 0x1D0));

HOOK(int64_t, __fastcall, _DivaPlayback, sigDivaPlayback(),
	DivaPlaybackStatus* a1, __int64 a2, __int64 a3, char a4)
{
	playbackStatus = a1;
	return original_DivaPlayback(a1, a2, a3, a4);
}

HOOK(char*, __fastcall, _LoadSongAudio, sigLoadSongAudio(),
	__int64 a1,
	__int64 a2,
	std::string* a3,
	unsigned __int8 a4,
	int a5,
	float a6,
	float a7,
	int a8)
{
	// 游戏原函数会消费传入字符串，必须在调用前保存独立路径。
	const std::string audioPath = a3 ? *a3 : std::string();
	LyricManager_Inst.SetSongAudio(audioPath.c_str());
	char* result = original_LoadSongAudio(a1, a2, a3, a4, a5, a6, a7, a8);
	// 加载完成后使用独立副本绑定歌曲对象，禁止读取已消费的 a3。
	NonVocalManager_Inst.OnSongAudio(result == nullptr ? reinterpret_cast<void*>(a1) : nullptr,
		result == nullptr ? audioPath.c_str() : nullptr);
	// OBS 仅观察已有加载结果，不改变歌曲音频加载或增益。
	if (result == nullptr) ObsManager_Inst.OnSongAudio(audioPath);
	return result;
}

HOOK(INT64, __fastcall, _ChangeGameState, sigChangeGameState(), INT64* a, const char* state) {
	// 状态切换可能释放歌曲对象，音频恢复必须在原函数之前完成。
	NonVocalManager_Inst.OnGameState(state);
	// 结束信号须在原函数切出 PV 画面前发布，避免遗漏单曲结果画面及额外轮询延迟。
	const bool obsEnding = ObsPvSession::IsEndState(state);
	if (obsEnding) ObsManager_Inst.OnGameState(state);
	INT64 result = original_ChangeGameState(a, state);
#ifdef _DEBUG
	LOG(L"Gamestate changed to : %S", state);
#endif // DEBUG
	LyricManager_Inst.UpdateGameState(state);
	if (!obsEnding) ObsManager_Inst.OnGameState(state);
	return result;
}
HOOK(void**, __fastcall, _RenderLyricAndTitle, sigRenderLyricAndTitle(),
	float y,
	float x,
	unsigned int scale,
	int a4,
	const char* text,
	char a6,
	unsigned int a7,
	void** a8)
{
	bool isLyric = y == 172.0f;
	if (isLyric) {
		// 原版歌词开关仅控制游戏渲染文本，KTV 缓存层由独立开关控制。
		const char* displayedText = LyricManager_Inst.showInternalLyrics && text ? text : "";
		return original_RenderLyricAndTitle(y, x, scale, a4, displayedText, a6, a7, a8);
	}
	else {
		return original_RenderLyricAndTitle(y, x, scale, a4, text, a6, a7, a8);
	}
}

HOOK(INT64, __fastcall, _UpdateLyrics, sigUpdateLyrics(), void* this_, int index, void* a3) {
	INT64 result = original_UpdateLyrics(this_, index, a3);
	LyricManager_Inst.UpdateLyricIndex(index);
	return result;
}

HOOK(void*, __fastcall, _GetInputState, sigGetInputState(), int player) {
	// TODO: Use this for ImGui's input handler
	// MM+ uses DirectInput for its main game.
	// But since there's no way to capture all keystrokes with this hook, I'll leave this as is.
	// Turns out dw_gui uses Win32 WndProc to handle K&M input as well...
	void* result = original_GetInputState(player);
	if (result && (ImGui::GetIO().WantCaptureKeyboard || ImGui::GetIO().WantCaptureMouse))
	{
		return original_GetInputState(1);
		// Since there's no player 2...
	}
	return result;
}

void CreateRenderTarget()
{
	ID3D11Texture2D* pBackBuffer;
	g_pSwapChain->GetBuffer(0, IID_PPV_ARGS(&pBackBuffer));
	if (pBackBuffer) {
		g_pd3dDevice->CreateRenderTargetView(pBackBuffer, NULL, &g_mainRenderTargetView);
		pBackBuffer->Release();
	}
}

void CleanupRenderTarget()
{
	if (g_mainRenderTargetView) { g_mainRenderTargetView->Release(); g_mainRenderTargetView = NULL; }
}

#define VK_F 0x46
#define VK_G 0x47
#define VK_L 0x4C
#define VK_S 0x53
#define KEY_PRESSED(K) LOWORD(wParam) == K
#define KEY_PRESSED_WITH_CONTROL(K) KEY_PRESSED(K) && GetKeyState(VK_CONTROL)
extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);
LRESULT WINAPI WndProc(const HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
	if (ImGui_ImplWin32_WndProcHandler(hWnd, uMsg, wParam, lParam))
		return true;
	switch (uMsg) {
	case WM_KEYDOWN:
		if (KEY_PRESSED_WITH_CONTROL(VK_F))
			FontManager_Inst.showGUI = !FontManager_Inst.showGUI;
		if (KEY_PRESSED_WITH_CONTROL(VK_G))
			LyricManager_Inst.showGUI = !LyricManager_Inst.showGUI;
		if (KEY_PRESSED_WITH_CONTROL(VK_S)) {
			Config::SaveGlobalConfig();
			MessageBeep(MB_ICONINFORMATION);
		}
		if (KEY_PRESSED_WITH_CONTROL(VK_L)) {
			Config::LoadGlobalConfig();
			MessageBeep(MB_ICONINFORMATION);
		}
		break;
	case WM_SIZE:
		if (g_pd3dDevice != NULL && wParam != SIZE_MINIMIZED)
		{
			CleanupRenderTarget();
			g_pSwapChain->ResizeBuffers(0, (UINT)LOWORD(lParam), (UINT)HIWORD(lParam), DXGI_FORMAT_UNKNOWN, 0);
			CreateRenderTarget();
		}
		return 0;
	case WM_DESTROY:
		PostQuitMessage(0);
		return 0;
	}
	return CallWindowProc(originalWndProc, hWnd, uMsg, wParam, lParam);
}

void Config::SaveGlobalConfig() {
	FontManager_Inst.ToConfig(GlobalConfig_Inst);
	LyricManager_Inst.ToConfig(GlobalConfig_Inst);
	GlobalConfig_Inst.ImGuiSettings = ImGui::SaveIniSettingsToMemory();
	GlobalConfig_Inst.Save();
}

void Config::LoadGlobalConfig() {
	GlobalConfig_Inst.Load();
	FontManager_Inst.FromConfig(GlobalConfig_Inst);
	LyricManager_Inst.FromConfig(GlobalConfig_Inst);
	if (GlobalConfig_Inst.ImGuiSettings.size() > 0)
		ImGui::LoadIniSettingsFromMemory(GlobalConfig_Inst.ImGuiSettings.c_str());
}

// 将游戏内实际扫描到的关键地址以稳定的 ASCII 格式落盘，供短启动后直接定位版本或初始化问题。
void WriteSignatureDiagnostics() {
	std::ofstream diagnostics(to_utf8(FullPathInDllFolder(L"freelyrics-diagnostics.log")), std::ios::trunc);
	if (!diagnostics.is_open())
		return;

	diagnostics << "MMFreeLyrics signature diagnostics\n";
	diagnostics << "sigChangeGameState=0x" << std::hex << (uint64_t)sigChangeGameStateAddr << "\n";
	diagnostics << "sigRenderLyricAndTitle=0x" << std::hex << (uint64_t)sigRenderLyricAndTitleAddr << "\n";
	diagnostics << "sigLoadSongAudio=0x" << std::hex << (uint64_t)sigLoadSongAudioAddr << "\n";
	diagnostics << "sigUpdateLyrics=0x" << std::hex << (uint64_t)sigUpdateLyricsAddr << "\n";
	diagnostics << "sigGetInputState=0x" << std::hex << (uint64_t)sigGetInputStateAddr << "\n";
	diagnostics << "sigDivaPlayback=0x" << std::hex << (uint64_t)sigDivaPlaybackAddr << "\n";
	diagnostics << "sigDivaPlayback2=0x" << std::hex << (uint64_t)sigDivaPlayback2Addr << "\n";
	diagnostics << "sigPvSelectorApplySel=0x" << std::hex << (uint64_t)sigpv_selector_switch__PvSelector__applySelAddr << "\n";
	diagnostics << "sigCreateTaskWaitScreen=0x" << std::hex << (uint64_t)sigMegaMix__CreateTaskWaitScreenAddr << "\n";
	diagnostics.flush();
}

// 追加 Init 的阶段标记，便于在游戏提前退出后确定最后成功执行的位置。
void WriteInitializationStage(const char* stage) {
	std::ofstream diagnostics(to_utf8(FullPathInDllFolder(L"freelyrics-diagnostics.log")), std::ios::app);
	if (diagnostics.is_open())
		diagnostics << "stage=" << stage << "\n";
}

// 在 DivaModLoader 调用 Init 后扫描游戏模块并绑定全部 Hook 目标；任一签名缺失时拒绝安装，避免解引用空地址。
bool InitializeGameAddresses() {
	sigChangeGameState();
	sigRenderLyricAndTitle();
	sigLoadSongAudio();
	sigUpdateLyrics();
	sigGetInputState();
	sigDivaPlayback();
	sigDivaPlayback2();
	sigpv_selector_switch__PvSelector__applySel();
	sigMegaMix__CreateTaskWaitScreen();
	WriteSignatureDiagnostics();
	if (!sigChangeGameStateAddr || !sigRenderLyricAndTitleAddr || !sigLoadSongAudioAddr ||
		!sigUpdateLyricsAddr || !sigGetInputStateAddr ||
		!sigDivaPlaybackAddr || !sigDivaPlayback2Addr ||
		!sigpv_selector_switch__PvSelector__applySelAddr || !sigMegaMix__CreateTaskWaitScreenAddr) {
		LOG(L"游戏版本签名不完整，已跳过歌词 Hook 以避免游戏崩溃。");
		return false;
	}

	original_ChangeGameState = (__ChangeGameState*)sigChangeGameStateAddr;
	original_RenderLyricAndTitle = (__RenderLyricAndTitle*)sigRenderLyricAndTitleAddr;
	original_LoadSongAudio = (__LoadSongAudio*)sigLoadSongAudioAddr;
	original_UpdateLyrics = (__UpdateLyrics*)sigUpdateLyricsAddr;
	original_GetInputState = (__GetInputState*)sigGetInputStateAddr;
	original_DivaPlayback = (__DivaPlayback*)sigDivaPlaybackAddr;
	getPlaybackStatus2 = (DivaPlaybackStatus2* (__fastcall*)())sigDivaPlayback2Addr;
	getPvSelAddr = (PvSelector* (__fastcall*)())readRelCall16Address((uint64_t)sigpv_selector_switch__PvSelector__applySelAddr + 0x1D0);
	return getPvSelAddr != nullptr;
}

// 工具窗口跟随歌词设置窗口右侧并顶部对齐，宽度适配内容，高度自动收紧。
void DrawPvToolsPanel() {
	if (!LyricManager_Inst.showGUI)
		return;
	const ImGuiViewport* viewport = ImGui::GetMainViewport();
	const float margin = ImGui::GetStyle().ItemSpacing.x;
	const float preferredWidth = ImGui::GetFontSize() * 34.0f;
	ImVec2 panelPos(viewport->WorkPos.x + margin, viewport->WorkPos.y + margin);
	float panelWidth = (std::min)(preferredWidth, viewport->WorkSize.x - margin * 2.0f);
	if (const ImGuiWindow* lyricWindow = ImGui::FindWindowByName("Lyric [Ctrl+G]")) {
		panelPos = ImVec2(lyricWindow->Pos.x + lyricWindow->Size.x + margin, lyricWindow->Pos.y);
		const float rightSpace = viewport->WorkPos.x + viewport->WorkSize.x - panelPos.x - margin;
		if (rightSpace >= ImGui::GetFontSize() * 22.0f)
			panelWidth = (std::min)(preferredWidth, rightSpace);
		else
			panelPos = ImVec2(lyricWindow->Pos.x, lyricWindow->Pos.y + lyricWindow->Size.y + margin);
	}
	ImGui::SetNextWindowPos(panelPos, ImGuiCond_Always);
	ImGui::SetNextWindowSize(ImVec2(panelWidth, 0.0f), ImGuiCond_Always);
	ImGui::SetNextWindowBgAlpha(0.9f);
	if (ImGui::Begin("PV 工具 [Ctrl+G]", nullptr, ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_NoMove)) {
		NonVocalManager_Inst.OnImGUI();
		ObsManager_Inst.OnImGUI();
	}
	ImGui::End();
}
extern "C"
{
	void __declspec(dllexport) D3DInit(IDXGISwapChain* swapChain,
		ID3D11Device* device,
		ID3D11DeviceContext* deviceContext) {
		g_pSwapChain = swapChain;
		g_pd3dDevice = device;
		g_pd3dDeviceContext = deviceContext;

		DXGI_SWAP_CHAIN_DESC m_ChainDesc;
		swapChain->GetDesc(&m_ChainDesc);
		CreateRenderTarget();
		window = m_ChainDesc.OutputWindow;
		originalWndProc = (WNDPROC)SetWindowLongPtrA(window, GWLP_WNDPROC, (LONG_PTR)WndProc);

		ImGui_ImplWin32_Init(window);
		ImGui_ImplDX11_Init(g_pd3dDevice, g_pd3dDeviceContext);
		RECT clientRect{};
		if (GetClientRect(window, &clientRect))
			PrepareKtvCompositeResources(ImVec2((float)(clientRect.right - clientRect.left),
				(float)(clientRect.bottom - clientRect.top)));
	}
	void __declspec(dllexport) Init() {
		// 加载器已离开 loader lock 后才解析 DLL 路径，避免 DllMain 中分配字符串导致加载失败。
		InitializeDllFilePath();
		TraceLoggingRegister(g_divaPerformanceProvider);
		// 全局配置对象只在此处填充默认值，避免 DLL 装载期执行业务初始化。
		GlobalConfig_Inst.LoadDefault();
		if (!InitializeGameAddresses())
			return;
		INSTALL_HOOK(_ChangeGameState);
		WriteInitializationStage("hook-change-game-state");
		INSTALL_HOOK(_RenderLyricAndTitle);
		WriteInitializationStage("hook-render-lyric-and-title");
		INSTALL_HOOK(_LoadSongAudio);
		WriteInitializationStage("hook-load-song-audio");
		INSTALL_HOOK(_UpdateLyrics);
		WriteInitializationStage("hook-update-lyrics");
		INSTALL_HOOK(_GetInputState);
		WriteInitializationStage("hook-get-input-state");
		INSTALL_HOOK(_DivaPlayback);
		WriteInitializationStage("hook-diva-playback");
		ImGui::CreateContext();
		WriteInitializationStage("imgui-context");
		SET_IMGUI_DEFAULT_FLAGS;
		WriteInitializationStage("imgui-default-flags");
		Config::LoadGlobalConfig();
		WriteInitializationStage("config-load");
		LyricManager_Inst.Init(GlobalConfig_Inst);
		WriteInitializationStage("lyric-manager-init");
		FontManager_Inst.Init(GlobalConfig_Inst);
		WriteInitializationStage("font-manager-init");
		// Prepare addresses from sigs
		playbackStatus = new DivaPlaybackStatus; // acquried by the hook
		WriteInitializationStage("playback-status-allocate");
		playbackStatus2 = getPlaybackStatus2();
		WriteInitializationStage("playback-status2-read");
		pvsel = getPvSelAddr();
		WriteInitializationStage("pv-selector-read");
		PVWaitScreenInfo = (PVWaitScreenInfoStruct*)readLongMOVAddress(
			(uint64_t)sigMegaMix__CreateTaskWaitScreenAddr + 0x34
		);
		WriteInitializationStage("wait-screen-read");
		// 工具管理器在地址与 ImGui 就绪后初始化，功能默认关闭。
		NonVocalManager_Inst.Init();
		ObsManager_Inst.Init();
		WriteInitializationStage("pv-tools-init");
	}
	void __declspec(dllexport) OnFrame(IDXGISwapChain* m_pSwapChain) {
		DivaPerformanceScope frameScope("帧总耗时");
		{ DivaPerformanceScope scope("歌词状态"); LyricManager_Inst.OnFrame(); }
		{ DivaPerformanceScope scope("音频控制"); NonVocalManager_Inst.OnFrame(); }
		{ DivaPerformanceScope scope("OBS状态"); ObsManager_Inst.OnFrame(); }
		{ DivaPerformanceScope scope("字体更新"); FontManager_Inst.OnFrame(); }
		{ DivaPerformanceScope scope("透明合成资源预热"); PrepareKtvCompositeResources(ImGui::GetIO().DisplaySize); }

		{
			DivaPerformanceScope scope("图形帧准备及图集上传");
			ImGui_ImplDX11_NewFrame();
			ImGui_ImplWin32_NewFrame();
			ImGui::NewFrame();
		}

		{ DivaPerformanceScope scope("歌词及注音绘制"); LyricManager_Inst.OnImGUI(); }
		{ DivaPerformanceScope scope("字体面板"); FontManager_Inst.OnImGUI(); }
		{ DivaPerformanceScope scope("音频及OBS面板"); DrawPvToolsPanel(); }

		{ DivaPerformanceScope scope("绘制数据生成"); ImGui::Render(); }
		{ DivaPerformanceScope scope("DX11提交及透明合成"); ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData()); }
	}
}
