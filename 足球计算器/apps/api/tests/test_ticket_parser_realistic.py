from app.domain.ocr.ocr_service import OcrLine
from app.domain.parser.ticket_parser import parse_ticket


def test_parse_ticket_realistic_jingcai_receipt_lines():
    # Simulated OCR lines close to what a Jingcai receipt contains.
    lines = [
        OcrLine("过关方式 2x1  50倍  合计 100元"),
        OcrLine("胜平负"),
        OcrLine("第1场周四003  胜平负"),
        OcrLine("主队: 阿斯顿维拉  Vs  客队: 诺丁汉森林"),
        OcrLine("胜@1.580"),
        OcrLine("第2场周四002 让球胜平负"),
        OcrLine("主队: 弗赖堡  Vs  客队: 布拉加"),
        OcrLine("让负@2.130"),
    ]

    draft = parse_ticket(lines, source_images=["t.png"])
    assert draft.multiplier == 50
    assert draft.passTypes == ["2x1"]
    assert draft.playType is not None
    assert len(draft.legs) >= 2

    assert draft.legs[0].selection in {"胜", "平", "负", "让胜", "让平", "让负"}
    assert draft.legs[0].sp is not None
    assert draft.legs[1].sp is not None

