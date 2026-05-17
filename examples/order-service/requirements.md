# Order Service — Requirements

## 1. Overview
한국 중소 셀러를 위한 SaaS형 주문 관리 서비스. 자사몰 / 네이버 스마트스토어 / 쿠팡에서 발생하는 주문을 단일 대시보드로 통합 조회/처리한다. 웹 대시보드와 셀러용 모바일 앱을 제공하며, 결제 자체는 처리하지 않고 외부 PG 결과를 수신만 한다.

## 2. Functional Requirements

### 2.1 Actors
- **셀러** (primary) — 중소 e-커머스 판매자
- **셀러 직원** — 셀러 계정 하위 권한 사용자
- **외부 채널 시스템** — 네이버 스마트스토어 / 쿠팡 (주문 인입)
- **외부 PG** — 결제 결과 webhook 전송자

### 2.2 Use Cases
- 다중 채널 주문을 단일 화면에서 조회
- 주문 상태 변경 (확인 / 발송 / 취소)
- CSV / Excel 일괄 export
- 모바일 푸시로 신규 주문 알림
- 채널별 매출 집계 리포트

### 2.3 External Integrations
- 네이버 스마트스토어 API (주문 polling)
- 쿠팡 WING API (주문 polling)
- 자사몰 webhook 수신
- PG webhook 수신 (결제 결과)
- 푸시 발송 (FCM)

### 2.4 Data Entities
- Seller, User, Order, OrderItem, Channel, PaymentEvent, ShipmentEvent

### 2.5 Out of Scope
- 결제 처리 (외부 PG 위임)
- 상품 카탈로그 관리
- 배송사 직접 연동 (별도 솔루션)
- 정산/세금계산서

## 3. Non-Functional Requirements (ISO/IEC 25010)

### 3.1 Functional Suitability
- **completeness**: §2.2의 5개 use case 모두 GA 시점 제공 _(stated)_
- **correctness**: 주문 데이터는 채널 원본과 100% 일치, mismatch 감지 시 알람 _(inferred)_

### 3.2 Performance Efficiency
- **peak TPS**: 200 (점심/저녁 피크, 채널 polling + 사용자 트래픽 합산) _(inferred)_
- **p99 latency**: 대시보드 조회 < 300ms _(inferred)_
- **capacity**: 일 활성 사용자 10K, 일 주문 처리량 ~50K _(stated)_

### 3.3 Compatibility
- REST/JSON over HTTPS 기본 _(inferred)_
- 외부 API: 네이버/쿠팡은 각자 SDK, PG webhook은 표준 HTTP _(stated)_

### 3.4 Usability
- 웹 + iOS/Android 모바일 _(stated)_
- 한국어 단일 로케일 _(inferred)_
- 웹 접근성 WCAG AA 권장 (법적 의무는 아님) _(inferred)_

### 3.5 Reliability
- **SLA**: 99.9% (월 다운타임 ~43분) _(inferred — SMB 대상 SaaS 표준)_
- **RPO**: 5분 _(inferred)_
- **RTO**: 30분 _(inferred)_
- **fault tolerance**: 단일 채널 API 장애가 다른 채널 처리에 영향 주지 않아야 함 _(inferred)_

### 3.6 Security
- **authn**: 셀러는 ID/PW + 2FA, 모바일은 OAuth2/PKCE _(inferred)_
- **authz**: 셀러-직원 권한 분리 (RBAC) _(inferred)_
- **데이터 분류**: 주문자 개인정보(이름/전화/주소) — PII _(stated)_
- **compliance**: K-ISMS 인증 목표 (1년 내), PCI는 결제 미보유로 회피 _(inferred)_
- **데이터 주권**: 한국 리전 필수 (ap-northeast-2) _(stated)_

### 3.7 Maintainability
- **팀 규모**: 4명 _(stated)_
- **배포 주기**: 주 1회 _(inferred)_
- **모듈성**: 채널 어댑터는 플러그인 형태로 확장 가능해야 함 _(inferred)_

### 3.8 Portability
- **target**: AWS 우선 (팀 익숙) + on-prem (DR/백업 검토) _(stated)_
- **multi-cloud**: 불필요 _(inferred)_
- **vendor lock-in tolerance**: medium — 관리형 서비스 적극 활용 OK, 단 핵심 비즈니스 로직은 컨테이너로 이식 가능 _(inferred)_

## 4. Assumptions
다음 항목은 사용자가 명시하지 않아 합리적 기본값으로 추정함:
- peak TPS 200, p99 300ms
- SLA 99.9% / RPO 5분 / RTO 30분
- 2FA + OAuth2/PKCE 인증
- K-ISMS 목표
- 채널 어댑터 플러그인 구조
- 주 1회 배포

## 5. Open Questions
- 채널 polling 주기 (1분? 5분?) — 비용 vs 신선도 trade-off
- 모바일 푸시 즉시성 요구 수준 — 새 주문 후 N초 이내?
- 데이터 보관 기간 (법정 5년 vs 비즈니스 필요)
- 백오피스 IP 화이트리스트 필요 여부
