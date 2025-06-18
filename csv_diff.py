import openai

with open("file1.csv", "r") as f1, open("file2.csv", "r") as f2:
    csv1 = f1.read()
    csv2 = f2.read()

prompt = f"""
以下は2つのCSVファイルの内容です。
file1.csv:
{csv1}

file2.csv:
{csv2}

この2つのCSVファイルの差分（file1にあってfile2にない行、file2にあってfile1にない行）を抽出し、日本語でわかりやすくリストアップしてください。
"""

response = openai.ChatCompletion.create(
    model="gpt-4-1106-preview", # または gpt-4o, gpt-4-turbo など
    messages=[
        {"role": "system", "content": "あなたはCSVファイルの差分抽出エキスパートです。"},
        {"role": "user", "content": prompt}
    ],
    max_tokens=2048
)

print(response["choices"][0]["message"]["content"])
