from flask import Flask, render_template, request, jsonify, session
import os
from google import genai
from google.genai import types
import PIL.Image
import json
import secrets
import textwrap
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Create uploads and conversations directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('conversations', exist_ok=True)

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyAGxnOv00AxrOfIYbEs8oOZBQwYisZ5u2I" 
client = genai.Client(api_key=GEMINI_API_KEY)
model = "gemini-2.0-flash-exp-image-generation"

# Server-side storage for conversations
# In a production app, this should be replaced with a database
conversation_store = {}

# Helper functions for conversation storage
def save_conversation(conversation_id, data):
    """Save conversation data to server-side storage"""
    conversation_store[conversation_id] = data
    
    # Also save to disk for persistence
    with open(f'conversations/{conversation_id}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_conversation(conversation_id):
    """Get conversation data from server-side storage"""
    if conversation_id in conversation_store:
        return conversation_store[conversation_id]
    
    # Try to load from disk if not in memory
    try:
        with open(f'conversations/{conversation_id}.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            conversation_store[conversation_id] = data
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def get_artwork_prompt():
    return textwrap.dedent("""
    請依照口述影像原則來描述這幅畫的內容，目標是要依照文字就能讓聽者想像此畫作。

    # 畫作描述
    ## 口述影像原則
    - 描述應該是客觀的，避免主觀情緒或詮釋性用語。
    - 使用簡單明瞭的語言，避免使用專業術語或難懂的詞彙。
    - 描述的長度應該適中，既要詳細又不冗長，讓讀者能夠快速理解畫作的內容。
    - 提到畫面中的物件時，請用上、下、左、右、遠、近來描述該物件在畫面中的絕對位置。
    - 使用更具象化、可觸知的描述，用比喻與觸覺可想像的形容，讓讀者能夠在腦海中形成清晰的畫面。
    - 適度引導聽者想像畫面可能的場景或情境，但避免主觀臆測。
        
    ## 口述影像描述順序
    1. 完形與整體印象
        - 先提供畫面的整體視覺印象，例如色調、構圖、氛圍等。
        - 描述主要物件的位置關係、整體結構與視覺風格（如筆觸、材質感、光線等）。
        - 可適度引導聽者想像畫面可能的場景或情境
    2. 區域與構成分析
        - 將畫面劃分為數個區塊（如左／中／右、上／下、前景／背景），有邏輯地描述各區塊。
        - 說明主體與背景、人物與物件、動靜對比、空間深度、顏色對比等構造特徵。
    3. 結語與情感總結
        - 在結尾整理畫面的整體印象，重申主體與畫面特徵。
        - 可指出畫面可能營造的情緒氛圍（如寧靜、壓迫、歡愉），但避免主觀臆測。
        - 若畫面有敘事性，可引導「可能的事件」或「未說出口的情境」，例如：「彷彿畫中人正準備轉身離去」等。

    ## 觀畫重點
    - 畫面的主題：畫作的主題是什麼？是人物、風景、靜物還是抽象？
    - 色彩與光線：畫面中使用了哪些顏色？是否有顏色上的對比？光線的來源和強度如何？
    - 筆觸與質感：筆觸是細膩柔和、光滑精緻，還是粗獷有力、充滿動感？
    - 人物的特徵：如果畫面中有人物，請描述它們的姿態、表情。

    # 畫作意境
    - 請用關鍵字來描述意境
    - 畫面給人的第一感覺是什麼？是寧靜的、壓抑的、歡快的、神祕的？

    # 畫作物件
    - 請列出畫面中的物件，並附上一種主要顏色就好。
    - 請使用常見的基本色系 
    - 格式：["實體":"顏色"]，例如:["樹木":"綠色"]，["天空":"藍色"]

    # 要求
    - 請勿用不確定的口吻描述，不確定的細節不必提到
    - 請保留顏色的描述，例如「紅色的花朵」或「藍色的天空」，而不是「花朵」或「天空」。
    - 請直接輸出繁體中文的描述內容，不需要列點式描述，請用語意通順的一個段落描述畫面。
    - 請不要提到「觀者」等詞彙，請用第三人稱的方式描述畫面。
    - 請回傳JSON格式輸出，包含以下欄位：
        1. "description": "畫作描述"
        2. "artistic_conception" : "畫作意境"
        3. "object": ["實體":"顏色"]
    """)

def analyze_artwork(image_path, color_impressions=None):
    """Analyze the uploaded artwork using Gemini API"""
    image = PIL.Image.open(image_path)
    user_prompt = get_artwork_prompt()
    
    response = client.models.generate_content(
        model=model,
        contents=[user_prompt, image],
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type='application/json'
        )
    )
    
    # Process the response
    cleaned_text = response.text.strip("`").strip()
    lines = cleaned_text.splitlines()
    
    if lines[0].strip().lower() in ['json', '```json']:
        lines = lines[1:]
    
    json_str = "\n".join(lines)
    data = json.loads(json_str)
    
    # Generate a unique conversation ID
    conversation_id = str(uuid.uuid4())
    
    # Initialize conversation data
    conversation_data = {
        "artwork_data": data,
        "image_path": image_path,
        "created_at": datetime.now().isoformat(),
        "color_impressions": color_impressions or {},  # Store color impressions
        "conversation_history": [
            {
                "role": "user", 
                "content": "你是一個藝術評論專家，專門解析畫作細節。請基於畫面內容回答問題，避免臆測。請用繁體中文回答。"
            },
            {
                "role": "assistant", 
                "content": f"我已經分析了這幅畫作，以下是基本描述：\n\n{data['description']}\n\n意境：{data['artistic_conception']}\n\n你可以問我關於這幅畫的任何細節。"
            }
        ]
    }
    
    # Save to server-side storage
    save_conversation(conversation_id, conversation_data)
    
    # Store only the conversation ID in the session
    session['conversation_id'] = conversation_id
    
    return data

def generate_personalized_description(color_impressions):
    """Generate a personalized description based on color impressions"""
    if 'conversation_id' not in session:
        return {"error": "請先上傳和分析圖片"}
    
    # Get conversation data
    conversation_id = session['conversation_id']
    conversation_data = get_conversation(conversation_id)
    
    if not conversation_data:
        return {"error": "對話記錄已失效，請重新上傳圖片"}
    
    # Get key data
    image_path = conversation_data['image_path']
    artwork_data = conversation_data['artwork_data']
    
    # Update color impressions in storage
    conversation_data['color_impressions'] = color_impressions
    save_conversation(conversation_id, conversation_data)
    
    # Create prompt for personalized description
    color_info = ""
    for color, impression in color_impressions.items():
        if impression:
            color_info += f"- {color}色：{impression}\n"
    print(f"color_info: {color_info}")
    if not color_info:
        return {"error": "請至少提供一種顏色的印象"}
    
    prompt = textwrap.dedent(f"""
    請根據用戶對顏色的個人印象，重新解讀這幅畫作。
    
    # 畫作基本資訊
    ## 基本描述
    {artwork_data["description"]}
    
    ## 意境
    {artwork_data["artistic_conception"]}
    
    ## 畫中物件與顏色
    {json.dumps(artwork_data["object"], ensure_ascii=False)}
    
    # 用戶對三原色的個人印象
    {color_info}
    
    # 任務
    請根據用戶對三原色的個人印象，對畫作的基本描述做修改，並保留基本描述的架構，使描述更加個人化
    - 基於用戶對三原色的印象，請將基本描述中所有顏色形容詞替換
    - 不需要列點式描述，請用語意通順的一個段落描述畫面
    - 描述應當流暢自然，有個人風格，不要過於生硬或機械
    """)
    
    try:
        # Call API
        image = PIL.Image.open(image_path)
        response = client.models.generate_content(
            model=model,
            contents=[prompt, image],
            config=types.GenerateContentConfig(temperature=0.7)
        )
        
        personalized_description = response.text
        return {"personalized_description": personalized_description}
    except Exception as e:
        return {"error": f"生成個人化描述時發生錯誤: {str(e)}"}

def ask_follow_up_question(question, personalized_description=None, use_personalized=False):
    """Process follow-up questions about the artwork"""
    if 'conversation_id' not in session:
        return {"error": "請先上傳和分析圖片"}
    
    # Get conversation data from server-side storage
    conversation_id = session['conversation_id']
    conversation_data = get_conversation(conversation_id)
    
    if not conversation_data:
        return {"error": "對話記錄已失效，請重新上傳圖片"}
    
    # Get key data
    image_path = conversation_data['image_path']
    artwork_data = conversation_data['artwork_data']
    conversation_history = conversation_data['conversation_history']
    
    # Add user question to history
    conversation_history.append({"role": "user", "content": question})
    
    # Create context from conversation history
    if use_personalized and personalized_description:
        context = textwrap.dedent(f'''
                                基於我們之前的對話和畫作圖像，不需要列點式描述，請用語意通順的一個段落回答問題。
                                請只回答與畫作的畫面直接相關的內容，如畫中的細節、技術、內容。
                                如果無法從畫面中判斷，請誠實說明，如果與畫作無關的問題，請告知「與畫作內容無關」。
                                # 畫作個人化描述
                                {personalized_description}\n
                                # 畫作意境
                                {artwork_data["artistic_conception"]}\n''')
    else:
        context = textwrap.dedent(f'''
                                基於我們之前的對話和畫作圖像，不需要列點式描述，請用語意通順的一個段落回答問題。
                                請只回答與畫作的畫面直接相關的內容，如畫中的細節、技術、內容。
                                如果無法從畫面中判斷，請誠實說明，如果與畫作無關的問題，請告知「與畫作內容無關」。
                                # 畫作描述
                                {artwork_data["description"]}\n
                                # 畫作意境
                                {artwork_data["artistic_conception"]}\n''')
    
    # Include previous conversation context
    if len(conversation_history) > 3:
        context += "# 先前的對話內容：\n"
        for i in range(2, len(conversation_history) - 1):  # Exclude the just added user question
            msg = conversation_history[i]
            prefix = "問題：" if msg["role"] == "user" else "回答："
            context += f"{prefix}{msg['content']}\n\n"
        
    context += f'# 我的問題是\n{question}'
    
    try:
        # Call API
        image = PIL.Image.open(image_path)
        response = client.models.generate_content(
            model=model,
            contents=[context, image],
            config=types.GenerateContentConfig(temperature=0.2)
        )
        
        # Record model answer
        answer = response.text
        conversation_history.append({"role": "assistant", "content": answer})
        
        # Update conversation data
        conversation_data['conversation_history'] = conversation_history
        save_conversation(conversation_id, conversation_data)
        
        return {
            "answer": answer, 
            "history": conversation_history
        }
    except Exception as e:
        return {"error": f"處理請求時發生錯誤: {str(e)}"}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Get color impressions if provided
    color_impressions = {}
    if 'color_impressions' in request.form:
        try:
            color_impressions = json.loads(request.form['color_impressions'])
        except json.JSONDecodeError:
            pass
    
    if file:
        # Save the file
        filename = f"artwork_{secrets.token_hex(8)}{os.path.splitext(file.filename)[1]}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Analyze the artwork
        try:
            data = analyze_artwork(filepath, color_impressions)
            return jsonify({
                "success": True, 
                "data": data,
                "image_url": f"/static/uploads/{filename}"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "No question provided"}), 400
    
    personalized_description = data.get('personalized_description', None)
    use_personalized = data.get('use_personalized', False)
    
    result = ask_follow_up_question(
        data["question"], 
        personalized_description=personalized_description,
        use_personalized=use_personalized
    )
    return jsonify(result)

@app.route('/personalize', methods=['POST'])
def personalize():
    data = request.get_json()
    if not data or 'color_impressions' not in data:
        return jsonify({"error": "No color impressions provided"}), 400
    
    result = generate_personalized_description(data['color_impressions'])
    return jsonify(result)

@app.route('/history')
def get_history():
    if 'conversation_id' not in session:
        return jsonify({"history": []}), 404
    
    conversation_id = session['conversation_id']
    conversation_data = get_conversation(conversation_id)
    
    if not conversation_data:
        return jsonify({"history": []}), 404
    
    return jsonify({"history": conversation_data['conversation_history']})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
