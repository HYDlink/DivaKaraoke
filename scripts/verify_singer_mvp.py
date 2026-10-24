#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核对歌手MVP的真实样本、分支拒绝、少量动作过滤与角色归并。"""
import json
from pathlib import Path
import sys
import tempfile

import build_singer_timeline as generator

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    """断言业务条件，并在失败时使用中文描述具体原因。"""
    if not condition:
        raise ValueError(message)


def commands(slot: int, branch: int, count: int) -> list[dict]:
    """生成连续口型样本，包含真实观察器相同的序号与参数字段。"""
    return [{"index": slot * 100 + index, "name": "MOUTH_ANIM", "branch": branch, "context": None,
             "raw_time": 10000 + index * 20000, "params": [slot, 0, (0, 1, 2)[index % 3], 120, 1000]}
            for index in range(count)]


def main() -> int:
    """验证隔离样本和已有六曲审计，不触碰游戏或生产缓存。"""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        sample = [{"start_ms": 0, "end_ms": 2000}]
        row = generator.classify_lines(sample, commands(0, 0, 6) + commands(1, 0, 4), {0: "MIK", 1: "LUK"})[0][0]
        require(row["singers"] == ["MIK"], "四次第二歌手动作产生假合唱")
        row = generator.classify_lines(sample, commands(0, 0, 6) + commands(1, 0, 6), {0: "MIK", 1: "LUK"})[0][0]
        require(row["singers"] == ["MIK", "LUK"], "双槽持续活动未保留组合")
        row = generator.classify_lines(sample, commands(0, 1, 6) + commands(1, 2, 6), {0: "MIK", 1: "LUK"})[0][0]
        require(not row["singers"] and row["reason"] == "branch_conflict", "成功失败分支被错误并成合唱")
        sparse = commands(0, 0, 4)
        for entry, time in zip(sparse, (100, 400, 1500, 1900)):
            entry["raw_time"] = time * 100
        row = generator.classify_lines(sample, sparse, {0: "MIK", 1: "RIN"})[0][0]
        require(row["singers"] == ["MIK"] and row["reason"] == "sparse_activity_proxy", "覆盖大半行的稀疏变化序列被漏标")
        row = generator.classify_lines([{"start_ms": 0, "end_ms": 5000}], sparse, {0: "MIK", 1: "RIN"})[0][0]
        require(not row["singers"], "长句局部零星动作被错误补判")
        same_pose = [{**entry, "params": [0, 0, 0, 120, 1000]} for entry in sparse]
        require(not generator.classify_lines(sample, same_pose, {0: "MIK", 1: "RIN"})[0][0]["singers"], "重复同一姿态被错误补判")
        paired = [{**entry, "index": entry["index"] + 100, "raw_time": entry["raw_time"] + 1000,
                   "params": [1, *entry["params"][1:]]} for entry in sparse]
        row = generator.classify_lines([{"start_ms": 0, "end_ms": 5000}], sparse + paired, {0: "LUK", 1: "MEI"})[0][0]
        require(row["singers"] == ["LUK", "MEI"], "连续同步口型未补判合唱")
        shifted = [{**entry, "raw_time": entry["raw_time"] + 10000} for entry in paired]
        require(not generator.classify_lines([{"start_ms": 0, "end_ms": 5000}], sparse + shifted, {0: "LUK", 1: "MEI"})[0][0]["singers"], "错时活动被错误认作同步")
        require(not generator.classify_lines(sample, commands(0, 0, 1), {0: "LEN", 1: "KAI"})[0][0]["singers"], "单次剧情动作被错误补判")
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as temporary:
            path = Path(temporary) / "pv_db.txt"
            path.write_text("pv_999.performer.num=3\npv_999.performer.0.chara=MIK\npv_999.performer.0.type=VOCAL\npv_999.performer.1.type=PSEUDO_SAME\npv_999.performer.2.type=PSEUDO_SAME\npv_999.performer.2.pseudo_same_id=1\n", encoding="utf-8")
            require(generator.read_performers([path], 999)[1] == {0: "MIK", 1: "MIK", 2: "MIK"}, "递归复制角色未归并")
        print("通过：零星动作过滤、持续/同步补判、错时/同姿态拒绝、分支冲突和复制角色归并。")
        for pv in (41, 62, 728, 802, 611, 268, 212):
            directory = "singer-full-export" if pv == 212 else "singer-mvp"
            report = json.loads((ROOT / f"artifacts/{directory}/cache/PV{pv:03d}.singers.audit.json").read_text(encoding="utf-8"))
            # 每次重新运行当前分类器，不能只检查上一版留在磁盘的成功结果。
            rows, _ = generator.classify_lines(report["lines"], report["commands"], {int(slot): identity for slot, identity in report["performers"].items()})
            require(all(check.get("missing") or check["labels_match"] for check in report["difficulty_checks"]), "真实样本难度标记不一致")
            require(all(len(row["singers"]) == len(set(row["singers"])) for row in report["lines"]), "真实样本有重复歌手")
            if pv == 802:
                require([row["line"] for row in rows if len(row["singers"]) > 1] == [39, 40, 41, 42], "愛Dee双人段与用户人工校对不符")
            if pv == 268:
                require(all(row["singers"] == ["MIK"] for row in rows), "六初音被判成六歌手")
            if pv == 728:
                require(not rows[9]["singers"], "回忆演出缺少口型的行被强行补判")
            if pv == 41:
                require(rows[28]["singers"] == ["MIK"], "楽しかったって未恢复初音标记")
            if pv == 212:
                require(all(row["singers"] for row in rows), "カラフル×セクシィ仍有无依据的默认行")
                require(all(rows[index - 1]["singers"] == ["LUK", "MEI"] for index in (10, 22, 29)), "双人连续活动未恢复合唱标记")
            print(f"通过：{report['title']}，完整审计与同曲难度标记。")
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"验证失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
