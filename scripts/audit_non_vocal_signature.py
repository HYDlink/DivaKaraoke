"""只读审计已验证歌曲声道音量函数的签名唯一性，不解包或启动游戏。"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


# 从模块代码取出实际签名，避免审计使用另一份不同的字节串。
def read_signature(source: Path) -> bytes:
    text = source.read_text(encoding="utf-8")
    encoded = re.search(r'const char\* signature = "([^"]+)";', text).group(1)
    mask = re.search(r'sigScan\(signature, "([^"]+)"', text).group(1)
    signature = bytes.fromhex(encoded.replace("\\x", ""))
    if len(signature) != len(mask) or set(mask) != {"x"}:
        raise ValueError("签名和掩码长度不一致，或包含未审计通配符")
    return signature


# 在用户本机 EXE 中审计唯一性和整函数语义关键指令，不写入游戏目录。
def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="只读核查人声音量函数签名")
    # 用户已有 MM+ 可执行文件，只读输入。
    parser.add_argument("--game-exe", type=Path, required=True, help="本机游戏 EXE 的只读路径")
    # 审计 JSON 输出文件，默认写入工作区产物目录。
    parser.add_argument("--output", type=Path, default=Path("artifacts/non-vocal-research/signature-audit.json"), help="审计结果 JSON 输出文件")
    args = parser.parse_args()
    signature = read_signature(Path(__file__).resolve().parents[1] / "Source/managers/non_vocal_manager.cpp")
    data = args.game_exe.read_bytes()
    hits = []
    position = 0
    while True:
        position = data.find(signature, position)
        if position < 0:
            break
        hits.append(position)
        position += 1
    if len(hits) != 1:
        raise ValueError(f"签名不是唯一命中：{len(hits)}")
    function = data[hits[0]:hits[0] + 0x5C]
    # 0x3A：歌曲对象+0xE8指向OGG wrapper；0x4A：调用OGG声道对增益接口。
    if function[0x3A:0x41] != bytes.fromhex("48 8b 8b e8 00 00 00") or function[0x4A] != 0xE8 or function[-1] != 0xC3:
        raise ValueError("函数尾部语义关键指令与反汇编证据不同")
    report = {"status": "离线签名唯一性与关键指令已验证", "game_exe_sha256": hashlib.sha256(data).hexdigest(), "signature_length": len(signature), "hits": len(hits), "file_offset": hex(hits[0]), "function_length": len(function), "function_sha256": hashlib.sha256(function).hexdigest(), "runtime_status": "尚需游戏内验收"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"人声音量函数唯一命中；签名 {len(signature)} 字节；函数 {len(function)} 字节。")
    print(f"审计结果已写入：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
