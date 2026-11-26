"""Generate artificial Korean records with independent template and value splits."""

from dataclasses import asdict, dataclass
import hashlib
import json
import random
import re


KINDS = ("PERSON", "PHONE", "RRN")
PLACEHOLDER = re.compile(r"\{(!?)(PERSON|PHONE|RRN)(?::(compact|space))?\}")
SYLLABLES = "가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허"

TEMPLATES = {
    "train": (
        "접수인의 이름은 {PERSON} 입니다.",
        "신청서 성명 칸에 {PERSON} 을 입력했습니다.",
        "이번 설문 참가자는 {PERSON} 이라고 답했습니다.",
        "문자 안내는 연락처 {PHONE} 로 보내세요.",
        "고객 전화번호는 {PHONE:compact} 입니다.",
        "비상 연락 번호 {PHONE:space} 를 확인했습니다.",
        "본인 확인란 주민등록번호는 {RRN} 입니다.",
        "주민번호 {RRN:compact} 를 확인한 뒤 접수합니다.",
        "주민등록번호 입력 칸에 {RRN:space} 가 적혀 있습니다.",
        "예약자 {PERSON} 의 연락처는 {PHONE} 입니다.",
        "성명 {PERSON}, 주민등록번호 {RRN} 를 기록했습니다.",
        "전화번호 {PHONE:compact} 와 주민번호 {RRN:compact} 를 등록합니다.",
        "문서 제목이 {!PERSON} 인 파일을 열었습니다.",
        "인식 실험의 가상 분류 코드는 {!PERSON} 입니다.",
        "서버 자산 관리 번호 {!PHONE} 를 확인했습니다.",
        "개발 장비 시험 코드 {!PHONE:compact} 를 출력했습니다.",
        "부품 일련번호는 {!RRN} 입니다.",
        "제품 시험용 관리 식별자 {!RRN:compact} 를 기록합니다.",
        "오늘은 접수 방법과 업무 시간을 안내합니다.",
        "주민등록번호와 전화번호를 보관하지 않는다는 안내입니다.",
    ),
    "validation": (
        "확인 문서에 기재된 성명: {PERSON}.",
        "증빙 서류를 제출한 사람은 {PERSON} 입니다.",
        "안내 메시지를 받을 휴대전화: {PHONE:space}.",
        "지원자의 연락 가능한 번호는 {PHONE} 입니다.",
        "본인 식별용 주민번호 항목: {RRN:compact}.",
        "등록 신청인이 기재한 주민등록번호는 {RRN} 입니다.",
        "성명 {PERSON} | 휴대전화 {PHONE:compact} | 주민번호 {RRN}.",
        "새로 추가한 분류표 이름은 {!PERSON} 입니다.",
        "시험 회선과 무관한 장비 식별 번호: {!PHONE:space}.",
        "조립 라인의 부품 태그 값은 {!RRN:compact} 입니다.",
        "필수 항목을 검토한 후 서류를 제출하세요.",
        "외부 공개 페이지에는 연락처 항목만 표시됩니다.",
    ),
    "test": (
        "신청인 성명([{PERSON}])을 쉽게 확인할 수 있습니다.",
        "회의 출석자 중 {PERSON}과 함께 도착했습니다.",
        "등록 카드의 성명: {PERSON}\n담당 부서: 테스트 부서.",
        "답신받을 전화는 {PHONE:compact}이니 여기로 연락하세요.",
        "연락 메모에 적힌 번호는 ({PHONE})입니다.",
        "확인할 휴대전화 번호: [{PHONE:space}]",
        "신분 확인 — 주민등록번호 [{RRN}]를 첫 줄에 적습니다.",
        "제출 기록의 주민번호({RRN:compact})를 확인했습니다.",
        "주민등록번호 확인 값 {RRN:space}, 처리는 보류입니다.",
        "{PERSON} / 전화 {PHONE} / 주민번호 {RRN:compact}",
        "작업명 {!PERSON}은 보존할 분류 레이블입니다.",
        "표의 {!PHONE} 항목은 등록된 실험 기기 번호입니다.",
        "보관함의 부품 인증 식별자: {!RRN:space}.",
        "프로젝트 분류 {!PERSON}; 장비 번호 {!PHONE:compact}; 부품 값 {!RRN}.",
        "휴대전화와 주민번호는 수집 항목 예시에만 나옵니다.",
        "양식에는 성명, 연락 방법과 처리 기한을 안내합니다.",
    ),
}
REPEATS = {"train": 8, "validation": 4, "test": 5}


@dataclass(frozen=True, order=True, slots=True)
class Span:
    start: int
    end: int
    kind: str


@dataclass(frozen=True, slots=True)
class Sample:
    family: str
    text: str
    gold: tuple[Span, ...]


def parts(kind, value):
    if kind == "PERSON":
        return ("표" + SYLLABLES[value // len(SYLLABLES)] + SYLLABLES[value % len(SYLLABLES)],)
    if kind == "PHONE":
        return ("000", "0000", f"{value:04d}")
    return ("991332", f"0{value:06d}")


def expand(partition, family_id, template, values):
    fragments, spans, surfaces = [], [], []
    position = cursor = 0
    for match in PLACEHOLDER.finditer(template):
        prefix = template[cursor:match.start()]
        fragments.append(prefix)
        position += len(prefix)
        nonprivate, kind, style = match.groups()
        value = next(values[kind])
        components = parts(kind, value)
        separator = {"compact": "", "space": " "}.get(style, "-")
        surface = separator.join(components)
        fragments.append(surface)
        if not nonprivate:
            spans.append(Span(position, position + len(surface), kind))
        surfaces.append((kind, "".join(components)))
        position += len(surface)
        cursor = match.end()
    fragments.append(template[cursor:])
    return Sample(f"{partition}:{family_id}", "".join(fragments), tuple(spans)), surfaces


def make_splits(seed):
    randomizer = random.Random(seed)
    splits, inventories = {}, {}
    for offset, (name, templates) in enumerate(TEMPLATES.items()):
        begin = offset * 256
        values = {kind: iter(randomizer.sample(range(begin, begin + 256), 256)) for kind in KINDS}
        rows, inventory = [], set()
        for _ in range(REPEATS[name]):
            for index, template in enumerate(templates):
                row, surfaces = expand(name, index, template, values)
                rows.append(row)
                inventory.update(surfaces)
        splits[name] = rows
        inventories[name] = inventory
    for first, second in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if inventories[first] & inventories[second] or set(TEMPLATES[first]) & set(TEMPLATES[second]):
            raise ValueError(f"Generated splits overlap: {first}, {second}")
    return splits


def split_metadata(splits):
    result = {}
    for name, records in splits.items():
        canonical = json.dumps([asdict(row) for row in records], ensure_ascii=False,
                               separators=(",", ":"), sort_keys=True).encode()
        result[name] = {
            "sha256": hashlib.sha256(canonical).hexdigest(),
            "records": len(records),
            "template_families": len({row.family for row in records}),
            "positives": {kind: sum(span.kind == kind for row in records for span in row.gold)
                          for kind in KINDS},
        }
    return result
