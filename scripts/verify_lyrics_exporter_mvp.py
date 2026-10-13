#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证歌词短入口的有效 Mod 选择、安装保护和失效缓存回收。"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from export_lyrics import ROOT, checksum, discover_mods, generate_ruby_cache, install, manifest_sources, publish_snapshot, safe_output_path, write_json
from extract_native_lyric_timeline import merge_short_duplicate_lines


def make_cache(root: Path, values: dict[int, str]) -> Path:
    """创建小型生成缓存及哈希清单，用于安装保护测试。"""
    root.mkdir(parents=True)
    entries = []
    for pv_id, text in values.items():
        path = root / f"PV{pv_id:03d}.srt"
        path.write_text(text, encoding="utf-8")
        ruby = root / f"PV{pv_id:03d}.ruby.tsv"
        ruby.write_text(f"# 测试注音：{text}\n1\t0:1:か\n", encoding="utf-8")
        audit = root / f"PV{pv_id:03d}.ruby.audit.json"
        write_json(audit, {"rows": [], "text": text})
        files = [{"file": item.name, "sha256": checksum(item)} for item in (path, ruby, audit)]
        entries.append({"pv_id": pv_id, "file": path.name, "sha256": checksum(path), "files": files})
    write_json(root / "export-manifest.json", {"schema_version": 2, "entries": entries})
    return root


def main() -> int:
    # 中文注释：验证较长连续同词事件合并，间隔明显的真实重复歌词保留。
    duplicate_lines = [
        {"start_ms": 0, "end_ms": 3123, "text": "重复句", "lyric_id": 5},
        {"start_ms": 3123, "end_ms": 5900, "text": "重复句", "lyric_id": 5},
    ]
    merged_lines = merge_short_duplicate_lines(duplicate_lines)
    assert len(merged_lines) == 1
    assert (merged_lines[0]["start_ms"], merged_lines[0]["end_ms"]) == (0, 5900)
    close_repeat = merge_short_duplicate_lines([
        {"start_ms": 0, "end_ms": 2250, "text": "重复句", "lyric_id": 5},
        {"start_ms": 2400, "end_ms": 4650, "text": "重复句", "lyric_id": 5},
    ])
    assert len(close_repeat) == 1
    separated_repeat = merge_short_duplicate_lines([
        {"start_ms": 0, "end_ms": 1200, "text": "重复句", "lyric_id": 5},
        {"start_ms": 1800, "end_ms": 3000, "text": "重复句", "lyric_id": 5},
    ])
    assert len(separated_repeat) == 2
    print("重复行回归通过：长段连续触发与150毫秒间隔合并，明显空档保留。")

    """在工作区临时目录执行真实文件操作验证，不触碰游戏安装。"""
    with tempfile.TemporaryDirectory(prefix="歌词工具 验证-", dir=ROOT / "artifacts") as directory:
        root = Path(directory)
        game = root / "游戏 空格"
        game.mkdir()
        (game / "config.toml").write_text('enabled=true\nmods="mods"\npriority=["高优先", "禁用", "低优先"]\n', encoding="utf-8")
        for name, enabled, includes in (("高优先", True, '[".", "选中"]'), ("低优先", True, '["."]'), ("禁用", False, '["."]'), ("未在白名单", True, '["."]')):
            mod = game / "mods" / name
            mod.mkdir(parents=True)
            (mod / "选中").mkdir()
            (mod / "未选中").mkdir()
            (mod / "config.toml").write_text(f"enabled={'true' if enabled else 'false'}\ninclude={includes}\n", encoding="utf-8")
        roots, _ = discover_mods(game)
        assert [item["name"] for item in roots] == ["高优先", "高优先", "低优先"]
        assert all("未选中" not in item["root"] for item in roots)
        print("有效 Mod 验证通过：白名单、禁用、优先级和 include 均正确。")
        cache1 = make_cache(root / "生成一", {1: "第一版", 2: "将失效", 3: "用户之后修改"})
        destination = root / "安装目录"
        install(cache1, destination)
        (destination / "PV003.srt").write_text("用户自定义", encoding="utf-8")
        (destination / "PV003.ruby.tsv").write_text("用户注音", encoding="utf-8")
        cache2 = make_cache(root / "生成二", {1: "第二版", 4: "新歌曲"})
        result = install(cache2, destination)
        assert (destination / "PV001.srt").read_text(encoding="utf-8") == "第二版"
        assert not (destination / "PV002.srt").exists()
        assert (destination / "PV003.srt").read_text(encoding="utf-8") == "用户自定义"
        assert (destination / "PV003.ruby.tsv").read_text(encoding="utf-8") == "用户注音"
        assert (destination / "PV001.ruby.tsv").read_bytes() == (cache2 / "PV001.ruby.tsv").read_bytes()
        assert {"PV002.srt", "PV002.ruby.tsv", "PV002.ruby.audit.json"}.issubset(result["removed"])
        print("安装更新验证通过：回收失效生成文件，保留用户修改与 Ruby。")
        (destination / "PV004.srt").write_text("手工编辑", encoding="utf-8")
        cache3 = make_cache(root / "生成三", {1: "不应更新", 4: "冲突"})
        before = (destination / "PV001.srt").read_bytes()
        try:
            install(cache3, destination)
        except ValueError as error:
            assert "受到保护" in str(error)
        else:
            raise AssertionError("安装没有保护自定义缓存。")
        assert (destination / "PV001.srt").read_bytes() == before
        # 原生缓存被篡改也必须在任何安装写入前拒绝。
        (cache3 / "PV001.srt").write_text("被改动", encoding="utf-8")
        try:
            install(cache3, destination)
        except ValueError as error:
            assert "哈希不匹配" in str(error)
        else:
            raise AssertionError("安装没有识别缓存篡改。")
        print("冲突与哈希预检通过：拒绝覆盖前未改动任何正式缓存。")
        (destination / "PV004.srt").write_bytes((cache2 / "PV004.srt").read_bytes())
        (destination / "PV004.ruby.tsv").write_text("用户修订注音", encoding="utf-8")
        before = (destination / "PV001.srt").read_bytes()
        try:
            install(cache2, destination)
        except ValueError as error:
            assert "PV004.ruby.tsv" in str(error)
        else:
            raise AssertionError("安装没有保护用户修订的注音。")
        assert (destination / "PV001.srt").read_bytes() == before
        (destination / "PV004.ruby.tsv").write_bytes((cache2 / "PV004.ruby.tsv").read_bytes())
        (cache2 / "PV004.ruby.tsv").write_text("被篡改的注音", encoding="utf-8")
        try:
            install(cache2, destination)
        except ValueError as error:
            assert "哈希不匹配" in str(error) and "ruby.tsv" in str(error)
        else:
            raise AssertionError("安装没有识别注音文件篡改。")
        print("振假名安装验证通过：成套更新、用户修订保护、注音哈希篡改拒绝。")
        legacy = root / "缺注音旧格式"
        legacy.mkdir()
        legacy_srt = legacy / "PV001.srt"
        legacy_srt.write_text("旧格式歌词", encoding="utf-8")
        write_json(legacy / "export-manifest.json", {"schema_version": 1, "entries": [{"pv_id": 1, "file": legacy_srt.name, "sha256": checksum(legacy_srt)}]})
        try:
            install(legacy, root / "不得安装缺注音版本")
        except ValueError as error:
            assert "缺少完整" in str(error)
        else:
            raise AssertionError("安装入口没有拒绝缺注音的旧格式。")
        assert not (root / "不得安装缺注音版本").exists()
        sidecar_fixture = root / "振假名行序夹具"
        sidecar_fixture.mkdir()
        database = sidecar_fixture / "mod_pv_db.txt"
        database.write_text("pv_001.lyric.017=声を伝える\npv_001.lyric_en.017=An unrelated English translation\npv_001.lyric.004=愛の詩\npv_001.lyric_en.004=Completely different translation text\npv_001.lyric.025=歌う 痛い 目覚め\npv_001.lyric.030=Sunday　君に惚れたパーティー　\npv_001.lyric_en.030=SUNDAY kimi ni horeta PARTY\npv_001.lyric.031=恋恋恋恋恋しちゃう\npv_001.lyric_en.031=koi koi koi koi koi shichau\npv_001.lyric.032=聞けば38度5分って\npv_001.lyric_en.032=kikeba sanjuuhachi do gobu tte\npv_001.lyric.033=魔法の一筆で 夢中にさせて\npv_001.lyric_en.033=mahou no hitofude de muchuu ni sasete\npv_001.lyric.034=棄てられた仔猫のように\npv_001.lyric_en.034=suterareta koneko no you ni\npv_001.lyric.035=赤く染まる頬を伝えば\npv_001.lyric_en.035=akaku somaru hoho wo tsutaeba\n", encoding="utf-8")
        different_database = sidecar_fixture / "另一个覆盖来源.txt"
        different_database.write_text("pv_001.lyric.017=別の歌詞\npv_001.lyric_en.017=betsu no kashi\n", encoding="utf-8")
        # 中文注释：插入一个空白 cue，回归运行时丢弃空行后 Ruby 编号仍连续。
        texts = ["声を伝える", "", "愛の詩", "声を伝える", "歌う 痛い 目覚め"]
        timeline = {"schema_version": 1, "pv_id": 1, "source": {"pv_db": [str(different_database), str(database)]}, "lines": [{"start_ms": index * 1000, "end_ms": (index + 1) * 1000, "text": text, "lyric_id": lyric_id} for index, (lyric_id, text) in enumerate(zip((17, 99, 4, 17, 25), texts))]}
        write_json(sidecar_fixture / "PV001.json", timeline)
        srt = sidecar_fixture / "PV001.srt"
        srt.write_text("\n".join(f"{index + 1}\n00:00:0{index},000 --> 00:00:0{index + 1},000\n{text}\n" for index, text in enumerate(texts)) + "\n", encoding="utf-8")
        write_json(sidecar_fixture / "export-manifest.json", {"schema_version": 1, "entries": [{"pv_id": 1, "file": srt.name, "sha256": checksum(srt)}]})
        generate_ruby_cache(sidecar_fixture, ROOT / "tools/furigana_runtime")
        audit = json.loads((sidecar_fixture / "PV001.ruby.audit.json").read_text(encoding="utf-8"))
        assert [row["index"] for row in audit["rows"]] == [1, 2, 3, 4, 5]
        assert [row["runtime_index"] for row in audit["rows"]] == [1, None, 2, 3, 4]
        assert [line.split("\t", 1)[0] for line in (sidecar_fixture / "PV001.ruby.tsv").read_text(encoding="utf-8").splitlines()[1:]] == ["1", "2", "3", "4"]
        assert [row["lyric_id"] for row in audit["rows"]] == [17, 99, 4, 17, 25]
        assert audit["rows"][0]["spans"] == audit["rows"][3]["spans"]
        assert all(row["alignment"]["status"] == "unmatched" for row in audit["rows"][:1]+audit["rows"][2:4])
        assert audit["rows"][4]["alignment"]["status"] == "missing"
        assert all(row["source"] == str(database) for row in audit["rows"] if row["japanese"])
        assert audit["rows"][1]["spans"] == [] and audit["rows"][1]["runtime_index"] is None
        assert all(not row["spans"] and row["review_reasons"] for row in audit["rows"][:1]+audit["rows"][2:4])
        assert audit["rows"][4]["spans"] and audit["rows"][4]["review_reasons"]
        suffix_row = audit["rows"][4]
        suffix_readings = {suffix_row["japanese"][span["start"]:span["start"] + span["length"]]: span["ruby"] for span in suffix_row["spans"]}
        assert suffix_readings == {"歌": "うた", "痛": "いた", "目覚": "めざ"}
        assert not suffix_row["uncovered_kanji_positions"]
        # 中文注释：验证空白词元不会跳过罗马音游标，并用官方唱法覆盖重复汉字词的词典误读。
        from generate_furigana_sidecar import generate_timeline_sidecar
        from janome.tokenizer import Tokenizer
        special_timeline = {
            "schema_version": 1,
            "pv_id": 1,
            "source": {"pv_db": [str(database)]},
            "lines": [
                {"start_ms": 0, "end_ms": 1000, "text": "Sunday　君に惚れたパーティー　", "lyric_id": 30},
                {"start_ms": 1000, "end_ms": 2000, "text": "恋恋恋恋恋しちゃう", "lyric_id": 31},
                {"start_ms": 2000, "end_ms": 3000, "text": "聞けば38度5分って", "lyric_id": 32},
                {"start_ms": 3000, "end_ms": 4000, "text": "魔法の一筆で 夢中にさせて", "lyric_id": 33},
                {"start_ms": 4000, "end_ms": 5000, "text": "棄てられた仔猫のように", "lyric_id": 34},
                {"start_ms": 5000, "end_ms": 6000, "text": "赤く染まる頬を伝えば", "lyric_id": 35},
            ],
        }
        _, special_audit = generate_timeline_sidecar(Tokenizer(), special_timeline)
        kimi_spans = special_audit["rows"][0]["spans"]
        assert any(span["ruby"] == "きみ" and special_audit["rows"][0]["japanese"][span["start"]:span["start"] + span["length"]] == "君" for span in kimi_spans)
        koi_spans = [span for span in special_audit["rows"][1]["spans"] if span["start"] < 5]
        assert [(span["start"], span["length"], span["ruby"]) for span in koi_spans] == [(0, 1, "こい"), (1, 1, "こい"), (2, 1, "こい"), (3, 1, "こい"), (4, 1, "こい")]
        number_spans = special_audit["rows"][2]["spans"]
        number_readings = {special_audit["rows"][2]["japanese"][span["start"]:span["start"] + span["length"]]: span["ruby"] for span in number_spans}
        assert number_readings == {"聞": "き", "度": "ど", "分": "ぶ"}
        # 中文注释：确认「で」不能被前一个汉字词的罗马音尾音吸收。
        anchor_row = special_audit["rows"][3]
        anchor_readings = {anchor_row["japanese"][span["start"]:span["start"] + span["length"]]: span["ruby"] for span in anchor_row["spans"]}
        assert anchor_readings["一筆"] == "ひとふで"
        assert anchor_readings["夢中"] == "むちゅう"
        kitten_row = special_audit["rows"][4]
        kitten_readings = {kitten_row["japanese"][span["start"]:span["start"] + span["length"]]: span["ruby"] for span in kitten_row["spans"]}
        assert kitten_readings["仔猫"] == "こねこ"
        hoho_row = special_audit["rows"][5]
        hoho_readings = {hoho_row["japanese"][span["start"]:span["start"] + span["length"]]: span["ruby"] for span in hoho_row["spans"]}
        assert hoho_readings["頬"] == "ほほ"
        print("来源唱法注音回归通过：君→きみ、恋→こい、分→ぶ，数字歌词遵循来源读音。")
        install(sidecar_fixture, root / "真实注音安装夹具")
        print("真实振假名验证通过：跳号、重复歌词ID按运行时有效行编号；空白 cue 不造成错位，Mod英文翻译被拒绝，生成成套文件可安装。")
        print("送り仮名后缀回归通过：歌→うた、痛→いた、目覚→めざ均完整标注。")
        manifest = root / "禁止解包清单.json"
        work = root / "不得创建的资产目录"
        source = {"name": "禁止新解包", "cpk": "未读取.cpk", "extract_dir": "不存在提取树", "rom_relative": "rom", "pv_db_relative": "rom/pv_db.txt", "output_dir": "不用", "report": "不用"}
        for reuse in (False, True):
            source["reuse_extracted"] = reuse
            write_json(manifest, {"schema_version": 1, "sources": [source]})
            with patch("export_lyrics.run") as runner:
                try:
                    manifest_sources(manifest, work)
                except ValueError as error:
                    assert "禁止新解包" in str(error) or "既有提取目录不存在" in str(error)
                else:
                    raise AssertionError("高级清单没有拒绝新解包。")
                runner.assert_not_called()
            assert not work.exists() and not (root / "不存在提取树").exists()
        print("禁止新解包验证通过：无工具调用、无新资产目录。")
        output = root / "发布目录"
        output.mkdir()
        publish = output / "生成暂存" / "publish"
        publish.mkdir(parents=True)
        (publish / "内容.txt").write_text("新版", encoding="utf-8")
        old = output / "cache"
        old.mkdir()
        (old / "内容.txt").write_text("旧版", encoding="utf-8")
        cache = publish_snapshot(publish, output)
        assert (cache / "内容.txt").read_text(encoding="utf-8") == "新版"
        assert not (output / "previous-cache").exists()
        try:
            safe_output_path(root / "外部资产", output)
        except ValueError as error:
            assert "越出输出目录" in str(error)
        else:
            raise AssertionError("发布没有拒绝外部路径。")
        if sys.platform == "win32":
            external = root / "受保护资产"
            external.mkdir()
            sentinel = external / "保留.txt"
            sentinel.write_text("必须保留", encoding="utf-8")
            linked_output = root / "联接点输出"
            linked_output.mkdir()
            junction = linked_output / "cache"
            subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(external)], check=True, capture_output=True)
            try:
                try:
                    safe_output_path(junction, linked_output)
                except ValueError as error:
                    assert "联接点" in str(error) or "符号链接" in str(error)
                else:
                    raise AssertionError("发布没有拒绝 Windows 联接点。")
                assert sentinel.read_text(encoding="utf-8") == "必须保留"
            finally:
                # 只删除已核对目标的联接点本身，不递归处理其指向的目录。
                assert junction.resolve() == external.resolve()
                junction.rmdir()
        print("快照边界验证通过：正常更新成功，越界目标与 Windows 联接点被拒绝。")
    print("歌词导出器 MVP 逻辑验证全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
