from fastapi import FastAPI
from app.database import Base, engine
from app.routers import applications, partners, servicing, provisioning

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Lendwise Demo API", version="0.1.0", description="Fictional NBFC lending platform for Mitro analysis")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(servicing.router, prefix="/api/v1")
app.include_router(partners.router, prefix="/api/v1")
app.include_router(provisioning.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok", "environment": "synthetic-demo"}
