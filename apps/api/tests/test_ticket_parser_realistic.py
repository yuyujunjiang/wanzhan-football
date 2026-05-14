from app.domain.ocr.ocr_service import OcrLine
from app.domain.parser.ticket_parser import parse_ticket
from app.domain.tickets.models import PlayType


def test_parse_ticket_realistic_jingcai_receipt_lines():
    # Simulated OCR lines close to what a Jingcai receipt contains.
    lines = [
        OcrLine("第2605071期"),
        OcrLine("过关方式 2x1  50倍  合计 100元"),
        OcrLine("胜平负"),
        OcrLine("第1场周四003  胜平负"),
        OcrLine("主队: 阿斯顿维拉  Vs  客队: 诺丁汉森林"),
        OcrLine("胜@1.580"),
        OcrLine("第2场周四002让球胜平负主队让1球"),
        OcrLine("主队: 弗赖堡  Vs  客队: 布拉加"),
        OcrLine("负@2.130元"),
    ]

    draft = parse_ticket(lines, source_images=["t.png"])
    assert draft.multiplier == 50
    assert draft.passTypes == ["2x1"]
    assert draft.playType is not None
    assert len(draft.legs) >= 2

    assert draft.legs[0].selection in {"胜", "平", "负", "让胜", "让平", "让负"}
    assert draft.legs[0].sp is not None
    assert draft.legs[1].sp is not None
    assert draft.legs[0].matchKey and "2026-05-07" in draft.legs[0].matchKey
    assert draft.legs[1].selection in {"让胜", "让平", "让负"}
    assert draft.legs[1].handicap in {-1.0, -1}


def test_parse_real_mixed_pass_receipt_with_amount_inferred_multiplier():
    lines = [
        OcrLine("第2605131期"),
        OcrLine("竞彩足球混合过关"),
        OcrLine("过关方式 2x1      合计 100元"),
        OcrLine("第1场周三009 让球胜平负 主队受让1球"),
        OcrLine("主队:阿拉维斯 Vs 客队:巴塞罗那"),
        OcrLine("胜@1.750元"),
        OcrLine("第2场周三012 胜平负"),
        OcrLine("主队:西雅图海湾人 Vs 客队:圣何塞地震"),
        OcrLine("胜@1.670元"),
        OcrLine("本票最高可能固定奖金:292.00元"),
        OcrLine("单位注数:2x1*1注;共1注"),
    ]

    draft = parse_ticket(lines, source_images=["receipt.jpg"])

    assert draft.multiplier == 50
    assert draft.passTypes == ["2x1"]
    assert len(draft.legs) == 2

    first, second = draft.legs
    assert first.matchKey == "2026-05-13 周三009 阿拉维斯 vs 巴塞罗那"
    assert first.playType == PlayType.RQSPF
    assert first.selection == "让胜"
    assert first.handicap == 1
    assert first.sp == 1.75

    assert second.matchKey == "2026-05-13 周三012 西雅图海湾人 vs 圣何塞地震"
    assert second.playType == PlayType.SPF
    assert second.selection == "胜"
    assert second.handicap is None
    assert second.sp == 1.67
