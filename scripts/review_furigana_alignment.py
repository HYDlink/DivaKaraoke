#!/usr/bin/env python3
"""检查全量来源对齐缓存，并导出差异与待复核行清单。"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from export_ruby_review import load_song
from export_lyrics import manifest_files


def read_json(path: Path) -> dict:
    """读取 UTF-8 审计或清单，兼容原有文件的 BOM。"""
    return json.loads(path.read_text(encoding='utf-8-sig'))


def reading_map(text: str, spans: list) -> dict:
    """把完整底字跨度映射为读音，便于比较新旧输出而不混淆行号。"""
    return {f"{span['start']}:{span['length']}:{text[span['start']:span['start']+span['length']]}":span['ruby'] for span in spans}


def verify_cache(cache: Path, baseline: Path | None) -> dict:
    """核对全量哈希、有效行号、TSV/审计一致性及来源完整消费，并收集差异。"""
    manifest = read_json(cache/'export-manifest.json')
    for item in manifest_files(manifest,require_ruby=True):
        assert hashlib.sha256((cache/item['file']).read_bytes()).hexdigest()==item['sha256'],f"哈希不符：{item['file']}"
    statuses = Counter()
    changed = []
    pending = []
    spans_count = 0
    kanji_review_rows = 0
    for entry in manifest['entries']:
        pv = int(entry['pv_id'])
        name = f'PV{pv:03d}'
        timeline = read_json(cache/f'{name}.json')
        audit = read_json(cache/f'{name}.ruby.audit.json')
        old_rows = []
        if baseline and (baseline/f'{name}.ruby.audit.json').is_file():
            old_rows = read_json(baseline/f'{name}.ruby.audit.json')['rows']
        # 重复事件合并会改变行数，新旧比较按 lyric ID 与完整原文而不按旧行号。
        old_by_key = {(row['lyric_id'],row['japanese']):row for row in old_rows}
        runtime_index = 0
        assert len(timeline['lines'])==len(audit['rows'])
        load_song(cache,pv)
        for line,row in zip(timeline['lines'],audit['rows']):
            text = line['text']
            assert text==row['japanese'] and line['lyric_id']==row['lyric_id']
            valid = bool(text) and line['end_ms']>=line['start_ms']
            runtime_index += int(valid)
            assert row['runtime_index']==(runtime_index if valid else None)
            alignment = row['alignment']
            statuses[alignment['status']] += 1
            if alignment['status'] in ('aligned','ambiguous'):
                assert alignment['source_consumed']==alignment['source_length'] and alignment['source_length']>0
                assert row['spans']==alignment['spans']
            elif alignment['status']=='unmatched':
                assert not row['spans'],f"失败对齐仍发布了猜读：{name} 行 {row['index']}"
            assert row['review_reasons'] or alignment['status']=='aligned' or not re.search('[一-龯々]',text)
            covered = set()
            for span in row['spans']:
                a,b = span['start'],span['start']+span['length']
                assert 0<=a<b<=len(text) and re.fullmatch('[ぁ-ゖー]+',span['ruby'])
                positions = set(range(a,b))
                assert not covered&positions,f"跨度重叠：{name} 行 {row['index']}"
                covered |= positions
            spans_count += len(row['spans'])
            old = old_by_key.get((row['lyric_id'],text))
            if old and old['spans']!=row['spans']:
                changed.append({'pv_id':pv,'index':row['index'],'lyric_id':row['lyric_id'],'text':text,'romaji':row['romaji'],
                                'before':reading_map(text,old['spans']),'after':reading_map(text,row['spans']),
                                'alignment_status':alignment['status']})
            if row['review_reasons'] and text:
                item = {'pv_id':pv,'index':row['index'],'lyric_id':row['lyric_id'],'text':text,'romaji':row['romaji'],
                        'status':alignment['status'],'reasons':row['review_reasons']}
                pending.append(item)
                kanji_review_rows += bool(re.search('[一-龯々]',text))
    return {'songs':len(manifest['entries']),'spans':spans_count,'statuses':dict(statuses),
            'changed_rows':len(changed),'changed_pvs':len({r['pv_id'] for r in changed}),
            'review_rows':len(pending),'kanji_review_rows':kanji_review_rows,'changes':changed,'pending':pending}


def main() -> int:
    """按指定缓存导出 UTF-8 报告，控制台仅显示中文结果。"""
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='核对整句来源注音缓存并输出差异报告')
    # 输入为完整生成缓存，基线只用于比较，不会修改任何已有文件。
    parser.add_argument('--cache-dir',type=Path,required=True,help='新生成缓存目录')
    parser.add_argument('--baseline-dir',type=Path,help='可选：用于比较读音的旧缓存目录')
    # 输出报告包含完整的新旧读音变化与待人工复核行，不能作为游戏内验收证明。
    parser.add_argument('--out-json',type=Path,required=True,help='全量验证、变化及待复核 JSON 报告输出文件')
    args = parser.parse_args()
    report = verify_cache(args.cache_dir,args.baseline_dir)
    args.out_json.parent.mkdir(parents=True,exist_ok=True)
    args.out_json.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"全量注音结构验证通过：{report['songs']} 首，{report['spans']} 个注音跨度；{report['changed_rows']} 行变化，{report['kanji_review_rows']} 个含汉字行待复核。")
    print('对齐状态统计：'+str(report['statuses']))
    print('差异与待复核报告：'+str(args.out_json))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
