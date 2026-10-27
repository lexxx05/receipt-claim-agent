import os
import time

from dotenv import load_dotenv
from langfuse import get_client
from strands import Agent
from strands.models.gemini import GeminiModel
from strands.types.exceptions import ModelThrottledException

# salin isi env ke environment variable python
load_dotenv()

langfuse = get_client() # baca api key langfuse
if langfuse.auth_check(): # satu request ke server langfuse
    print("[INFO] Langfuse auth_check: OK")
else:
    raise SystemExit("[ERROR] Langfuse failed to load: check API key.")

model = GeminiModel(
    client_args={"api_key": os.environ['GEMINI_API_KEY']},
    model_id=os.environ['AGENT_MODEL_ID'],
    params={
        "temperature":0, # jawaban paling deterministik (0-1)
        "max_output_tokens":512, # max output tokensnya
    },
)

agent = Agent(
    model = model,
    system_prompt = "Answer this question based on your knowledge",
    callback_handler = None,
)

PROMPT = "Sebutkan 3 komponen yang biasa ada di struk restoran."

try:
    start = time.perf_counter()
    result = agent(PROMPT)
    elapsed = time.perf_counter() - start

    print(f"[INFO] Model   : {os.environ['AGENT_MODEL_ID']}")
    print(f"[INFO] Latensi : {elapsed:.2f} detik")
    print(f"[INFO] Jawaban :\n{result}")
except ModelThrottledExecption as exc:
    print(f"[WARN] Kena rate limit Gemini: {exc}")
finally:
    langfuse.flush()
    print("[INFO] Trace dikirim ke Langfuse. Cek menu Tracing.")