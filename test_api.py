import requests
import json
import re
import sqlite3

# 1. 这里填你刚才搞到的 API Key
API_KEY = "fe5ddaf6791c411eb09fb3c84fca7278.2vywNXjIuHNSWG6D" 

# 2. 这里填平台提供的接口地址（国内平台一般都很显眼，比如智谱是 https://open.bigmodel.cn/api/paas/v4/chat/completions）
URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions" 

# 3. 填你要用的模型名字（比如智谱填 glm-4-flash，阿里填 qwen-turbo）
MODEL_NAME = "glm-4-flash" 

# 用来保存历史对话的列表（这就是最初的记忆）
history_messages = []

def generate_sql(user_query, table_schema, error_msg=None):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = f"你是一个专业的 SQL 翻译器。当前数据库表结构如下：\n{table_schema}\n"
    system_prompt += "任务：将自然语言转为 SQL。只输出 SQL，不要任何解释和 markdown 格式。"

    # 构建 messages 列表
    messages = [{"role": "system", "content": system_prompt}]
    
    # 【核心改造】：把之前的历史记录加进来！
    messages.extend(history_messages)
    
    # 把当前用户的问题加进去
    messages.append({"role": "user", "content": user_query})

    # 如果传了报错信息，说明需要自我纠错
    if error_msg:
        messages.append({"role": "assistant", "content": "我上一次生成错了。"})
        messages.append({"role": "user", "content": f"数据库报错信息是：{error_msg}，请重新生成正确的 SQL。"})

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.1
    }

    try:
        response = requests.post(URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        raw_answer = response.json()["choices"][0]["message"]["content"]
        clean_sql = re.sub(r"```sql|```", "", raw_answer).strip()
        
        # 【核心改造】：把这次成功的问答，存进记忆里，供下次使用
        history_messages.append({"role": "user", "content": user_query})
        history_messages.append({"role": "assistant", "content": clean_sql})
        
        return clean_sql
    except Exception as e:
        return f"生成失败：{e}"
    """
    生成 SQL。如果传入了 error_msg，说明上一次生成错了，让大模型纠正。
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = f"你是一个专业的 SQL 翻译器。当前数据库表结构如下：\n{table_schema}\n"
    system_prompt += "任务：将自然语言转为 SQL。只输出 SQL，不要任何解释和 markdown 格式。"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    # 如果传了报错信息，说明需要自我纠错
    if error_msg:
        system_prompt += "\n注意：你上一次生成的 SQL 执行报错了，请根据报错信息修正。"
        messages[0]["content"] = system_prompt
        messages.append({"role": "assistant", "content": "我上一次生成错了。"})
        messages.append({"role": "user", "content": f"数据库报错信息是：{error_msg}，请重新生成正确的 SQL。"})

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.1
    }

    try:
        response = requests.post(URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        raw_answer = response.json()["choices"][0]["message"]["content"]
        clean_sql = re.sub(r"```sql|```", "", raw_answer).strip()
        return clean_sql
    except Exception as e:
        return f"生成失败：{e}"

def safe_execute_sql(sql):
    """
    安全检查 + 执行 SQL，并支持报错纠错
    """
    # 1. 保安拦截：只允许 SELECT，拦截其他危险操作
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return "【安全拦截】拒绝执行：只允许执行查询(SELECT)操作！", False

    # 2. 尝试执行
    print(f"[准备执行]: {sql}")
    try:
        conn = sqlite3.connect('test.db')
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        conn.close()
        return results, True # 成功返回 True
    except Exception as e:
        # 3. 如果报错，把错误信息交出去，让上层去自我纠错
        return str(e), False # 失败返回 False

def init_db():
    # 1. 连接（如果文件不存在会自动创建）
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # 2. 创建刚才提示词里提到的 users 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            city TEXT
        )
    ''')
    
    # 3. 插入几条真实的测试数据
    cursor.execute("DELETE FROM users") # 清空旧数据
    users_data = [
        (1, '张三', 22, '北京'),
        (2, '李四', 18, '上海'),
        (3, '王五', 25, '北京'),
        (4, '赵六', 30, '深圳')
    ]
    cursor.executemany('INSERT INTO users VALUES (?, ?, ?, ?)', users_data)
    
    conn.commit()
    conn.close()

def execute_sql(sql):
    # 兜底：如果大模型生成失败返回了报错信息
    if "生成失败" in sql:
        return "SQL 生成有误，不执行。"
        
    print(f"\n[正在执行 SQL]: {sql}")
    try:
        conn = sqlite3.connect('test.db')
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        # 这就是面试官最爱问的：如果 SQL 执行报错怎么办？
        return f"SQL 执行报错：{e}"
# ================= 测试区域 =================

# 模拟一个数据库表结构（以后你可以从 MySQL 动态获取）
schema = """
表名: users
字段: id (INT), name (VARCHAR), age (INT), city (VARCHAR)
"""

# 初始化数据库
init_db()

# 模拟表结构
schema = "表名: users, 字段: id, name, age, city"

# 第一轮对话
print("--- 第一轮：查北京用户 ---")
q1 = "帮我查一下北京的用户"
sql1 = generate_sql(q1, schema)
res1, _ = safe_execute_sql(sql1)
print("查询结果：", res1)

print("\n--- 第二轮：追问上海用户（考验记忆） ---")
q2 = "那上海的呢？"  # 这里故意不说“查一下上海的用户”，只说“那...呢”
sql2 = generate_sql(q2, schema)
res2, _ = safe_execute_sql(sql2)
print("查询结果：", res2)