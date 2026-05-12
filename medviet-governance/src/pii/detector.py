import logging
import warnings

import spacy.util
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

logger = logging.getLogger(__name__)

# spaCy PER → PERSON; email built-in; custom VN patterns; underthesea → PERSON (khi không có vi_core_news_lg)
PII_ENTITIES = ["PERSON", "EMAIL_ADDRESS", "VN_CCCD", "VN_PHONE"]


def _vietnamese_spacy_model_name() -> str:
    """
    `vi_core_news_lg` thường không tải được trên Python 3.12 (spacy download báo không tương thích).

    Presidio chỉ chấp nhận **tên package** mô hình (vd. en_core_web_sm), không dùng được
    `blank:vi` vì engine sẽ gọi `spacy download blank:vi` và lỗi.

    Fallback: gán pipeline `en_core_web_sm` cho lang "vi"; PERSON tiếng Việt do underthesea
    trong detect_pii().
    """
    if spacy.util.is_package("vi_core_news_lg"):
        return "vi_core_news_lg"
    warnings.warn(
        "vi_core_news_lg chưa cài — dùng en_core_web_sm cho nhánh 'vi' trong Presidio; "
        "PERSON (tiếng Việt) qua underthesea. Trên Python 3.11 có thể thử: "
        "python -m spacy download vi_core_news_lg",
        stacklevel=2,
    )
    return "en_core_web_sm"


def build_vietnamese_analyzer() -> AnalyzerEngine:
    """AnalyzerEngine: spaCy (vi + en), recognizer CCCD/SĐT Việt Nam."""

    cccd_pattern = Pattern(
        name="cccd_pattern",
        regex=r"(?<!\d)\d{11,12}(?!\d)",
        score=0.9,
    )
    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        name="vn_cccd_vi",
        patterns=[cccd_pattern],
        context=None,
        supported_language="vi",
    )
    cccd_recognizer_en = PatternRecognizer(
        supported_entity="VN_CCCD",
        name="vn_cccd_en",
        patterns=[cccd_pattern],
        context=None,
        supported_language="en",
    )

    phone_patterns = [
            Pattern(
                name="vn_phone",
                regex=r"(?<!\d)(?:0[35789]\d{8}|[35789]\d{8})(?!\d)",
                score=0.85,
            )
    ]
    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        name="vn_phone_vi",
        patterns=phone_patterns,
        context=None,
        supported_language="vi",
    )
    phone_recognizer_en = PatternRecognizer(
        supported_entity="VN_PHONE",
        name="vn_phone_en",
        patterns=phone_patterns,
        context=None,
        supported_language="en",
    )

    vi_model = _vietnamese_spacy_model_name()

    provider = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "vi", "model_name": vi_model},
                {"lang_code": "en", "model_name": "en_core_web_sm"},
            ],
        }
    )
    nlp_engine = provider.create_engine()

    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine, supported_languages=["vi", "en"]
    )
    analyzer.registry.add_recognizer(cccd_recognizer)
    analyzer.registry.add_recognizer(cccd_recognizer_en)
    analyzer.registry.add_recognizer(phone_recognizer)
    analyzer.registry.add_recognizer(phone_recognizer_en)

    return analyzer


def _underthesea_iob_spans(text: str, tagged: list, label: str) -> list[tuple[int, int]]:
    """Gộp token underthesea có B-{label} / I-{label} thành các (start, end) trên text."""
    spans: list[tuple[int, int]] = []
    span_start: int | None = None
    span_end: int | None = None
    search_from = 0

    def flush():
        nonlocal span_start, span_end
        if span_start is not None:
            spans.append((span_start, span_end))
            span_start = None
            span_end = None

    for word, _pos, _chunk, ntag in tagged:
        ntag = (ntag or "O").strip()
        idx = text.find(word, search_from)
        if idx == -1:
            idx = text.find(word)
            if idx == -1:
                continue
        end = idx + len(word)
        search_from = max(search_from, end)

        is_hit = label in ntag and ntag != "O"
        if not is_hit:
            flush()
            continue

        if ntag.startswith(f"B-{label}"):
            flush()
            span_start = idx
            span_end = end
        elif ntag.startswith(f"I-{label}") and span_start is not None:
            span_end = end

    flush()
    return spans


def _underthesea_person_results(text: str) -> list:
    """NER tiếng Việt: PER; fallback LOC→PERSON khi underthesea nhầm tên người thành địa danh."""
    try:
        from underthesea import ner as ut_ner
    except ImportError:
        return []

    tagged = ut_ner(text)
    if not tagged:
        return []

    meta = {"recognizer_name": "underthesea_ner"}
    per_spans = _underthesea_iob_spans(text, tagged, "PER")
    if per_spans:
        return [
            RecognizerResult("PERSON", s, e, 0.82, recognition_metadata=meta)
            for s, e in per_spans
        ]

    stripped = text.strip()
    if "," in stripped or any(c.isdigit() for c in stripped) or len(stripped) > 120:
        return []

    loc_spans = _underthesea_iob_spans(text, tagged, "LOC")
    return [
        RecognizerResult(
            "PERSON",
            s,
            e,
            0.55,
            recognition_metadata={**meta, "loc_name_fallback": True},
        )
        for s, e in loc_spans
        if (e - s) >= 2
    ]


def detect_pii(text: str, analyzer: AnalyzerEngine) -> list:
    """Detect PII: merge vi + en Presidio; bổ sung PERSON qua underthesea nếu cần."""
    merged: list = []
    seen: set = set()

    for lang in ("vi", "en"):
        for r in analyzer.analyze(
            text=text,
            language=lang,
            entities=PII_ENTITIES,
        ):
            key = (r.start, r.end, r.entity_type)
            if key not in seen:
                seen.add(key)
                merged.append(r)

    if "PERSON" in PII_ENTITIES:
        for r in _underthesea_person_results(text):
            key = (r.start, r.end, r.entity_type)
            if key not in seen:
                seen.add(key)
                merged.append(r)

    return merged
