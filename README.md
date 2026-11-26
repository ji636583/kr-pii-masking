# kr-pii-masking
KLUE-RoBERTa 기반 한국어 개인정보 탐지·마스킹 프로젝트 (오픈소스기초설계 팀 프로젝트)

## 웹 초안

저장소 루트에서 아래 명령을 실행한 뒤 [로컬 데모](http://localhost:8000/)를 엽니다. 별도 패키지 설치는 필요 없습니다.

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory web
```

`web/`에서 문서 원문과 마스킹 결과를 나란히 확인하는 화면을 개발합니다.
