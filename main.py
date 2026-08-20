from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json
import base64

app = FastAPI()

JUDGE0_LANGS_URL = "https://ce.judge0.com/languages"
JUDGE0_EXEC_URL = "https://ce.judge0.com/submissions?wait=true&base64_encoded=true"

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

    # خريطة ربط امتدادات الملفات بالكلمات الدالة التي تبحث عنها في قائمة سيرفر Judge0
    ext_keyword_map = {
        "rs": "rust",
        "cpp": "c++",
        "c": "c (gcc",
        "js": "javascript",
        "java": "java",
        "go": "go",
        "cs": "c#"
    }

    keyword = ext_keyword_map.get(ext)
    if not keyword:
        return {"output": f"❌ Language extension .{ext} is not supported."}

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            # 3. سحب قائمة اللغات مباشرة من سيرفر Judge0 ومعرفة الـ ID الخاص بها
            langs_response = await client.get(JUDGE0_LANGS_URL)
            language_id = None
            
            if langs_response.status_code == 200:
                languages = langs_response.json()
                for lang in languages:
                    lang_name = lang.get("name", "").lower()
                    if keyword in lang_name:
                        language_id = lang.get("id")
                        break
            
            # قيمة احتياطية لو السيرفر ما ردش لسبب ما
            if not language_id:
                fallback_map = {"rs": 73, "cpp": 54, "c": 50, "js": 63, "java": 62, "go": 60, "cs": 51}
                language_id = fallback_map.get(ext, 73)

            # تشفير الكود بـ Base64 لضمان عدم ضياع أي رموز أو إيموجي
            encoded_code = base64.b64encode(payload.code.encode("utf-8")).decode("utf-8")

            judge0_payload = {
                "source_code": encoded_code,
                "language_id": language_id
            }
            
            response = await client.post(JUDGE0_EXEC_URL, json=judge0_payload)
        
        if response.status_code in [200, 201]:
            res = response.json()
            
            def decode_output(val):
                if not val:
                    return ""
                try:
                    return base64.b64decode(val).decode("utf-8")
                except Exception:
                    return val

            stdout = decode_output(res.get("stdout"))
            stderr = decode_output(res.get("stderr"))
            compile_output = decode_output(res.get("compile_output"))

            output = stdout or stderr or compile_output or "[No Output]"
            return {"output": output}
        else:
            return {"output": f"❌ Judge0 Error ({response.status_code}): {response.text}"}
            
    except Exception as e:
                return {"output": f"❌ Server Error: {str(e)}"}
