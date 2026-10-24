"""只读审计歌曲音频的实际声道能量，识别空白声道，不推断音频歌手。"""

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np


# 流式计算输入文件哈希，供审计结果绑定具体原始资源。
def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


# 保留原采样率和声道数，完整解码并逐声道累计峰值、非零样本和均方根。
def audit_audio(path):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=codec_name,sample_rate,channels,channel_layout", "-of", "json", str(path)],
        capture_output=True, check=True,
    )
    metadata = json.loads(probe.stdout)["streams"][0]
    channels = metadata["channels"]
    process = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0",
         "-c:a", "pcm_f32le", "-f", "f32le", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # 每次读取完整声道帧；不添加混音、重采样或声道重排滤镜。
    frame_bytes = channels * 4
    pending = b""
    count = 0
    energy = np.zeros(channels, dtype=np.float64)
    peak = np.zeros(channels, dtype=np.float64)
    nonzero = np.zeros(channels, dtype=np.int64)
    # 累计现有模组保留与静音的声道对合成能量，用于识别重复混音。
    group_energy = np.zeros(3, dtype=np.float64)
    comparable_groups = channels in (2, 4, 6, 8)
    try:
        while True:
            block = process.stdout.read(frame_bytes * 65536)
            if not block:
                break
            pending += block
            complete = len(pending) // frame_bytes * frame_bytes
            samples = np.frombuffer(pending[:complete], dtype="<f4").reshape(-1, channels)
            pending = pending[complete:]
            if not len(samples):
                continue
            if not np.isfinite(samples).all():
                raise ValueError("音频解码包含非有限值，拒绝发布结果")
            count += len(samples)
            energy += np.square(samples, dtype=np.float64).sum(axis=0)
            peak = np.maximum(peak, np.abs(samples).max(axis=0))
            nonzero += np.count_nonzero(samples, axis=0)
            if comparable_groups:
                kept = np.zeros((len(samples), 2), dtype=np.float64)
                muted = np.zeros_like(kept)
                for channel in range(0, channels, 2):
                    target = muted if (channel // 2) % 2 else kept
                    target += samples[:, channel:channel + 2]
                group_energy += (np.square(kept).sum(), np.square(muted).sum(), (kept * muted).sum())
        errors = process.stderr.read().decode("utf-8", errors="replace")
        if process.wait() != 0:
            raise RuntimeError("音频解码失败：" + errors)
        if pending or count == 0:
            raise ValueError("音频解码为空或末尾存在不完整声道帧")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
        process.stderr.close()
    channel_results = []
    for index in range(channels):
        rms = math.sqrt(float(energy[index]) / count)
        channel_results.append({
            "channel_index_zero_based": index,
            "sample_count": count,
            "nonzero_samples": int(nonzero[index]),
            "peak": float(peak[index]),
            "rms": rms,
            "rms_dbfs": 20 * math.log10(rms) if rms else None,
            "exact_silence": bool(nonzero[index] == 0),
        })
    # 声道对只表示相邻两个解码声道，不把格式标签当作人声内容证明。
    pairs = []
    for index in range(0, channels, 2):
        indices = list(range(index, min(index + 2, channels)))
        pairs.append({
            "pair_index_zero_based": index // 2,
            "channels_zero_based": indices,
            "exact_silence": all(channel_results[item]["exact_silence"] for item in indices),
        })
    effect = None
    if comparable_groups:
        kept_energy, muted_energy, cross_energy = map(float, group_energy)
        correlation = cross_energy / math.sqrt(kept_energy * muted_energy) if kept_energy and muted_energy else None
        residual = max(0.0, 1 - correlation * correlation) if correlation is not None else None
        effect = {
            "kept_pair_indices": list(range(0, channels // 2, 2)),
            "muted_pair_indices": list(range(1, channels // 2, 2)),
            "kept_rms": math.sqrt(kept_energy / (count * 2)),
            "muted_rms": math.sqrt(muted_energy / (count * 2)),
            "muted_to_kept_db": 10 * math.log10(muted_energy / kept_energy) if kept_energy and muted_energy else None,
            "kept_muted_correlation": correlation,
            "scaled_duplicate_residual_ratio": residual,
            "positive_scaled_duplicate": bool(correlation is not None and correlation > 0 and residual <= 1e-8),
        }
    return {
        "source": str(path.resolve()),
        "sha256": file_sha256(path),
        "metadata": metadata,
        "decoded_duration_seconds": count / int(metadata["sample_rate"]),
        "channels": channel_results,
        "stereo_pairs": pairs,
        "non_vocal_effect": effect,
        "scope": "整首原采样率浮点解码；只判定信号是否存在，不自动识别人声或乐器",
    }


# 解析中文参数说明，并将完整审计结果保存到指定输出文件。
def main():
    parser = argparse.ArgumentParser(description="只读检查歌曲音频是否包含空白声道对")
    # 输入音频参数：可重复指定，以同时审计问题曲目和已知分轨对照。
    parser.add_argument("--audio", type=Path, action="append", required=True, help="待审计原始音频文件，可重复指定")
    # 输出结果文件参数：保存原文件哈希、格式及整首逐声道统计的JSON路径。
    parser.add_argument("--output", type=Path, required=True, help="审计结果JSON输出文件，不修改原始音频")
    args = parser.parse_args()
    try:
        report = {"schema_version": 1, "files": [audit_audio(path) for path in args.audio]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for result in report["files"]:
            silent = [str(item["pair_index_zero_based"]) for item in result["stereo_pairs"] if item["exact_silence"]]
            print(f"{Path(result['source']).name}：{result['metadata']['channels']}声道，完整解码{result['decoded_duration_seconds']:.3f}秒；全零声道对：{'、'.join(silent) if silent else '无'}")
        print(f"审计结果已保存：{args.output}")
    except Exception as error:
        parser.exit(1, f"音频审计失败：{error}\n")


if __name__ == "__main__":
    main()
