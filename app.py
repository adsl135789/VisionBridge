import os
import PIL.Image
import json
import secrets
import uuid
import textwrap 
from datetime import datetime, timedelta  # 修改這一行，直接導入 timedelta
from dotenv import load_dotenv
from google import genai
from google.genai import types
from flask import Flask, render_template, request, jsonify
from utils.mongodb_helper import connect_db, close_db, query_color_descriptions


# 載入環境變數
load_dotenv()
connect_db()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# 增加session設定以確保cookie正確設置
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)  # 修改為直接使用 timedelta
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # 開發環境設為False，生產環境設為True

# Create uploads and conversations directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('conversations', exist_ok=True)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)
model = "gemini-2.0-flash-exp-image-generation"

# Server-side storage for conversations
# In a production app, this should be replaced with a database
conversation_store = {}

# 新增一個全局字典來追蹤用戶的 conversation_id
user_conversation_map = {}

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

# 新增函數來獲取用戶標識符
def get_user_identifier():
    """獲取用戶標識符，這裡使用 IP 地址"""
    if request.headers.get('X-Forwarded-For'):
        # 處理代理情況
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip = request.remote_addr
    return ip

# 獲取當前用戶的 conversation_id
def get_current_conversation_id():
    """獲取當前用戶的 conversation_id"""
    user_id = get_user_identifier()
    return user_conversation_map.get(user_id)

# 設置當前用戶的 conversation_id
def set_current_conversation_id(conversation_id):
    """設置當前用戶的 conversation_id"""
    user_id = get_user_identifier()
    user_conversation_map[user_id] = conversation_id
    print(f"為用戶 {user_id} 設置 conversation_id: {conversation_id}")

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
    - 適度引導聽者想像畫面可能的場景或情境，但避免主觀臆測.
        
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

    # 畫作顏色
    - 請列出畫作描述中有提到的顏色

    # 要求
    - 請勿用不確定的口吻描述，不確定的細節不必提到
    - 請保留重要物件的顏色描述，例如「紅色的花朵」或「藍色的天空」，而不是「花朵」或「天空」。
    - 請使用常見的基本色來形容，不要使用如「深色」、「淺色」等模糊的描述
    - 請直接輸出繁體中文的描述內容，不需要列點式描述，請用語意通順的一個段落描述畫面。
    - 請不要提到「觀者」等詞彙，請用第三人稱的方式描述畫面。
    - 請回傳JSON格式輸出，包含以下欄位：
        1. "description": "畫作描述"
        2. "artistic_conception" : "畫作意境"
        3. "color": ["顏色1", "顏色2", ...]
    """)

def analyze_artwork(image_path):
    """Analyze the uploaded artwork using Gemini API"""
    image = PIL.Image.open(image_path)
    user_prompt = get_artwork_prompt()
    
    response = client.models.generate_content(
        model=model,
        contents=[user_prompt, image],
        config=types.GenerateContentConfig(
            temperature=1,
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
        "personalized_data": "",
        "conversation_history": [
            {
                "role": "user", 
                "content": "你是一個藝術評論專家，專門解析畫作細節。請基於畫面內容回答問題，避免臆測。請用繁體中文回答。"
            },
            {
                "role": "assistant", 
                "content": f"我已經分析了這幅畫作，以下是基本描述：\n\n{data['description']}\n\n意境：{data['artistic_conception']}\n\n你可以問我關於這幅畫的任何細節。"
            }
        ],
        "color_impressions": {}  # 新增一個空的顏色印象欄位
    }
    # 使用全局變數存儲 conversation_id，而非 session
    set_current_conversation_id(conversation_id)
    print(f"在 analyze_artwork 中設置 conversation_id: {conversation_id}")
    
    # Save to server-side storage
    save_conversation(conversation_id, conversation_data)
    
    return {**data, "conversation_id": conversation_id}

def generate_personalized_description(personalized_data, color_impressions=None):
    """Generate a personalized description based on the user's country and color impressions"""
    # 獲取當前用戶的 conversation_id，而非從 session 中獲取
    conversation_id = get_current_conversation_id()
    print(f"當前用戶的 conversation_id: {conversation_id}")
    
    if not conversation_id:
        return {"error": "請先上傳和分析圖片"}
    
    # Get conversation data
    conversation_data = get_conversation(conversation_id)
    
    if not conversation_data:
        return {"error": "對話記錄已失效，請重新上傳圖片"}
    
    # Get key data
    image_path = conversation_data['image_path']
    artwork_data = conversation_data['artwork_data']
    
    # 更新使用者的國家/文化背景和顏色印象
    conversation_data['personalized_data'] = personalized_data
    if color_impressions:
        conversation_data['color_impressions'] = color_impressions
    save_conversation(conversation_id, conversation_data)
    
    # 獲取文化相關的顏色描述
    cultural_data = ""
    try:
        # 從畫作資料中獲取顏色列表
        colors = artwork_data["color"]
        
        print(f"Colors from artwork data: {colors}")
        
        # 查詢顏色描述
        color_descriptions = query_color_descriptions(personalized_data, colors)
        
        if color_descriptions:
            for color, descriptions in color_descriptions.items():
                cultural_data += f"## {color}色\n"
                for desc in descriptions:
                    cultural_data += f"- {desc}\n"
        print(f"文化顏色描述: {cultural_data}")
    except Exception as e:
        print(f"獲取文化顏色描述時出錯: {str(e)}")
    
    # 添加使用者的顏色印象到提示中
    user_color_impressions = ""
    if color_impressions:
        user_color_impressions += "# 使用者對顏色的個人印象\n"
        if color_impressions.get('red'):
            user_color_impressions += f"## 紅色\n- {color_impressions['red']}\n"
        if color_impressions.get('green'):
            user_color_impressions += f"## 綠色\n- {color_impressions['green']}\n"
        if color_impressions.get('blue'):
            user_color_impressions += f"## 藍色\n- {color_impressions['blue']}\n"
    
    prompt = textwrap.dedent(f"""
    # 任務
    請根據此盲人的文化背景和個人對顏色的印象，對畫作的基本描述做修改，融入{personalized_data}文化對於畫作的解讀視角
    - 依照口述影像原則來修改這幅畫的內容，目標是要依照文字就能讓聽者想像此畫作。
    - 請將基本描述中出現的顏色用{personalized_data}文化對於這些顏色的描述和使用者的個人色彩印象來補充/替換，請從中選擇最適合的描述來補充/替換。
    - 若基本描述中有顏色描述中沒有提到顏色，請依照畫作意境中合適的感覺來將補充/替換該顏色成盲人友善的描述。
    - 請直接輸出繁體中文的描述內容，不需要列點式描述，請用語意通順的一個段落描述畫面。
    
    # 畫作基本資訊
    ## 基本描述
    {artwork_data["description"]}
    
    ## 意境
    {artwork_data["artistic_conception"]}
    
    # {personalized_data}文化中的顏色描述
    {cultural_data}
    
    {user_color_impressions}
    """)
    
    try:
        # Call API
        image = PIL.Image.open(image_path)
        response = client.models.generate_content(
            model=model,
            contents=[prompt, image],
            config=types.GenerateContentConfig(temperature=1)
        )
        
        personalized_description = response.text
        conversation_data["artwork_data"]['personalized_description'] = personalized_description
        save_conversation(conversation_id, conversation_data)
        return {"personalized_description": personalized_description}
    except Exception as e:
        return {"error": f"生成個人化描述時發生錯誤: {str(e)}"}

def ask_follow_up_question(question):
    """Process follow-up questions about the artwork"""
    # 獲取當前用戶的 conversation_id，而非從 session 中獲取
    conversation_id = get_current_conversation_id()
    
    if not conversation_id:
        return {"error": "請先上傳和分析圖片"}
    
    # Get conversation data from server-side storage
    conversation_data = get_conversation(conversation_id)
    
    if not conversation_data:
        return {"error": "對話記錄已失效，請重新上傳圖片"}
    
    # Get key data
    image_path = conversation_data['image_path']
    artwork_data = conversation_data['artwork_data']
    personalized_description = conversation_data['artwork_data'].get('personalized_description', None)
    conversation_history = conversation_data['conversation_history']
    
    # Add user question to history
    conversation_history.append({"role": "user", "content": question})
    
    # Create context from conversation history
    if personalized_description is not None:
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
    
    
    if file:
        # Save the file
        filename = f"artwork_{secrets.token_hex(8)}{os.path.splitext(file.filename)[1]}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 獲取顏色印象資料
        color_impressions = {}
        if 'color_impressions' in request.form:
            try:
                color_impressions = json.loads(request.form['color_impressions'])
            except:
                color_impressions = {}
        
        # Analyze the artwork
        try:
            data = analyze_artwork(filepath)
            
            # 如果獲取到顏色印象資料，更新到會話中
            if color_impressions:
                conversation_id = data.get('conversation_id')
                conversation_data = get_conversation(conversation_id)
                if conversation_data:
                    conversation_data['color_impressions'] = color_impressions
                    save_conversation(conversation_id, conversation_data)
            
            return jsonify({
                "success": True, 
                "data": data,
                "image_url": f"/static/uploads/{filename}",
                "conversation_id": data.get('conversation_id')  # 返回conversation_id到前端
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({"error": "No question provided"}), 400
    
    # 如果前端提供了 conversation_id，則使用它來恢復對話狀態
    if 'conversation_id' in data and not get_current_conversation_id():
        conversation_id = data['conversation_id']
        set_current_conversation_id(conversation_id)
        print(f"從請求中恢復 conversation_id: {conversation_id}")
    
    print(f"在 ask_question 中的 conversation_id: {get_current_conversation_id()}")

    
    result = ask_follow_up_question(data["question"])
    return jsonify(result)

@app.route('/personalize', methods=['POST'])
def personalize():
    data = request.get_json()
    if not data:
        return jsonify({"error": "未提供資料"}), 400
    
    # 檢查是否提供了國家/文化背景
    personalized_data = data.get('personalized_data')
    if not personalized_data:
        return jsonify({"error": "未選擇國家/文化背景"}), 400
    
    # 獲取顏色印象資料
    color_impressions = data.get('color_impressions', {})
    
    # 如果前端提供了 conversation_id，則使用它來恢復對話狀態
    if 'conversation_id' in data and not get_current_conversation_id():
        conversation_id = data['conversation_id']
        set_current_conversation_id(conversation_id)
        print(f"從請求中恢復 conversation_id: {conversation_id}")
    
    result = generate_personalized_description(personalized_data, color_impressions)
    return jsonify(result)

@app.route('/history')
def get_history():
    # 獲取當前用戶的 conversation_id，而非從 session 中獲取
    conversation_id = get_current_conversation_id()
    
    if not conversation_id:
        return jsonify({"history": []}), 404
    
    conversation_data = get_conversation(conversation_id)
    
    if not conversation_data:
        return jsonify({"history": []}), 404
    
    return jsonify({"history": conversation_data['conversation_history']})

    
if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=8080)
