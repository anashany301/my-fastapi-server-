from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json
import base64
import os

app = FastAPI()

JUDGE0_LANGS_URL = "https://ce.judge0.com/languages"
JUDGE0_EXEC_URL = "https://ce.judge0.com/submissions?wait=true&base64_encoded=true"

class CodePayload(BaseModel):
    code: str
    filename: str

class FileLoadPayload(BaseModel):
    filename: str

# 1. مسار تشغيل الكود وحفظه تلقائياً
@app.post("/run")
async def run_code(payload: CodePayload):
    filename = payload.filename.strip()
    
    if filename:
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(payload.code)
        except Exception:
            pass

    ext = filename.split(".")[-1].lower() if "." in filename else "py"

    if ext in ["yaml", "yml"]:
        try:
            import yaml
            parsed_data = yaml.safe_load(payload.code)
            return {"output": f"✅ Valid YAML!\n{json.dumps(parsed_data, indent=2, ensure_ascii=False)}"}
        except Exception as e:
            return {"output": f"❌ Invalid YAML: {str(e)}"}

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

    ext_keyword_map = {
        "py": "python", "js": "javascript", "ts": "typescript", "rs": "rust",
        "cpp": "c++", "c": "c (gcc", "cs": "c#", "java": "java", "go": "go",
        "rb": "ruby", "php": "php", "swift": "swift", "kt": "kotlin",
        "scala": "scala", "s": "assembly", "asm": "assembly", "f": "fortran",
        "f90": "fortran", "cob": "cobol", "ada": "ada", "d": "d",
        "sh": "bash", "lua": "lua", "pl": "perl", "r": "r", "jl": "julia",
        "ex": "elixir", "exs": "elixir", "erl": "erlang", "hs": "haskell",
        "clj": "clojure", "rkt": "racket", "ml": "ocaml", "pas": "pascal",
        "tcl": "tcl", "groovy": "groovy", "dart": "dart", "scm": "scheme",
        "lisp": "common lisp", "fs": "f#", "b": "brainfuck", "bf": "brainfuck",
        "coffee": "coffeescript"
    }

    keyword = ext_keyword_map.get(ext, ext)

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            langs_response = await client.get(JUDGE0_LANGS_URL)
            language_id = None
            
            if langs_response.status_code == 200:
                languages = langs_response.json()
                for lang in languages:
                    lang_name = lang.get("name", "").lower()
                    if keyword in lang_name:
                        language_id = lang.get("id")
                        break
            
            if not language_id:
                fallback_map = {"rs": 73, "cpp": 54, "c": 50, "js": 63, "java": 62, "go": 60, "cs": 51, "s": 45}
                language_id = fallback_map.get(ext, 73)

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

# 2. مسار تحميل وقراءة الملفات القديمة لتعديلها
@app.post("/load")
async def load_file(payload: FileLoadPayload):
    filename = payload.filename.strip()
    if not filename:
        return {"output": "❌ Error: Filename is empty.", "content": ""}
    
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            return {"content": content, "output": f"✅ File '{filename}' loaded successfully!"}
        except Exception as e:
            return {"output": f"❌ Error reading file: {str(e)}", "content": ""}
    else:
        return {"output": f"⚠️ File '{filename}' not found on server!", "content": ""}
