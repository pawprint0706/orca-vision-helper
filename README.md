# orca-vision-helper

> **For AI agents (vision-blind coding models)**: follow [docs/AGENT_INSTALL.md](docs/AGENT_INSTALL.md)
> for step-by-step installation instructions, and [docs/AGENT_UNINSTALL.md](docs/AGENT_UNINSTALL.md)
> for removal.
>
> **한국어 안내는 하단에 동일한 내용으로 있습니다**: [한국어 안내로 건너뛰기](#한국어-안내)

---

## English Guide

### What it is

A CLI tool that gives vision-blind LLMs (deepseek family, some local models) an
"eye" inside Orca: it sends screenshots and browser captures to a vision-capable
model API and returns a **text report** the main model can read.

```
Main model (no vision, any harness: codex/claude/opencode/cursor/pi…)
  → bash: orca-vision-helper analyze <image> [--prompt "…"]
      = sends the image to a vision model API → returns a text report (2~10s)
  → main model reads the report and continues working
```

### Install

```bash
cd orca-vision-helper           # into the cloned repo root
python3 -m venv .venv
./.venv/bin/pip install -e .
```

Or use the convenience scripts — no commands needed (double-click on
Windows/macOS):

| Platform | Install | Uninstall |
|---|---|---|
| Windows | double-click `scripts/install.bat` | double-click `scripts/uninstall.bat` |
| macOS | double-click `scripts/install.command` | double-click `scripts/uninstall.command` |
| Linux | `bash scripts/install.sh` | `bash scripts/uninstall.sh` |

Requirements: Python 3.11+ (macOS may need `brew install python@3.11`). On
macOS, if double-clicking does nothing, run `chmod +x scripts/*.command` once.
After installing, each script asks whether to launch the interactive `setup`
wizard, where you choose your **default provider and model**. Each script then
**registers a global `orca-vision-helper` command** (required) so it works from
any directory — a symlink on macOS/Linux, a PATH shim on Windows. If the repo
is moved, re-run the install script to refresh the global command.

### Make agents aware of the tool (recommended)

A plain CLI is invisible to coding agents unless it appears in their context —
there is no MCP-style tool list to discover it from. To make every agent
session (in any harness: opencode / codex / Claude Code / Cursor …) know about
the tool, merge the project-root `AGENTS.md` into the global instructions file
of each harness you use. These files are read automatically at session start.
**Always append** — never overwrite an existing file:

| Harness | Global instructions file |
|---|---|
| opencode | `~/.config/opencode/AGENTS.md` |
| Codex | `~/.codex/AGENTS.md` |
| Claude Code | `~/.claude/CLAUDE.md` (newer versions also read `AGENTS.md`) |
| Cursor | `~/.cursor/rules/` (global rules) |

```bash
cat AGENTS.md >> ~/.config/opencode/AGENTS.md   # example: opencode
```

Skipping this is fine for interactive use (the human tells the agent about the
tool), but agents will not discover it on their own.

### Quick Start

```bash
# 1. Interactive first-time setup (provider → key(hidden) → model → default)
./.venv/bin/orca-vision-helper setup

# 2. Analyze an image (default provider; JSON-schema report)
./.venv/bin/orca-vision-helper analyze shot.png

# 3. Free-form question (no schema)
./.venv/bin/orca-vision-helper analyze shot.png --prompt "List every button text in this dialog."
```

The opencode-go / opencode providers need no key entry — the key is auto-detected
from `~/.local/share/opencode/auth.json` (or `OPENCODE_API_KEY`).

### CLI

```
orca-vision-helper                          # prompts to run setup if unconfigured
orca-vision-helper setup                    # interactive: provider → key → model → default
orca-vision-helper provider add --type <t> [--model M] [--key -] [--base-url U] [--set-default]
orca-vision-helper provider list            # registered providers (with key presence)
orca-vision-helper provider update <id> [--model M] [--key -]
orca-vision-helper provider remove <id>     # also deletes the keychain key
orca-vision-helper analyze <image> [--prompt P] [--provider ID] [--model M] [--json]
orca-vision-helper check                    # settings, keys, endpoint probe
orca-vision-helper models                   # supported providers + vision models
```

- `--key -` reads the key via a hidden prompt.
- Keys are **never stored in the config file** — only in the OS keychain
  (keyring, service `orca-vision-helper`), with env-var / opencode auth.json
  fallbacks.
- A successful `analyze` promotes that provider to the default.

### Providers

| type | name | default model |
|---|---|---|
| `opencode-go` | OpenCode Go | `qwen3.6-plus` |
| `opencode` | OpenCode Zen | `claude-sonnet-4-6` |
| `openrouter` | OpenRouter | `anthropic/claude-sonnet-4.6` |
| `anthropic` | Anthropic Claude | `claude-sonnet-4-6` |
| `openai` | OpenAI GPT | `gpt-5.4` |
| `ollama` | Ollama (local) | `llava:7b` |
| `custom` | Custom (OpenAI-compatible) | user-defined |

#### Key resolution order

- `opencode-go` / `opencode`: `OPENCODE_API_KEY` → opencode auth.json
  (`~/.local/share/opencode/auth.json`) → keychain
- `openrouter` / `anthropic` / `openai`: `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` /
  `OPENAI_API_KEY` → keychain
- `custom`: keychain (env/keyless gateways supported), `ollama`: no key

### How it works

1. Image is downscaled to ≤1568px (PNG preferred; large RGB re-encoded as JPEG q90)
2. Default prompt + JSON schema instruction → vision model call
3. Report parse fallback: direct JSON → fenced block → one corrective retry → raw_text

All requests use a browser-style User-Agent (to pass the opencode endpoint's
Cloudflare bot check).

### Troubleshooting

| Symptom | Fix |
|---|---|
| `error 1010` / 403 | Check the User-Agent (browser-style required) |
| `AUTH_FAILED` | Re-enter the key: `provider update <id> --key -`; check the auth.json path |
| `MODEL_NOT_FOUND` | Check the model name: `provider update <id> --model M`; list vision models with `models` |
| `OLLAMA_UNAVAILABLE` | Run `ollama serve` and `ollama pull <model>` |

### Privacy note

Using a cloud provider sends **your screenshots to an external API**. For
sensitive screens, use the local Ollama provider instead.

### Uninstall

The convenience scripts (table above) remove everything — providers,
keychain keys, config, and the venv. Manual equivalent:

```bash
# 1. (Optional, but recommended) Remove each provider — also deletes its keychain key
./.venv/bin/orca-vision-helper provider remove <id>

# 2. Delete the config directory (config.json + lock file)
rm -rf ~/.config/orca-vision-helper

# 3. Uninstall the package
./.venv/bin/pip uninstall orca-vision-helper

# 4. (Optional) Remove the virtual environment
rm -rf .venv
```

- Step 1 is the only way to cleanly remove API keys from the OS keychain
  (keyring service `orca-vision-helper`). If you already deleted the config,
  `provider remove` can no longer find the providers — remove the keychain
  entries manually with your keyring manager instead.
- Steps 2–4 leave no trace in `~/.config`, the Python environment, or the repo.

### Development

```bash
./.venv/bin/pip install -e ".[dev]"
./.venv/bin/ruff check src/ tests/
./.venv/bin/python -m pytest -q
```

### Related docs

- `docs/plan.md` — design decisions
- `docs/research.md` — research notes (opencode API verification, Cloudflare UA measurements)

---

## 한국어 안내

> 위 영문 안내와 동일한 내용입니다.

### 소개

비전 해독 기능이 없는 LLM(deepseek 계열, 일부 로컬 모델 등)이 Orca 안에서
화면 캡처·브라우저 스크린샷 등 **비전을 요구하는 작업**을 수행할 수 있게 해주는 CLI 툴.
이미지를 비전 모델 API로 보내 **텍스트 리포트**를 돌려받습니다.

```
메인 모델 (비전 없음, 아무 하네스: codex/claude/opencode/cursor/pi…)
  → bash: orca-vision-helper analyze <이미지> [--prompt "…"]
      = 이미지를 비전 모델 API로 전송 → 텍스트 리포트 반환 (2~10초)
  → 메인 모델이 리포트를 읽고 작업을 계속
```

### 설치

```bash
cd orca-vision-helper           # 클론한 저장소 루트로 이동
python3 -m venv .venv
./.venv/bin/pip install -e .
```

또는 편의 스크립트를 사용하세요 — 명령어 입력 없이 (윈도우/맥은 더블클릭):

| 플랫폼 | 설치 | 삭제 |
|---|---|---|
| Windows | `scripts/install.bat` 더블클릭 | `scripts/uninstall.bat` 더블클릭 |
| macOS | `scripts/install.command` 더블클릭 | `scripts/uninstall.command` 더블클릭 |
| Linux | `bash scripts/install.sh` | `bash scripts/uninstall.sh` |

요구사항: Python 3.11+ (macOS는 `brew install python@3.11` 필요할 수 있음).
macOS에서 더블클릭이 반응하지 않으면 `chmod +x scripts/*.command`를 한 번 실행하세요.
스크립트는 설치 후 **기본 제공자와 모델을 고르는** 대화형 `setup` 마법사를
실행할지 묻습니다. 그리고 **어느 디렉토리에서든 실행 가능한 전역 명령어로
등록**을 (macOS/Linux: 심볼릭 링크, Windows: PATH 셈 파일) 필수 단계로
수행합니다. 저장소를 옮긴 경우 설치 스크립트를 다시 실행해 전역 명령어를
갱신하세요.

### 에이전트가 이 도구를 알게 하기 (권장)

일반 CLI는 MCP처럼 툴 목록에 나타나지 않아 에이전트가 스스로 발견할 수
없습니다. 모든 세션에서 에이전트(어떤 하네스든: opencode / codex / Claude
Code / Cursor …)가 이 도구를 알게 하려면, 프로젝트 루트의 `AGENTS.md`를
사용 중인 하네스의 전역 지침 파일에 병합하세요. 이 파일들은 세션 시작 시
자동으로 읽힙니다. **반드시 append** — 기존 파일을 덮어쓰지 마세요:

| 하네스 | 전역 지침 파일 |
|---|---|
| opencode | `~/.config/opencode/AGENTS.md` |
| Codex | `~/.codex/AGENTS.md` |
| Claude Code | `~/.claude/CLAUDE.md` (신버전은 `AGENTS.md`도 읽음) |
| Cursor | `~/.cursor/rules/` (전역 규칙) |

```bash
cat AGENTS.md >> ~/.config/opencode/AGENTS.md   # 예: opencode
```

생략해도 대화형 사용에는 문제없지만(사람이 필요할 때 알려주면 됨),
에이전트가 스스로 이 도구를 발견할 수는 없습니다.

### 빠른 시작

```bash
# 1. 대화형 최초 설정 (제공자 선택 → 키(가려진 입력) → 모델 → 기본값)
./.venv/bin/orca-vision-helper setup

# 2. 이미지 분석 (기본 제공자 사용; JSON 스키마 리포트)
./.venv/bin/orca-vision-helper analyze shot.png

# 3. 자유 형식 질문 (스키마 없음)
./.venv/bin/orca-vision-helper analyze shot.png --prompt "이 다이얼로그의 버튼 텍스트를 모두 나열해줘"
```

opencode-go/opencode 제공자는 키 입력이 필요 없습니다.
`~/.local/share/opencode/auth.json`(또는 `OPENCODE_API_KEY`)를 자동 감지합니다.

### CLI

```
orca-vision-helper                          # 설정 없으면 setup 안내
orca-vision-helper setup                    # 대화형: 제공자 선택 → 키 → 모델 → 기본값
orca-vision-helper provider add --type <t> [--model M] [--key -] [--base-url U] [--set-default]
orca-vision-helper provider list            # 등록 목록 (키 존재 여부 포함)
orca-vision-helper provider update <id> [--model M] [--key -]
orca-vision-helper provider remove <id>     # 키체인 키도 함께 삭제
orca-vision-helper analyze <이미지> [--prompt P] [--provider ID] [--model M] [--json]
orca-vision-helper check                    # 설정·키·엔드포인트 점검
orca-vision-helper models                   # 지원 제공자 + 비전 모델 목록
```

- `--key -`는 가려진 입력으로 키를 물어봅니다.
- 키는 **설정 파일에 저장되지 않습니다** — OS 키체인(keyring, 서비스
  `orca-vision-helper`) 또는 환경 변수 / opencode auth.json 폴백만 사용합니다.
- `analyze` 성공 시 해당 provider가 기본값으로 승격됩니다.

### 제공자

| type | 이름 | 기본 모델 |
|---|---|---|
| `opencode-go` | OpenCode Go | `qwen3.6-plus` |
| `opencode` | OpenCode Zen | `claude-sonnet-4-6` |
| `openrouter` | OpenRouter | `anthropic/claude-sonnet-4.6` |
| `anthropic` | Anthropic Claude | `claude-sonnet-4-6` |
| `openai` | OpenAI GPT | `gpt-5.4` |
| `ollama` | Ollama (로컬) | `llava:7b` |
| `custom` | 커스텀 (OpenAI 호환) | 사용자 지정 |

#### 키 해석 순서

- `opencode-go` / `opencode`: `OPENCODE_API_KEY` → opencode auth.json
  (`~/.local/share/opencode/auth.json`) → 키체인
- `openrouter` / `anthropic` / `openai`: `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` /
  `OPENAI_API_KEY` → 키체인
- `custom`: 키체인 (게이트웨이에 따라 env/무키 사용 가능), `ollama`: 키 없음

### 동작 방식

1. 이미지를 1568px 이하로 다운스케일 (PNG 우선, 대형 RGB는 JPEG q90)
2. 기본 프롬프트 + JSON 스키마 지시문으로 비전 모델 호출
3. 리포트 파싱 폴백: 직접 JSON → fenced block → 1회 corrective 재시도 → raw_text

모든 요청은 브라우저형 User-Agent를 사용합니다 (opencode 엔드포인트의
Cloudflare 봇 차단 대응).

### 트러블슈팅

| 증상 | 조치 |
|---|---|
| `error 1010` / 403 | User-Agent 확인 (브라우저형 필수) |
| `AUTH_FAILED` | 키 재입력: `provider update <id> --key -`, auth.json 경로 확인 |
| `MODEL_NOT_FOUND` | 모델명 확인: `provider update <id> --model M`, `models`로 비전 모델 확인 |
| `OLLAMA_UNAVAILABLE` | `ollama serve` 실행 및 `ollama pull <모델>` |

### 주의

클라우드 제공자를 사용하면 **스크린샷이 외부 API로 전송**됩니다.
민감한 화면이 있는 경우 로컬 Ollama 제공자를 사용하세요.

### 삭제

위 편의 스크립트(표)로 제공자·키체인 키·설정·venv를 한 번에 제거할 수
있습니다. 수동으로 하려면:

```bash
# 1. (권장) 각 제공자 삭제 — 키체인 키도 함께 삭제됩니다
./.venv/bin/orca-vision-helper provider remove <id>

# 2. 설정 디렉토리 삭제 (config.json + lock 파일)
rm -rf ~/.config/orca-vision-helper

# 3. 패키지 제거
./.venv/bin/pip uninstall orca-vision-helper

# 4. (선택) 가상환경 삭제
rm -rf .venv
```

- 1단계가 OS 키체인(keyring 서비스 `orca-vision-helper`)의 API 키를 깨끗하게
  제거하는 유일한 방법입니다. 이미 설정을 지웠다면 `provider remove`로 제공자를
  찾을 수 없으므로, 키체인 관리자로 항목을 직접 삭제하세요.
- 2~4단계를 마치면 `~/.config`, Python 환경, 저장소에 흔적이 남지 않습니다.

### 개발

```bash
./.venv/bin/pip install -e ".[dev]"
./.venv/bin/ruff check src/ tests/
./.venv/bin/python -m pytest -q
```

### 관련 문서

- `docs/plan.md` — 설계 확정 사항
- `docs/research.md` — 조사 기록 (opencode API 검증, Cloudflare UA 실측)
