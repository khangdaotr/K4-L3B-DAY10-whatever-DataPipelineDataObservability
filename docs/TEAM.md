# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên nhóm:** `whatever`
- **Mã nhóm / Lớp:** `K4-L3-DAY10`
- **Tên repository nộp bài:** `K4-L3B-DAY10-whatever-DataPipelineDataObservability`

## Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Đào Trọng Khang | 2A202602974 | daotrongkhang072@gmail.com | Trưởng nhóm kiêm kỹ sư toàn tuyến: ingestion, cleaning, ChromaDB/RAG, evaluation, observability, corruption, repair, orchestration và reporting | `reports/individual_2A202602974_DaoTrongKhang.md` |

## Phân công và kết quả

### Đào Trọng Khang — 2A202602974

- **Vai trò:** Trưởng nhóm, Pipeline Integrator và owner toàn bộ deliverable.
- **Công việc đã hoàn thành:**
  - Hoàn thiện Crossref ingestion, retry, offline fallback và raw preservation.
  - Chuẩn hóa dữ liệu, tính `age_days`, tạo `text_for_embedding` và khử DOI trùng.
  - Xây dựng test set 10 câu hỏi và Great Expectations 1.x/Freshness SLA.
  - Xây dựng ba ChromaDB collections cho baseline, corrupted và repaired.
  - Tiêm 6 dạng lỗi, ghi lineage log và phục hồi idempotent từ raw snapshot.
  - Tích hợp hai pipeline và sinh báo cáo từ metrics thực tế.
- **Kết quả chính:**
  - Baseline: Hit Rate `1.0000`, Token F1 `1.0000`.
  - Corrupted: Hit Rate `0.9000`, Token F1 `0.9170`; quality/freshness fail.
  - Repaired: Hit Rate `1.0000`, Token F1 `1.0000`; quality/freshness pass.
- **Điều học được:** Thiết kế pipeline có lineage anchor, quality gate, phép đo Silent Failure và cơ chế phục hồi có thể chạy lặp an toàn.

## Bảng tự chấm tỷ lệ đóng góp

Nhóm chỉ có một thành viên; tỷ lệ dưới đây đã được thành viên duy nhất xác nhận.

| STT | Họ và tên | MSSV | Phạm vi đóng góp | % Contribution | Xác nhận |
|---:|---|---|---|---:|---|
| 1 | Đào Trọng Khang | 2A202602974 | Toàn bộ mã nguồn, tích hợp, kiểm thử, artifacts và báo cáo | 100% | Đồng ý |
|  | **Tổng cộng** |  |  | **100%** | **Đã thống nhất** |

## Cam kết nhóm

- Thông tin phân công phản ánh đúng mô hình nhóm một thành viên.
- Các số liệu được lấy từ artifacts do pipeline thực tế sinh ra.
- Báo cáo và tài liệu không chứa API key, token hoặc nội dung `.env`.
