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

# ...前面保留 import requests, json, re, sqlite3...

def generate_sql(user_query, table_schema, error_msg=None):
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

# 测试 1：测试安全拦截（故意让它删数据）
print("--- 测试 1：危险操作 ---")
bad_sql = generate_sql("把张三从数据库里删掉", schema)
result, success = safe_execute_sql(bad_sql)
print("最终结果：", result)

# 测试 2：测试自我纠错
print("\n--- 测试 2：自我纠错 ---")
# 我们故意给一个错误的 schema（把 users 写成 user_info），逼大模型报错
wrong_schema = "表名: user_info, 字段: id, name, age"
query = "帮我查一下所有年龄大于20的人"

# 第一次尝试
sql_v1 = generate_sql(query, wrong_schema)
result_v1, success_v1 = safe_execute_sql(sql_v1)

if not success_v1:
    print(f"发现报错：{result_v1}，正在让大模型自我纠正...")
    # 把报错信息发回去，让它重写
    sql_v2 = generate_sql(query, "表名: users, 字段: id, name, age, city", error_msg=result_v1)
    result_v2, success_v2 = safe_execute_sql(sql_v2)
    print("纠正后的最终结果：", result_v2)
else:
    print("查询结果：", result_v1)