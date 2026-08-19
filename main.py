from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json

app = FastAPI()

# رابط Piston API المجاني المفتوح المصدر لتشغيل +100 لغة برمجية
PISTON_API_URL = "https://emkc.org/api/v2/piston/execute"

class CodePayload(BaseModel):
    code: str
    filename: str

@app.get("/")
async def home():
    return {"status": "Universal Multi-Language Engine Active (100+ Languages Supported)"}

@app.post("/run")
async def run_code(payload: CodePayload):
    filename = payload.filename.strip()
    ext = filename.split(".")[-1].lower() if "." in filename else "py"
    
    # معالجة خاصة لملفات YAML داخل السيرفر مباشرة
    if ext in ["yaml", "yml"]:
        try:
            import yaml
            parsed_data = yaml.safe_load(payload.code)
            formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)
            return {"output": f"✅ Valid YAML Syntax!\nParsed JSON:\n{formatted_json}"}
        except Exception as e:
            return {"output": f"❌ Invalid YAML Syntax:\n{str(e)}"}

    # خريطة الامتدادات إلى أسماء اللغات في Piston API
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
        "sh": "bash",
        "kt": "kotlin",
        "swift": "swift",
        "zig": "zig",
        "hs": "haskell",
        "lua": "lua",
        "r": "r",
        "pl": "perl",
        "dart": "dart",
        "scala": "scala",
        "nim": "nim",
        "ex": "elixir",
        "clj": "clojure"
    }

    # تحديد اللغة أو استخدام اسم الامتداد مباشرة
    language = lang_map.get(ext, ext)

    # تجهيز الطلب لمحرك التشغيل الشامل
    piston_payload = {
        "language": language,
        "version": "*",  # استخدام أحدث إصدار متوفر للغة
        "files": [
            {
                "name": filename,
                "content": payload.code
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(PISTON_API_URL, json=piston_payload)

        if response.status_code == 200:
            res_data = response.json()
            run_stage = res_data.get("run", {})
            compile_stage = res_data.get("compile", {})

            # إذا كان هناك خطأ في التجميع (Compilation Error)
            if compile_stage and compile_stage.get("code") != 0:
                return {"output": f"❌ Compilation Error:\n{compile_stage.get('output')}"}

            # مخرجات التشغيل الفعلي (Execution Output)
            output = run_stage.get("output", "[No Output]")
            return {"output": output}
        else:
            return {"output": f"❌ Language '{language}' not supported or API Error ({response.status_code})."}

    except httpx.TimeoutException:
        return {"output": "❌ Error: Request Timed Out (20s Limit)."}
    except Exception as e:
        return {"output": f"❌ Server Execution Error: {str(e)}"}
