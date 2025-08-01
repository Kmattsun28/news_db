import os
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

model_path = os.getenv("QWEN_MODEL_PATH", "Qwen/Qwen3-4B")

tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    trust_remote_code=True,
    torch_dtype=torch.float16,
    device_map="auto"
)

def summarize_text(text: str) -> str:
    messages = [
        {"role": "user", "content": 
            "あなたは優秀な金融専門のデータサイエンティストです。以下のニュース記事について、記載された事実のみをもとに、日本語で3文以内で要約してください。\
            •	記事の内容を正確に把握し、主観・推測・解釈を一切含めずに要約してください。\
            •	日付、地名、人物、機関名、数値など、為替市場に影響しうる情報をなるべく削らずに記載してください。\
            •	記事が英語でも、日本語で要約してください。\
            •	もし記事の本文が取得できなかった場合は、記事タイトルを日本語で要約してください。\
            以下が対象記事です："},
        {"role": "user", "content": text}
    ]
    text_in = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False
    )
    inputs = tokenizer([text_in], return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=32768)
    gen = out[0][inputs["input_ids"].shape[-1]:]
    
    return tokenizer.decode(gen, skip_special_tokens=True).strip()

def summarize_news(news: str) -> str:
    """
    ニュース記事を要約する関数
    :param news: ニュース記事のテキスト
    :return: 要約されたテキスト
    """
    messages = [
        {"role": "user", "content": 
            "あなたは優秀な金融為替アナリストです。以下はアメリカのトランプ大統領のSNS投稿です。\
            この発言がUSD（米ドル）、JPY（日本円）、EUR（ユーロ）に与える影響を、為替市場の観点から推論してください。\
            また、これらの通貨を保有している場合、それぞれの通貨についてどのようなアクション（保持・売却・購入など）を取るべきか、理由とともに日本語で簡潔に述べてください。\
            以下が対象の投稿です："},
        {"role": "user", "content": news}
    ]
    text_in = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False
    )
    inputs = tokenizer([text_in], return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=32768)
    gen = out[0][inputs["input_ids"].shape[-1]:]
    
    return tokenizer.decode(gen, skip_special_tokens=True).strip()  