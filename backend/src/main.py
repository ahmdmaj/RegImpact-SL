from fastapi import FastAPI

app = FastAPI(title="RegImpact-SL API")

@app.get("/health")
def health_check():
    return {"status": "ok"}
