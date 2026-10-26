#include <globals.h>
#include <filesystem>
#include <cstdio>

// 验证新目录缺少配置时，生产配置代码可以首次保存、读取并保留用户字段。
int wmain(int argc, wchar_t** argv) {
    if (argc != 2) return 2;
    const std::filesystem::path root = std::filesystem::absolute(argv[1]);
    std::filesystem::create_directories(root);
    wcscpy_s(DllFilePathBuffer, (root / L"DivaKaraoke.dll").c_str());
    Config config;
    config.LoadDefault();
    if (std::filesystem::exists(root / L"freelyrics.toml")) return 3;
    if (!config.Save() || !config.Load()) return 4;
    config.fontSize = 78.0f;
    std::ofstream marker(root / L"freelyrics.toml", std::ios::app);
    marker << "\nuserMarker = \"保留用户设置\"\n";
    marker.close();
    if (!config.Save()) return 5;
    Config restored;
    if (!restored.Load() || restored.fontSize != 78.0f) return 6;
    auto saved = toml::parse((root / L"freelyrics.toml").string());
    if (toml::find<std::string>(saved, "userMarker") != "保留用户设置") return 7;
    puts("新目录首次保存、配置重读和用户字段保留验证通过。");
    return 0;
}
