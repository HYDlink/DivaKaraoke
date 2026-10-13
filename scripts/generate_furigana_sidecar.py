#!/usr/bin/env python3
"""从官方日文歌词和罗马音生成 MMFreeLyrics 的词组 Ruby 旁路文件。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path

from furigana_alignment import align_lyric_reading


KANJI_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆]")
KANA_PATTERN = re.compile(r"[ぁ-ゖァ-ヺー]")
ENTRY_PATTERN = re.compile(r"^pv_(?P<pv_id>\d+)\.(?P<kind>lyric(?:_en)?)\.(?P<index>\d+)=(?P<text>.*)$")

@dataclass
class MorphToken:
    """保存一个日文形态词及其在原歌词中的 Unicode 字符位置。"""

    surface: str
    start: int
    reading: str
    # 词性只用于助词表记变体，不能决定歌曲唱法。
    part_of_speech: str = ""


def load_pairs(database_path: Path, pv_id: int) -> dict[int, dict[str, str]]:
    """读取指定 PV 的日文歌词和官方罗马音，并按原始 lyric 编号配对。"""
    pairs: dict[int, dict[str, str]] = {}
    with database_path.open("r", encoding="utf-8-sig") as source:
        for raw_line in source:
            match = ENTRY_PATTERN.match(raw_line.rstrip("\r\n"))
            if match and int(match.group("pv_id")) == pv_id:
                pairs.setdefault(int(match.group("index")), {})[match.group("kind")] = match.group("text")
    return pairs


def katakana_to_hiragana(value: str) -> str:
    """将形态分析器返回的片假名读音转换成 Ruby 所需的平假名。"""
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in value)


def tokenize_japanese(tokenizer: object, text: str) -> list[MorphToken]:
    """调用 Janome 切分歌词，并记录每个词在原文中的 Unicode 字符起点。"""
    tokens: list[MorphToken] = []
    cursor = 0
    for token in tokenizer.tokenize(text):
        surface = token.surface
        start = text.find(surface, cursor)
        if start < 0:
            continue
        cursor = start + len(surface)
        reading = token.reading if token.reading != "*" else surface
        tokens.append(MorphToken(surface=surface, start=start, reading=katakana_to_hiragana(reading),
                                 part_of_speech=token.part_of_speech.split(",")[0]))
    return tokens


def dictionary_token_spans(token: MorphToken) -> list[dict[str, object]]:
    """从词典读音拆出汉字组参考，仅用于边界参考和来源缺失时的显式推测。"""
    # 该函数仅构造词典参考，来源唱法统一走完整正文对齐。
    full_reading = token.reading
    groups = list(re.finditer(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆]+", token.surface))
    if not groups:
        return []
    spans: list[dict[str, object]] = []
    reading_cursor = 0
    for group_index, group in enumerate(groups):
        preceding_kana = token.surface[groups[group_index - 1].end():group.start()] if group_index else token.surface[:group.start()]
        if preceding_kana:
            normalized_preceding_kana = katakana_to_hiragana(preceding_kana)
            kana_position = full_reading.find(normalized_preceding_kana, reading_cursor)
            if kana_position >= reading_cursor:
                reading_cursor = kana_position + len(normalized_preceding_kana)
        following_start = group.end()
        following_end = groups[group_index + 1].start() if group_index + 1 < len(groups) else len(token.surface)
        following_kana = token.surface[following_start:following_end]
        normalized_following_kana = katakana_to_hiragana(following_kana)
        if normalized_following_kana:
            # 末尾送り仮名必须匹配读音后缀，歌う/うたう不能误取开头的「う」。
            if group_index == len(groups) - 1 and full_reading.endswith(normalized_following_kana):
                boundary = len(full_reading) - len(normalized_following_kana)
            else:
                boundary = full_reading.find(normalized_following_kana, reading_cursor)
            ruby = full_reading[reading_cursor:boundary] if boundary >= reading_cursor else full_reading[reading_cursor:]
            reading_cursor = boundary if boundary >= reading_cursor else len(full_reading)
        elif group_index + 1 < len(groups):
            ruby = full_reading[reading_cursor:]
            reading_cursor = len(full_reading)
        else:
            ruby = full_reading[reading_cursor:]
        if ruby:
            spans.append({"start": token.start + group.start(), "length": len(group.group()), "ruby": ruby})
    return spans


@lru_cache(maxsize=256)
def generate_line_ruby(tokenizer: object, text: str, romaji: str) -> dict:
    """整句来源对齐优先；来源缺失才提供显式标记的词典推测。"""
    tokens = tokenize_japanese(tokenizer, text)
    hints = [span for token in tokens if re.fullmatch(r"[ぁ-ゖー]+", token.reading)
             for span in dictionary_token_spans(token)]
    particles = {token.start for token in tokens if token.part_of_speech == "助詞"}
    alignment = align_lyric_reading(text, romaji, hints, particles)
    spans = alignment["spans"]
    reasons = []
    if alignment["status"] == "missing":
        spans = hints
        strategy = "词典推测（来源唱法缺失）"
        if KANJI_PATTERN.search(text):
            reasons.append("来源唱法缺失；以下注音为词典推测，尚未核对歌曲唱法")
    else:
        strategy = "来源唱法整句对齐" if alignment["status"] == "aligned" else "来源唱法对齐待复核"
        if alignment["status"] == "unmatched":
            reasons.append(alignment["reason"])
        elif alignment["status"] == "ambiguous":
            reasons.append("整句存在并列切分，歧义汉字未猜读：" + "、".join(alignment["ambiguous_groups"]))
    covered = {position for span in spans for position in range(span["start"],span["start"]+span["length"])}
    uncovered = [position for position,char in enumerate(text) if KANJI_PATTERN.fullmatch(char) and position not in covered]
    if uncovered:
        reasons.append("存在未确认读音的汉字，位置：" + ",".join(map(str,uncovered)))
    return {"reading_strategy":strategy,"spans":spans,"alignment":alignment,
            "dictionary_hints":hints,"uncovered_kanji_positions":uncovered,"review_reasons":reasons}


def build_sidecar(tokenizer: object, pairs: dict[int, dict[str, str]], pv_id: int) -> tuple[str, dict]:
    """旧文本表入口也复用整句对齐，避免与正式时间线入口使用不同读音算法。"""
    timeline = {"pv_id":pv_id,"source":{},"lines":[
        {"lyric_id":index,"text":pair.get("lyric",""),"start_ms":0,"end_ms":1}
        for index,pair in sorted(pairs.items())]}
    return generate_timeline_sidecar(tokenizer,timeline,pairs)


@lru_cache(maxsize=64)
def load_timeline_database(path: str, modified_ns: int) -> dict[int, dict[int, dict[str, str]]]:
    """按文件修改时间缓存文本表，批量生成时每份表只读取一次。"""
    result: dict[int, dict[int, dict[str, str]]] = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        match = ENTRY_PATTERN.match(line)
        if match:
            result.setdefault(int(match["pv_id"]), {}).setdefault(int(match["index"]), {})[match["kind"]] = match["text"]
    return result


def generate_timeline_sidecar(tokenizer: object, timeline_document: dict, direct_pairs: dict | None = None) -> tuple[str, dict]:
    """按最终有效歌词行号生成 Ruby，同源同 ID 同全文才允许配对来源唱法。"""
    pv_id = int(timeline_document["pv_id"])
    databases = []
    if direct_pairs is not None:
        databases.append(("旧版显式文本表",direct_pairs))
    for name in timeline_document.get("source",{}).get("pv_db",[]):
        path = Path(name)
        databases.append((str(path),load_timeline_database(str(path),path.stat().st_mtime_ns).get(pv_id,{})))
    rows = []
    tsv = ["# MMFreeLyrics Ruby TSV v1：有效行号<TAB>起点:长度:平假名；..."]
    runtime_index = 0
    for index,line in enumerate(timeline_document["lines"],start=1):
        text = str(line["text"])
        valid = bool(text) and int(line["end_ms"]) >= int(line["start_ms"])
        if valid:
            runtime_index += 1
        lyric_id = int(line["lyric_id"])
        selected = next(((path,pairs[lyric_id]) for path,pairs in databases
                         if lyric_id in pairs and pairs[lyric_id].get("lyric") == text),None)
        romaji = selected[1].get("lyric_en","") if selected else ""
        generated = generate_line_ruby(tokenizer,text,romaji)
        if valid:
            tsv.append(f"{runtime_index}\t" + ";".join(f"{span['start']}:{span['length']}:{span['ruby']}" for span in generated["spans"]))
        rows.append({"index":index,"runtime_index":runtime_index if valid else None,"lyric_id":lyric_id,
                     "japanese":text,"romaji":romaji,"source":selected[0] if selected else None,**generated})
    return "\n".join(tsv)+"\n",{"format":"MMFreeLyrics Ruby v1","algorithm":"整句来源对齐 v2","pvId":pv_id,"rows":rows}


def parse_arguments() -> argparse.Namespace:
    """解析官方文本表、PV 编号、Janome 路径和两个输出文件路径。"""
    parser = argparse.ArgumentParser(description="生成 MMFreeLyrics 日文振假名旁路文件")
    parser.add_argument("--pv-db", type=Path, help="旧版单曲入口：官方 mdata_pv_db.txt 文件路径")
    parser.add_argument("--pv-id", type=int, help="旧版单曲入口：要生成的 PV 编号")
    parser.add_argument("--timeline-json", type=Path, help="最终 SRT 对应的时间线 JSON；按实际行顺序生成注音")
    parser.add_argument("--out-tsv", type=Path, required=True, help="供 DLL 读取的 Ruby TSV 输出路径")
    parser.add_argument("--out-json", type=Path, required=True, help="人工审计 Ruby spans 的 JSON 输出路径")
    parser.add_argument("--janome-path", type=Path, default=Path(__file__).resolve().parents[1] / "tools/furigana_runtime", help="Janome 离线依赖目录")
    arguments = parser.parse_args()
    if not arguments.timeline_json and (arguments.pv_db is None or arguments.pv_id is None):
        parser.error("需要最终时间线 JSON，或同时提供文本表与 PV 编号")
    return arguments


def main() -> int:
    """加载日文分析器，生成旁路文件，并输出可复核的中文统计。"""
    sys.stdout.reconfigure(encoding="utf-8")
    arguments = parse_arguments()
    sys.path.insert(0, str(arguments.janome_path))
    from janome.tokenizer import Tokenizer

    if arguments.timeline_json:
        document = json.loads(arguments.timeline_json.read_text(encoding="utf-8"))
        tsv, report = generate_timeline_sidecar(Tokenizer(), document)
    else:
        pairs = load_pairs(arguments.pv_db, arguments.pv_id)
        tsv, report = build_sidecar(Tokenizer(), pairs, arguments.pv_id)
    arguments.out_tsv.parent.mkdir(parents=True, exist_ok=True)
    arguments.out_tsv.write_text(tsv, encoding="utf-8")
    arguments.out_json.parent.mkdir(parents=True, exist_ok=True)
    arguments.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    span_count = sum(len(row["spans"]) for row in report["rows"])
    print(f"已生成 PV{report['pvId']} 的 {len(report['rows'])} 行 Ruby 数据，共 {span_count} 个汉字词组标注。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
