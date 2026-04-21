# Reflection - Person B

**Họ và tên:** Trần Thanh Nguyên
**MSSV:** 2A202600311

---

## Đóng góp của tôi

- Triển khai `eval/async_runner.py`: chạy benchmark bất đồng bộ với semaphore giới hạn tối đa 5 case song song, đảm bảo 50 case hoàn thành trong thời gian mục tiêu.
- Xây dựng `eval/judge.py` (OpenAIJudge, MultiJudge) và `eval/consensus.py` (ConsensusEngine) để chấm điểm đa judge và xử lý conflict giữa các judge.
- Cấu hình `eval/llm_config.py`: thiết lập judge models (`gpt-4.1-mini`, `gpt-4.1-nano`), ngưỡng release gate và baseline metrics.
- Thiết lập pipeline so sánh hai phiên bản trong `main.py`: chạy V1 (`gpt-4.1-nano`) làm baseline thực tế, sau đó chạy V2 (`gpt-4o-mini`) làm candidate và đưa kết quả V1 vào regression gate.
- Tạo toàn bộ output cuối: `reports/benchmark_results.json`, `reports/summary.json`, `reports/release_gate_decision.json`, `metrics/judge_consensus.json`.

---

## Những vấn đề đã phát hiện và fix

### 1. Không có file `.env` — API key không được load
- **Vấn đề:** Toàn bộ agent và judge đang chạy ở chế độ heuristic fallback vì `OPENAI_API_KEY` không được đọc. Kết quả: `avg_score = 0.319`, `failure_rate = 0.92`, quyết định ROLLBACK.
- **Fix:** Tạo file `.env` với `OPENAI_API_KEY` đúng. Sau khi fix, avg_score tăng lên 0.79, failure rate giảm xuống 26%.

### 2. Model judge `gpt-5.4-nano` không tồn tại
- **Vấn đề:** Config dùng `gpt-5.4-nano` làm judge thứ hai — model này không có trên OpenAI API, gây lỗi và toàn bộ lần chấm đó fallback về heuristic scoring.
- **Fix:** Đổi sang `gpt-4.1-nano` (model thực tế). Cũng bỏ đoạn code check prefix `gpt-5` đặc biệt trong `judge.py` vì không còn cần thiết.

### 3. `asyncio.sleep(0.1)` không cần thiết trong agent
- **Vấn đề:** Mỗi query của agent chờ thêm 0.1s không có lý do — với 50 case chạy song song, điều này làm tăng latency trung bình lên đáng kể.
- **Fix:** Xóa `await asyncio.sleep(0.1)` khỏi `agent/main_agent.py`. Latency giảm từ ~2.4s xuống ~1.9s.

### 4. System prompt ưu tiên sai — adversarial cases trả "I do not know"
- **Vấn đề:** Agent trả lời "I do not know" cho các câu hỏi adversarial thay vì từ chối đúng cách. Nguyên nhân: system prompt đặt xử lý adversarial sau xử lý "không có trong tài liệu", nên model chọn nhánh sai.
- **Fix:** Sắp xếp lại thứ tự trong system prompt: FIRST từ chối adversarial, SECOND hỏi clarification, THIRD trả lời từ tài liệu.

### 5. Documents thiếu nội dung để trả lời câu hỏi reasoning
- **Vấn đề:** Một số câu hỏi reasoning yêu cầu thông tin không có trong documents (ví dụ: tại sao cần async, tại sao agreement rate quan trọng, sự khác biệt giữa summary.json và benchmark_results.json).
- **Fix:** Bổ sung nội dung vào `doc_performance`, `doc_judge`, `doc_reports` trong `data/synthetic_gen.py` để LLM có đủ context trả lời đúng.

### 6. Thiếu pipeline so sánh V1 vs V2 thực tế
- **Vấn đề:** Trước đây baseline là con số hardcode, không phản ánh kết quả chạy thực tế của V1.
- **Fix:** Cập nhật `main.py` để chạy V1 (`gpt-4.1-nano`) trước, lưu kết quả, rồi dùng metrics V1 thực tế làm baseline khi so sánh với V2 (`gpt-4o-mini`).

---

## Kết quả cuối

| Metric | V1 (gpt-4.1-nano) | V2 (gpt-4o-mini) |
|--------|-------------------|-------------------|
| Avg Score | 0.782 | **0.791** |
| Passed Cases | 37 / 50 | 37 / 50 |
| Failure Rate | 26.0% | 26.0% |
| Avg Latency | 1.531s | 1.920s |
| Tổng tokens | — | 16,763 |
| Chi phí ước tính | — | $0.168 |
| Judge Agreement | — | 72.0% |
| Release Decision | — | **CONDITIONAL_RELEASE** |

V2 (gpt-4o-mini) có avg_score cao hơn V1 (gpt-4.1-nano), đúng với yêu cầu "V2 tốt hơn V1". Quyết định CONDITIONAL_RELEASE vì `agreement_ok` chưa đạt (72% < 80% threshold) do hai judge `gpt-4.1-mini` và `gpt-4.1-nano` bất đồng trên các câu adversarial refusal.

---

## Điều hoạt động tốt

- Async execution giúp toàn bộ 50 case chạy dưới 2 phút, đáp ứng mục tiêu hiệu năng.
- Việc chạy V1 thực tế trước rồi dùng làm baseline giúp regression gate có ý nghĩa thực sự — không phải so với con số tưởng tượng.
- Multi-judge scoring phát hiện ngay vấn đề calibration trên adversarial cases — nếu chỉ dùng 1 judge, lỗi này bị che khuất.
- Chi phí rất thấp ($0.003/case) cho thấy gpt-4o-mini hiệu quả về chi phí ở quy mô này.

---

## Thách thức

- `gpt-4.1-mini` và `gpt-4.1-nano` bất đồng trên adversarial refusal cases: agent từ chối đúng nhưng khác cách diễn đạt so với expected answer, khiến hai judge chấm điểm khác nhau và kéo agreement rate xuống 72%.
- Câu hỏi ngắn mơ hồ (ví dụ: "How should we improve it?") không kích hoạt được nhánh clarification — agent fallback về "I do not know" thay vì hỏi lại.
- Một số câu comparison không retrieve được đúng tài liệu do thiếu boost trong `_retrieve()` cho title "Hard Case Design".

---

## Cải tiến tiếp theo

- Bổ sung rubric chấm điểm cho adversarial trong judge prompt: "Nếu agent từ chối đúng cách, cho điểm 0.8–1.0 bất kể cách diễn đạt."
- Thêm tiebreak judge khi hai judge chính lệch nhau hơn 0.3 điểm.
- Thêm bước kiểm tra ambiguity trước khi generate — đặc biệt cho câu hỏi ngắn hoặc có đại từ mơ hồ.
- Sau khi `agreement_ok` pass, đưa metrics V2 lên làm baseline mới cho lần so sánh tiếp theo.
