#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从已有歌词缓存来源自动生成逐行歌手旁路文件，不解包、不修改字幕或游戏。"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import extract_native_lyric_timeline as extractor

ROOT = Path(__file__).resolve().parents[1]


def parse_arguments() -> argparse.Namespace:
    """读取可重复使用的缓存输入及研究输出参数，不扫描全曲或自动部署。"""
    parser = argparse.ArgumentParser(description="自动生成单人及多人组合的口型推测歌手标记。")
    # 输入缓存参数：可重复指定；使用缓存中已有的DSC和文本表来源。
    parser.add_argument("--cache", type=Path, action="append", help="已有PV歌词JSON，可重复指定。")
    # 批量输入参数：自动扫描成功缓存中的有效曲目，不指定PV名单。
    parser.add_argument("--cache-dir", type=Path, help="已有成功歌词缓存目录，自动扫描不同身份的多角色PV。")
    # 人工修订目录参数：单独保存可反复使用的修订，不覆盖自动结果源文件。
    parser.add_argument("--manual-dir", type=Path, help="可选人工歌手修订目录；自动创建未存在的修订模板。")
    # 输出结果目录参数：保存歌手TSV、审计JSON和中文校对稿，不覆盖SRT/Ruby。
    parser.add_argument("--output-dir", type=Path, required=True, help="UTF-8歌手旁路与报告输出目录。")
    # 核对参数：仅检查同曲的已存在其他难度，缺失时记录，不解包补齐。
    parser.add_argument("--verify-difficulties", action="store_true", help="比较同曲已存在难度的歌手标记。")
    # 活动阈值参数：对普通行要求至少这么多口型事件，短于1.2秒的行使用至多3次。
    parser.add_argument("--min-events", type=int, default=6, help="普通行的最少活动事件数量，默认6；不是音频准确率。")
    args = parser.parse_args()
    if bool(args.cache) == bool(args.cache_dir):
        parser.error("请且仅请指定 --cache 或 --cache-dir。")
    return args


def digest(path: Path) -> dict:
    """记录输入文件哈希，防止把不同来源误当成相同的歌手时间线。"""
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def read_commands(path: Path, opcode_db: Path) -> tuple[list[dict], list[tuple[int, int]], int | None]:
    """通过生产读取器的观察器收集命令，不实现另一套二进制解析器。"""
    database = json.loads(opcode_db.read_text(encoding="utf-8"))
    names = {int(value["info_FT"]["id"]): name for name, value in database.items() if "info_FT" in value}
    commands = []

    def observe(index, offset, opcode, time, parameters):
        """接收现有读取器解码后的完整命令，保留复核所需偏移。"""
        commands.append({"index": index, "offset": offset, "name": names[opcode], "raw_time": time, "params": list(parameters)})

    events, end = extractor.read_lyric_events(path, extractor.load_opcode_lengths(opcode_db, "ft"), "ft", observe)
    if 4 + sum(4 * (len(command["params"]) + 1) for command in commands) != path.stat().st_size:
        raise ValueError("DSC未被完整读取，拒绝生成歌手标记。")
    branch, context = 0, None
    for command in commands:
        if command["name"] == "PV_BRANCH_MODE":
            branch = command["params"][0]
        if command["name"] == "SET_CHARA":
            context = command["params"][0]
        command["branch"] = branch
        command["context"] = context
    return commands, events, end


@lru_cache(maxsize=64)
def read_performer_table(path: Path, modified_ns: int, size: int) -> dict:
    """按路径/修改时间/大小缓存角色表索引，一次运行只读取每份数据库一次。"""
    records = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"^pv_(\d+)\.(performer\..+|song_name)=(.*)$", line)
        if match:
            records.setdefault(int(match[1]), {}).setdefault(match[2], match[3])
    return records


def read_performers(paths: list[Path], pv_id: int) -> tuple[str, dict[int, str], dict]:
    """按缓存的文本表优先序读取角色，并递归合并复制角色而不排除GUEST。"""
    fields = {}
    for path in paths:
        stat = path.stat()
        for key, value in read_performer_table(path.resolve(), stat.st_mtime_ns, stat.st_size).get(pv_id, {}).items():
            fields.setdefault(key, value)
    count = int(fields.get("performer.num", 0))
    if not 1 <= count <= 64:
        raise ValueError("文本表中没有可用的角色数量。")
    resolved = {}

    def resolve(slot: int, visiting: set[int]) -> str:
        """递归解析复制槽位；发现环、越界或未知身份时保持未识别。"""
        if slot in visiting or not 0 <= slot < count:
            return ""
        key = f"performer.{slot}."
        kind = fields.get(key + "type", "")
        if kind == "PSEUDO_SAME":
            parent = int(fields.get(key + "pseudo_same_id", "0"))
            return resolve(parent, visiting | {slot})
        identity = fields.get(key + "chara", "")
        return identity if re.fullmatch(r"[A-Z][A-Z0-9_]{0,31}", identity) else ""

    for slot in range(count):
        resolved[slot] = resolve(slot, set())
    return fields.get("song_name", f"PV{pv_id:03d}"), resolved, fields


def choose_activity_poses(mouths: list[dict]) -> dict:
    """保留工具已知姿态并按本文件频率扩展候选，未知扩展不冒充音素语义。"""
    counts = Counter(command["pose"] for command in mouths)
    neutral = 28 if counts[28] > counts[8] else 8
    documented = {24, 25, 31, 32} if neutral == 28 else {0, 1, 2, 5, 10, 11}
    # 频繁的来源专用姿态可作为活动代理；偶发表情不能因出现过就算演唱。
    minimum = max(8, math.ceil(len(mouths) * 0.04))
    inferred = {pose for pose, count in counts.items() if count >= minimum and pose != neutral} - documented
    # 只有主体序列采用另一套编号时才扩展，避免把偶发的表情编号当作元音。
    if sum(counts[pose] for pose in documented) >= len(mouths) * 0.30 or sum(counts[pose] for pose in inferred) < len(mouths) * 0.40:
        inferred = set()
    return {"neutral": neutral, "documented": sorted(documented), "inferred": sorted(inferred), "active": sorted(documented | inferred), "counts": dict(counts), "note": "频率扩展仅是口型活动推测，不是已确认音素或音频歌手。"}


def sparse_activity_support(entries_by_slot: dict[int, list[dict]], duration: int) -> dict[int, dict]:
    """仅供整行证据不足时补判：要求覆盖大半行的变化序列，或两槽重复同步变化。"""
    support = {slot: {"sustained": False, "synchronized_with": []} for slot in entries_by_slot}
    for slot, entries in entries_by_slot.items():
        span = (entries[-1]["raw_time"] - entries[0]["raw_time"]) / 100 if entries else 0
        support[slot]["sustained"] = (len(entries) >= 3 and len({entry["pose"] for entry in entries}) >= 2
                                            and span >= max(600, duration * 0.60))
    for slot, entries in entries_by_slot.items():
        for other, candidates in entries_by_slot.items():
            if slot >= other or min(len(entries), len(candidates)) < 3:
                continue
            # 同姿态事件一对一匹配，允许30毫秒演出偏移；一条事件不能重复充数。
            matched, used = [], set()
            for entry in entries:
                nearby = [candidate for candidate in candidates if candidate["index"] not in used
                          and candidate["pose"] == entry["pose"]
                          and abs(candidate["raw_time"] - entry["raw_time"]) <= 3000]
                if nearby:
                    closest = min(nearby, key=lambda candidate: abs(candidate["raw_time"] - entry["raw_time"]))
                    used.add(closest["index"])
                    matched.append(entry)
            if (len(matched) >= 3 and len(matched) >= max(len(entries), len(candidates)) * 0.80
                    and len({entry["pose"] for entry in matched}) >= 2
                    and (matched[-1]["raw_time"] - matched[0]["raw_time"]) / 100 >= 600):
                support[slot]["synchronized_with"].append({"slot": other, "matched_events": len(matched)})
                support[other]["synchronized_with"].append({"slot": slot, "matched_events": len(matched)})
    return support


def classify_lines(lines: list[dict], commands: list[dict], performers: dict[int, str], min_events: int = 6) -> tuple[list[dict], dict]:
    """以两种分支一致结果标记行级参与者，过滤短边界事件并去重相同身份。"""
    mouths = []
    for command in commands:
        if command["name"] == "MOUTH_ANIM":
            slot, pose = command["params"][0], command["params"][2]
        elif command["name"] == "EDIT_MOUTH_ANIM" and command["context"] is not None:
            slot, pose = command["context"], command["params"][0]
        elif command["name"] == "EDIT_MOUTH":
            raise ValueError("发现尚未支持的EDIT_MOUTH格式，拒绝猜测。")
        else:
            continue
        mouths.append({**command, "slot": slot, "pose": pose})
    profile = choose_activity_poses(mouths)
    rows = []
    branches = (1, 2) if any(command["branch"] in (1, 2) for command in mouths) else (0,)
    for index, line in enumerate(lines, 1):
        duration = int(line["end_ms"]) - int(line["start_ms"])
        margin = 0
        branch_results, evidence, branch_samples = [], [], []
        for branch in branches:
            samples = [command for command in mouths if command["branch"] in (0, branch)
                       and (line["start_ms"] + margin) * 100 <= command["raw_time"] < (line["end_ms"] - margin) * 100
                       and command["pose"] in profile["active"]]
            totals = Counter(command["slot"] for command in samples)
            branch_samples.append({slot: sorted([command for command in samples if command["slot"] == slot],
                                                key=lambda command: (command["raw_time"], command["index"]))
                                   for slot in performers})
            selected = []
            for slot in sorted(performers):
                entries = [command for command in samples if command["slot"] == slot]
                span_ms = (max(command["raw_time"] for command in entries) - min(command["raw_time"] for command in entries)) / 100 if entries else 0
                # 活动必须持续且有足够事件，单个跨句动作不直接产生第二歌手。
                qualifies = len(entries) >= (min(3, min_events) if duration < 1200 else min_events) and span_ms >= min(120, duration * 0.15)
                qualifies = qualifies and len(entries) >= max(totals.values(), default=0) * 0.15
                if qualifies and performers[slot] and performers[slot] not in selected:
                    selected.append(performers[slot])
                evidence.append({"branch": branch, "slot": slot, "chara": performers[slot], "events": len(entries), "span_ms": span_ms, "selected": qualifies, "command_indices": [command["index"] for command in entries]})
            branch_results.append(selected)
        sparse_selected = False
        # 仅补救原本整行未知的情况；已有主唱时，少量伴随动作仍受原六次门槛过滤。
        if not any(branch_results):
            for position, branch in enumerate(branches):
                support = sparse_activity_support(branch_samples[position], duration)
                for item in [item for item in evidence if item["branch"] == branch]:
                    detail = support[item["slot"]]
                    item["sparse_support"] = detail
                    item["selected"] = bool(detail["sustained"] or detail["synchronized_with"])
                    if item["selected"] and item["chara"] and item["chara"] not in branch_results[position]:
                        branch_results[position].append(item["chara"])
                        sparse_selected = True
        unique_identities = list(dict.fromkeys(identity for identity in performers.values() if identity))
        singers = branch_results[0] if all(set(item) == set(branch_results[0]) for item in branch_results) else []
        # 只有一个不同歌手身份时可由歌曲角色表归属，复制角色不制造假合唱。
        if len(unique_identities) == 1:
            singers = unique_identities
        reason = ("branch_conflict" if any(set(item) != set(branch_results[0]) for item in branch_results)
                  else "sparse_activity_proxy" if singers and sparse_selected
                  else "activity_proxy" if singers else "insufficient_evidence")
        rows.append({"line": index, **line, "singers": singers, "classification": "multiple" if len(singers) > 1 else "single" if singers else "unknown", "reason": reason, "evidence": evidence})
    profile["unmapped_slots"] = sorted({command["slot"] for command in mouths} - set(performers))
    profile["mouth_count"] = len(mouths)
    profile["sparse_policy"] = {"scope": "仅所有分支均未选出歌手的行", "minimum_events": 3,
                               "minimum_distinct_poses": 2, "sustained_coverage": 0.60,
                               "minimum_span_ms": 600, "sync_tolerance_ms": 30, "sync_match_ratio": 0.80}
    return rows, profile


def apply_manual_singers(rows: list[dict], pv_id: int, performers: dict[int, str], directory: Path | None) -> dict | None:
    """创建独立修订模板；只覆盖显式标记且时间/全文仍匹配的行，保留原自动判断。"""
    if directory is None:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"PV{pv_id:03d}.singers.manual.tsv"
    if not path.exists():
        lines = [f"# singers-manual-v1\t{pv_id}\t{len(rows)}", "# 仅修改第四列：auto=自动；LEN=镜音连；KAI=KAITO；LEN,KAI=合唱；-=默认色。", "# 身份：" + ", ".join(dict.fromkeys(performers.values())), "# 行号\t开始毫秒\t结束毫秒\t人工歌手\t歌词全文"]
        lines += [f"{row['line']}\t{row['start_ms']}\t{row['end_ms']}\tauto\t{row['text']}" for row in rows]
        with path.open("x", encoding="utf-8", newline="") as output:
            output.write("\n".join(lines) + "\n")
    records = path.read_text(encoding="utf-8-sig").splitlines()
    overrides, seen = [], set()
    for record in records:
        if not record or record.startswith("#"):
            continue
        fields = record.split("\t", 4)
        if len(fields) != 5:
            raise ValueError(f"{path.name}人工修订必须为五列。")
        number, start, end = (int(value) for value in fields[:3])
        if number in seen:
            raise ValueError(f"{path.name}存在重复行号{number}。")
        seen.add(number)
        if fields[3].strip() == "auto":
            continue
        if not 1 <= number <= len(rows):
            raise ValueError(f"{path.name}人工修订行号越界：{number}。")
        row = rows[number - 1]
        if (start, end, fields[4]) != (row["start_ms"], row["end_ms"], row["text"]):
            raise ValueError(f"{path.name}第{number}行时间或全文已变化，拒绝错行套用人工修订。")
        identities = [] if fields[3].strip() == "-" else [value.strip() for value in fields[3].split(",")]
        if any(not re.fullmatch(r"[A-Z][A-Z0-9_]{0,31}", value) for value in identities) or len(identities) != len(set(identities)):
            raise ValueError(f"{path.name}第{number}行歌手格式无效；使用英文逗号连接身份。")
        overrides.append((row, identities))
    if overrides and (not records or records[0] != f"# singers-manual-v1\t{pv_id}\t{len(rows)}"):
        raise ValueError(f"{path.name}曲目或行数不匹配，拒绝旧版人工修订。")
    for row, identities in overrides:
        row["auto_singers"], row["auto_reason"] = row["singers"], row["reason"]
        row["singers"], row["reason"] = identities, "manual_override"
        row["classification"] = "multiple" if len(identities) > 1 else "single" if identities else "unknown"
    return {**digest(path), "overrides": len(overrides)}


def generate(cache_path: Path, output_dir: Path, verify: bool, min_events: int = 6, manual_dir: Path | None = None) -> dict:
    """验证输入同源后生成强绑定字幕文本的旁路文件与审计，不写游戏安装目录。"""
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    pv_id = int(cache["pv_id"])
    source = cache["source"]
    dsc = Path(source["dsc"])
    db_paths = [Path(path) for path in source["pv_db"]]
    opcode_db = Path(source["opcode_db"])
    commands, events, end = read_commands(dsc, opcode_db)
    rebuilt = extractor.build_lines(events, extractor.load_lyrics(db_paths, pv_id, True), end)
    lines = [line for line in cache["lines"] if line["text"].strip()]
    fields = ("start_ms", "end_ms", "lyric_id", "text")
    if [tuple(line[key] for key in fields) for line in lines] != [tuple(line[key] for key in fields) for line in rebuilt if line["text"].strip()]:
        raise ValueError(f"PV{pv_id:03d}缓存与来源重新解析不一致。")
    title, performers, performer_fields = read_performers(db_paths, pv_id)
    if not 1 <= min_events <= 100:
        raise ValueError("活动阈值必须在1至100之间。")
    rows, profile = classify_lines(lines, commands, performers, min_events)
    comparisons = []
    if verify:
        for difficulty in ("easy", "hard", "extreme"):
            path = dsc.with_name(dsc.name.replace("_normal.dsc", f"_{difficulty}.dsc"))
            if not path.is_file():
                comparisons.append({"difficulty": difficulty, "missing": True})
                continue
            other, other_events, _ = read_commands(path, opcode_db)
            other_rows, _ = classify_lines(lines, other, performers, min_events)
            comparisons.append({"difficulty": difficulty, "input": digest(path), "labels_match": [row["singers"] for row in rows] == [row["singers"] for row in other_rows], "lyric_events_match": events == other_events})
    manual = apply_manual_singers(rows, pv_id, performers, manual_dir)
    report = {"manual": manual, "schema_version": 1, "pv_id": pv_id, "title": title, "algorithm": "mouth-activity-v2", "min_events": min_events, "validation": "口型推测；非音频声部真值", "inputs": {"cache": digest(cache_path), "dsc": digest(dsc), "pv_db": [digest(path) for path in db_paths], "opcode_db": digest(opcode_db)}, "performers": performers, "performer_fields": performer_fields, "profile": profile, "difficulty_checks": comparisons, "lines": rows, "commands": commands}
    output_dir.mkdir(parents=True, exist_ok=True)
    records = [f"# singers-v1\t{pv_id}\t{len(rows)}"]
    records += [f"# performer\t{slot}\t{identity}" for slot, identity in performers.items() if identity]
    for row in rows:
        if any(char in row["text"] for char in "\r\n"):
            raise ValueError("歌词包含TSV控制字符，不能生成歧义旁路。")
        records.append(f"{row['line']}\t{row['start_ms']}\t{row['end_ms']}\t{','.join(row['singers']) or '-'}\t{row['text']}")
    stem = f"PV{pv_id:03d}"
    (output_dir / f"{stem}.singers.tsv").write_text("\n".join(records) + "\n", encoding="utf-8")
    (output_dir / f"{stem}.singers.audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    review = [f"# {title}（{stem}）自动歌手标记", "", "标记为口型活动推测，未知行沿用默认颜色；多人表示行内参与，不保证同词合唱。", "", "| 行 | 秒 | 标记 | 原因 | 歌词 |", "| --- | --- | --- | --- | --- |"]
    for row in rows:
        reason = {"activity_proxy": "活动证据", "sparse_activity_proxy": "持续/同步活动补判", "branch_conflict": "分支冲突", "insufficient_evidence": "证据不足", "manual_override": "人工修订"}[row["reason"]]
        text = row["text"].replace("|", "\\|")
        review.append(f"| {row['line']} | {row['start_ms']/1000:.3f}–{row['end_ms']/1000:.3f} | {'+'.join(row['singers']) or '默认'} | {reason} | {text} |")
    (output_dir / f"{stem}.singers.md").write_text("\n".join(review) + "\n", encoding="utf-8")
    return report


def scan_cache_performers(cache_dir: Path) -> list[dict]:
    """依据成功导出清单扫描角色，复制槽归并，资料不完整时明确记录而不猜曲名。"""
    manifest = cache_dir / "export-manifest.json"
    if manifest.is_file():
        ids = [int(entry["pv_id"]) for entry in json.loads(manifest.read_text(encoding="utf-8"))["entries"]]
    else:
        ids = [int(path.stem[2:]) for path in sorted(cache_dir.glob("PV*.json")) if re.fullmatch(r"PV\d+", path.stem)]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("缓存曲目清单为空或存在重复PV编号。")
    records = []
    for pv_id in sorted(ids):
        path = cache_dir / f"PV{pv_id:03d}.json"
        cache = json.loads(path.read_text(encoding="utf-8"))
        if int(cache["pv_id"]) != pv_id:
            raise ValueError(f"PV{pv_id:03d}缓存编号与文件名不一致。")
        record = {"pv_id": pv_id, "cache": str(path), "identities": []}
        try:
            title, slots, fields = read_performers([Path(value) for value in cache["source"]["pv_db"]], pv_id)
            identities = list(dict.fromkeys(identity for identity in slots.values() if identity))
            record.update(title=title, identities=identities, performers=slots)
            record["unresolved_slots"] = [slot for slot, identity in slots.items() if not identity]
            record["status"] = "candidate" if len(identities) > 1 else "incomplete" if not all(slots.values()) else "single_identity"
            if record["status"] == "incomplete":
                record["reason"] = "角色身份或复制关系不完整，保留默认配色。"
        except (ValueError, OSError, KeyError) as error:
            record.update(status="metadata_unavailable", reason=str(error))
        records.append(record)
    return records


def generate_cache_singers(cache_dir: Path, output_dir: Path, verify: bool = False, manual_dir: Path | None = None, min_events: int = 6) -> dict:
    """自动扫描全部有效PV，仅为多个不同身份生成歌手旁路；人工修订单独保存。"""
    records = scan_cache_performers(cache_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    totals = Counter()
    for record in records:
        if record["status"] != "candidate":
            continue
        report = generate(Path(record["cache"]), output_dir, verify, min_events, manual_dir)
        record["status"] = "generated"
        counts = Counter(row["classification"] for row in report["lines"])
        record["lines"] = {key: counts[key] for key in ("single", "multiple", "unknown")}
        record["manual_lines"] = report["manual"]["overrides"] if report["manual"] else 0
        record["unmapped_slots"] = report["profile"]["unmapped_slots"]
        record["difficulty_checks"] = report["difficulty_checks"]
        stem = f"PV{record['pv_id']:03d}"
        record["files"] = [stem + suffix for suffix in (".singers.tsv", ".singers.audit.json", ".singers.md")]
        totals.update(counts)
        print(f"自动生成：{record['title']}（{stem}），单人{counts['single']}句、多人{counts['multiple']}句、默认{counts['unknown']}句。")
    statuses = Counter(record["status"] for record in records)
    summary = {"schema_version": 1, "selection": "最终有效歌词缓存→角色身份/复制关系→多个不同身份", "scanned": len(records), "generated": statuses["generated"], "single_identity": statuses["single_identity"], "unresolved": statuses["incomplete"] + statuses["metadata_unavailable"], "line_counts": dict(totals), "records": records}
    (output_dir / "singer-scan.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = ["# 自动多歌手扫描", "", f"扫描{len(records)}首，生成{statuses['generated']}首；同身份{statuses['single_identity']}首；资料不明确{summary['unresolved']}首。", "", "口型活动是声部推测；回忆演出及无声动作仍可能漏判或误判。", "", "| PV | 曲名 | 不同身份 | 结果 |", "| --- | --- | --- | --- |"]
    labels = {"generated": "已生成", "single_identity": "同身份，跳过", "incomplete": "身份不完整", "metadata_unavailable": "角色资料不可用"}
    for record in records:
        title = record.get("title", "").replace("|", "\\|")
        rows.append(f"| PV{record['pv_id']:03d} | {title} | {'+'.join(record['identities'])} | {labels[record['status']]} |")
    (output_dir / "singer-scan.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"歌手扫描完成：{len(records)}首，自动生成{statuses['generated']}首，同身份跳过{statuses['single_identity']}首，资料不明确{summary['unresolved']}首。")
    return summary


def main() -> int:
    """执行指定缓存的自动标记，所有控制台摘要使用中文。"""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    arguments = parse_arguments()
    try:
        if arguments.cache_dir:
            generate_cache_singers(arguments.cache_dir, arguments.output_dir, arguments.verify_difficulties, arguments.manual_dir, arguments.min_events)
            return 0
        for cache in arguments.cache:
            report = generate(cache, arguments.output_dir, arguments.verify_difficulties, arguments.min_events, arguments.manual_dir)
            counts = Counter(row["classification"] for row in report["lines"])
            print(f"完成：{report['title']}，单人{counts['single']}句，多人{counts['multiple']}句，默认{counts['unknown']}句。")
            if any(not check.get("missing") and not check["labels_match"] for check in report["difficulty_checks"]):
                print("提示：不同难度的标记有差异，请查看审计；当前输出仅适用于输入缓存的来源。")
        print(f"输出目录：{arguments.output_dir.resolve()}")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"生成失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
