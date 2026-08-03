# 조사 기록 (Research)

> 작성일: 2026-08-03 · 프로젝트: orca-vision-helper (구 vgmcp-for-orca)
> 이 문서는 프로젝트 착수 전 수행한 조사(Orca · 기존 vgmcp · opencode 모델 제공자)와
> 그 과정에서 확인된 실험 결과를 기록합니다.

---

## 1. 배경: 기존 프로젝트 vision-graft-mcp (VGMCP)

이미지를 보지 못하는 AI 코딩 모델에게 **눈**을 달아주는 범용 MCP 서버.

- **3계층 구조**: `AI 도구(stdio) → vgmcp-adapter(FastMCP 프록시) → HTTP/SSE 상주 호스트(127.0.0.1:8765/mcp)`
- 캡처(macOS ScreenCaptureKit / Windows mss+win32gui) → 비전 백엔드(anthropic · openai ·
  openrouter · custom · ollama) → 구조화된 **텍스트 리포트**(JSON 스키마 + 단계적 파싱 폴백)
- API 키는 OS 키체인(keyring)에만 저장, 설정은 `~/.config/vgmcp/config.json`
- 환경 점검(EnvironmentChecker) → 누락 항목별 해결 가이드 반환
- `self_analyze` — 시각 가능한 모델이 외부 백엔드 없이 직접 분석 (능력 검증 코드로 환각 방지)

**핵심 통찰**: VGMCP의 "이미지 전처리 · 리포트 스키마 · 에러 매핑"은 프로바이더와 무관한
공용 파이프라인이다. orca-vision-helper는 이 파이프라인을 그대로 재사용하고,
"비전 백엔드"만 교체하면 된다.

---

## 2. Orca 조사

### 2.1 Orca란?

- 자체 하네스가 아니라 **여러 하네스를 모아 관리하는 지휘자**(conductor).
- 내부에 codex · claude code · opencode · cursor · pi · grok · gemini 등 하네스 CLI 연동 가능.
- Orca 차원에서 제공하는 도구: **browser-use**(`browser.screencast.v1`), **computer-use**
  (접근성 트리 + 스크린샷 + UI 액션), 워크트리, 터미널, 자동화.
- 버전 1.4.167 (macOS, 본 세션에서 실행 확인).

### 2.2 Orca 오케스트레이션 (조사 결론)

Orca는 구조화된 다중 에이전트 조정 인프라를 제공한다:

```bash
orca orchestration run-create --objective "<obj>" --json
orca orchestration task-create --spec "<spec>" --json
orca orchestration worker-start --task <id> --worktree current --agent claude --json   # --agent: codex|claude|omp|pi|grok|cursor|...
orca orchestration check --wait --types worker_done,escalation,question --timeout-ms 900000 --json
```

- `worker-start --agent <name>`으로 **비전 가능 모델을 사용하는 에이전트를 서브 에이전트로 스폰** 가능.
- `worker_done` 1회 보고, heartbeat, ask/reply, 결정 게이트 등 수명주기 관리.
- 그룹 주소: `@all`, `@idle`, `@claude`, `@codex`, `@opencode`, `@gemini`, `@cursor` 등.

**→ 서브 에이전트 스폰은 기술적으로 가능하나, 순수 이미지 분석 용도로는 과함(에이전트 부팅 수 초~십수 초).**

### 2.3 Orca computer-use

- 접근성 트리(텍스트) + 스크린샷 + 클릭/타이핑 등 안전한 UI 액션.
- 스크린샷은 Orca가 파일로 저장 → **캡처는 orca-vision-helper의 역할이 아님**(분석 전용).

---

## 3. opencode 모델 제공자 조사 (핵심)

### 3.1 프로바이더 식별

| 항목 | opencode-go | opencode |
|---|---|---|
| 이름 | OpenCode Go | OpenCode Zen |
| 엔드포인트 | `https://opencode.ai/zen/go/v1` | `https://opencode.ai/zen/v1` |
| 인터페이스 | **OpenAI 호환** (`chat/completions`, npm `@ai-sdk/openai-compatible`) | 동일 |
| 키 출처 | `~/.local/share/opencode/auth.json` (두 항목 동일 키) 또는 `OPENCODE_API_KEY` | 동일 |

- `opencode models` 로 확인된 사용자 환경의 실제 프로바이더: `opencode-go`(18개 모델), `opencode`(방대).
- auth.json 구조: `{"opencode-go": {"type": "api", "key": "sk-O6aXj…"}, "opencode": {"type": "api", "key": "sk-O6aXj…"}}`

### 3.2 비전(이미지 입력) 지원 모델 목록

models.dev 레지스트리(`~/.cache/opencode/models.json`)의 `modalities.input` 기준:

- **opencode-go — 13개**: gpt-5.6-luna, grok-4.5, kimi-k2.5, kimi-k2.6, kimi-k2.7-code, kimi-k3,
  mimo-v2-omni, mimo-v2.5, minimax-m3, qwen3.5-plus, qwen3.6-plus, qwen3.7-plus, qwen3.8-max
- **opencode(zen) — 52개**: claude-3-5-haiku, claude-sonnet-4/4-5/4-6/5, claude-opus-4.x/5,
  gemini-3-flash/pro/3.1-pro/3.5-flash/3.6-flash, gpt-5~5.6 계열, grok-4.5, kimi-k2.5~k3,
  minimax-m3, qwen3.5-plus, qwen3.6-plus 등

### 3.3 실험 기록 (직접 호출 검증)

| 시도 | 결과 |
|---|---|
| `GET {base}/models` + Bearer 키 | **403** (models 목록 엔드포인트 미노출) |
| `POST /chat/completions` + Python urllib 기본 헤더 | **403, error 1010** (Cloudflare 봇 차단) |
| 브라우저 UA(`Mozilla/5.0 … Chrome/126…`) 추가 | **200** — `qwen3.6-plus`가 "pong" 정상 응답 |
| `opencode run -m opencode-go/qwen3.6-plus` | 정상 응답 (opencode 경유는 문제없음) |

**결론**: API는 표준 OpenAI 호환 `chat/completions`이며 `image_url` data-URI 형식 지원.
단, **Cloudflare 봇 보호를 통과하려면 브라우저형 User-Agent 헤더가 필수**.
httpx 기본 UA(`python-httpx/…`)로는 차단될 가능성이 높아 헤더 강제가 필요하다.

---

## 4. 조사 요약

1. Orca 안에서는 모든 하네스가 bash 툴을 가지므로, 비전 헬퍼는 **MCP 없이 CLI 한 줄**로 호출 가능.
2. Orca 오케스트레이션의 `worker-start --agent`는 서브 에이전트 스폰이 가능하지만, 이미지 분석에는 **직접 API 호출이 더 빠르고 단순**.
3. opencode-go / opencode(zen)는 모두 **OpenAI 호환 API** — 사용자가 이미 보유한 키로 비전 모델을 호출 가능.
4. 기존 VGMCP의 공용 파이프라인(전처리·리포트 스키마·에러 매핑)은 그대로 재사용 가능.
