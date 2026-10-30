import requests

# 注意：这里是 8080，请求的是 Java 后端
url = "http://127.0.0.1:8080/api/ask"

data = {
    "query": "帮我查一下深圳的用户" # 换个条件，看看是不是真的走通了
}

print("正在请求 Java (8080端口)...")

try:
    response = requests.post(url, json=data)
    print("\n--- Java 返回结果 ---")
    print("状态码:", response.status_code)
    print("返回数据:", response.json())
except Exception as e:
    print("\n请求失败：", e)