from pathlib import Path
import csv
from sqlalchemy import select
from app.database import SessionLocal
from app.models import LoanAccount

OUT = Path(__file__).resolve().parents[1] / "var" / "exports" / "portfolio.csv"

def run():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db, OUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["loan_id", "customer_id", "principal", "outstanding", "status"])
        for loan in db.scalars(select(LoanAccount)).all():
            writer.writerow([loan.id, loan.customer_id, loan.principal, loan.outstanding, loan.status])
    return OUT

if __name__ == "__main__":
    print(run())
