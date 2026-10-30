from fastapi import FastAPI
from pydantic import BaseModel
import requests
import json
import re
import sqlite3

app = FastAPI()

# ⚠️ 换成你自己的 Key 和 URL
API_KEY = "fe5ddaf6791c411eb09fb3c84fca7278.2vywNXjIuHNSWG6D"
URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions" 
MODEL_NAME = "glm-4-flash" 

# 全局记忆（真实场景要存 Redis 或数据库，这里为了演示用全局变量）
history_messages = []

# 定义请求体的格式
class QueryRequest(BaseModel):
    query: str

# 你的核心函数（和你昨天写的一样，只是去掉了 print，改成 return）
def generate_sql(user_query, table_schema):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    system_prompt = f"你是一个专业的 SQL 翻译器。当前数据库表结构如下：\n{table_schema}\n只输出 SQL，不要解释。"
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history_messages)
    messages.append({"role": "user", "content": user_query})

    payload = {"model": MODEL_NAME, "messages": messages, "temperature": 0.1}

    try:
        response = requests.post(URL, headers=headers, json=payload, timeout=30)
        raw_answer = response.json()["choices"][0]["message"]["content"]
        clean_sql = re.sub(r"```sql|```", "", raw_answer).strip()
        
        history_messages.append({"role": "user", "content": user_query})
        history_messages.append({"role": "assistant", "content": clean_sql})
        return clean_sql
    except Exception as e:
        return f"生成失败：{e}"

def execute_sql(sql):
    if not sql.upper().startswith("SELECT"): return "拦截：非查询操作"
    try:
        conn = sqlite3.connect('test.db')
        cursor = conn.cursor()
        cursor.execute(sql)
        return str(cursor.fetchall()) # 把列表转成字符串方便返回
    except Exception as e:
        return f"执行报错：{e}"

# 核心接口
@app.post("/chat")
def chat_with_db(req: QueryRequest):
    schema = "表名: users, 字段: id, name, age, city"
    # 1. 生成 SQL
    sql = generate_sql(req.query, schema)
    # 2. 执行 SQL
    result = execute_sql(sql)
    
    # 3. 返回给前端的数据
    return {
        "code": 200,
        "user_query": req.query,
        "generated_sql": sql,
        "data": result
    }