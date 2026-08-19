from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json

app = FastAPI()

# نقطة النهاية العامة المباشرة
PISTON_API_URL = "https://emkc.org/api/v2/piston/execute"

class CodePayload(BaseModel):
    code: str
    filename: str

@app.get("/")
async def home():
    return {"status": "Universal Multi-Language API Active"}

@app.post("/run")
async def run_code(payload: CodePayload):
    filename = payload.filename.strip() if payload.filename else "main.py"
    ext = filename.split(".")[-1].lower() if "." in filename else "py"

    # معالجة ملفات YAML
    if ext in ["yaml", "yml"]:
        try:
            import yaml
            parsed_data = yaml.safe_load(payload.code)
            formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)
            return {"output": f"✅ Valid YAML Syntax!\nParsed JSON:\n{formatted_json}"}
        except Exception as e:
            return {"output": f"❌ Invalid YAML Syntax:\n{str(e)}"}

    lang_map = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "cpp": "cpp",
        "c": "c",
        "cs": "csharp",
        "rs": "rust",
        "go": "go",
        "java": "java",
        "rb": "ruby",
        "php": "php",
        "sh": "bash"
    }

    language = lang_map.get(ext, ext)

    piston_payload = {
        "language": language,
        "version": "*",
        "files": [
            {
                "name": filename,
                "content": payload.code
            }
        ]
    }

    # إضافة Headers لمنع خطأ 401 Unauthorized
    headers = {
        "User-Agent": "CodeXApp/1.0",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=25.0, headers=headers) as client:
            response = await client.post(PISTON_API_URL, json=piston_payload)

        if response.status_code == 200:
            res_data = response.json()
            run_stage = res_data.get("run", {})
            compile_stage = res_data.get("compile", {})

            if compile_stage and compile_stage.get("code", 0) != 0:
                return {"output": f"❌ Compilation Error:\n{compile_stage.get('output')}"}

            output = run_stage.get("output", "[No Output]")
            return {"output": output}
        else:
            return {"output": f"❌ Server Returned Code {response.status_code}:\n{response.text}"}

    except Exception as e:
        return {"output": f"❌ Server Error: {str(e)}"}
