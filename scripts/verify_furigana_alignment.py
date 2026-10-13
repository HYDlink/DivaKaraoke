#!/usr/bin/env python3
"""验证真实注音边界样例及不允许静默猜读的安全条件。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/furigana_runtime'))
from janome.tokenizer import Tokenizer
from generate_furigana_sidecar import generate_line_ruby, build_sidecar
from furigana_alignment import strict_romaji, align_lyric_reading


def check_readings(tokenizer: object, text: str, source: str, expected: dict) -> None:
    """核对来源完整消费和底字读音，同时验证各 span 的 Unicode 范围。"""
    result = generate_line_ruby(tokenizer,text,source)
    assert result['alignment']['status']=='aligned',f"未完整对齐：{text}；{result['review_reasons']}"
    assert result['alignment']['source_consumed']==result['alignment']['source_length']
    readings = {text[span['start']:span['start']+span['length']]:span['ruby'] for span in result['spans']}
    assert readings==expected,f"读音不符：{text}；实际 {readings}；预期 {expected}"


def main() -> int:
    """运行真实 PV 句子与拒绝猜读回归，以中文报告验证结果。"""
    sys.stdout.reconfigure(encoding='utf-8')
    tokenizer = Tokenizer()
    examples = [
        ('Sunday　君に惚れたパーティー','SUNDAY kimi ni horeta PARTY',{'君':'きみ','惚':'ほ'}),
        ('何度だって聞こえる　一人きりの拙い声','nando datte kikoeru hitori kiri no tsutanai koe',{'何度':'なんど','聞':'き','一人':'ひとり','拙':'つたな','声':'こえ'}),
        ('海が近づく','umi ga chikazuku',{'海':'うみ','近':'ちか'}),
        ('生クリィムのシャボンの中で眠ってた','nama-CREAM no shabon no naka de nemutteta',{'生':'なま','中':'なか','眠':'ねむ'}),
        ('殻を破って今そう！　lots of laugh','kara o yabutte ima sou! LOTS OF LAUGH',{'殻':'から','破':'やぶ','今':'いま'}),
        ('聞けば38度5分って','kikeba sanjuuhachi do gobu tte',{'聞':'き','度':'ど','分':'ぶ'}),
        ('魔法の一筆で 夢中にさせて','mahou no hitofude de muchuu ni sasete',{'魔法':'まほう','一筆':'ひとふで','夢中':'むちゅう'}),
        ('棄てられた仔猫のように','suterareta koneko no you ni',{'棄':'す','仔猫':'こねこ'}),
        ('宇宙へ','sora e',{'宇宙':'そら'}),
        ('時々君を','tokidoki kimi wo',{'時々君':'ときどききみ'}),
        ('才能（ちから）を','chikara wo',{'才能':'ちから'}),
        ('君に歌うスターストーリー','kimi ni utau STAR STORY',{'君':'きみ','歌':'うた'}),
        ('私の一言には三つの言葉','watashi no hitokoto ni wa mittsu no kotoba',{'私':'わたし','一言':'ひとこと','三':'みっ','言葉':'ことば'}),
    ]
    examples += [
        ('「落ち着け、カフェオレ飲もう」','"ochitsuke, CAFE AU LAIT nomou"',{'落':'お','着':'つ','飲':'の'}),
        ('オレンジ色の雲間に','ORANGE iro no kumoma ni',{'色':'いろ','雲間':'くもま'}),
        ('淡いドレスも　デフォ・ノースリーブも','awai DRESS mo DEFO-NO SLEEVE mo',{'淡':'あわ'}),
        ('固まった日常　シェケシェケシェケ・ダウン','katamatta nichijou SHAKEE-SHAKEE-SHAKEE-DOWN',{'固':'かた','日常':'にちじょう'}),
    ]
    for text,source,expected in examples:
        check_readings(tokenizer,text,source,expected)
    repeated = generate_line_ruby(tokenizer,'恋恋恋恋恋しちゃう','koi koi koi koi koi shichau')
    assert [(span['start'],span['length'],span['ruby']) for span in repeated['spans']]==[(i,1,'こい') for i in range(5)]
    # 未知字母、源串尾巴、英文翻译与词序错误必须失败，不能从局部命中继续猜。
    for source in ['umi ga chikazuku XYZ','The sea approaches','chikazuku umi ga','umi ga chikazuku Ж']:
        rejected = generate_line_ruby(tokenizer,'海が近づく',source)
        assert rejected['alignment']['status']=='unmatched' and not rejected['spans'],source
    opaque = generate_line_ruby(tokenizer,'君にパーティー','kimi ni ORANGE')
    assert opaque['alignment']['status']=='unmatched' and not opaque['spans']
    translated = generate_line_ruby(tokenizer,'時間','TIME')
    assert translated['alignment']['status']=='unmatched' and not translated['spans']
    assert strict_romaji('love') is None and strict_romaji('tqx') is None
    ambiguity = align_lyric_reading('生の生','namanoononama',[],set())
    assert ambiguity['status']=='ambiguous' and not ambiguity['spans']
    # 显式提供故意错误的词典读音，独立来源仍须胜出；不允许词典改写唱法。
    official = align_lyric_reading('君に','kimi ni',[{'start':0,'length':1,'ruby':'くん'}],set())
    assert official['spans']==[{'start':0,'length':1,'ruby':'きみ'}]
    guessed = generate_line_ruby(tokenizer,'君に','')
    assert guessed['alignment']['status']=='missing' and guessed['review_reasons']
    _, legacy = build_sidecar(tokenizer,{8:{'lyric':'恋恋恋恋恋しちゃう','lyric_en':'koi koi koi koi koi shichau'}},249)
    assert legacy['rows'][0]['spans']==repeated['spans']
    print(f'来源优先注音验证通过：{len(examples)+1} 个真实/典型句，未知音节、源串尾巴、翻译、歧义及双入口一致性均通过。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
