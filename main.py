from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json

app = FastAPI()

# بيانات حسابك في JDoodle
JDOODLE_CLIENT_ID = "c1dd783f1c39b45d4d81eaf787d98df"
JDOODLE_CLIENT_SECRET = "e39ea5f80075906801e3f8f3b73763085f24800abd1897cd8eea73d3712e1ca4"

class CodePayload(BaseModel):
    code: str
    filename: str

@app.post("/run")
async def run_code(payload: CodePayload):
    filename = payload.filename.strip()
    ext = filename.split(".")[-1].lower() if "." in filename else "py"

    # معالجة ملفات YAML محلياً
    if ext in ["yaml", "yml"]:
        try:
            import yaml
            parsed_data = yaml.safe_load(payload.code)
            return {"output": f"✅ Valid YAML!\n{json.dumps(parsed_data, indent=2, ensure_ascii=False)}"}
        except Exception as e:
            return {"output": f"❌ Invalid YAML: {str(e)}"}

    # خريطة لغات JDoodle (اللغة ورقم الإصدار)
    lang_map = {
        "py": ("python3", "4"),
        "js": ("nodejs", "4"),
        "rs": ("rust", "4"),
        "cpp": ("cpp", "5"),
        "c": ("c", "5"),
        "java": ("java", "4"),
        "go": ("go", "4"),
        "cs": ("csharp", "4"),
        "php": ("php", "4"),
        "rb": ("ruby", "4")
    }

    lang_info = lang_map.get(ext, ("python3", "4"))
    language, version = lang_info[0], lang_info[1]

    jdoodle_payload = {
        "clientId": JDOODLE_CLIENT_ID,
        "clientSecret": JDOODLE_CLIENT_SECRET,
        "script": payload.code,
        "language": language,
        "versionIndex": version
    }

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post("https://api.jdoodle.com/v1/execute", json=jdoodle_payload)
        
        if response.status_code == 200:
            result = response.json()
            return {"output": result.get("output", "[No Output]")}
        else:
            return {"output": f"❌ Error ({response.status_code}): {response.text}"}
    except Exception as e:
        return {"output": f"❌ Server Error: {str(e)}"}
