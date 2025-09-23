from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class CodeRequest(BaseModel):
    code: str


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.post("/eval")
async def evaluate_code(request: CodeRequest):
    try:
        # WARNING: Using exec can be dangerous and is not recommended for untrusted input.
        from typing import Any

        namespace: dict[str, Any] = {}
        exec(request.code, namespace)

        # The code should end with an expression that we can capture
        # For function calls, we'll capture the last expression
        lines = request.code.strip().split("\n")
        last_line = lines[-1].strip()

        if last_line and not last_line.startswith("#"):
            # If the last line looks like a function call or expression, evaluate it
            try:
                result = eval(last_line, namespace)
                return {"result": result}
            except Exception:
                # If eval fails, maybe it was just a statement, return the namespace
                return {"result": None}
        else:
            return {"result": None}

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
