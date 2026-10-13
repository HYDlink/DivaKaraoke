#include <Windows.h>
#include <cstdio>

// 最小 DLL 加载宿主：仅调用 LoadLibraryW 并输出 Windows 错误码，供调试器定位装载期失败。
int wmain(int argc, wchar_t** argv) {
    if (argc != 2) {
        fwprintf(stderr, L"用法：dll_load_harness <DLL 路径>\n");
        return 2;
    }

    HMODULE module = LoadLibraryW(argv[1]);
    if (module == nullptr) {
        fwprintf(stderr, L"LoadLibraryW 失败；Windows 错误码=%lu\n", GetLastError());
        return 1;
    }

    fwprintf(stdout, L"LoadLibraryW 成功；模块地址=%p\n", module);
    FreeLibrary(module);
    return 0;
}
