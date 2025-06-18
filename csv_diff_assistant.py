#!/usr/bin/env python
# diff_csv_with_gpt.py
import os, sys, time, openai

openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-4o-mini"           # 2025-06 現在の軽量 GPT-4 モデル
SLEEP_SEC  = 5                       # Run 完了待ちのポーリング間隔

def upload(path: str) -> str:
    """CSV をアップロードして file_id を返す"""
    print(f"⏫  Uploading {path} …")
    rsp = openai.files.create(file=open(path, "rb"), purpose="assistants")
    return rsp.id

def create_assistant() -> str:
    """Code Interpreter 付きアシスタントを生成"""
    print("⚙️  Creating assistant …")
    asst = openai.beta.assistants.create(
        name        = "CSV Diff Bot",
        model       = MODEL_NAME,
        instructions=(
            "You are a data engineer. "
            "Given two CSV files with the same schema, "
            "load them with pandas, detect row-level differences "
            "(added, removed, updated rows), "
            "and write the result to diff.csv. "
            "Return a concise natural-language summary as well."
        ),
        tools=[{"type": "code_interpreter"}],
    )
    return asst.id

def run_diff(assistant_id: str, file_ids: list[str]) -> tuple[str,str]:
    """スレッドを立ち上げ差分処理を実行"""
    thread = openai.beta.threads.create()
    openai.beta.threads.messages.create(
        thread_id = thread.id,
        role      = "user",
        content   = "Compare these two CSVs and generate diff.csv.",
        file_ids  = file_ids,
    )
    run = openai.beta.threads.runs.create(
        thread_id    = thread.id,
        assistant_id = assistant_id,
    )
    return thread.id, run.id

def wait_run(thread_id: str, run_id: str):
    """Run 完了まで待機"""
    while True:
        run = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run.status in ("completed", "failed", "cancelled"):
            return run
        print("⏳  Waiting…", run.status)
        time.sleep(SLEEP_SEC)

def fetch_messages(thread_id: str):
    msgs = openai.beta.threads.messages.list(thread_id=thread_id).data
    # 最新 (= index 0) がアシスタントの返答
    return msgs[0].content[0].text.value

def download_csv(run):
    """Code Interpreter が生成した diff.csv を保存 (あれば)"""
    # run.step_details がまだ β 仕様なので簡易的に検索
    steps = openai.beta.threads.runs.steps.list(
        thread_id=run.thread_id, run_id=run.id
    ).data
    for st in steps:
        if st.type == "tool" and "file_ids" in st.additional_kwargs:
            for fid in st.additional_kwargs["file_ids"]:
                meta = openai.files.retrieve(fid)
                if meta.filename == "diff.csv":
                    print("💾  Downloading diff.csv …")
                    content = openai.files.retrieve_content(fid)
                    with open("diff.csv", "wb") as f:
                        f.write(content)
                    return "diff.csv"
    return None

def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python diff_csv_with_gpt.py old.csv new.csv")

    file_ids = [upload(p) for p in sys.argv[1:3]]
    asst_id  = create_assistant()
    thread_id, run_id = run_diff(asst_id, file_ids)
    run = wait_run(thread_id, run_id)
    print("✅  Run finished.\n")
    print(fetch_messages(thread_id))
    fn = download_csv(run)
    if fn:
        print(f"\n→ 差分ファイル {fn} が保存されました。")

if __name__ == "__main__":
    main()
