#include "../Source/managers/obs_session.h"
#include <cstdio>

// 检查核心会话边界；失败时只输出中文，不访问真实游戏或 OBS。
int main() {
    ObsPvSession session;
    session.OnState("PV POST PROCESS TASK", 424);
    session.OnFrame(true, 424, true, 0.0f);
    if (session.active) return 1;
    session.OnFrame(true, 424, true, 0.1f);
    if (!session.active) return 2;
    auto first = session.epoch;
    session.OnFrame(true, 424, true, 100.0f);
    session.OnState("PAUSE_MENU_SWITCH", 424);
    session.OnFrame(true, 424, false, 100.0f);
    if (!session.active || session.epoch != first) return 3;
    // 不返回 PVsel 的不同歌曲连续切换。
    session.OnSongLoaded();
    if (session.active) return 4;
    session.OnFrame(true, 824, true, 100.0f);
    if (session.active || session.prepared) return 5;
    session.OnState("PV POST PROCESS TASK", 824);
    session.OnFrame(true, 824, true, 0.0f);
    session.OnFrame(true, 824, true, 0.1f);
    if (!session.active || session.pvid != 824 || session.epoch == first) return 6;
    // 没有再次发出准备事件时，同曲加载必须等时钟归零再开始。
    session.OnFrame(true, 824, true, 100.0f);
    first = session.epoch;
    session.OnSongLoaded();
    session.OnFrame(true, 824, true, 100.1f);
    if (session.active) return 7;
    session.OnFrame(true, 824, true, 0.0f);
    session.OnFrame(true, 824, true, 0.1f);
    if (!session.active || session.epoch == first) return 8;
    // 不发歌曲加载或准备事件，仍能识别同曲播放中的时钟重置。
    session.OnFrame(true, 824, true, 100.0f);
    first = session.epoch;
    session.OnFrame(true, 824, true, 0.0f);
    session.OnFrame(true, 824, true, 0.1f);
    if (!session.active || session.epoch == first) return 9;
    session.OnState("PVsel", -1);
    session.OnFrame(false, -1, false, 0.0f);
    if (session.active || session.prepared) return 10;
    session.OnFrame(true, 424, true, 50.0f);
    if (session.active) return 11;
    puts("OBS 会话回归通过：连续切歌、同曲循环、旧时钟保护、暂停及退出；未运行游戏。");
    return 0;
}
