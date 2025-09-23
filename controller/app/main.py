from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.post("/eval")
async def evaluate_code(code: str):
    try:
        # WARNING: Using eval can be dangerous and is not recommended for untrusted input.
        result = eval(code)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
