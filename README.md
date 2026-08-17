# AI Financial — ViFinQA End-to-end Pipeline

Repository cho dự án **ViFinQA**: hệ thống trả lời câu hỏi tài chính Việt Nam
end-to-end, từ OCR báo cáo tài chính → bảng → long format → synthetic QA →
BM25 retrieval → text2pandas → sandbox verify → submission.

Nội dung chính nằm trong [`vi-finqa/`](vi-finqa/README.md). Xem README bên trong
`vi-finqa` để biết hướng dẫn cài đặt, chạy pipeline và kiểm thử.

## Bố cục

```
.github/          CI / community health files
vi-finqa/         Toàn bộ source + docs + stats của dự án
  src/            Pipeline code (extraction, schema, gold, retrieval, ...)
  validators/     Submission validator + local scorer
  data/gold/      gold_set.json (chỉ giữ JSON nhỏ trong git)
  docs/           Báo cáo tuần + chiến lược
  stats/          Kết quả đánh giá (JSON nhỏ)
  status/         Trạng thái từng tuần
  scripts/        Tiện ích / smoke test
```

## Lưu ý

- Toàn bộ dữ liệu nặng (raw OCR, extracted, processed, retrieval index, synthetic
  evidence, submissions, backups) **không commit** vào git — xem `vi-finqa/.gitignore`.
- Tải dataset gốc từ HuggingFace: `AIGuruTinix/ViFinQA`.
- Chi tiết rebuild artifacts xem trong [vi-finqa/README.md](vi-finqa/README.md).

## License

Dataset OCR: CC BY-NC (theo nguồn HuggingFace).
Source code: MIT.
