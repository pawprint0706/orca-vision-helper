현재 [`AGENTS.md`](http://AGENTS.md)는 내용 자체는 좋지만, **전역 지침에 병합되는 도구 등록 정보**로는 다음 부분이 불필요하게 큽니다.

- 오류 코드와 provider별 세부 설정은 전역 지침이 아니라 CLI의 `--help` 또는 설치 문서가 담당하는 편이 좋습니다.
- `.venv/bin/...`, `docs/AGENT_[INSTALL.md](http://INSTALL.md)` 같은 상대 경로는 다른 저장소에서 전역 지침으로 읽힐 때 의미가 없습니다.
- 특정 모델명은 빠르게 낡을 수 있으므로 전역 지침에서 제거하는 편이 안전합니다.
- “이미지가 필요하면 항상 사용”보다는 **현재 에이전트가 이미지를 직접 볼 수 없을 때 사용**한다고 범위를 한정해야 합니다.
- 병합과 업데이트가 쉽도록 시작·종료 표식을 두는 것이 좋습니다.

저장소의 핵심 기능은 이미지 파일을 비전 모델에 보내 텍스트 보고서를 반환하는 것이고, 실제 주 명령은 `orca-vision-helper analyze <image>`입니다. 또한 클라우드 provider 사용 시 이미지가 외부 API로 전송될 수 있습니다. ([GitHub](https://github.com/pawprint0706/orca-vision-helper/blob/main/README.md "orca-vision-helper/README.md at main · pawprint0706/orca-vision-helper · GitHub"))

제가 권하는 전역 등록용 초안은 아래입니다.

## Tool: orca-vision-helper

`orca-vision-helper` is a CLI for agents that cannot directly inspect images. It sends a local image to a configured vision provider and returns a text report.

Repository: [`https://github.com/pawprint0706/orca-vision-helper`](https://github.com/pawprint0706/orca-vision-helper)

### Use it when

Use this tool when all of the following apply:

- The task requires information from an image or screenshot.
- You cannot reliably inspect the image with your built-in tools.
- A local image path is available.

Typical uses include reading UI text, inspecting application state, and diagnosing layout, clipping, overlap, or alignment problems.

### Commands

```bash
# Verify availability
command -v orca-vision-helper

# General image analysis
orca-vision-helper analyze "<image-path>"

# Ask a focused question
orca-vision-helper analyze "<image-path>" \
  --prompt "<specific question about the image>"

# Diagnose configuration
orca-vision-helper check

# Show current CLI usage
orca-vision-helper --help

```

Read the returned report and continue the original task. Prefer a focused `--prompt` when the required visual information is specific.

### Constraints

- Do not claim to have inspected the original image directly; distinguish the tool's report from direct observation.
- Do not invent an image path. Use a path confirmed to exist.
- Do not install, configure, or modify providers without user approval.
- Cloud providers may upload the image to an external service. Do not send sensitive images unless the user has approved it; prefer a configured local provider when appropriate.
- If the command is unavailable, report that `orca-vision-helper` is not installed or not on `PATH`. Installation instructions are in the repository's `docs/AGENT_[INSTALL.md](http://INSTALL.md)`.

## 이렇게 줄인 이유

### 1. 전역 지침에는 “발견과 판단”만 둡니다

에이전트가 세션 시작 시 알아야 하는 것은 사실 네 가지뿐입니다.

1. 이 도구가 무엇인지
2. 언제 호출할지
3. 기본 호출법
4. 보안상 주의점

Provider 추가, 모델 변경, 오류별 복구 명령은 실제 문제가 생겼을 때 `--help`, `check`, 저장소 문서에서 확인하게 하는 편이 토큰과 유지보수 측면에서 낫습니다.

### 2. 하네스에 종속되지 않습니다

기존 문장의 다음 부분은 삭제하는 것이 좋습니다.

```md
Works in any harness (opencode, codex, Claude Code, Cursor, …)
because it's just a bash command.

```

에이전트가 호출할 수 있는 셸 도구의 이름은 하네스마다 다를 수 있습니다. 전역 지침에는 단순히 실행 명령만 제공하고, 어떤 내부 도구로 실행할지는 하네스가 판단하게 두는 편이 안정적입니다.

### 3. 자동 설치를 막았습니다

현재 초안은 명령이 없으면 `docs/AGENT_[INSTALL.md](http://INSTALL.md)`를 따라 설치하도록 읽힐 수 있습니다. 하지만 전역 지침에서 에이전트가 임의로 다음 작업을 수행하게 만드는 것은 위험합니다.

- 패키지 설치
- PATH 변경
- 심볼릭 링크 생성
- API provider 등록
- 키체인 접근

따라서 **명령이 없으면 상태를 보고하고, 설치나 설정은 사용자 승인 후 수행**하도록 변경했습니다.

### 4. 모델명과 provider 세부사항을 제거했습니다

현재 파일에는 `claude-sonnet-4-6`처럼 구체적인 기본 모델이 들어 있습니다. 저장소 README에서도 여러 provider와 기본 모델을 관리하고 있어, 이 값들은 향후 변경 가능성이 큽니다. ([GitHub](https://github.com/pawprint0706/orca-vision-helper/blob/main/README.md "orca-vision-helper/README.md at main · pawprint0706/orca-vision-helper · GitHub"))

전역 지침은 오래 유지되어야 하므로 다음처럼 동적 명령에 위임하는 편이 낫습니다.

```bash
orca-vision-helper --help
orca-vision-helper check
orca-vision-helper models

```

### 5. 병합 표식을 추가했습니다

아래 표식을 사용하면 설치 스크립트에서 기존 블록을 찾아 교체할 수 있습니다.

```md
<!-- BEGIN orca-vision-helper -->
...
<!-- END orca-vision-helper -->

```

단순한 `cat [AGENTS.md](http://AGENTS.md) >> ...` 방식은 재설치할 때 같은 내용이 계속 중복됩니다. 장기적으로는 설치 스크립트가 다음 방식으로 동작하는 것이 좋습니다.

- 기존 블록이 없으면 추가
- 기존 블록이 있으면 해당 블록만 교체
- 나머지 전역 지침은 보존

## 저장소 파일도 역할을 분리하는 편이 좋습니다

현재 루트 [`AGENTS.md`](http://AGENTS.md)를 프로젝트 개발 지침과 전역 배포 블록 양쪽에 모두 사용하면 역할이 충돌할 수 있습니다. 다음처럼 분리하는 구조가 더 명확합니다.

```text
orca-vision-helper/
├─ AGENTS.md
└─ docs/
   ├─ AGENT_TOOL_RULE.md
   ├─ AGENT_INSTALL.md
   └─ AGENT_UNINSTALL.md

```

- [`AGENTS.md`](http://AGENTS.md): 이 저장소를 수정하는 에이전트를 위한 개발 규칙
- `docs/AGENT_TOOL_[RULE.md](http://RULE.md)`: 각 하네스의 전역 지침에 병합할 짧은 도구 등록 블록
- `docs/AGENT_[INSTALL.md](http://INSTALL.md)`: 설치·PATH·provider 설정
- `docs/AGENT_[UNINSTALL.md](http://UNINSTALL.md)`: 제거 절차

현재 README는 프로젝트 루트의 [`AGENTS.md`](http://AGENTS.md)를 각 하네스 전역 파일에 병합하도록 안내하고 있습니다. ([GitHub](https://github.com/pawprint0706/orca-vision-helper/blob/main/README.md "orca-vision-helper/README.md at main · pawprint0706/orca-vision-helper · GitHub")) 이를 `docs/AGENT_TOOL_[RULE.md](http://RULE.md)`로 바꾸면 루트 [`AGENTS.md`](http://AGENTS.md)를 일반적인 저장소 개발 지침으로 자유롭게 사용할 수 있습니다.

가장 추천하는 방향은 **전역 등록 블록을 약 30줄로 유지하고, 설치·복구·provider 정보는 별도 문서와 CLI 자체에 위임하는 구조**입니다.