from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import os
import uuid
import json
import yaml

app = FastAPI()

class CodePayload(BaseModel):
    code: str
    filename: str

@app.get("/")
async def home():
    return {"status": "Universal Multi-Language API Active (100+ Languages + YAML Supported)"}

LANG_COMMANDS = {
    # لغات التفسير المباشر
    ".py": lambda f, e: ["python3", f],
    ".js": lambda f, e: ["node", f],
    ".sh": lambda f, e: ["bash", f],
    ".php": lambda f, e: ["php", f],
    ".rb": lambda f, e: ["ruby", f],
    ".pl": lambda f, e: ["perl", f],
    ".lua": lambda f, e: ["lua", f],
    ".r": lambda f, e: ["Rscript", f],
    
    # لغات التجميع والتنفيذ
    ".c": lambda f, e: f"gcc {f} -o {e} && {e}",
    ".cpp": lambda f, e: f"g++ {f} -o {e} && {e}",
    ".rs": lambda f, e: f"rustc {f} -o {e} && {e}",
    ".go": lambda f, e: ["go", "run", f],
    ".java": lambda f, e: f"javac {f} && java -cp /tmp Main",
    ".cs": lambda f, e: f"mcs {f} -out:{e}.exe && mono {e}.exe",
    ".kt": lambda f, e: f"kotlinc {f} -include-runtime -d {e}.jar && java -jar {e}.jar",
    ".swift": lambda f, e: ["swift", f],
    ".zig": lambda f, e: f"zig run {f}",
    ".hs": lambda f, e: ["runhaskell", f],
    ".nim": lambda f, e: f"nim c -r --hints:off {f}"
}

@app.post("/run")
async def run_code(payload: CodePayload):
    ext = os.path.splitext(payload.filename)[1].lower()
    if not ext:
        ext = ".py"

    unique_id = str(uuid.uuid4())[:8]
    temp_file = f"/tmp/code_{unique_id}{ext}"
    exec_file = f"/tmp/exec_{unique_id}"

    # معالجة خاصة لملفات YAML
    if ext in [".yaml", ".yml"]:
        try:
            parsed_data = yaml.safe_load(payload.code)
            formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)
            return {"output": f"✅ Valid YAML Syntax!\nParsed JSON Representation:\n{formatted_json}"}
        except Exception as yml_err:
            return {"output": f"❌ Invalid YAML Syntax:\n{str(yml_err)}"}

    # كتابة الكود للملف المؤقت لبقية اللغات
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(payload.code)

    try:
        if ext in LANG_COMMANDS:
            cmd_builder = LANG_COMMANDS[ext]
            cmd = cmd_builder(temp_file, exec_file)
            
            if isinstance(cmd, str):
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
        else:
            process = await asyncio.create_subprocess_shell(
                f"python3 {temp_file}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15.0)
            output = stdout.decode('utf-8', errors='ignore') if stdout else stderr.decode('utf-8', errors='ignore')
        except asyncio.TimeoutError:
            process.kill()
            output = "Error: Execution Timeout (15s limit)"

        for p in [temp_file, exec_file, f"{exec_file}.exe", f"{exec_file}.jar"]:
            if os.path.exists(p):
                os.remove(p)

        return {"output": output if output.strip() else "[No Output]"}

    except Exception as e:
        if os.path.exists(temp_file): os.remove(temp_file)
        return {"output": f"Execution Error: {str(e)}"}
