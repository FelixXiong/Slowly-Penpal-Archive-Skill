# Slowly-Penpal-Archive-Skill

[简体中文](README.md) | [English](README.en.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [العربية](README.ar.md)

## 만들게 된 계기
> 펜팔과의 소중한 인연을 정성껏 간직하세요.

어떤 편지는 점차 뜸해지고, 어떤 펜팔과는 작별해야 할 때가 옵니다.

하지만 펜팔 목록을 정리하기 전에, 정성껏 쓰고 받았던 편지들은 남겨 두고 싶습니다.

모든 편지를 PDF로 저장한 뒤에는 어떻게 정리하고, 편지 한 통 한 통과 펜팔과의 인연을 다시 돌아볼 수 있을까요?

Slowly 사용자라면 아시겠지만, Plus를 이용하지 않으면 펜팔은 100명까지만 등록할 수 있습니다. Slowly Plus를 구독했다가 만료 후 갱신하지 않으면 펜팔 목록을 정리해야 할 수도 있습니다.

그래서 이 skill을 만들었습니다.

이 skill은:
1. 사용자를 대신해 웹사이트에서 편지를 다운로드하지 않습니다.
2. 저장해 둔 편지를 검색하고 읽어 볼 수 있는 로컬 아카이브로 정리하여, 모든 편지를 간직할 공간을 만듭니다.

현재는 Slowly 편지의 보관을 대상으로 합니다. 편지를 PDF로 내보낼 수 있는 다른 앱은 아직 테스트하지 않았습니다. 직접 사용해 보시고 Issues에 의견을 남겨 주세요.

## 사용 전 준비
Slowly 웹 버전에 접속하여 펜팔의 편지를 직접 PDF로 저장하세요. 펜팔마다 별도의 폴더를 만드세요. 예:

```text
편지폴더/
└── 펜팔이름/
    ├── Slowly.pdf
    ├── Slowly2.pdf
    ├── 우표/
    │   ├── 우표1.png
    │   └── 우표2.png
    └── 프로필/
        └── 아바타.png
```

참고: 수동으로 내보낸 파일의 실제 호환성은 직접 확인해야 합니다.

## 작업 흐름
편지를 PDF로 저장 → 펜팔별 폴더 생성(같은 펜팔의 편지는 한곳에 모으기) → 선택 사항: AI로 파일명 정리 → skill로 아카이브 생성 → 열어서 읽기.

## 시작하기
1. 이 저장소를 내려받아(초록색 **Code** 버튼 → *Download ZIP* 또는 `git clone`) 압축을 풉니다. `SKILL.md`와 `scripts/`가 들어 있는 폴더(ZIP의 경우 `Slowly-Penpal-Archive-Skill-main`)가 생깁니다. 그 **폴더 전체**를 사용하는 도구의 skills 디렉터리에 넣고 `slowly-penpal-archive`로 이름을 바꾸세요. 도구의 로컬 skill 가져오기 기능을 사용해도 됩니다.
   `SKILL.md`만 복사하면 실행되지 않습니다. 옆에 `scripts/`가 없으면 `scripts/pdf_index.py`를 찾을 수 없습니다.
2. Skills를 지원하는 업무 도구(WorkBuddy, 千问办公 또는 豆包工作)나 IDE에 다음과 같이 요청하세요.

> slowly-penpal-archive를 사용하여 (편지를 저장한 경로)에 있는 PDF를 오프라인 아카이브로 정리해 주세요. 원본 파일을 보존하고, 생성이 끝나면 아카이브 시작 페이지를 열어 주세요.

편지 추가:

> slowly-penpal-archive를 사용해 주세요. 자료 디렉터리는 (편지를 저장한 경로)입니다. 기존 아카이브에 새 편지를 추가해 주세요.

처음 실행할 때는 Python을 실행할 수 있는 호스트 환경이 필요합니다. `pypdf`가 없으면 AI가 해당 환경에서 허용하는 방식으로 처리합니다.

의존성 패키지를 처음 가져올 때는 인터넷 연결이 필요할 수 있습니다. 아카이브 생성 및 읽기 과정에서는 Slowly에 접속하지 않습니다.

생성 후에는 로컬 `index.html`을 열면 바로 읽을 수 있습니다. 이후 AI나 로컬 서비스를 계속 실행할 필요가 없습니다.

## AI 없이 실행하기
명령 두 개면 충분합니다.

```bash
python3 -m pip install -r requirements.txt

python3 scripts/pdf_index.py --root '<편지 폴더>' --out '<출력 폴더>'
open '<출력 폴더>/index.html'    # Windows는 start, Linux는 xdg-open
```

- `--root`를 생략하면 `~/Desktop/笔友库`를 읽습니다. 폴더가 없으면 추측하지 않고 어디를 지정해야 하는지 알려 줍니다.
- `--out`을 생략하면 `~/Desktop/Slowly离线档案`에 씁니다. 같은 편지 폴더에는 항상 같은 `--out`을 쓰면 증분 추가됩니다.
- 기타 옵션: `--pal '<펜팔 이름>'`, `--full`, `--pdf-only`, `--verify-data`, `--sql '<쿼리>'`.
- Python 3.9 / 3.12 / 3.14에서 같은 데이터로 실행을 확인했습니다. 자체 점검: `python3 -m unittest discover -s scripts -t scripts`(32개)와 `bash scripts/audit_offline.sh`.

## 생성되는 파일

| 파일 | 용도 |
| --- | --- |
| `index.html` | 바로 열 수 있는 오프라인 아카이브 |
| `slowly_pdf.db` | 편지 데이터베이스 |
| `letters.jsonl` | 구조화된 편지 레코드 |
| `build.json` | 가져오기 통계, 실패 기록 및 확인 대기 항목 수 |
| `media.json` | 로컬 이미지·텍스트 및 연결 관계 인덱스 |

## 미리 보기
펜팔 아카이브 화면:

<img width="1440" height="1000" alt="편지 목록" src="https://github.com/user-attachments/assets/a36b1725-bb47-465f-8345-772511a49c02" />
<img width="1920" height="1080" alt="펜팔 아카이브 미리 보기 2" src="https://github.com/user-attachments/assets/c26fa704-91a7-432c-af86-03447fffb644" />
<img width="1920" height="1080" alt="펜팔 아카이브 미리 보기 3" src="https://github.com/user-attachments/assets/195632ad-4681-450e-9e95-f1b345cd3767" />

## 데이터 보안
이 skill 자체는 인터넷에 접속하지 않고, Slowly 웹페이지를 자동으로 조작하거나 로그인 상태를 읽지 않습니다. Slowly에 로그인할 필요도 없습니다. 이미 저장한 편지 PDF만 읽고, `pypdf`로 본문을 추출하여 검색 가능한 SQLite 데이터베이스와 데이터가 내장된 단일 파일 웹 아카이브를 생성합니다. 아카이브는 더블 클릭으로 열 수 있습니다.

의존성 패키지: `pypdf`. 최초 설치 시 패키지를 다운로드하기 위한 인터넷 연결이 필요합니다.

이 경계는 텍스트를 믿지 않고 직접 확인할 수 있습니다. `bash scripts/audit_offline.sh`는 스크립트·템플릿·생성된 페이지를 훑어 네트워크 스택, 외부 참조, 브라우저 자동화 키워드가 걸리면 오류로 종료합니다. 생성된 `index.html`의 외부 `link`/`script`/`img` 참조는 0건입니다.

참고: `index.html`에는 본문이 모두 내장되고, 각 편지는 디스크의 절대 경로로 연결됩니다. 생성된 페이지와 `*.db`, `letters.jsonl`, `media.json`은 본인만 보관하세요(의도적으로 `.gitignore`에 제외되어 있습니다).

## 자주 묻는 질문
**Q: 편지 저장 폴더를 바꾸면 어떻게 하나요?**

A: IDE 또는 WorkBuddy로 돌아가 AI에게 새 경로를 알려 주고 다시 생성하세요.

## 후원
<img width="1920" height="1080" alt="프로젝트 후원" src="https://github.com/user-attachments/assets/b84194e5-e9d3-4149-81ae-f9d664d9f813" />
