# 설계 계획 (Plan)

> 작성일: 2026-08-03 · 프로젝트: **orca-vision-helper** (구 vgmcp-for-orca)

## 1. 개요

Orca 안에서 **비전 해독 기능이 없는 모델**(예: deepseek 계열, 일부 로컬 모델)로 코딩할 때,
화면 캡처·브라우저 스크린샷 등 **비전을 요구하는 작업**을 수행할 수 있게 해주는 헬퍼.

```
메인 모델 (비전 없음, 아무 하네스: codex/claude/opencode/cursor/pi…)
  → bash: orca-vision-helper analyze <이미지> [--prompt "…"]
      = 이미지를 비전 모델 API로 전송 → 텍스트 리포트 반환 (2~10초)
  → 메인 모델이 리포트를 읽고 작업을 계속
```

## 2. 결정 사항 (Decision Log)

| # | 결정 | 이유 |
|---|---|---|
| D1 | **CLI 툴**로 구현 (MCP 아님) | Orca 안의 모든 하네스가 bash 툴 보유. MCP 등록(어댑터+상주 호스트) 오버헤드 불필요. 하네스 무관 범용 적용 |
| D2 | **직접 API 호출** (Orca 서브 에이전트 스폰 배제) | opencode-go/zen이 OpenAI 호환 API임을 확인. 에이전트 부팅 수 초~십수 초 대기 불필요. VGMCP 공용 파이프라인 재사용 가능 |
| D3 | **다중 제공자 지원** (opencode 전용 금지) | 사용자는 opencode-go/zen 외에도 Anthropic·OpenAI·OpenRouter·Ollama·기타 OpenAI 호환 API를 직접 보유 가능. 제공자 선택은 **최초 설정(setup)** 에서 |
| D4 | 기본 분석 모델: **qwen3.6-plus** (opencode-go) | 저렴하고 품질 우수, 사용자 현재 프로바이더. 제공자/모델은 언제든 변경 가능 |
| D5 | **캡처 미구현** (v1) | 스크린샷은 Orca의 computer-use / browser-use가 파일로 생성. 헬퍼는 분석 전용 |
| D6 | 프로젝트명: **orca-vision-helper** | opencode 전용 느낌의 구명(vgmcp-for-orca) 탈피 |
| D7 | 키 저장: **OS 키체인**(keyring) + env var + opencode auth.json 폴백 | VGMCP와 동일 보안 기준. 키는 설정 파일에 평문 저장 금지 |

## 3. 제공자 카탈로그 (v1)

| type | 이름 | 인터페이스 | 기본 base_url | 기본 모델 | 키 출처 |
|---|---|---|---|---|---|
| `opencode-go` | OpenCode Go | OpenAI 호환 | `https://opencode.ai/zen/go/v1` | `qwen3.6-plus` | `OPENCODE_API_KEY` → opencode auth.json |
| `opencode` | OpenCode Zen | OpenAI 호환 | `https://opencode.ai/zen/v1` | `claude-sonnet-4-6` | `OPENCODE_API_KEY` → opencode auth.json |
| `openrouter` | OpenRouter | OpenAI 호환 | `https://openrouter.ai/api/v1` | `anthropic/claude-sonnet-4.6` | `OPENROUTER_API_KEY` → 키체인 |
| `anthropic` | Anthropic Claude | Messages API | `https://api.anthropic.com/v1/messages` | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` → 키체인 |
| `openai` | OpenAI GPT | OpenAI 호환 | `https://api.openai.com/v1` | `gpt-5.4` | `OPENAI_API_KEY` → 키체인 |
| `ollama` | Ollama (로컬) | `/api/chat` | `http://localhost:11434` | `llava:7b` | 없음 (로컬) |
| `custom` | 커스텀 (OpenAI 호환) | OpenAI 호환 | 사용자 지정 (필수) | 사용자 지정 (필수) | 선택 (env/키체인/없음) |

### 키 해석 순서 (클라우드 제공자)

1. env var (`OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `OPENCODE_API_KEY`)
2. OS 키체인 (`orca-vision-helper` 서비스, `provider:<id>` 키)
3. opencode 제공자는 `~/.local/share/opencode/auth.json` 자동 폴백
4. CLI `--key -` 가려진 입력으로 직접 등록

## 4. 아키텍처

```
src/orca_vision_helper/
  cli.py        # argparse: setup / provider add|list|update|remove / analyze / check / models
  config.py     # ~/.config/orca-vision-helper/config.json (원자적 저장)
  providers.py  # 제공자 카탈로그 (표 3)
  auth.py       # 키 해석 (env → 키체인 → opencode auth.json)
  api.py        # 백엔드 빌더 + OpenAI 호환 / Anthropic / Ollama 클라이언트
  imaging.py    # 이미지 전처리 (VGMCP 포팅: 1568px 다운스케일, PNG/JPEG)
  report.py     # JSON 스키마 + 단계적 파싱 폴백 (VGMCP 포팅)
  errors.py     # VisionErrorCode + next_action (VGMCP 포팅)
  models.py     # ProviderConfig / VisionReportBody (VGMCP 포팅)
```

### 4.1 분석 파이프라인 (VGMCP 재사용)

1. `imaging.preprocess` — 원본 보존, 전송본만 1568px 이하 다운스케일 (PNG 우선, 대형 RGB는 JPEG q90)
2. 프롬프트 + JSON 스키마 지시문 (`report.SCHEMA_INSTRUCTION`)
3. 백엔드 호출 (`api.py`) — 제공자별 차이는 base_url/헤더/본문 형식뿐
4. `report.try_parse` 단계적 폴백: 직접 JSON → fenced block → 1회 corrective 재시도 → raw_text (parse_degraded)

### 4.2 HTTP 요청 공통 규칙

- **브라우저형 User-Agent 필수** (Cloudflare 봇 차단 회피 — 조사 §3.3). 모든 OpenAI 호환 엔드포인트에 적용
- 타임아웃: 클라우드 120s, Ollama 180s (실측: qwen3.6-plus 응답 26~55s, 간헐적 60s 초과 — 초기 60s 안에서 2회 중 1회 타임아웃 실측되어 상향)
- 에러 매핑: 401/403→AUTH_FAILED, 429→RATE_LIMIT, 404→MODEL_NOT_FOUND, 5xx→SERVER_ERROR 등 (VGMCP `errors.py` 재사용)

## 5. CLI 스펙 (v1)

```
orca-vision-helper                          # 설정 없으면 setup 안내, 있으면 사용법 출력
orca-vision-helper setup                    # 최초 대화형 설정: 제공자 선택 → 키(가려진 입력) → 모델 → 기본값 지정
orca-vision-helper provider add --type <t> [--model M] [--key -] [--base-url U] [--set-default]
orca-vision-helper provider list            # 등록 목록 (키 존재 여부 포함)
orca-vision-helper provider update <id> [--type T] [--model M] [--base-url U] [--key -]
orca-vision-helper provider remove <id>     # 저장된 키도 함께 삭제
orca-vision-helper analyze <이미지> [--prompt P] [--provider ID] [--model M] [--json]
orca-vision-helper check                    # 설정·키·엔드포인트 점검
orca-vision-helper models                   # 지원 제공자 + 비전 기본 모델 목록
```

- `--key -`는 항상 "가려진 입력으로 키를 물어보라"
- `analyze` 기본 출력: 텍스트 리포트 (LLM 소비용). `--json` = 구조화 덤프
- 기본 프롬프트는 UI 레이아웃 디버깅용 스키마 지시문 포함, `--prompt`로 자유 지정 시 스키마 없음

## 6. 설정 파일 예시

```jsonc
// ~/.config/orca-vision-helper/config.json
{
  "target_folder": null,          // v1 미사용 (예비)
  "providers": [
    { "id": "opencode-go", "type": "opencode-go", "label": "OpenCode Go",
      "model": "qwen3.6-plus", "base_url": null, "key_ref": null }
  ],
  "default_provider_id": "opencode-go",
  "last_used_provider_id": null   // analyze 성공 시 기본값으로 승격 (VGMCP §7.3 규칙 계승)
}
```

## 7. 마일스톤

- **M1 (현재)**: 스캐폴드 + VGMCP 파이프라인 포팅 + opencode-go 실전 검증 + setup/provider/analyze/check CLI
- **M2**: 나머지 제공자 검증 (anthropic / openrouter / ollama / custom) + `models`/`check` 완성
- **M3 (옵션)**: `capture-analyze` (Orca computer-use 스크린샷 → 분석 원샷), MCP 래퍼 제공

## 8. 추후 과제 / 고려 사항

- **외부 전송 동의(consent)**: 최초 설치 스크립트에서 외부 전송 사실을 고지하고
  기본 거부 방식으로 명시적 동의를 받는다. 동의 버전은 가상환경 마커에 기록하며,
  런타임 최초 분석 UI는 두지 않는다. 민감 이미지 전송은 여전히 별도 승인이 필요하다.
- **상시 워커**: 반복 분석이 잦아지면 상주(백그라운드) 분석 데몬 또는 Orca 상시 비전 워커로 전환 검토
- **VGMCP와의 관계**: VGMCP는 범용 MCP 서버, orca-vision-helper는 Orca 전용 CLI. 공용 파이프라인(imaging/report/errors)은 양쪽에서 유지보수 (향후 공유 패키지 분리 검토)
