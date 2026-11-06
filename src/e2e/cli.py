import argparse
import uvicorn

from .integrations import storage
from .core.pipeline import run_pipeline

def main() -> None:
    p = argparse.ArgumentParser(prog="e2e")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run one task end-to-end")
    r.add_argument("task")
    r.add_argument("--provider")
    r.add_argument("--model")

    sub.add_parser("serve", help="start dashboard at http://localhost:8000")

    args = p.parse_args()
    if args.cmd == "run":
        run_id = run_pipeline(args.task, args.provider, args.model)
        run = storage.get_run(run_id)
        print(f"run #{run_id}: {run['status']}")
        if run["status"] == "done":
            print("quality gate:", run["quality_gate"])
            for k, v in run["metrics"].items():
                print(f"  {k}: {v}")
        else:
            print(run["error"])
    else:
        # ชี้ไปที่ api.app แทน
        uvicorn.run("e2e.api.app:app", port=8000)

if __name__ == "__main__":
    main()