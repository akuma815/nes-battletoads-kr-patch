# Battletoads NES 한국어화

Battletoads 일본판 NES ROM을 기준으로 진행 중인 한국어화 프로젝트다. 현재 시스템 1 텍스트 117건과 시스템 2 텍스트 45건의 사용자 최종 번역이 빌드에 반영됐으며, Galmuri8x8 기반 한글 렌더링과 BizHawk 교차 에뮬레이터 검증을 통과했다. 다음 제작 대상은 타이틀 로고 `Battletoads`의 한국어 그래픽 `전투 두꺼비`다.

## 기준 입력

- ROM: `original/Battletoads (Japan).nes`
- SHA-256: `B831F75C36EEF329A34D0E0D9308CDF85864EDD87E7DA6D8E408307F8BF402D8`
- 폰트 기준 파일: `../../Font/Galmuri8x8.ttf`
- 폰트 SHA-256: `97BA3DCC2CD5E5B2927E4E6BA9558A48A2A194A852C420DF160654D66BBF2A05`

원본 ROM은 수정하지 않는다. 모든 분석·빌드는 원본을 읽기 전용 입력으로 사용하고 새 경로에 결과를 만든다.

## 폴더 역할

```text
Battletoads/
├─ original/                 사용자 제공 원본 ROM
├─ extracted/                원본에서 재생성 가능한 추출 데이터
├─ workspace/
│  ├─ analysis/              뱅크, 주소, 텍스트·렌더러 조사 결과
│  ├─ config/                리비전, 인코딩, 빌드 설정
│  ├─ font/                  Galmuri8x8 변환 사양과 생성 글리프
│  ├─ text/
│  │  ├─ source/             가역 추출 원문
│  │  └─ translation/        한국어 번역 원장
│  ├─ asm/                   6502 훅·패치 소스
│  ├─ graphics/              번역용 그래픽 소스
│  ├─ scripts/               추출·삽입·빌드 도구
│  └─ tests/                 라운드트립·회귀 테스트
├─ work/                     일회성 조사·빌드 작업 공간
├─ build/                    재현 가능한 빌드 산출물
├─ dist/                     배포용 패치·설명서·해시
├─ backups/                  로컬 백업
├─ qa/                       스크린샷·세이브스테이트·실행 로그
├─ tools/                    로컬 외부 도구
└─ docs/                     조사 기록과 인수인계 문서
```

## 작업 규칙

1. 원본 ROM과 이전 검증 산출물을 덮어쓰지 않는다.
2. 반복 작업은 `workspace/scripts`의 단일 빌드 경로로 승격한다.
3. ROM 변경은 대상 리비전 확인과 Expected Write 검증을 거친다.
4. 정적·빌드 검증과 에뮬레이터 실행 검증을 구분해 기록한다.
5. 매 작업 종료 시 최신 `docs/HANDOFF_*.md`에 변경 파일, 해시, 검증 결과, 미해결 항목, 재현 명령과 다음 단계를 반영한다.

현재 상태와 다음 작업은 [`docs/HANDOFF_2026-08-16.md`](docs/HANDOFF_2026-08-16.md)를 기준으로 한다.
