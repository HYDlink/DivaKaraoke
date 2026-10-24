#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证自动多身份筛选、人工修订、统一安装保护及真实批量结果。"""
import copy
import json
from pathlib import Path
import sys
import tempfile

import build_singer_timeline as singer
from export_lyrics import ROOT, checksum, install, manifest_files, write_json
from verify_lyrics_exporter_mvp import make_cache


def require(condition: bool, message: str) -> None:
    """断言失败时输出中文原因。"""
    if not condition:
        raise ValueError(message)


def verify_isolated(root: Path) -> None:
    """在隔离目录验证候选筛选、人工标记与旁路安装安全，不触碰游戏。"""
    database = root / "角色表.txt"
    database.write_text("pv_001.performer.num=2\npv_001.performer.0.chara=LEN\npv_001.performer.0.type=VOCAL\npv_001.performer.1.chara=KAI\npv_001.performer.1.type=GUEST\npv_002.performer.num=3\npv_002.performer.0.chara=MIK\npv_002.performer.1.type=PSEUDO_SAME\npv_002.performer.2.type=PSEUDO_SAME\npv_002.performer.2.pseudo_same_id=1\n", encoding="utf-8")
    cache = root / "扫描缓存"
    cache.mkdir()
    for pv in (1,2,999):
        write_json(cache / f"PV{pv:03d}.json", {"pv_id":pv,"source":{"pv_db":[str(database)]}})
    write_json(cache / "export-manifest.json", {"entries":[{"pv_id":1},{"pv_id":2}]})
    scan = singer.scan_cache_performers(cache)
    require(len(scan)==2 and scan[0]["status"]=="candidate" and scan[0]["identities"]==["LEN","KAI"], "自动扫描没有采用有效清单或错误过滤GUEST")
    require(scan[1]["status"]=="single_identity" and scan[1]["identities"]==["MIK"],"复制角色被当成不同歌手")
    rows=[{"line":i+1,"start_ms":i*1000,"end_ms":(i+1)*1000,"text":f"测试歌词{i}","singers":["KAI"],"reason":"activity_proxy","classification":"single"} for i in range(3)]
    manual=root/"人工标记"
    singer.apply_manual_singers(copy.deepcopy(rows),1,{0:"LEN",1:"KAI"},manual)
    path=manual/"PV001.singers.manual.tsv"
    untouched=path.read_text(encoding="utf-8")
    changed=untouched.replace("0\t1000\tauto", "0\t1000\tLEN").replace("1000\t2000\tauto", "1000\t2000\tLEN,KAI").replace("2000\t3000\tauto", "2000\t3000\t-")
    path.write_text(changed,encoding="utf-8")
    updated=copy.deepcopy(rows)
    result=singer.apply_manual_singers(updated,1,{0:"LEN",1:"KAI"},manual)
    require(result["overrides"]==3 and [r["singers"] for r in updated]==[["LEN"],["LEN","KAI"],[]],"人工单人/合唱/默认标记不正确")
    require(updated[0]["auto_singers"]==["KAI"] and path.read_text(encoding="utf-8")==changed,"人工模板被覆盖或自动证据丢失")
    for bad in (changed.replace("测试歌词0","错行"), changed.replace("LEN,KAI","LEN,LEN"), changed.replace("singers-manual-v1\t1\t3","singers-manual-v1\t2\t3")):
        path.write_text(bad,encoding="utf-8")
        original=copy.deepcopy(rows)
        try:
            singer.apply_manual_singers(original,1,{0:"LEN",1:"KAI"},manual)
        except ValueError:
            require(original==rows,"人工修订错误时已部分修改结果")
        else:
            raise ValueError("人工修订没有拒绝错行、重复身份或错曲")
    source=make_cache(root/"安装源",{1:"歌词"})
    document=json.loads((source/"export-manifest.json").read_text(encoding="utf-8"))
    entry=document["entries"][0]
    entry["singer"]={"status":"generated"}
    for suffix in (".singers.tsv",".singers.audit.json",".singers.md"):
        file=source/("PV001"+suffix)
        file.write_text("验证内容",encoding="utf-8")
        entry["files"].append({"file":file.name,"sha256":checksum(file)})
    document["schema_version"]=3
    write_json(source/"export-manifest.json",document)
    require(len(manifest_files(document,True))==6,"统一清单没有包含歌手三件套")
    destination=root/"模组"/"lyrics"
    destination.mkdir(parents=True)
    stale=destination/"PV268.singers.tsv"
    stale.write_text("旧复制角色标记",encoding="utf-8")
    write_json(destination.parent/"singer-mvp-manifest.json",{"files":[{"relative":"lyrics/PV268.singers.tsv","sha256":checksum(stale).upper()}]})
    installed=install(source,destination)
    require(not stale.exists() and "PV268.singers.tsv" in installed["removed"],"旧MVP生成旁路所有权没有安全迁移")
    edited=destination/"PV001.singers.tsv"
    edited.write_text("用户修改的歌手标记",encoding="utf-8")
    before=(destination/"PV001.srt").read_bytes()
    try:
        install(source,destination)
    except ValueError:
        require(edited.read_text(encoding="utf-8")=="用户修改的歌手标记" and (destination/"PV001.srt").read_bytes()==before,"冲突发生后正式文件被改动")
    else:
        raise ValueError("安装没有保护用户歌手标记")
    print("通过：有效清单自动筛选、GUEST、复制归并、人工单人/合唱/默认、错行拒绝、模板保留及安装保护。")


def verify_real(cache: Path) -> None:
    """核对真实批量生成清单及每首全文绑定，不把口型推测当作音频准确率。"""
    document=json.loads((cache/"export-manifest.json").read_text(encoding="utf-8"))
    require(document["schema_version"]==3,"真实缓存尚未集成歌手导出")
    summary=json.loads((cache/"singer-scan.json").read_text(encoding="utf-8"))
    require(summary["scanned"]==len(document["entries"]),"自动扫描漏掉有效歌曲")
    generated=0
    for entry in document["entries"]:
        for item in entry["files"]:
            require(checksum(cache/item["file"])==item["sha256"],"批量清单文件哈希不一致")
        if entry["singer"]["status"]!="generated":
            continue
        generated+=1
        pv=int(entry["pv_id"])
        timeline=json.loads((cache/f"PV{pv:03d}.json").read_text(encoding="utf-8"))
        rows=[row for row in timeline["lines"] if row["text"].strip()]
        records=(cache/f"PV{pv:03d}.singers.tsv").read_text(encoding="utf-8").splitlines()
        parsed=[line.split("\t",4) for line in records if line and not line.startswith("#")]
        require(len(rows)==len(parsed),"批量旁路行数没有绑定")
        for index,(row,fields) in enumerate(zip(rows,parsed),1):
            require((int(fields[0]),int(fields[1]),int(fields[2]),fields[4])==(index,row["start_ms"],row["end_ms"],row["text"]),"批量旁路时间或全文没有绑定")
    require(generated==summary["generated"],"清单与扫描数量不一致")
    # 在隔离目录用真实DSC确认人工单句修订贯穿TSV、审计和中文结果，不修改用户模板。
    with tempfile.TemporaryDirectory(prefix="真实人工标记-",dir=ROOT/"artifacts") as directory:
        stage=Path(directory)
        before=singer.generate(cache/"PV728.json",stage/"输出",False,manual_dir=stage/"人工")
        path=stage/"人工/PV728.singers.manual.tsv"
        text=path.read_text(encoding="utf-8").replace("10\t26426\t32079\tauto\t","10\t26426\t32079\tLEN\t")
        path.write_text(text,encoding="utf-8")
        after=singer.generate(cache/"PV728.json",stage/"输出",False,manual_dir=stage/"人工")
        row=after["lines"][9]
        require(row["singers"]==["LEN"] and row["auto_singers"]==before["lines"][9]["singers"] and row["reason"]=="manual_override","真实回忆演出单句修订没有覆盖自动结果或丢失自动证据")
        require(path.read_text(encoding="utf-8")==text,"实际生成时覆盖了用户人工模板")
        print("通过：真实Erase or Zero第10句人工LEN标记贯通输出，其他行自动推断且修订文件未覆盖。")
    print(f"通过：真实{summary['scanned']}首自动扫描、{generated}首多身份旁路、成套哈希和逐行时间/全文绑定。")


def main() -> int:
    """执行隔离回归与已有全量缓存检查，输出中文摘要。"""
    sys.stdout.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="歌手导出验证-",dir=ROOT/"artifacts") as temporary:
        verify_isolated(Path(temporary))
    verify_real(ROOT/"artifacts/singer-full-export/cache")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
