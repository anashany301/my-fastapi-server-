from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json

app = FastAPI()

# عنوان API الجديد الخاص بـ Glot.io
GLOT_API_URL = "https://run.glot.io/languages"

class CodePayload(BaseModel):
    code: str
    filename: str

@app.get("/")
async def home():
    return {"status": "Universal Multi-Language API Active (Glot.io)"}

@app.post("/run")
async def run_code(payload: CodePayload):
    filename = payload.filename.strip() if payload.filename else "main.py"
    ext = filename.split(".")[-1].lower() if "." in filename else "py"

    # معالجة ملفات YAML محلياً (لأنها لا تحتاج تجميع)
    if ext in ["yaml", "yml"]:
        try:
            import yaml
            parsed_data = yaml.safe_load(payload.code)
            return {"output": f"✅ Valid YAML!\n{json.dumps(parsed_data, indent=2)}"}
        except Exception as e:
            return {"output": f"❌ Invalid YAML: {str(e)}"}

    # خريطة لغات glot.io (الأسماء تختلف قليلاً عن Piston)
    lang_map = {
        "py": "python",
        "js": "javascript",
        "rs": "rust",
        "cpp": "cpp",
        "c": "c",
        "cs": "csharp",
        "go": "go",
        "java": "java",
        "rb": "ruby",
        "php": "php",
        "sh": "bash"
    }

    language = lang_map.get(ext, ext)
    
    # تنسيق الطلب لـ Glot.io
    glot_payload = {
        "files": [{"name": filename, "content": payload.code}]
    }

    # API Token مجاني من Glot (تحتاج فقط التسجيل في glot.io والحصول على توكن بسيط، أو استخدامه بدون توكن بحدود)
    # ملاحظة: إذا توقف العمل، سأعطيك طريقة بديلة فوراً.
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                f"{GLOT_API_URL}/{language}/latest", 
                json=glot_payload
            )

        if response.status_code == 200:
            res_data = response.json()
            output = res_data.get("stdout", "") + res_data.get("stderr", "")
            return {"output": output if output.strip() else "[No Output]"}
        else:
            return {"output": f"❌ Error ({response.status_code}): {response.text}"}

    except Exception as e:
        return {"output": f"❌ Server Error: {str(e)}"}
