"""将歌词正文与来源唱法作完整单调对齐，保留来源证据并显式报告歧义。"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

# 汉字迭代符与前字组成同一底字组；字节位置一律不参与 Ruby 索引。
KANJI = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆"
KANJI_RE = re.compile(f"[{KANJI}]")
UNIT_RE = re.compile(f"[{KANJI}]+|[ぁ-ゖー]+|[ァ-ヺー]+|[A-Za-zＡ-Ｚａ-ｚ]+|[0-9０-９]+(?:[.．][0-9０-９]+)?|\\s+|.")
# 罗马音表只接受完整音节；禁止跳过无法转换的字母。
ROMAN = {
    'a':'あ','i':'い','u':'う','e':'え','o':'お',
    'ka':'か','ki':'き','ku':'く','ke':'け','ko':'こ',
    'ga':'が','gi':'ぎ','gu':'ぐ','ge':'げ','go':'ご',
    'sa':'さ','shi':'し','si':'し','su':'す','se':'せ','so':'そ',
    'za':'ざ','ji':'じ','zi':'じ','zu':'ず','ze':'ぜ','zo':'ぞ',
    'ta':'た','chi':'ち','ti':'ち','tsu':'つ','tu':'つ','te':'て','to':'と',
    'da':'だ','di':'ぢ','du':'づ','de':'で','do':'ど',
    'na':'な','ni':'に','nu':'ぬ','ne':'ね','no':'の',
    'ha':'は','hi':'ひ','fu':'ふ','hu':'ふ','he':'へ','ho':'ほ',
    'ba':'ば','bi':'び','bu':'ぶ','be':'べ','bo':'ぼ',
    'pa':'ぱ','pi':'ぴ','pu':'ぷ','pe':'ぺ','po':'ぽ',
    'ma':'ま','mi':'み','mu':'む','me':'め','mo':'も',
    'ya':'や','yu':'ゆ','yo':'よ','ra':'ら','ri':'り','ru':'る','re':'れ','ro':'ろ',
    'wa':'わ','wi':'うぃ','we':'うぇ','wo':'を','vu':'ゔ',
    'kya':'きゃ','kyu':'きゅ','kyo':'きょ','gya':'ぎゃ','gyu':'ぎゅ','gyo':'ぎょ',
    'sha':'しゃ','shu':'しゅ','sho':'しょ','sya':'しゃ','syu':'しゅ','syo':'しょ',
    'ja':'じゃ','ju':'じゅ','jo':'じょ','jya':'じゃ','jyu':'じゅ','jyo':'じょ',
    'cha':'ちゃ','chu':'ちゅ','cho':'ちょ','tya':'ちゃ','tyu':'ちゅ','tyo':'ちょ',
    'nya':'にゃ','nyu':'にゅ','nyo':'にょ','hya':'ひゃ','hyu':'ひゅ','hyo':'ひょ',
    'bya':'びゃ','byu':'びゅ','byo':'びょ','pya':'ぴゃ','pyu':'ぴゅ','pyo':'ぴょ',
    'mya':'みゃ','myu':'みゅ','myo':'みょ','rya':'りゃ','ryu':'りゅ','ryo':'りょ',
    'fa':'ふぁ','fi':'ふぃ','fe':'ふぇ','fo':'ふぉ',
    'va':'ゔぁ','vi':'ゔぃ','ve':'ゔぇ','vo':'ゔぉ',
    'she':'しぇ','che':'ちぇ','je':'じぇ',
    'thi':'てぃ','dhi':'でぃ','twu':'とぅ','dwu':'どぅ',
}
HIRA_ROMAN = {}
for roman, kana in ROMAN.items():
    HIRA_ROMAN.setdefault(kana, []).append(roman)
# 外来语表记与罗马音标准存在 ti/tu 歧义，只为正文固定假名提供这些变体。
HIRA_ROMAN.update({'てぃ':['thi','ti'],'でぃ':['dhi','di'],'とぅ':['twu','tu'],'どぅ':['dwu','du'],
                   'ぢ':['ji','di'],'づ':['zu','du'], 'ん':['n', 'nn'], 'ゐ':['wi','i'], 'ゑ':['we','e']})


@dataclass(frozen=True)
class Unit:
    """保存正文单元、Unicode 范围、固定唱法模式以及词典边界参考。"""
    kind: str
    text: str
    start: int
    end: int
    pattern: str = ''
    hint: str = ''


def hira(text: str) -> str:
    """将片假名转换为平假名，保持原文长度与位置关系。"""
    return ''.join(chr(ord(c)-0x60) if 'ァ' <= c <= 'ヶ' else c for c in text)


def phonetic_key(text: str) -> str:
    """只规范等价长音与同音假名，词典可提供拼写但不能替换发音。"""
    value = hira(text).replace('ぢ','じ').replace('づ','ず')
    expanded = ''
    for char in value:
        if char == 'ー':
            ending = expanded[-2:] if expanded[-2:] in HIRA_ROMAN else expanded[-1:]
            forms = HIRA_ROMAN.get(ending,[])
            vowel = forms[0][-1] if forms and forms[0][-1] in 'aeiou' else ''
            expanded += {'a':'あ','i':'い','u':'う','e':'え','o':'お'}.get(vowel,'ー')
        else:
            expanded += char
    value = expanded
    value = re.sub(r'([おこごそぞとどのほぼぽもよろ])う', r'\1お', value)
    value = re.sub(r'([えけげせぜてでねへべぺめれ])い', r'\1え', value)
    return value


@lru_cache(maxsize=16384)
def strict_romaji(text: str) -> str | None:
    """把一段罗马音完整解析为假名；任一字母无音节对应时整段失败。"""
    value = text.lower()
    # 感叹长音末尾 h 是来源呼气表记，不是可任意省略的辅音。
    if re.fullmatch(r'[aeiou]+h',value):
        value = value[:-1]
    result = []
    cursor = 0
    while cursor < len(value):
        c = value[cursor]
        if c == 'n' and (cursor+1 == len(value) or value[cursor+1] not in 'aeiouy'):
            result.append('ん')
            cursor += 2 if value[cursor:] == 'nn' else 1
            continue
        if cursor+1 < len(value) and c == value[cursor+1] and c not in 'aeioun':
            result.append('っ')
            cursor += 1
            continue
        syllable = next((value[cursor:cursor+size] for size in (3,2,1)
                         if value[cursor:cursor+size] in ROMAN), None)
        if syllable is None:
            return None
        result.append(ROMAN[syllable])
        cursor += len(syllable)
    return ''.join(result)


def kana_pattern(text: str, particles: set[int], start: int) -> str:
    """为正文固定假名建立有限罗马音变体，处理促音、长音和助词唱法。"""
    value = hira(text)
    pieces = []
    previous_vowel = ''
    cursor = 0
    while cursor < len(value):
        c = value[cursor]
        pair = value[cursor:cursor+2]
        if c == 'っ':
            next_kana = value[cursor+1:cursor+3]
            candidates = HIRA_ROMAN.get(next_kana, HIRA_ROMAN.get(next_kana[:1], []))
            consonants = sorted({candidate[0] for candidate in candidates if candidate[0] not in 'aeioun'})
            pieces.append('[' + ''.join(consonants or list('bcdfghjklmpqrstvwxyz')) + ']')
            cursor += 1
            continue
        if c == 'ー':
            choices = {'o':'[ou]', 'e':'[ei]'}.get(previous_vowel, previous_vowel or '[aeiou]')
            pieces.append('(?:'+choices+')?')
            cursor += 1
            continue
        key = pair if pair in HIRA_ROMAN else c
        alternatives = list(HIRA_ROMAN.get(key, []))
        if start+cursor in particles or value in {'は','へ','を'}:
            alternatives += {'は':['wa'], 'へ':['e'], 'を':['o','wo']}.get(c, [])
        if c in 'ぁぃぅぇぉ':
            alternatives.append({'ぁ':'a','ぃ':'i','ぅ':'u','ぇ':'e','ぉ':'o'}[c])
        if c == 'う' and previous_vowel == 'o':
            alternatives.append('o')
        if c == 'い' and previous_vowel == 'e':
            alternatives.append('e')
        if not alternatives:
            return '(?!)'
        alternatives = sorted(set(alternatives), key=lambda v:(-len(v),v))
        pieces.append('(?:' + '|'.join(map(re.escape, alternatives)) + ')')
        previous_vowel = alternatives[0][-1] if alternatives[0][-1] in 'aeiou' else previous_vowel
        cursor += len(key)
    expression = ''.join(pieces)
    if re.fullmatch('[あいうえお]+',value) and len(set(value))==1:
        expression = '(?:'+expression+'|'+value.replace('あ','a').replace('い','i').replace('う','u').replace('え','e').replace('お','o')[:1]+'{1,'+str(len(value))+'})h?'
    return expression


def number_readings(value: int) -> set[str]:
    """生成四位以内日语数字的常见读法，不把任意来源单词当成数字。"""
    if value == 0:
        return {'zero','rei','maru'}
    if value >= 10000:
        return set()
    ones = {0:{''},1:{'ichi'},2:{'ni'},3:{'san'},4:{'yon','shi'},5:{'go'},6:{'roku'},
            7:{'nana','shichi'},8:{'hachi'},9:{'kyuu','ku'}}
    results = {''}
    remainder = value
    for divisor, suffix, exceptional in [(1000,'sen',{1:{'sen'},3:{'sanzen'},8:{'hassen'}}),
                                         (100,'hyaku',{1:{'hyaku'},3:{'sanbyaku'},6:{'roppyaku'},8:{'happyaku'}}),
                                         (10,'juu',{1:{'juu'}})]:
        digit,remainder = divmod(remainder,divisor)
        choices = exceptional.get(digit,{word+suffix for word in ones[digit]}) if digit else {''}
        results = {left+right for left in results for right in choices}
    return {left+right for left in results for right in ones[remainder]}


def build_units(text: str, hints: list[dict], particles: set[int]) -> list[Unit]:
    """按正文脚本边界构造固定假名、汉字读音空位、英文和数字单元。"""
    # 禁止使用改变字符长度的规范化文本来定位，保证 TSV 索引始终来自原文。
    units = []
    explicit = {m.start():m for m in re.finditer(f'[{KANJI}]+[（(]([ぁ-ゖァ-ヺー]+)[）)]',text)}
    excluded = {i for m in explicit.values() for i in range(m.start(1)-1,m.end())}
    for match in UNIT_RE.finditer(text):
        surface = match.group()
        plain = unicodedata.normalize('NFKC',surface)
        begin,end = match.span()
        if begin in excluded:
            continue
        if re.fullmatch(f'[{KANJI}]+',surface):
            candidates = [span for span in hints if begin <= span['start'] and span['start']+span['length'] <= end]
            expected = ''.join(span['ruby'] for span in candidates) if sum(span['length'] for span in candidates)==end-begin else ''
            declaration = hira(explicit[begin].group(1)) if begin in explicit else ''
            units.append(Unit('kanji',surface,begin,end,pattern=declaration,hint=expected))
        elif re.fullmatch('[ぁ-ゖー]+',surface):
            units.append(Unit('kana',surface,begin,end,kana_pattern(surface,particles,begin)))
        elif re.fullmatch('[ァ-ヺー]+',surface):
            units.append(Unit('katakana',surface,begin,end,kana_pattern(surface,particles,begin)))
        elif re.fullmatch('[A-Za-z]+',plain):
            units.append(Unit('latin',surface,begin,end,re.escape(plain.lower())))
        elif re.fullmatch('[0-9]+(?:[.][0-9]+)?',plain):
            choices = {plain.replace('.','')}
            if plain.isdigit():
                choices |= number_readings(int(plain))
                native = {1:'hito',2:'futa',3:'mi',4:'yo',5:'itsu',6:'mu',7:'nana',8:'ya',9:'kokono',10:'to'}
                if int(plain) in native:
                    choices.add(native[int(plain)])
                if plain == '10':
                    choices.add('tou')
            units.append(Unit('number',surface,begin,end,'(?:'+'|'.join(sorted(map(re.escape,choices),key=len,reverse=True))+')'))
        elif surface.isspace():
            units.append(Unit('space',surface,begin,end))
        # 标点本身不发音，不推进唱法；未知有音字符不允许静默丢弃。
        elif unicodedata.category(surface[0]).startswith('P'):
            units.append(Unit('separator',surface,begin,end))
        elif unicodedata.category(surface[0]).startswith('S'):
            continue
        else:
            units.append(Unit('unsupported',surface,begin,end))
    return units


def normalize_source(value: str) -> tuple[str, set[int], dict[int, tuple[int,str]], list[tuple[int,int,int,int]]]:
    """保留来源单词边界、大小写和原始位置；去掉排版符号而不丢音节。"""
    normalized = unicodedata.normalize('NFKC',value)
    compact = ''
    boundaries = {0}
    uppercase = {}
    words = []
    for match in re.finditer('[A-Za-z0-9]+',normalized):
        begin = len(compact)
        word = match.group()
        compact += word.lower()
        end = len(compact)
        boundaries.update((begin,end))
        if word.isalpha() and len(word)>1 and (word.isupper() or (any(c.isupper() for c in word) and strict_romaji(word) is None)):
            uppercase[begin] = (end,word)
        words.append((begin,end,match.start(),match.end()))
    # 原文中出现非拉丁字母/数字的读音文字，不能通过清洗伪装成罗马音。
    if any(c.isalpha() and not c.isascii() for c in normalized):
        return '',set(),{},[]
    return compact,boundaries,uppercase,words


def align_lyric_reading(text: str, romaji: str, hints: list[dict], particles: set[int]) -> dict:
    """用有界动态规划完整消费唱法；并列最优路径只发布共同确定的汉字读音。"""
    source,boundaries,uppercase,words = normalize_source(romaji)
    units = build_units(text,hints,particles)
    strong_boundaries = set()
    normalized_original = unicodedata.normalize('NFKC',romaji)
    previous_raw_end = 0
    for left,right,raw_start,raw_end in words:
        separator = normalized_original[previous_raw_end:raw_start]
        if re.search(r'\s{2,}|[,;.!?、。-]',separator):
            strong_boundaries.add(left)
        previous_raw_end = raw_end
    if not source:
        return {'status':'missing' if not romaji.strip() else 'unmatched','spans':[], 'reason':'来源唱法缺失或含不支持的文字'}
    if any(unit.kind == 'unsupported' for unit in units) or len(source)>800 or len(units)>200:
        return {'status':'unmatched','spans':[], 'reason':'正文存在未支持的字符或超出对齐资源上限'}
    # 保存最优切分图，歧义不会因遍历顺序而被任意选中。
    # 外来语是有限的明确表记映射；每个候选仍须完整匹配正文片假名。
    # 此表不为汉字提供词典猜读，未知英文也不能吞掉任意片假名。
    loan_aliases = {
        'party':('paatii','paati'), 'time':('taimu',), 'again':('agein',),
        'cafe':('kafe',), 'au':('',), 'lait':('ore',), 'orange':('orenji',),
        'dress':('doresu',), 'defo':('defo',), 'no':('noo',), 'sleeve':('suriibu',),
        'shakee':('sheke',), 'down':('daun',), 'cream':('kuriimu',),
        'star':('sutaa',), 'story':('sutoorii',), 'love':('rabu',),
        'wine':('wain',), 'hero':('hiiroo','hiro'), 'game':('geemu',),
        'take':('teiku',), 'name':('neemu',), 'soda':('sooda',),
        'more':('moa',), 'solo':('soro',), 'rave':('reibu',),
        'same':('seimu',), 'care':('kea',), 'cute':('kyuuto',), 'mode':('moodo',),
        'baby':('beibii','beibi'), 'music':('myuujikku',), 'dance':('dansu',),
        'night':('naito',), 'dream':('doriimu',), 'heart':('haato',),
        'light':('raito',), 'life':('raifu',), 'world':('waarudo',),
        'girl':('gaaru',), 'boy':('booi',), 'happy':('happii','happi'),
        'smile':('sumairu',), 'hello':('haroo',), 'rain':('rein',),
        'blue':('buruu',), 'beat':('biito',), 'sound':('saundo',),
        'sweet':('suiito',), 'show':('shoo',), 'kiss':('kisu',),
        'computer':('konpyuutaa',), 'wish':('wisshu',), 'melody':('merodii',),
        'skirt':('sukaato',), 'shortcake':('shootokeeki',), 'bus':('basu',),
        'speed':('supiido',), 'shirt':('shatsu',), 'pink':('pinku',),
        'melt':('meruto',), 'message':('messeeji',), 'shower':('shawaa',),
        'candy':('kyandii','kyandi'), 'violet':('baioretto',), 'glass':('garasu','gurasu'),
        'color':('karaa',), 'collection':('korekushon',), 'marginal':('maajinaru',),
        'canvas':('kyanbasu',), 'red':('reddo',), 'technique':('tekunikku',),
        'headphone':('heddohon',), 'stereo':('sutereo',), 'real':('riaru',),
        'iced':('aisu',), 'cocoa':('kokoa',), 'milk':('miruku',), 'sandal':('sandaru',),
        'arabesque':('arabesuku',), 'rhythm':('rizumu',), 'event':('ibento',),
        'list':('risuto',), 'package':('pakkeeji',), 'requiem':('rekuiemu',),
        'lesson':('ressun',), 'legato':('regaato',), 'display':('disupurei',),
        'original':('orijinaru',), 'drama':('dorama',), 'bell':('beru',),
        'illumination':('irumineeshon',), 'type':('taipu',), 'mark':('maaku',),
        'finder':('faindaa',), 'period':('piriodo',), 'colorful':('karafuru',),
        'stage':('suteeji',), 'bye':('bai',), 'juice':('juusu',),
        'city':('shiti','siti'), 'underground':('andaaguraundo',), 'mayday':('meedee',),
        'two':('tsuu','tuu'), 'door':('doa',), 'net':('netto',), 'virtual':('baacharu',),
        'magic':('majikku',), 'black':('burakku',), 'gum':('gamu',), 'noise':('noizu',),
        'note':('nooto',), 'oh':('oo','o'), 'yeah':('yee','iee','yei'),
        'speaker':('supiikaa',), 'knife':('naifu',), 'puzzle':('pazuru',),
        'harmony':('haamonii',), 'step':('suteppu',), 'page':('peeji',),
        'yay':('yei',), 'service':('saabisu',), 'zigzag':('jiguzagu',),
        'one':('wan',), 'gemini':('jemini',), 'call':('kooru',), 'lip':('rippu',),
        'rule':('ruuru',), 'hop':('hoppu',), 'mail':('meeru',), 'bitter':('bitaa',),
        'fever':('fiibaa',), 'monogram':('monoguramu',), 'bed':('beddo',),
        'telecaster':('terekyasutaa',), 'kitchen':('kicchin',), 'tick':('tikku',), 'tock':('takku',),
        'rock':('rokku',), 'roll':('rooru',), 'sun':('san',),
    }
    word_by_start = {left:(right,source[left:right]) for left,right,_,_ in words}

    def loan_ends(cursor: int, unit: Unit) -> list[int]:
        """只接受外来语声明表与固定假名等价的整词序列，禁止任意大写占位。"""
        expression = re.compile(unit.pattern)
        ends = []
        variants = {''}
        for _ in range(32):
            item = word_by_start.get(cursor)
            if item is None:
                break
            end,word = item
            aliases = loan_aliases.get(word,()) if cursor in uppercase else ()
            choices = set(aliases)
            if strict_romaji(word) is not None:
                choices.add(word)
            if not choices:
                break
            variants = {left+right for left in variants for right in choices}
            # 超限时拒绝该别名分支，不能任意裁掉候选后假装唯一。
            if len(variants)>512:
                break
            if any(expression.fullmatch(value) for value in variants):
                ends.append(end)
            cursor = end
        return ends

    explored = 0
    exhausted = False
    best_edges = {}
    expressions = {i:re.compile(unit.pattern) for i,unit in enumerate(units) if unit.kind in {'kana','katakana','latin','number'}}
    @lru_cache(maxsize=None)
    def decode_segment(begin: int, end: int) -> str | None:
        """逐个源词严格转换片段，保留撇号与空格对音节边界的作用。"""
        result = []
        for left,right,_,_ in words:
            a,b = max(begin,left),min(end,right)
            if a<b:
                if left in uppercase and source[left:right] in loan_aliases:
                    return None
                decoded = strict_romaji(source[a:b])
                if decoded is None and b == end and b < len(source) and source[b-1] == source[b] and source[b] not in 'aeioun':
                    stem = strict_romaji(source[a:b-1])
                    decoded = stem+'っ' if stem else None
                if decoded is None:
                    return None
                result.append(decoded)
        return ''.join(result)

    @lru_cache(maxsize=None)
    def solve(unit_index: int, cursor: int) -> tuple[int,int] | None:
        """先满足完整来源与正文边界，再以词典同音锚点辅助切分；并列解保留歧义。"""
        nonlocal explored,exhausted
        explored += 1
        if explored>40000:
            exhausted = True
            return None
        if unit_index == len(units):
            return (0,0) if cursor == len(source) else None
        unit = units[unit_index]
        options = []
        if unit.kind in {'space','separator'}:
            structure = 0 if cursor in strong_boundaries else (1 if cursor in boundaries else 3)
            options.append((cursor,'',structure,0,'正文分隔'))
        elif unit.kind == 'kanji':
            for end in range(cursor+1,min(len(source),cursor+24*len(unit.text))+1):
                reading = decode_segment(cursor,end)
                if reading is None or not reading:
                    continue
                if unit.pattern and phonetic_key(reading)!=phonetic_key(unit.pattern):
                    continue
                if len(reading)>8*len(unit.text):
                    continue
                # 完整来源和正文边界为第一约束；词典相同发音仅作二级切点证据。
                equivalent = bool(unit.hint) and phonetic_key(reading)==phonetic_key(unit.hint)
                hint_cost = 0 if equivalent or not unit.hint else 1
                options.append((end,unit.pattern or (unit.hint if equivalent else reading),0,hint_cost,'歌词明示读音' if unit.pattern else '来源罗马音'))
            if unit.pattern:
                declared = Unit('katakana',unit.text,unit.start,unit.end,kana_pattern(unit.pattern,set(),0))
                for end in loan_ends(cursor,declared):
                    options.append((end,unit.pattern,0,0,'歌词明示读音与已知外来语'))
        else:
            expression = expressions[unit_index]
            # 枚举所有完整匹配终点，避免正则贪心隐藏其它全句解。
            for end in range(cursor+1,len(source)+1):
                if expression.fullmatch(source[cursor:end]):
                    structural = (0 if cursor in boundaries else 1)+(0 if end in boundaries else 1)
                    options.append((end,'',structural,0,'正文固定唱法'))
            if unit.kind == 'katakana':
                for end in loan_ends(cursor,unit):
                    options.append((end,'',0,0,'来源外来语 '+source[cursor:end]))
            abbreviations = {'センチ':'cm','キロ':'km','メートル':'m','ミリ':'mm'}
            abbreviation = abbreviations.get(unit.text)
            if abbreviation and source.startswith(abbreviation,cursor):
                options.append((cursor+len(abbreviation),'',0,0,'正文单位缩写'))
            if unit.text == 'らっきー' and source.startswith('lucky',cursor):
                options.append((cursor+5,'',0,0,'正文外来词 lucky'))
        best = None
        accepted = []
        for end,reading,structure,hint_cost,evidence in options:
            tail = solve(unit_index+1,end)
            if tail is None:
                continue
            score = (tail[0]+structure,tail[1]+hint_cost)
            edge = (end,reading,evidence)
            if best is None or score<best:
                best,accepted = score,[edge]
            elif score == best:
                accepted.append(edge)
        if best is not None:
            best_edges[(unit_index,cursor)] = tuple(set(accepted))
        return best

    answer = solve(0,0)
    if exhausted:
        solve.cache_clear()
        decode_segment.cache_clear()
        best_edges.clear()
        return {'status':'unmatched','spans':[], 'reason':'对齐搜索达到资源上限，未发布不完整搜索中的猜读', 'states':explored}
    if answer is None:
        solve.cache_clear()
        decode_segment.cache_clear()
        best_edges.clear()
        return {'status':'unmatched','spans':[], 'reason':'来源唱法无法与整句正文完整对齐；未使用局部片段猜读', 'states':explored}
    spans = []
    segments = []
    ambiguous = []
    # 只从根节点遍历最优边图，避免每个搜索状态复制整条候选路径。
    # 空间规模按状态/边计，不再按「状态数 × 剩余歌词单元数」增长。
    values = [set() for _ in units]
    cursors = {0}
    for index in range(len(units)):
        following = set()
        for cursor in cursors:
            for end,reading,evidence in best_edges.get((index,cursor),()):
                values[index].add((cursor,end,reading,evidence))
                following.add(end)
        cursors = following
    solve.cache_clear()
    decode_segment.cache_clear()
    best_edges.clear()
    for unit,choices in zip(units,values):
        records = [{'source_start':a,'source_end':b,'source_fragment':source[a:b],'reading':r,'evidence':e}
                   for a,b,r,e in sorted(choices)]
        segments.append({'text':unit.text,'start':unit.start,'length':unit.end-unit.start,'kind':unit.kind,'dictionary_hint':unit.hint,'explicit_reading':unit.pattern if unit.kind=='kanji' else '', 'candidates':records})
        if unit.kind != 'kanji':
            continue
        readings = {record['reading'] for record in records}
        if len(readings)!=1:
            ambiguous.append(unit.text)
            continue
        reading = next(iter(readings))
        # 重复汉字只在源读音能等分为相同音串时逐字标，避免词典把「恋恋」当成复合词。
        repeated = len(unit.text)>1 and len(set(unit.text))==1 and len(reading)%len(unit.text)==0
        chunk = reading[:len(reading)//len(unit.text)] if repeated else ''
        if repeated and chunk and chunk*len(unit.text)==reading:
            spans.extend({'start':unit.start+i,'length':1,'ruby':chunk} for i in range(len(unit.text)))
        else:
            spans.append({'start':unit.start,'length':len(unit.text),'ruby':reading})
    status = 'ambiguous' if ambiguous else 'aligned'
    return {'status':status,'spans':spans,'segments':segments,'source_normalized':source,'source_consumed':len(source),
            'source_length':len(source),'score':answer,'ambiguous_groups':ambiguous,'states':explored}
