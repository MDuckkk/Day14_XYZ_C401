# Reflection - Bùi Minh Đức (Person A — Data Engineer)

## Đóng góp cá nhân

- Thiết kế schema và tạo Golden Dataset `data/golden_set.jsonl` gồm 50 test cases phân bố đều 5 loại: fact-check (15), reasoning (10), comparison (5), adversarial (10), edge-case (10). Mỗi case có `ground_truth_doc_ids` để tính retrieval metrics.
- Triển khai Retrieval Evaluator trong `engine/retrieval_eval.py`: tính Hit Rate@5, MRR, NDCG@5 từ kết quả benchmark.
- Xây dựng pipeline Failure Clustering trong `analysis/failure_clustering.py`: tự động phân nhóm các case thất bại theo nguyên nhân gốc rễ (retrieval failure, reasoning failure, edge-case handling failure).
- Tạo `analysis/failure_clusters.json` và báo cáo `analysis/failure_analysis.md` với phân tích 5 Whys cho 3 case tệ nhất.
- Kiểm tra tính nhất quán giữa retrieval metrics, failure clusters và release gate summary trước khi nộp bài.


## Điều hoạt động tốt

- Việc gắn `ground_truth_doc_ids` vào từng case ngay từ đầu giúp phân biệt rõ retrieval failure và generation failure — không cần đoán mò khi debug.
- Phân bố dataset đa dạng (đặc biệt adversarial và edge-case) phát hiện được vấn đề judge calibration mà một benchmark thuần factual sẽ bỏ qua hoàn toàn.
- Failure clustering tự động xác định đúng 76.9% lỗi nằm ở tầng reasoning/generation, không phải retrieval — giúp tập trung cải tiến đúng chỗ.
- Retrieval rất mạnh (Hit Rate@5 = 94.87%), chứng minh Vector DB hoạt động tốt trước khi đánh giá generation.

## Khó khăn gặp phải

- Adversarial cases khó chấm điểm tự động: agent từ chối đúng về hành vi nhưng phrasing khác expected answer, khiến 2 judge cho điểm lệch nhau và kéo agreement rate xuống 72% — đây là nguyên nhân duy nhất dẫn đến CONDITIONAL_RELEASE thay vì RELEASE.
- Các case không có `ground_truth_doc_ids` (adversarial/out-of-scope) bị loại khỏi retrieval scoring, làm Hit Rate trông cao hơn thực tế. Cần ghi chú rõ trong báo cáo để tránh hiểu nhầm.
- Câu hỏi edge-case mơ hồ ngắn (ví dụ: "How should we improve it?") cần agent hỏi làm rõ, nhưng cơ chế phát hiện ambiguity của agent không đủ tin cậy với các câu thiếu chủ ngữ rõ ràng.

## Bài học kỹ thuật

- **MRR quan trọng hơn Hit Rate** khi đánh giá retrieval: Hit Rate chỉ cho biết có tìm thấy hay không, MRR cho biết tìm thấy ở vị trí nào — vị trí ảnh hưởng trực tiếp đến chất lượng context đưa vào LLM.
- **Failure clustering nên chạy tự động** thay vì phân loại thủ công: với 50 cases còn quản lý được, nhưng ở scale 500+ cases thì bắt buộc phải có pipeline tự động.
- **Judge rubric cần được thiết kế song song với dataset**: nếu dataset có adversarial cases thì rubric phải có scoring band riêng cho behavioral correctness, không thể dùng chung rubric factual QA.

## Cải tiến tiếp theo

- Mở rộng golden dataset với các comparison cases nhắm vào từng cặp tài liệu để stress-test retrieval boost coverage.
- Thêm per-case retrieval diagnostics (ground truth doc được retrieve ở rank mấy) vào `analysis/failure_clusters.json`.
- Xây dựng pre-generation ambiguity classifier với few-shot examples để câu hỏi ngắn/mơ hồ trigger clarification thay vì fallback "I do not know".
- Căn chỉnh expected answers của adversarial cases gần hơn với phrasing thực tế của agent để giảm judge scoring variance.
