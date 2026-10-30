import argparse, json
from mitro.database import SessionLocal
from mitro.phase1.ingest import bootstrap

def main():
    parser = argparse.ArgumentParser(prog="mitro")
    parser.add_argument("command", choices=["bootstrap"])
    args = parser.parse_args()
    if args.command == "bootstrap":
        with SessionLocal() as db:
            print(json.dumps({"ingested": bootstrap(db)}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
