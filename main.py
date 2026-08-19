from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import os
import uuid
import json

app = FastAPI()

class CodePayload(BaseModel):
    code: str
    filename: str

@app.get("/")
async def home():
    return {"status": "Server Active"}

@app.post("/run")
async def run_code(payload: CodePayload):
    ext = os.path.splitext(payload.filename)[1].lower()
    if not ext:
        ext = ".py"

    unique_id = str(uuid.uuid4())[:8]
    temp_file = f"/tmp/code_{unique_id}{ext}"

    # معالجة ملفات YAML
    if ext in [".yaml", ".yml"]:
        try:
            import yaml
            parsed_data = yaml.safe_load(payload.code)
            formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)
            return {"output": f"✅ Valid YAML Syntax!\nParsed JSON Representation:\n{formatted_json}"}
        except ModuleNotFoundError:
            return {"output": "❌ Error: PyYAML library is missing on server. Add 'pyyaml' to requirements.txt."}
        except Exception as yml_err:
            return {"output": f"❌ Invalid YAML Syntax:\n{str(yml_err)}"}

    # كتابة الكود للملف المؤقت
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(payload.code)

    try:
        if ext == ".py":
            cmd = ["python3", temp_file]
        elif ext == ".js":
            cmd = ["node", temp_file]
        elif ext == ".sh":
            cmd = ["bash", temp_file]
        else:
            if os.path.exists(temp_file): os.remove(temp_file)
            return {"output": f"Language '{ext}' requires custom environment setup on Vercel."}

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15.0)
            output = stdout.decode('utf-8', errors='ignore') if stdout else stderr.decode('utf-8', errors='ignore')
        except asyncio.TimeoutError:
            process.kill()
            output = "Error: Timeout (15s limit)"

        if os.path.exists(temp_file):
            os.remove(temp_file)

        return {"output": output if output.strip() else "[No Output]"}

    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return {"output": f"Server Error: {str(e)}"}

