# dispatch-hub — Requirements

## 1. Overview
B2B SaaS 실시간 라스트마일 배송 디스패치 플랫폼. 한국·일본 EC 기업의 주문을 라이더 회사 풀에 자동 매칭/배차, 라이더 모바일 워크플로 + 엔드유저 실시간 추적 제공. ML 기반 경로 최적화 포함. 결제는 외부 PG 위임.

## 2. Functional Requirements

### 2.1 Actors
- **EC 기업** (주문 입력) — REST/Webhook
- **라이더** — 모바일 앱
- **라이더 회사 관리자** — 웹 대시보드
- **엔드유저** — 추적 페이지 (계정 없음, signed URL)
- **내부 운영자** — admin 콘솔
- **PG** — 결제 결과 webhook (간접)

### 2.2 Use Cases
- 주문 인입 (API / Webhook / Batch upload)
- 라이더 매칭 (지역·용량·우선순위·ML 점수)
- 배차 확정 → 라이더 앱 push
- 라이더 위치 실시간 수집 + 추적 페이지 송출
- 배차/배송 상태 전이 이벤트 발행
- 라이더 회사 정산 데이터 생성
- 라이더용 알림 (push/SMS)
- 운영자 SLA 모니터링·수동 개입
- ML 모델 재학습 (배치)

### 2.3 External Integrations
- EC 기업 API/Webhook (다양)
- PG Webhook
- FCM / APNs
- SMS gateway (KR / JP 각각)
- Map provider (Google Maps / TMap)

### 2.4 Data Entities (도메인 9개)
Order, Dispatch, Assignment, Rider, RiderCompany, TrackingEvent, BillingItem, Notification, RouteModel

### 2.5 Out of Scope
- 결제 처리
- 라이더 채용/온보딩
- EC 기업 상품 카탈로그
- 정산서 발행/세금계산서

## 3. Non-Functional Requirements (ISO/IEC 25010)

### 3.1 Functional Suitability
- §2.2 use case 9개 GA 시점 제공 _(stated)_
- 디스패치 정확도 ≥ 95% (잘못 배차 5% 이하) _(inferred)_

### 3.2 Performance Efficiency
- **ingest peak TPS**: 3,000 (주문 + 상태 webhook 합산) _(inferred)_
- **tracking ingest**: 50,000 events/sec (라이더 5K × 10s 핑) _(stated)_
- **p99 dashboard**: < 500ms _(inferred)_
- **assignment latency**: 주문 입력 → 라이더 push < 5초 _(inferred)_
- **daily order volume**: 500K _(stated)_

### 3.3 Compatibility
- 클라이언트 API: REST/JSON + gRPC (driver app, 저지연)
- 내부 통신: Kafka 이벤트 (canonical Avro schema)
- 외부: 각 EC 기업 표준 webhook + map provider SDK

### 3.4 Usability
- 라이더 앱: iOS/Android, 한·일 양어
- 대시보드: 웹, 한·일 양어
- 추적 페이지: 게스트 액세스 (signed URL, 24h 만료) _(inferred)_

### 3.5 Reliability
- **SLA**: 99.95% (월 다운 ~21분) _(stated)_
- **RPO**: 1분 (재무 인접 데이터) _(inferred)_
- **RTO**: 15분 _(inferred)_
- **fault tolerance**: 단일 도메인 서비스 장애가 배차 핵심 흐름을 멈추지 않아야 함 (graceful degradation)

### 3.6 Security
- PII (라이더 신원, 엔드유저 연락처) + 위치 데이터 (민감)
- **compliance**: K-ISMS (KR) + APPI (Japan), 데이터 주권 각국 보존 _(stated)_
- 라이더 앱 authn: OIDC + 디바이스 바인딩
- EC 기업 API: API Key + HMAC signed webhook
- 추적 페이지: signed URL (시간제한)

### 3.7 Maintainability
- **팀**: 35명 (백엔드 12 / SRE 4 / 데이터 6 / iOS·Android·web 각 2 / PM·QA 5) _(stated)_
- **배포 주기**: 서비스별 일 1~3회 (CD) _(inferred)_
- **모듈성**: 도메인 단위 서비스 분리, **DB는 도메인 수보다 적게 — 결합도 낮은 도메인끼리 같은 DB 공유 허용** _(stated 사용자 요구)_
- **회사 표준**: K8s _(stated)_

### 3.8 Portability
- **target**: AWS + K8s (회사 표준)
- **multi-region**: KR + JP 동시 운영 _(stated)_
- **multi-cloud**: 불필요
- vendor lock-in tolerance: medium (관리형 적극, ML 서빙은 in-cluster)

## 4. Assumptions
- 디스패치 정확도 95%, assignment latency 5초
- p99 dashboard 500ms, RPO 1분 / RTO 15분
- 추적 페이지는 signed URL 24h 만료
- 라이더 OIDC + 디바이스 바인딩
- 배포는 서비스별 CD, 일 1~3회

## 5. Open Questions
- 위치 데이터 보존 기간 (법정 vs 정산/분쟁용)
- 라이더 회사 정산 cadence (실시간 vs 주간 batch)
- ML 모델 학습 데이터 보관 정책 (개인정보 비식별화 cadence)
- 추적 페이지 캐싱 TTL (실시간성 vs 비용)
- KR-JP 간 라이더/주문 cross-border 발생 시 데이터 주권 처리 (현재 가정: 분리)
