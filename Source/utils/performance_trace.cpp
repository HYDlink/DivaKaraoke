#include <utils/performance_trace.h>

// 固定 GUID 只用于本 Mod 的本地诊断，字段可由 WPA 或 PerfView 读取。
TRACELOGGING_DEFINE_PROVIDER(g_divaPerformanceProvider, "DivaKaraoke.Performance",
    (0x8ce8f03d, 0xd445, 0x4c7e, 0x90, 0xe9, 0x13, 0x1a, 0xff, 0x5d, 0x1b, 0x34));
