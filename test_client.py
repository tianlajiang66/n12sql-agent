import requests

# 你的 API 地址
url = "http://127.0.0.1:8000/chat"

# 模拟前端发来的数据
data = {
    "query": "帮我查一下北京的用户"
}

print("正在向本地服务发送请求...")

try:
    # 像前端一样发送 POST 请求
    response = requests.post(url, json=data)
    
    # 打印服务器返回的结果
    print("\n--- 服务器成功返回 ---")
    print("状态码:", response.status_code)
    print("返回数据:", response.json())
except Exception as e:
    print("\n请求失败，错误信息：", e)