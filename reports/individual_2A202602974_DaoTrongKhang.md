# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Đào Trọng Khang |
| MSSV | 2A202602974 |
| Khóa/Lớp | K4-L3-DAY10 |
| Tên nhóm | whatever |
| Vai trò chính | Trưởng nhóm, Pipeline Integrator và owner toàn tuyến |
| Repository | `K4-L3B-DAY10-whatever-DataPipelineDataObservability` |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
|---|---|---|---|---|
| Raw ingestion | `src/ingestion/crossref.py` | Crossref API/snapshot | Hai raw JSON artifacts | Hoàn thành |
| Cleaning | `src/ingestion/cleaning.py` | `PaperRecord` | Clean CSV/JSON | Hoàn thành |
| Evaluation/observability | `testset.py`, `quality.py` | Clean DataFrame | Test set, GX và freshness | Hoàn thành |
| Corruption/repair | `corruption.py`, `repair.py` | Clean data/raw snapshot | Corrupted/repaired data và log | Hoàn thành |
| Orchestration/reporting | `phase1.py`, `corruption_flow.py`, `reporting.py` | Các module pipeline | Metrics và Markdown reports | Hoàn thành |

Nhóm chỉ có một thành viên, vì vậy toàn bộ tích hợp, debug, chạy thử và đối chiếu artifact do Đào Trọng Khang trực tiếp thực hiện.

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/artifact | Kết quả | Cách xác minh |
|---|---|---|---|
| Chạy baseline | `script/run_phase1.py` | 24 documents, 10 câu hỏi | `python script/run_phase1.py` |
| Tiêm lỗi và phục hồi | `script/run_corruption_flow.py` | Ba trạng thái so sánh được | `python script/run_corruption_flow.py` |
| Kiểm định dữ liệu | `data/quality/` | Corrupted fail, repaired pass | Đọc quality/freshness JSON |
| Báo cáo tác động | `data/reports/corruption_report.md` | Bảng metrics thực tế | Đối chiếu ba metrics JSON |

Output nổi bật chứng minh Hit Rate giảm từ `1.0` xuống `0.9` khi dữ liệu bị phá và trở lại `1.0` sau repair.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline phải thu thập và chuẩn hóa metadata, kiểm định trước khi index, đo tác động của lỗi dữ liệu đến RAG và phục hồi mà không cần gọi lại API ngoài.

### Cách triển khai

Raw response được giữ làm lineage anchor. Metadata được map sang `PaperRecord`, làm sạch và ghép thành văn bản embedding. Ba collection ChromaDB độc lập tránh nhiễm chéo. Cùng một test set được dùng cho ba trạng thái. GX 1.x và freshness SLA phát hiện lỗi; repair tái dựng từ raw snapshot nên idempotent.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | Crossref JSON và `Settings` |
| Output | Raw/clean/corrupted/repaired data, Chroma, metrics, reports |
| Phụ thuộc | pandas, requests, GX 1.x, ChromaDB, sentence-transformers |
| Module dùng output | Retrieval, evaluation, observability, reporting |
| Lỗi xử lý | 429/mất mạng, XML rác, ngày lỗi, DOI trùng, stale data, artifact thiếu |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả thực tế:** Hai pipeline hoàn thành; quality gate phân biệt đúng corrupted và repaired.
- **Artifact/log:** `data/results/`, `data/quality/`, `data/reports/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần phục hồi sau corruption.
- **Phương án cân nhắc:** Sao chép clean artifact cũ hoặc tái dựng từ raw snapshot.
- **Phương án chọn:** `repair_from_raw_snapshot()`.
- **Lý do:** Raw snapshot là lineage anchor đáng tin cậy và cho phép chạy lặp an toàn.
- **Bằng chứng:** Repaired Hit Rate/Token F1 về `1.0000`; quality và freshness đều pass.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `FileNotFoundError` với `data/clean/papers_clean.json`.
- **Nguyên nhân:** Cleaning đã chạy trong bộ nhớ nhưng chưa ghi artifact.
- **Xử lý:** Ghi clean DataFrame ra JSON và CSV trong Phase 1.
- **Xác minh:** `pd.read_json(...)` đọc 24 dòng và GX trả `success=True`.
- **Bài học:** Thành công trong bộ nhớ chưa đủ; cần kiểm chứng artifact contract giữa các bước.

## 7. Hiểu biết về luồng end-to-end

1. Crossref được lưu raw, parse thành `PaperRecord`, cleaning, embed bằng MiniLM và index vào ChromaDB.
2. Test set giữ DOI ground truth; Hit Rate đo retrieval đúng DOI, Token F1 đo độ khớp câu trả lời.
3. Quality checks kiểm tra cấu trúc/nội dung; freshness đo tỷ lệ `age_days > 180`.
4. Cùng test set giúp chênh lệch metrics phản ánh thay đổi dữ liệu, không phải thay đổi đề.
5. Repair thành công khi artifacts sạch, quality/freshness pass và metrics trở lại baseline.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0000 | 0.9000 | 1.0000 | Retrieval suy giảm rồi phục hồi |
| `mean_token_f1` | 1.0000 | 0.9170 | 1.0000 | Câu trả lời vẫn sinh được nhưng kém chính xác |
| `judge_accuracy` | 1.0000 | 0.9000 | 1.0000 | Judge phát hiện silent failure |
| `mean_judge_score` | 5.0000 | 4.6000 | 5.0000 | Chất lượng phục hồi hoàn toàn |
| Quality checks | Pass | Fail | Pass | GX phát hiện duplicate/summary lỗi |
| Freshness | Pass | Fail | Pass | Corrupted có 6/21 dòng stale (28.57%) |

Corruption làm GX/freshness fail và metrics giảm. Repair từ raw snapshot làm các tín hiệu pass và metrics trở lại baseline. Drop latest ảnh hưởng rõ đến Hit Rate vì tài liệu ground-truth có thể biến mất hoàn toàn. Pipeline corrupted vẫn chạy là bằng chứng điển hình của Silent Failure.

## 9. Điều học được và hướng cải thiện

1. Raw preservation là nền tảng của lineage và phục hồi.
2. Data quality/freshness phải là gate tự động.
3. RAG có thể silent fail dù hạ tầng vẫn hoạt động.

Nếu có thêm thời gian, tôi sẽ bổ sung pytest end-to-end và CI để đo coverage và kiểm tra idempotency tự động.

## 10. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end.
- [x] Mọi kết luận đều có artifact hoặc metric đối chiếu.
- [x] Tôi không ghi thành công cho phần chưa kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo không sao chép nguyên văn báo cáo chung.

**Họ và tên:** Đào Trọng Khang  
**Ngày xác nhận:** 2026-09-26
