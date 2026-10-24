#define IMGUI_DEFINE_MATH_OPERATORS
#include <globals.h>
#include <managers/font_manager.h>
#include <srtparser/srtparser.h>
// 测试入口和生产定义使用相同的成员可见性，保持 MSVC 修饰名一致。
#define private public
#include <managers/lyric_manager.h>
#undef private
#ifdef PERFORMANCE_LEGACY_NATIVE
#include "../artifacts/performance-investigation/baseline-source/lyric_manager.cpp"
#else
#include "../Source/managers/lyric_manager.cpp"
#endif
