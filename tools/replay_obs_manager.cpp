#include <globals.h>
#include <atomic>
#include <thread>
#include <condition_variable>
// 仅在隔离回归中允许检查发布缓存，生产 DLL 保持原成员可见性。
#define private public
#include <managers/obs_manager.h>
#undef private
#include "../Source/managers/obs_manager.cpp"
