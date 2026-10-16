# Battletoads (J) 용어·어조 승인 기준

상태: **전 항목 인간 승인 대기**(draft). 초안 번역은 이 기준을 따르되, 배포 적격 전에
사람이 이 문서를 승인해야 한다. 결정 변경 시 영향 엔트리를 재검토한다.

## TERM-01: 라틴 고유명사 원문 유지 (状態: draft)

- 근거: 일본판 자체가 인명·지명·레벨명을 라틴 문자로 유지한다. 스타일 보존 + 글리프 수요 절감.
- 적용: RASH, ZITZ, PIMPLE, ANGELICA, DARK QUEEN, T.BIRD, BATTLETOAD(S), GARGANTUA,
  VULTURE, BIG-BLAG, ROBO-MANUS, MUTANT-RAT, TALL-WALKER, BIRDS OF PREY, PSYKO-PIGS,
  WALKERS, SNAKE PIT, FIRE ZONE, TURBO TUNNEL, TURBO-CABLE, SPEED-BIKE,
  ELEVATOR SHAFT, CLINGER-WINGER, DARK ZONE, RAGNAROK WORLD, SURFIN, GOAL,
  NON STOP, GO!GO!, IT'S SHOW TIME!, PARTY, SPEED, 1MILE
- 전이 한계: 시스템 1·2의 본문. 그래픽 로고는 별도 결정.

## TERM-02: 영문 메뉴·HUD·치트 문자열 원문 유지 (状態: draft)

- 근거: 일본판도 영어 그대로(PRESS START TO PLAY, GAME OVER, CONTINUE, MEGA WARP 등).
- 적용: fixed_strings 중 가나가 없는 전 엔트리(스토리 제외). status=excluded로 표기.

## TERM-03: 호칭·직함 (状態: draft)

- ｷｮｳｼﾞｭ(教授) = "교수"(지문), 대사 호칭은 "교수님"
- ﾋﾒ(姫) = "공주" (ANGELICA공주)
- ｶｴﾙﾄﾞﾓ(Dark Queen이 부를 때) = "개구리들"(경멸조)
- ｾﾝｶﾝ = "전함", ﾊｲｽｲｺｳ = "배수구", ｼﾞｹﾞﾝﾊﾞｸﾀﾞﾝ(時限爆弾) = "시한폭탄"
- ｲﾁﾘﾝｼｬ = "외발자전거", ﾀﾝﾁｷ = "탐지기"

## VOICE-01: 화자별 어조 (状態: draft)

- **T.Bird 교수**(브리핑 지시): 반말 명령·격려체. "~해라!", "~하는 거다!", "~다!"
- **Dark Queen**(도발): 오만한 반말. "~하시지!", "~해 주마!", "~라고!", 웃음 "아-핫핫핫!"
- **Rash/Zitz**(1인칭 대사): 열혈 반말. "~하겠어!", "~하자!"
- **어트랙트 내레이션**: 동화체 경어. "~했습니다"
- 근거: 일본판 어미(ﾝﾀﾞ!/ｼﾛ!=명령, ~ﾜ!/~ﾈ!=여왕 여성어, ~ﾏｼﾀ=내레이션)의 역할 대응.

## NOTE-01: 원문 오탈자 교정 (状態: draft)

- id 74 "GARAGANTUA", id 93 "DARK QUEEEN"은 일본판 원문 오타 → 한국어판에서 바로잡는다.

## NOTE-02: 문장부호 (状態: draft)

- 물음표: 심볼 테이블에 '?'가 없고 0x22(")가 물음표 글리프로 쓰임(미검증, 스크린샷 확인 예정).
  ko 원고는 '?'로 쓰고 빌드에서 0x22로 매핑한다.
- 쉼표: JP '､'(0xA4) 심볼을 재사용하고 글리프를 한국어 쉼표 모양으로 교체 예정. ko 원고는 '､'.
- 말줄임: '･'(0xA5) 반복(JP 관행 유지). 장음 '-'는 ASCII 하이픈.
