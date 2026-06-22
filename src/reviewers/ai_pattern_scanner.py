"""
AI Writing Pattern Scanner — rule-based detection of AI-generated text patterns.

Based on Wikipedia "Signs of AI Writing" and the humanizer project
(github.com/blader/humanizer). Detects 24+ patterns across 5 categories
with 3-tier vocabulary.

This is a PURE RULE-BASED scanner — no LLM calls. It produces Annotation
objects that say "here's what was found and why it looks AI-generated,"
never "here's how to fix it."
"""

import re
from src.annotation import Annotation, Location, Severity


# ============================================================
# TIER 1 — True AI giveaways (always flagged HIGH regardless of count)
# ============================================================
TIER1_HARD = [
    "delve", "delve into", "delve deeper",
    "tapestry", "rich tapestry", "vibrant tapestry",
    "pivotal", "pivotal moment", "pivotal role",
    "testament", "a testament to", "serves as a testament",
    "showcase", "showcases", "showcasing",
    "underscores", "underscoring",
    "realm", "in the realm of", "realm of",
    "landscape", "evolving landscape", "changing landscape",
    "intricate", "intricately",
    "embodies", "epitomizes",
    "unwavering", "unwaveringly",
    "indelible", "indelibly",
    "transformative",
    "groundbreaking",
    "revolutionary",
    "cutting-edge",
    "state-of-the-art",
    "paradigm", "paradigm shift",
    "game-changer",
    "seamless", "seamlessly",
    "holistic",
    "synergistic", "synergy",
    "bespoke",
    "curated",
    "meticulous", "meticulously",
    "thought-provoking",
    "game changing",
    "world-class",
    "best-in-class",
    "market-leading",
]

# ============================================================
# TIER 1b — Transition/signposting words (normal in academic prose,
# only flagged if density is high: 3+ in a 5-sentence window)
# ============================================================
TIER1_TRANSITIONS = [
    "moreover", "furthermore", "additionally", "consequently", "thus", "hence",
    "notably", "importantly", "interestingly", "surprisingly",
    "crucial", "paramount", "vital", "essential",
    "profound", "profoundly", "deeply",
    "highlighting", "highlight",
    "robust",
]

# ============================================================
# TIER 2 — Suspicious in Density (flagged when frequent)
# ============================================================
TIER2_VOCAB = [
    "comprehensive", "comprehensively",
    "sophisticated",
    "innovative", "innovation",
    "dynamic", "dynamically",
    "diverse", "diversity",
    "nuanced", "nuance",
    "compelling",
    "resonate", "resonates",
    "empower", "empowering", "empowerment",
    "embrace", "embracing",
    "foster", "fostering",
    "leverage", "leveraging",
    "optimize", "optimization",
    "streamline", "streamlined",
    "facilitate",
    "enable",
    "ensure",
    "significant", "significantly",
    "substantial", "substantially",
    "considerable", "considerably",
    "demonstrate", "demonstrates",
    "indicate", "indicates",
    "suggest", "suggests",
    "reveal", "reveals",
    "illustrate", "illustrates",
    "elucidate", "articulate", "delineate", "explicate",
    "contextualize", "situate", "foreground",
    "unpack", "interrogate",
    "complicate", "complicates",
    "gesture toward", "speak to",
    "reckon with", "grapple with", "wrestle with",
]

# ============================================================
# TIER 3 — Context-Dependent (only in academic writing context)
# ============================================================
TIER3_VOCAB = [
    "ultimately",
    "in other words", "that is to say", "put differently",
    "simply put", "in essence", "at its core", "fundamentally",
    "it is worth noting", "it should be noted", "it is important to note",
    "one might argue", "some might argue", "it could be argued",
    "as previously mentioned", "as noted earlier", "as discussed above",
    "in conclusion", "to summarize", "in summary", "to conclude",
    "moving forward", "going forward", "looking ahead",
    "in today's world", "in recent years", "in the modern era",
    "in the age of", "in the context of", "in light of",
]

# ============================================================
# HELPER
# ============================================================

def _make_annotation(
    dimension: str,
    title: str,
    severity: Severity,
    line_number: int,
    matched_text: str,
    why: str,
    category: str,
    section: str = "",
    paragraph: int = 0,
) -> Annotation:
    """Create an Annotation without any suggestion field."""
    return Annotation(
        dimension=dimension,
        title=title,
        severity=severity,
        location=Location(
            section=section,
            paragraph=paragraph,
            line_start=line_number,
            line_end=line_number,
            quoted_text=matched_text[:200],
        ),
        what=matched_text,
        why=why,
        category=category,
    )


def _match_patterns(
    text: str,
    patterns: list[tuple[str, float]],
    title: str,
    category: str,
    why_template: str | None = None,
) -> list[Annotation]:
    """Apply regex patterns and produce Annotation objects."""
    results: list[Annotation] = []
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        for pat, sev in patterns:
            for m in re.finditer(pat, line, re.IGNORECASE):
                why = why_template.format(match=m.group()) if why_template else \
                      f'检测到"{title}"模式，这是AI生成文本的常见特征'
                results.append(_make_annotation(
                    "ai_patterns",
                    title,
                    Severity.HIGH if sev >= 0.8 else (Severity.MEDIUM if sev >= 0.5 else Severity.LOW),
                    i,
                    m.group(),
                    why,
                    category,
                ))
    return results


# ============================================================
# DETECTION FUNCTIONS
# ============================================================

def detect_tier_vocab(text: str) -> list[Annotation]:
    """Detect Tier 1 hard, Tier 1b transition (density-gated), Tier 2, Tier 3 vocabulary.

    Tier 1 hard: always flagged HIGH (true AI giveaways like 'delve', 'tapestry').
    Tier 1b transitions: 'hence', 'thus', 'moreover' — normal in academic prose,
        only flagged when 3+ appear in a 5-sentence window (density trigger).
    Tier 2: flagged MEDIUM per occurrence.
    Tier 3: flagged LOW per occurrence.
    """
    results: list[Annotation] = []
    lines = text.split("\n")

    # ── First pass: collect all matches ──
    # tier1_hard_matches: list of (line_no, match_text)
    # tier1b_matches: list of line_no
    # tier2_matches, tier3_matches: same as before

    tier1b_line_numbers: list[int] = []
    tier2_line_numbers: list[int] = []
    tier2_line_words: dict[int, list[str]] = {}

    for i, line in enumerate(lines, 1):
        line_lower = line.lower()

        # Tier 1 hard: always flag HIGH
        for word in TIER1_HARD:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            for m in pattern.finditer(line):
                results.append(_make_annotation(
                    "ai_patterns",
                    "AI词汇 (Tier1)",
                    Severity.HIGH,
                    i,
                    m.group(),
                    f'"{m.group()}" 是AI生成文本的强烈标志词，在学术写作中几乎仅由AI使用',
                    "language",
                ))

        # Tier 1b: track positions, don't flag yet
        for word in TIER1_TRANSITIONS:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            for m in pattern.finditer(line):
                tier1b_line_numbers.append(i)

        # Tier 2: track positions, density-gate later
        tier2_line_numbers: list[int] = []
        tier2_line_words: dict[int, list[str]] = {}

        for word in TIER2_VOCAB:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            for m in pattern.finditer(line):
                tier2_line_numbers.append(i)
                tier2_line_words.setdefault(i, []).append(m.group())

        # Tier 3: flag LOW
        for word in TIER3_VOCAB:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            for m in pattern.finditer(line):
                results.append(_make_annotation(
                    "ai_patterns",
                    "AI词汇 (Tier3)",
                    Severity.LOW,
                    i,
                    m.group(),
                    f'"{m.group()}" 可能是AI填充语，在上下文中显得冗余或公式化',
                    "language",
                ))

    # ── Second pass: density-gate Tier 2 ──
    # Only flag when 4+ Tier2 words appear in a 40-line window
    # (individual words like "demonstrate" "optimization" are normal in economics)
    if tier2_line_numbers:
        sorted_t2 = sorted(set(tier2_line_numbers))
        flagged_t2: set[int] = set()
        for i, line_no in enumerate(sorted_t2):
            window_count = sum(
                1 for j in range(max(0, i - 3), min(len(sorted_t2), i + 4))
                if abs(sorted_t2[j] - line_no) <= 40
            )
            if window_count >= 4 and line_no not in flagged_t2:
                words_at_line = tier2_line_words.get(line_no, [])
                unique_words = list(set(words_at_line))[:3]
                for w in unique_words:
                    results.append(_make_annotation(
                        "ai_patterns",
                        "密集AI词汇 (Tier2)",
                        Severity.MEDIUM,
                        line_no,
                        w,
                        f'"{w}" 等AI倾向词汇在短距离内密集出现了 {window_count} 次，'
                        f'学术写作中此类词汇密度异常是AI生成文本的次级信号',
                        "language",
                    ))
                # Mark all nearby lines as flagged
                for j in range(max(0, i - 3), min(len(sorted_t2), i + 4)):
                    if abs(sorted_t2[j] - line_no) <= 40:
                        flagged_t2.add(sorted_t2[j])

    # ── Third pass: density-gate Tier 1b transitions ──
    # Only flag if 3+ transition words appear within a 5-sentence window
    if tier1b_line_numbers:
        sentences = re.split(r'[.!?。！？]\s*', text)
        sentence_bounds: list[tuple[int, int]] = []  # (start_line, end_line) per sentence
        for sentence in sentences:
            start = text.find(sentence[:30]) if sentence else 0
            before = text[:start]
            start_line = before.count("\n") + 1 if start >= 0 else 1
            end_line = start_line + sentence.count("\n")
            sentence_bounds.append((start_line, end_line))

        # Use approximate: count transitions per 5-line windows
        flagged_lines: set[int] = set()
        sorted_lines = sorted(set(tier1b_line_numbers))
        for i, line_no in enumerate(sorted_lines):
            # Count transitions in window of 5 consecutive transition occurrences
            window_start = max(0, i - 2)
            window_end = min(len(sorted_lines), i + 3)
            window_count = sum(
                1 for j in range(window_start, window_end)
                if abs(sorted_lines[j] - line_no) <= 30  # within ~30 lines = ~1 paragraph
            )
            if window_count >= 3 and line_no not in flagged_lines:
                # Flag all transitions in this dense cluster
                for j in range(window_start, window_end):
                    if j != i and abs(sorted_lines[j] - line_no) <= 30:
                        continue  # will be caught when we reach them
                # Find the actual word that triggered at this line
                line_text = lines[line_no - 1].lower() if line_no <= len(lines) else ""
                matched_words = [w for w in TIER1_TRANSITIONS
                                if re.search(r'\b' + re.escape(w) + r'\b', line_text)]
                for w in set(matched_words):
                    context = f"密集过渡词簇（{window_count}次/{30}行内）"
                    results.append(_make_annotation(
                        "ai_patterns",
                        "密集过渡词 (Tier1b)",
                        Severity.MEDIUM,
                        line_no,
                        w,
                        f'"{w}" 等过渡词在短距离内密集出现了 {window_count} 次，'
                        f'学术写作中过渡词密度过高是AI生成文本的特征（正常使用通常每页1-2次）',
                        "language",
                    ))
                flagged_lines.update(
                    sorted_lines[j] for j in range(window_start, window_end)
                    if abs(sorted_lines[j] - line_no) <= 30
                )

    return results


def detect_significance_inflation(text: str) -> list[Annotation]:
    """Detect inflated significance claims."""
    patterns = [
        (r'mark(?:ing|s)? a (?:pivotal|significant|crucial|major) (?:moment|turning point|shift)', 0.9),
        (r'serves as a testament to', 0.8),
        (r'stand(?:s|ing) as a (?:beacon|testament|monument|cornerstone)', 0.9),
        (r'a (?:landmark|watershed|defining) (?:moment|achievement|accomplishment)', 0.8),
        (r'profound(?:ly)? (?:impact|influence|effect|change|shift|implication)', 0.7),
        (r'reshap(?:e|ing) (?:the|our) understanding of', 0.8),
        (r'fundamentally (?:alter|change|transform|shift)', 0.7),
        (r'usher(?:s|ing|ed) in a new era', 0.9),
        (r'at the forefront of', 0.7),
        (r'breakthrough', 0.6),
        (r'unprecedented', 0.7),
    ]
    return _match_patterns(text, patterns, "意义夸大", "content",
        why_template='"{match}" 是夸大的意义声明，AI生成文本倾向于使用过度宏大的语言')


def detect_vague_attributions(text: str) -> list[Annotation]:
    """Detect vague attributions without specific citations."""
    patterns = [
        (r'Experts (?:believe|suggest|argue|agree|note|claim|say)', 0.8),
        (r'Studies (?:show|suggest|indicate|demonstrate|reveal|prove|find)', 0.8),
        (r'Research (?:shows|suggests|indicates|demonstrates|reveals)', 0.7),
        (r'Many (?:scholars|researchers|scientists|experts) (?:believe|argue|suggest)', 0.8),
        (r'It is (?:widely|generally|commonly) (?:believed|accepted|known|understood)', 0.7),
        (r'According to (?:experts|researchers|scholars|scientists)', 0.7),
        (r'A growing body of (?:evidence|research|literature)', 0.6),
        (r'Critics (?:argue|say|claim|suggest|note)', 0.7),
        (r'Some (?:argue|say|believe|suggest|claim)', 0.5),
    ]
    return _match_patterns(text, patterns, "模糊引用", "content",
        why_template='"{match}" 是模糊的归因表述，未引用具体文献，AI生成文本常以此规避缺乏真实引用的问题')


def detect_superficial_ing(text: str) -> list[Annotation]:
    """Detect superficial -ing clause patterns."""
    patterns = [
        (r'highlighting the (?:importance|significance|role|need|challenges)', 0.6),
        (r'reflecting the (?:complexity|diversity|nature|importance|challenges)', 0.6),
        (r'showcasing the (?:ability|potential|importance|power|versatility)', 0.7),
        (r'demonstrating the (?:importance|significance|power|potential|need)', 0.6),
        (r'underscoring the (?:importance|need|significance|challenges|role)', 0.6),
        (r'suggesting a (?:need|shift|trend|pattern|relationship)', 0.5),
    ]
    return _match_patterns(text, patterns, "肤浅分词分析", "content",
        why_template='"{match}" 是"highlighting the importance of..."型的分词从句，这是AI写作中"肤浅分析"的典型标志')


def detect_promotional_language(text: str) -> list[Annotation]:
    """Detect promotional/marketing language."""
    patterns = [
        (r'\b(?:nestled|breathtaking|stunning|vibrant|gorgeous|magnificent|exquisite)\b', 0.7),
        (r'\b(?:renowned|prestigious|esteemed|distinguished|eminent|illustrious)\b', 0.6),
        (r'\b(?:world-renowned|world-famous|internationally recognized)\b', 0.7),
        (r'\b(?:exceptional|extraordinary|remarkable|outstanding|superb|excellent)\b', 0.5),
        (r'\b(?:unmatched|unparalleled|unequalled|unsurpassed|peerless)\b', 0.6),
    ]
    return _match_patterns(text, patterns, "推销性语言", "content",
        why_template='"{match}" 是推销/营销性质的词汇，在学术写作中使用显得不客观')


def detect_negative_parallelisms(text: str) -> list[Annotation]:
    """Detect 'it's not just X, it's Y' patterns."""
    patterns = [
        (r"It(?:'s| is) not (?:just|merely|only|simply) (\w+(?:\s+\w+){0,3}), it(?:'s| is) (\w+(?:\s+\w+){0,5})", 0.7),
        (r"not (?:just|merely|only|simply) a (\w+(?:\s+\w+){0,3}), but (?:a |also )?(\w+(?:\s+\w+){0,3})", 0.6),
        (r"more than (?:just|merely|simply) (\w+(?:\s+\w+){0,3})", 0.5),
        (r"This is not (?:just|merely|only|simply) (\w+(?:\s+\w+){0,5})", 0.6),
    ]
    return _match_patterns(text, patterns, "否定并列", "language",
        why_template='"{match}" 是"不仅是X，更是Y"的否定并列句式，AI常以此结构增强说服力，但显得公式化')


def detect_em_dashes(text: str) -> list[Annotation]:
    """Detect em dashes — only flag when 3+ on a single line.

A single en-dash in "mean–variance" or "high–risk" is normal academic writing.
Excessive dashes (3+ per line) is a genuine AI writing signal.
"""
    results: list[Annotation] = []
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        count = line.count('—') + line.count('--') + line.count('–')
        # Only flag when 3+ dashes on one line. Single en-dash in
        # "mean–variance" or "high–risk" is completely normal.
        if count >= 3:
            results.append(_make_annotation(
                "ai_patterns",
                "破折号使用",
                Severity.HIGH if count >= 5 else Severity.MEDIUM,
                i,
                line.strip()[:200],
                f"此行包含 {count} 个破折号。AI生成的文本倾向于大量使用破折号（—），频率远超人类作者",
                "style",
            ))
    return results


def detect_copula_avoidance(text: str) -> list[Annotation]:
    """Detect copula avoidance — 'serves as' instead of 'is', 'boasts' instead of 'has'."""
    patterns = [
        (r'\bserves as\b', 0.6, '使用 "serves as" 而非更直接的 "is"，是AI写作中系词回避的常见特征'),
        (r'\bacts as\b', 0.5, '使用 "acts as" 而非更直接的 "is"，是AI写作中系词回避的特征'),
        (r'\bfunctions as\b', 0.5, '使用 "functions as" 而非更直接的 "is"，是AI写作中系词回避的特征'),
        (r'\bboasts\b(?!\s+(?:a|an|the|its|their)\s+(?:history|tradition|record|lineage))', 0.6, '"boasts" 是AI常用的拟人化动词，在学术写作中显得不自然'),
        (r'\bpossesses\b', 0.5, '"possesses" 在AI生成文本中常被用来替代更简洁的 "has"'),
    ]
    results: list[Annotation] = []
    lines = text.split("\n")
    for pat, sev, why in patterns:
        for i, line in enumerate(lines, 1):
            for m in re.finditer(pat, line, re.IGNORECASE):
                results.append(_make_annotation(
                    "ai_patterns",
                    "系词回避",
                    Severity.HIGH if sev >= 0.8 else (Severity.MEDIUM if sev >= 0.5 else Severity.LOW),
                    i,
                    m.group(),
                    why,
                    "language",
                ))
    return results


def detect_rule_of_three(text: str) -> list[Annotation]:
    """Detect rule-of-three adjective/noun sequences."""
    patterns = [
        (r'(\w+),\s*(\w+),\s*(?:and|&)\s*(\w+)\s*(?:approach|method|solution|strategy|framework|model|system|process|experience|journey|understanding|perspective|analysis|design|development|implementation)', 0.5, '三连排比("X, Y, and Z approach")是AI写作的风格特征，在人类学术写作中较少出现'),
    ]
    results: list[Annotation] = []
    lines = text.split("\n")
    for pat, sev, why in patterns:
        for i, line in enumerate(lines, 1):
            for m in re.finditer(pat, line, re.IGNORECASE):
                results.append(_make_annotation(
                    "ai_patterns", "三连排比",
                    Severity.MEDIUM, i, m.group(), why, "language",
                ))
    return results


def detect_elegant_variation(text: str) -> list[Annotation]:
    """Detect elegant variation — cycling synonyms unnaturally."""
    synonym_groups = [
        ["researcher", "scholar", "academic", "scientist", "investigator"],
        ["study", "research", "investigation", "examination", "inquiry", "exploration"],
        ["important", "significant", "crucial", "vital", "essential", "paramount"],
        ["shows", "demonstrates", "reveals", "indicates", "illustrates", "highlights"],
        ["method", "approach", "technique", "methodology", "framework"],
        ["result", "finding", "outcome", "discovery", "insight"],
        ["problem", "challenge", "issue", "difficulty", "obstacle", "limitation"],
    ]
    results: list[Annotation] = []
    sentences = re.split(r'[.!?。！？]\s*', text)
    for group in synonym_groups:
        for i in range(len(sentences) - 2):
            window = " ".join(sentences[i:i + 5]).lower()
            found = [w for w in group if re.search(r'\b' + re.escape(w) + r'\b', window)]
            if len(found) >= 3:
                results.append(_make_annotation(
                    "ai_patterns",
                    "同义词轮换",
                    Severity.LOW,
                    i + 1,
                    f'在5句内使用了: {", ".join(found)}',
                    f"在5个句子内轮换了 {len(found)} 个同义词({', '.join(found)})，可能是AI的'优雅变体'策略。学术写作应保持术语一致性",
                    "language",
                ))
                break
    return results


def detect_false_ranges(text: str) -> list[Annotation]:
    """Detect false ranges — 'From X to Y' spanning unrelated extremes."""
    known_pairs = [
        (r'from the Big Bang to', 0.9),
        (r'from quantum mechanics to', 0.8),
        (r'from artificial intelligence to', 0.7),
        (r'from ancient (?:times|civilizations) to', 0.8),
        (r'from molecules to', 0.7),
        (r'from the microscopic to', 0.8),
        (r'from neurons to', 0.7),
        (r'from genes to', 0.7),
        (r'from cells to', 0.7),
        (r'from the individual to', 0.6),
        (r'from theory to', 0.6),
        (r'from academia to', 0.6),
    ]
    results: list[Annotation] = []
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        for pat, sev in known_pairs:
            for m in re.finditer(pat, line, re.IGNORECASE):
                results.append(_make_annotation(
                    "ai_patterns",
                    "虚假范围",
                    Severity.HIGH if sev >= 0.8 else (Severity.MEDIUM if sev >= 0.5 else Severity.LOW),
                    i,
                    m.group(),
                    f'"From X to Y" 句式("{m.group()}")跨度空泛，是AI生成文本的典型特征。具体研究应有明确、有限的范围',
                    "language",
                ))
    return results


def detect_chatbot_artifacts(text: str) -> list[Annotation]:
    """Detect chatbot-style communication patterns."""
    patterns = [
        (r'I hope this (?:helps|clarifies|answers|explains|sheds)', 0.95),
        (r'Let me know if you (?:have|need|want|would like)', 0.95),
        (r'Feel free to (?:ask|reach|contact|get in touch)', 0.95),
        (r'As (?:an AI|a language model|a large language model)', 0.99),
        (r'(?:As of|Based on) my (?:knowledge cutoff|training (?:data|cutoff)|last update)', 0.99),
        (r'(?:Great|Excellent|Good|Interesting|Fascinating) question', 0.9),
        (r"You(?:'re| are) (?:absolutely|completely|totally) right", 0.9),
        (r'I (?:completely|fully|totally|absolutely) agree', 0.8),
        (r"(?:That|This)(?:'s| is) (?:an? )?(?:excellent|great|wonderful|fantastic|interesting) (?:question|point|observation|perspective)", 0.9),
        (r"It(?:'s| is) (?:important|crucial|essential|vital|worthwhile) to (?:note|mention|remember|consider|understand)", 0.6),
        (r'^(?:Sure!|Of course!|Absolutely!|Certainly!|Great!|Excellent!)', 0.9),
        (r'^(?:Hi|Hello|Hey|Greetings|Dear)\b.{0,50}(?:I|we|let me|allow me)', 0.5),
    ]
    return _match_patterns(text, patterns, "聊天机器人痕迹", "communication",
        why_template='"{match}" 是聊天机器人式的表达，学术论文中不应出现此类互动性语言')


def detect_formulaic_challenges(text: str) -> list[Annotation]:
    """Detect formulaic 'despite challenges' structures."""
    patterns = [
        (r'[Dd]espite (?:these |the |its |their )?(?:challenges|limitations|difficulties|obstacles|setbacks),.{0,80}(?:continue|remain|persist|thrive|flourish|grow|succeed|advance|progress)', 0.7),
        (r'[Ww]hile (?:challenges|limitations|obstacles) (?:remain|exist|persist),', 0.6),
        (r'[Nn]ot without (?:its |their )?(?:challenges|limitations|difficulties)', 0.6),
        (r'[Cc]hallenges (?:remain|persist|continue|abound), (?:but|yet|however)', 0.6),
    ]
    return _match_patterns(text, patterns, "公式化挑战段", "content",
        why_template='"{match}" 是"尽管存在挑战，但仍..."的公式化结构，是AI生成文本中常见的过渡模板')


def detect_hedging_excess(text: str) -> list[Annotation]:
    """Detect excessive hedging phrases."""
    patterns = [
        (r'\b(?:could potentially possibly|could possibly|might possibly|may potentially|could potentially)\b', 0.7),
        (r'\b(?:it is possible that|it may be that|it might be that|it could be that)\b', 0.6),
        (r'\b(?:to some extent|to a certain extent|to a degree|in some sense|in a sense)\b', 0.5),
        (r'\b(?:perhaps|maybe|possibly|potentially|arguably)\b', 0.3),
    ]
    annotations = _match_patterns(text, patterns, "过度模糊限定", "filler",
        why_template='"{match}" 是模糊限定语，过度使用会削弱学术论证的力度')
    # Increase severity if density is high
    word_count = len(text.split())
    if word_count > 0 and len(annotations) / (word_count / 100) > 3:
        for a in annotations:
            if a.severity == Severity.LOW:
                a.severity = Severity.MEDIUM
            elif a.severity == Severity.MEDIUM:
                a.severity = Severity.HIGH
    return annotations


def detect_generic_conclusions(text: str) -> list[Annotation]:
    """Detect generic/conclusory endings."""
    patterns = [
        (r'[Ff]uture (?:research|work|studies|investigation) (?:should|could|may|might|will|would|need to) (?:focus on|explore|examine|investigate|address|consider)', 0.7),
        (r'[Ff]urther (?:research|investigation|study|work|analysis) (?:is|are) (?:needed|required|necessary|warranted|called for)', 0.7),
        (r'[Mm]ore (?:research|work|studies) (?:is|are) needed', 0.6),
        (r'[Tt]his (?:study|paper|research|work) (?:has|provides|offers|contributes) (?:a |an )?(?:foundation|basis|stepping stone|starting point) for', 0.6),
        (r'[Tt]his (?:opens|paves) (?:the|a) (?:way|door|path) (?:for|to)', 0.7),
        (r'[Ii]n conclusion,?\s*(?:this|the|we|I|our|these)', 0.4),
        (r'[Tt]o (?:summarize|sum up|conclude),?\s*', 0.4),
    ]
    return _match_patterns(text, patterns, "模板化结论", "filler",
        why_template='"{match}" 是模板化的结论表述，AI生成文本倾向使用此类公式化结尾而非具体的结论陈述')


def detect_title_case_headings(text: str) -> list[Annotation]:
    """Detect excessive Title Case headings.

    Excludes lines that are clearly LaTeX code, math, or placeholders —
    those are not real headings and should not be flagged.
    """
    results: list[Annotation] = []
    lines = text.split("\n")
    title_case_count = 0

    # Patterns that indicate a line is NOT a real heading
    _LATEX_LINE = re.compile(
        r'\\'               # LaTeX commands
        r'|\$'               # math mode
        r'|\{'               # braces (code, not prose)
        r'|_\{'              # subscripts
        r'|\^'               # superscripts
        r'|\\begin\{|\\end\{|\\textbf\{|\\textit\{|\\texttt\{'
        r'|\\section|\\subsection|\\chapter|\\part'
        r'|\[公式\]'           # formula placeholder
        r'|&=|\\\\'          # alignment tabs, line breaks
        r'|\\label|\\ref|\\cite'  # cross-references
        r'|(?:sec|app|fig|tab|eq|thm|lem|cor|prop):\w+'  # label remnants
    )

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip empty, short, or obviously-code lines
        if not stripped or len(stripped) < 3 or len(stripped) > 120:
            continue
        if _LATEX_LINE.search(stripped):
            continue

        words = stripped.split()
        # Only consider lines with at least 2 alphabetic words
        alpha_words = [w for w in words if w[0].isalpha() and len(w) > 2]
        if len(alpha_words) < 2:
            continue

        if all(w[0].isupper() if w[0].isalpha() else True for w in words if len(w) > 2):
            title_case_count += 1
            if title_case_count > 2:
                results.append(_make_annotation(
                    "ai_patterns",
                    "Title Case标题",
                    Severity.LOW,
                    i,
                    stripped[:200],
                    f"过度使用Title Case标题（已累计 {title_case_count} 处）是AI写作的风格特征。学术论文通常使用Sentence case",
                    "style",
                ))
    return results


def detect_structured_abstract(text: str) -> list[Annotation]:
    """Detect structured abstracts with bold sub-headings — a common AI writing pattern."""
    patterns = [
        (r'\\textbf\{(?:Background|Methods?|Results?|Conclusions?|Findings?|Objective|Design|Setting|Participants?|Intervention|Outcome|Limitations?|Implications?|Contribution|Purpose|Approach|Framework|Originality|Value):?\}', 0.7),
        (r'\\textbf\{(?:研究背景|研究方法|研究结果|研究结论|背景|方法|结果|结论|发现|目标|设计|贡献|创新|意义):?\}', 0.7),
    ]
    results: list[Annotation] = []
    lines = text.split("\n")
    for pat, sev in patterns:
        for i, line in enumerate(lines, 1):
            for m in re.finditer(pat, line):
                results.append(_make_annotation(
                    "ai_patterns",
                    "结构化摘要小标题",
                    Severity.HIGH if sev >= 0.8 else (Severity.MEDIUM if sev >= 0.5 else Severity.LOW),
                    i,
                    m.group(),
                    "摘要中的加粗小标题（\\textbf{Background:}等）是AI生成论文的典型特征。摘要应为自然流畅的段落，不加小标题",
                    "style",
                ))
    # Escalate severity if 2+ such headings found (likely fully AI-generated abstract)
    if len(results) >= 2:
        for r in results:
            r.severity = Severity.HIGH
    return results


# ============================================================
# STATISTICAL SIGNALS
# ============================================================

def compute_burstiness(text: str) -> float:
    """Compute text burstiness (sentence length variance).

    Low burstiness (uniform sentence length) is an AI writing signal.
    Human writing has natural variation in sentence length.
    Returns AI-likeness score: 0.0 (bursty/human-like) to 1.0 (uniform/AI-like).
    """
    sentences = re.split(r'[.!?。！？]\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    lengths = [len(s.split()) for s in sentences]
    if len(lengths) < 2:
        return 0.0
    mean_len = sum(lengths) / len(lengths)
    if mean_len == 0:
        return 0.0
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    cv = variance ** 0.5 / mean_len
    # Low CV = uniform = AI-like
    if cv > 1.0:
        return 0.0
    elif cv > 0.6:
        return 0.3
    elif cv > 0.4:
        return 0.5
    else:
        return 0.8


def compute_type_token_ratio(text: str) -> float:
    """Compute lexical diversity (type-token ratio).

    AI text often has a moderate TTR (0.45-0.65).
    Returns AI-likeness score for this range.
    """
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < 10:
        return 0.0
    unique = len(set(words))
    total = len(words)
    ttr = unique / total
    if 0.45 <= ttr <= 0.65:
        return 0.5
    else:
        return 0.2


def _compute_sentence_cv(text: str) -> float:
    """Compute sentence length coefficient of variation (normalized)."""
    sentences = re.split(r'[.!?。！？]\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    lengths = [len(s.split()) for s in sentences]
    if len(lengths) < 2:
        return 0.0
    mean_len = sum(lengths) / len(lengths)
    if mean_len == 0:
        return 0.0
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    cv = variance ** 0.5 / mean_len
    return min(cv / 2.0, 1.0)


# ============================================================
# MAIN ANALYSIS
# ============================================================

def scan(text: str) -> list[Annotation]:
    """Run all AI pattern detectors and return a flat list of Annotations.

    This is the main entry point. Returns annotations that say "here's what
    was found and why it looks AI-generated" — no suggestions or fixes.
    """
    all_annotations: list[Annotation] = []

    # Content patterns
    all_annotations.extend(detect_significance_inflation(text))
    all_annotations.extend(detect_vague_attributions(text))
    all_annotations.extend(detect_superficial_ing(text))
    all_annotations.extend(detect_promotional_language(text))
    all_annotations.extend(detect_formulaic_challenges(text))

    # Language patterns
    all_annotations.extend(detect_tier_vocab(text))
    all_annotations.extend(detect_negative_parallelisms(text))
    all_annotations.extend(detect_copula_avoidance(text))
    all_annotations.extend(detect_rule_of_three(text))
    all_annotations.extend(detect_elegant_variation(text))
    all_annotations.extend(detect_false_ranges(text))

    # Style patterns
    all_annotations.extend(detect_em_dashes(text))
    all_annotations.extend(detect_title_case_headings(text))
    all_annotations.extend(detect_structured_abstract(text))

    # Communication patterns
    all_annotations.extend(detect_chatbot_artifacts(text))

    # Filler/Hedging
    all_annotations.extend(detect_hedging_excess(text))
    all_annotations.extend(detect_generic_conclusions(text))

    return all_annotations


def compute_ai_score(annotations: list[Annotation], text: str) -> float:
    """Compute a composite AI-likeness score from annotations and statistical signals.

    Returns 0.0 (human-like) to 1.0 (AI-like).
    """
    # Pattern score from annotations
    if annotations:
        total_severity = sum(
            0.9 if a.severity == Severity.HIGH else
            0.5 if a.severity == Severity.MEDIUM else
            0.2
            for a in annotations
        )
        raw_score = total_severity / (1 + total_severity * 0.1)
        pattern_score = min(raw_score, 1.0)
    else:
        pattern_score = 0.0

    # Statistical signals
    burstiness = compute_burstiness(text)
    ttr = compute_type_token_ratio(text)
    sent_cv = _compute_sentence_cv(text)

    uniformity_score = 0.5 * burstiness + 0.3 * (1 - ttr) + 0.2 * (1 - sent_cv)

    # Composite: 70% pattern + 30% statistical
    return 0.7 * pattern_score + 0.3 * uniformity_score
