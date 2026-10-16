# 배틀토드 최종판 재빌드

Git 소스와 별도로 준비한 일본판 원본 ROM으로 2026-08-16 최종 배포본을 다시 만듭니다. 과거 작업·검증 폴더나 별도 비공개 복원 ZIP은 필요하지 않습니다.

## 준비와 실행

Python 3.12 환경에서 저장소 최상위에서 실행합니다.

```powershell
python -m pip install -r requirements-rebuild.txt
python -X utf8 -B workspace/scripts/build_all.py --source-rom "원본 ROM의 절대 경로.nes" --output-dir build/restored_final
```

출력 폴더는 아직 존재하지 않는 새 경로를 사용하세요. 원본 ROM은 수정하지 않습니다. 결과는 `Battletoads_KR_dev.nes`이며 기존 파일 이름의 `dev`와 무관하게 아래 해시로 최종 배포본과의 일치 여부를 판별합니다. `build_report.txt`에 디코드 왕복·슬롯·로고 압축 등의 검사 결과가 기록됩니다.

| 구분 | SHA-256 |
| --- | --- |
| 지원 일본판 원본 | `b831f75c36eef329a34d0e0d9308cdf85864edd87e7da6d8e408307f8bf402d8` |
| 최종 배포본 | `300d7a335e404fcba4522d21ab58af1dc77140dd7c4a6de4ea7331e50b6e5090` |

추가된 입력은 원문 JSON 2개, 승인 타이틀 원화·시안 PNG 2개, 폰트 TTF 1개, 타일 배치 JSON 1개입니다. [INPUTS.json](INPUTS.json)에 크기와 해시를 고정했습니다. 타일 배치는 기존 런타임 관측을 공개 입력으로 분리한 것이며, 원본에서 해제한 로고의 해시와 일치하는지도 검사합니다. 빌드할 때 과거 화면 메모리 덤프는 읽지 않습니다. 폰트 이용 조건은 [외부 자료 안내](../../THIRD_PARTY_NOTICES.md)를 참고하세요.

`make_dist.py`로 배포 ZIP까지 새로 포장하려면 별도의 xdelta3 실행 파일이 필요합니다. 이 실행 파일은 Git에 포함하지 않습니다. 위 ROM 재빌드 명령에는 xdelta3가 필요하지 않습니다.

번역 수정은 `workspace/text/translation/translation.json`, 타이틀 편집은 `workspace/graphics/title_logo/title_logo_reference_custom_v1.png`에서 이어갑니다. 수정 버전은 별도의 새 출력 폴더로 빌드하세요. 입력 변경 이후에는 기존 최종 해시가 유지되지 않으므로 새로운 산출물로 검증해야 합니다.

실제 재빌드 및 공개 릴리즈 패치 적용 결과는 [VERIFICATION_2026-10-16.json](VERIFICATION_2026-10-16.json)에 기록합니다. 이번 소스 정비에서는 새 에뮬레이터 실행·장면 검수·전체 플레이 검수를 수행하지 않습니다.
