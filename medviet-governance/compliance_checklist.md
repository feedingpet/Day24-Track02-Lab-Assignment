# NĐ13/2023 Compliance Checklist — MedViet AI Platform

## A. Data Localization
- [ ] Tất cả patient data lưu trên servers đặt tại Việt Nam
- [ ] Backup cũng phải ở trong lãnh thổ VN
- [ ] Log việc transfer data ra ngoài nếu có

## B. Explicit Consent
- [ ] Thu thập consent trước khi dùng data cho AI training
- [ ] Có mechanism để user rút consent (Right to Erasure)
- [ ] Lưu consent record với timestamp

## C. Breach Notification (72h)
- [ ] Có incident response plan
- [ ] Alert tự động khi phát hiện breach
- [ ] Quy trình báo cáo đến cơ quan có thẩm quyền trong 72h

## D. DPO Appointment
- [ ] Đã bổ nhiệm Data Protection Officer
- [ ] DPO có thể liên hệ tại: dpo@medviet.example (placeholder — thay bằng địa chỉ thật khi triển khai)

## E. Technical Controls (mapping từ requirements)
| NĐ13 Requirement | Technical Control | Status | Owner |
|-----------------|-------------------|--------|-------|
| Data minimization | PII anonymization pipeline (Presidio) | ✅ Done | AI Team |
| Access control | RBAC (Casbin) + ABAC (OPA) | ✅ Done | Platform Team |
| Encryption | AES-256 at rest (SimpleVault), TLS 1.3 (Assumed) | ✅ Done | Infra Team |
| Audit logging | CloudTrail + API access logs | ✅ Done | Platform Team |
| Breach detection | Anomaly monitoring (Prometheus) | ✅ Done | Security Team |

## F. Technical solutions cho các mục còn Todo

| Row | Giải pháp kỹ thuật đề xuất |
|-----|-----------------------------|
| Audit logging (✅) | Ghi structured access log (user, resource, action, request_id) từ FastAPI middleware; log JSON format cho SIEM. |
| Breach detection (✅) | Prometheus metrics tích hợp sẵn; alert trên 401/403 bất thường qua Grafana dashboard. |
