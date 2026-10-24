#pragma once
#include <cmath>
#include <cstring>

// 只观察现有游戏信号；不依赖新签名、音频增益或歌词时间线。
struct ObsPvSession {
    bool prepared = false;
    bool active = false;
    bool waitingForReset = false;
    int pvid = -1;
    float previousTime = -1.0f;
    unsigned long long epoch = 0;

    // 自然结束进入结果画面，中途暂停不是结束，不能仅按 isPlaying 判断。
    static bool IsEndState(const char* state) {
        return state && (std::strcmp(state, "GameResultTask") == 0 ||
            std::strcmp(state, "PVsel") == 0 || std::strcmp(state, "PV_WATCH") == 0 ||
            std::strcmp(state, "PV_STAGE") == 0 || std::strcmp(state, "MAINMENU_SWITCH") == 0 ||
            std::strcmp(state, "MENU") == 0 || std::strcmp(state, "STARTUP") == 0);
    }

    // 已有准备事件每次建立新会话，加载/菜单状态只结束旧会话。
    void OnState(const char* state, int selectedPvid) {
        if (!state) return;
        if (std::strcmp(state, "PV POST PROCESS TASK") == 0) {
            prepared = true;
            active = false;
            waitingForReset = false;
            previousTime = -1.0f;
            pvid = selectedPvid;
            ++epoch;
        }
        else if (IsEndState(state)) {
            prepared = active = waitingForReset = false;
            previousTime = -1.0f;
        }
    }

    // 歌曲加载结束旧录像；没有准备事件时必须先看到新曲时钟归零再允许启动。
    void OnSongLoaded() {
        if (active) ++epoch;
        active = prepared = false;
        waitingForReset = true;
        previousTime = -1.0f;
    }

    // 暂停不分文件；曲目变更或播放时回到开头建立新会话，保持原来的递增启动时机。
    void OnFrame(bool viewer, int selectedPvid, bool playing, float now) {
        if (!viewer) {
            active = prepared = waitingForReset = false;
            previousTime = -1.0f;
            return;
        }
        if (!std::isfinite(now) || now < 0.0f) return;
        if (waitingForReset) {
            if (!playing || now > 1.0f) return;
            waitingForReset = false;
            prepared = true;
        }
        if (!prepared) return;
        if (pvid != selectedPvid || (active && playing && now <= 1.0f && previousTime > 2.0f)) {
            pvid = selectedPvid;
            active = false;
            ++epoch;
            previousTime = -1.0f;
        }
        if (!active && playing && previousTime >= 0.0f && now > previousTime) active = true;
        previousTime = now;
    }
};
