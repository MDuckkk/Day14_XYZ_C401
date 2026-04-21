# Person A Run Guide (Handoff)

## Mục tiêu
Tài liệu này giúp Person A pull code, chạy benchmark end-to-end, và xác nhận output trước khi push GitHub.

## 1. Chuẩn bị môi trường
```powershell
cd D:\Lab\Lab14\Lab14-AI-Evaluation-Benchmarking
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. (Tuỳ chọn) Cấu hình API key để dùng judge thật
Tạo file `.env` ở root project:
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```
Nếu không có key, hệ thống vẫn chạy bằng fallback heuristic.

## 3. Sinh Golden Dataset
```powershell
python data/synthetic_gen.py
```
Kỳ vọng tạo file: `data/golden_set.jsonl`.

## 4. Chạy toàn bộ pipeline
```powershell
python main.py
```
Pipeline sẽ tạo các file:
- `reports/benchmark_results.json`
- `reports/summary.json`
- `metrics/judge_consensus.json`
- `reports/release_gate_decision.json`
- `analysis/failure_analysis.md`

## 5. Validate format trước khi push
```powershell
python check_lab.py
```
Nếu gặp lỗi encoding trên Windows console:
```powershell
$env:PYTHONUTF8='1'; python check_lab.py
```

## 6. Checklist trước khi push
- [ ] `check_lab.py` báo pass
- [ ] `reports/summary.json` có `metadata` và `metrics`
- [ ] `reports/benchmark_results.json` tồn tại và có danh sách `results`
- [ ] `analysis/failure_analysis.md` đã được tạo
- [ ] Commit đầy đủ file code + reports cần thiết

## 7. Lưu ý quan trọng cho Person A
- Hiện `data/synthetic_gen.py` mới sinh ít case mẫu. Để bám rubric, nên nâng lên **50+ test cases** và thêm đa dạng (`easy/medium/hard/adversarial`).
- Nên bổ sung `ground_truth_doc_ids` cho mỗi case để retrieval metrics có ý nghĩa hơn.
- Nếu có API key thật, chạy lại để judge score phản ánh chất lượng chính xác hơn (thay vì fallback).
