#pragma once
#include <string_view>

// 用户实机确认的10首默认音源；仅供支持提示，不参与音量、Hook或录像控制。
inline constexpr std::string_view kConfirmedNonVocalExceptionFiles[] = {
    "pv_255.ogg", "pv_261.ogg", "pv_263.ogg", "pv_274.ogg", "pv_603.ogg",
    "pv_643.ogg", "pv_731.ogg", "pv_818.ogg", "pv_70210.ogg", "pv_70211_sekai.ogg"
};

// 按实际加载文件名匹配已确认音源，兼容路径分隔符与大小写，避免误标其他换唱。
inline bool IsConfirmedNonVocalException(std::string_view path) {
    const auto separator = path.find_last_of("/\\");
    const auto filename = separator == std::string_view::npos ? path : path.substr(separator + 1);
    for (const auto known : kConfirmedNonVocalExceptionFiles) {
        if (filename.size() != known.size())
            continue;
        bool matches = true;
        for (size_t index = 0; index < filename.size(); ++index) {
            const char value = filename[index];
            const char lower = value >= 'A' && value <= 'Z' ? value + ('a' - 'A') : value;
            if (lower != known[index]) {
                matches = false;
                break;
            }
        }
        if (matches)
            return true;
    }
    return false;
}
