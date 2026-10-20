import argparse
import json

from sqlmodel import Session

from app.db.session import get_engine
from app.evaluation.harness import evaluate
from app.services.investigation import (
    active_policy,
    active_rule_versions,
    policy_views,
    rule_views,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluasi offline rule dan policy aktif pada set validasi sintetis")
    parser.add_argument("--indent", type=int, default=2)
    args = parser.parse_args()
    with Session(get_engine()) as session:
        policy = active_policy(session)
        versions = active_rule_versions(session)
        if policy is None or not versions:
            raise SystemExit("Tidak ada rule version atau policy version aktif")
        rules = [view for version, vector in versions for view in rule_views(session, version, vector)]
        report = evaluate(rules, policy_views(session, policy))
    print(json.dumps(report.as_dict(), indent=args.indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
