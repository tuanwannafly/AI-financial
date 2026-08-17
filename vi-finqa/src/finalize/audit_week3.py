import json
from pathlib import Path


def audit_week3() -> dict:
    e2e_path = Path("stats/e2e_eval.json")
    if not e2e_path.exists():
        return {
            "critical": True,
            "reason": "e2e_eval.json không tồn tại — pipeline Tuần 3 chưa chạy. Sẽ vá tối thiểu rồi tiếp.",
        }
    e2e = json.loads(e2e_path.read_text(encoding="utf-8"))
    ovr_path = Path("stats/oracle_vs_real.json")
    oracle_vs_real = json.loads(ovr_path.read_text(encoding="utf-8")) if ovr_path.exists() else {}
    return {"critical": False, "e2e": e2e, "oracle_vs_real": oracle_vs_real}


if __name__ == "__main__":
    print(json.dumps(audit_week3(), ensure_ascii=False, indent=2))
