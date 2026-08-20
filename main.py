from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json

app = FastAPI()

JUDGE0_API_URL = "https://ce.judge0.com/submissions?wait=true"

class CodePayload(BaseModel):
    code: str
    filename: str

@app.post("/run")
async def run_code(payload: CodePayload):
    filename = payload.filename.strip()
    ext = filename.split(".")[-1].lower() if "." in filename else "py"

    # 1. معالجة ملفات YAML محلياً
    if ext in ["yaml", "yml"]:
        try:
            import yaml
            parsed_data = yaml.safe_load(payload.code)
            return {"output": f"✅ Valid YAML!\n{json.dumps(parsed_data, indent=2, ensure_ascii=False)}"}
        except Exception as e:
            return {"output": f"❌ Invalid YAML: {str(e)}"}

    # 2. تشغيل بايثون محلياً بسرعة البرق
    if ext == "py":
        import sys
        import io
        import contextlib
        
        f = io.StringIO()
        try:
            with contextlib.redirect_stdout(f):
                exec(payload.code, {})
            output = f.getvalue()
            return {"output": output if output.strip() else "[No Output]"}
        except Exception as e:
            return {"output": f"❌ Python Error:\n{str(e)}"}

    # 3. خريطة أرقام اللغات الثابتة والمعتمدة في Judge0
    # 73: Rust, 54: C++, 50: C, 63: JavaScript, 62: Java, 60: Go
    lang_map = {
        "rs": 73,
        "cpp": 54,
        "c": 50,
        "js": 63,
        "java": 62,
        "go": 60,
        "cs": 51
    }

    language_id = lang_map.get(ext)
    if not language_id:
        return {"output": f"❌ Language extension .{ext} is not supported."}

    judge0_payload = {
        "source_code": payload.code,
        "language_id": language_id
    }

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(JUDGE0_API_URL, json=judge0_payload)
        
        if response.status_code in [200, 201]:
            res = response.json()
            output = res.get("stdout") or res.get("stderr") or res.get("compile_output") or "[No Output]"
            return {"output": output}
        else:
            return {"output": f"❌ Judge0 Error ({response.status_code}): {response.text}"}
            
    except Exception as e:
        return {"output": f"❌ Server Error: {str(e)}"}
