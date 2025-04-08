from typing import List, Dict, Any, Optional
from pymongo import MongoClient

# 獲取MongoDB連接資訊
MONGO_URI = "mongodb+srv://visionbridge:visionbridge@visionbridge.jcycl3h.mongodb.net/?retryWrites=true&w=majority&appName=VisionBridge&tls=true"
DATABASE_NAME = "VisionBridge"

# 全局變數保存MongoDB連接
_client = None
_db = None

def connect_db() -> tuple:
    """
    建立與MongoDB的連接
    
    Returns:
        tuple: (MongoClient, Database) 包含客戶端連接和資料庫對象
    """
    global _client, _db
    
    if _client is None:
        try:
            _client = MongoClient(MONGO_URI)
            _db = _client[DATABASE_NAME]
            print(f"成功連接到資料庫: {DATABASE_NAME}")
        except Exception as e:
            print(f"連接資料庫時發生錯誤: {str(e)}")
            raise
            
    return _client, _db

def close_db() -> None:
    """關閉與MongoDB的連接"""
    global _client
    
    if _client is not None:
        _client.close()
        _client = None
        print("資料庫連接已關閉")

def query_color_descriptions(personalized_data: str, colors: List[str]) -> Dict[str, List[str]]:
    """
    根據國籍和顏色列表查詢對應的顏色描述
    
    Args:
        personalized_data (str): 國籍，如「日本」
        colors (List[str]): 顏色列表，如 ['紅', '黃', '藍']
    
    Returns:
        Dict[str, List[str]]: 以顏色為鍵，描述列表為值的字典
    """
    try:        
        # 獲取指定collection
        collection = _db[personalized_data]
        
        # 查詢文檔
        results = list(collection.find())
        if not results:
            print(f"未找到國籍 '{personalized_data}' 的資料")
            return {}
                    
        # 篩選出請求的顏色描述
        color_descriptions = {}
        for color in colors:
            # 轉換顏色名稱，處理可能的差異，例如「紅色」->「紅」
            color_key = color.replace('色', '')
            
            # 在所有文檔中尋找匹配的顏色
            for doc in results:
                if doc.get('color') == color_key:
                    color_descriptions[color_key] = doc.get('descriptions', [])
                    break
        
        return color_descriptions
        
    except Exception as e:
        print(f"查詢顏色描述時發生錯誤: {str(e)}")
        return {}
