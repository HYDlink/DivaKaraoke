#include <Windows.h>

// 临时加载探针：仅验证 DivaModLoader 是否会从当前 MMFreeLyrics 配置加载 DLL。
BOOL APIENTRY DllMain(HMODULE, DWORD, LPVOID) {
    return TRUE;
}

extern "C" {
// 保持与正式 Mod 一致的初始化导出接口，供加载器调用。
__declspec(dllexport) void Init() {}

// 保持与正式 Mod 一致的 D3D 初始化导出接口，供加载器调用。
__declspec(dllexport) void D3DInit(void*, void*, void*) {}

// 保持与正式 Mod 一致的逐帧导出接口，供加载器调用。
__declspec(dllexport) void OnFrame(void*) {}
}
