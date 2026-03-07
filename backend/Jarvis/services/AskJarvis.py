import requests
from dotenv import load_dotenv
import os

load_dotenv()  

url = "https://models.github.ai/inference/chat/completions"
ApiKey =os.getenv('API_KEY')

headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {ApiKey}",
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json"
}

data = {
    "model": "openai/gpt-4.1",
    "messages": [
        {"role": "user", "content": "iNONA NY ATAO HOE FIRAISANA ARA NOFO"}
    ]
}

response = requests.post(url, headers=headers, json=data)

print(response.status_code)
#print(response.json())
print(response.json()["choices"][0]["message"]["content"])
