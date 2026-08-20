from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json

app = FastAPI()

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

    # 3. خريطة compilers المعتمدة رسمياً في Wandbox
    wandbox_map = {
        "rs": "rust-stable",       # الاسم الصحيح المعتمد في Wandbox للغة Rust
        "cpp": "gcc-head",          # لأحدث إصدار من C++
        "c": "gcc-head",            # لغة C
        "js": "nodejs-head",        # لغة JavaScript
        "go": "go-head"             # لغة Go
    }
    
    compiler = wandbox_map.get(ext)
    if not compiler:
        return {"output": f"❌ Language extension .{ext} is not supported on Wandbox."}

    wandbox_payload = {
        "code": payload.code,
        "compiler": compiler,
        "save": False
    }

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post("https://wandbox.org/api/compile.json", json=wandbox_payload)
        
        if response.status_code == 200:
            res = response.json()
            # استخراج النتيجة أو أخطاء التجميع بوضوح
            output = res.get("program_output", "") or res.get("compiler_error", "") or res.get("signal", "")
            return {"output": output if output.strip() else "[No Output]"}
        else:
            return {"output": f"❌ Wandbox Error ({response.status_code}): {response.text}"}
            
    except Exception as e:
        return {"output": f"❌ Server Error: {str(e)}"}
