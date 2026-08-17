# Anticipated Q&A

**Q: Why BM25+hybrid not dense-only?**  
A: No GPU/API this run; BM25 metric index hit R@20 81%. Dense hook exists in `HybridRetriever`.

**Q: Why not keep repair/ensemble in frozen?**  
A: Ablation: same F2/acc as full. Principle: drop components with no measured gain.

**Q: Why no_ontology frozen?**  
A: Highest 0.5*F2+0.5*answer_acc (answer_acc 91.9%). Templates already encode metrics.

**Q: Why synthetic if gold exists?**  
A: Gold is 160 eval-only; HF has no answers. Synthetic for coverage of taxonomy, not for leaking gold.

**Q: Are answers LLM-invented?**  
A: No. Every kept number is pandas-executed on evidence CSV.

**Q: notes_qa text?**  
A: All 30 thuyet_minh gold answers are numeric.
