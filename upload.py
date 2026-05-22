import os
import json
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

BACKUP_FOLDER = "backup_files"
LOG_FILE = "backup_log.json"


def get_credentials():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return creds


def load_log():
    if not os.path.exists(LOG_FILE):
        return {}

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_log(log):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def upload_file(service, file_path):
    file_name = os.path.basename(file_path)

    file_metadata = {
        "name": file_name
    }

    media = MediaFileUpload(file_path, resumable=True)

    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink"
    ).execute()

    return uploaded_file


def backup_files():
    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)
        print(f"{BACKUP_FOLDER} フォルダを作成しました。")
        print("この中にアップロードしたいファイルを入れてください。")
        return

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    log = load_log()

    files = os.listdir(BACKUP_FOLDER)

    if not files:
        print("バックアップ対象ファイルがありません。")
        return

    for file_name in files:
        file_path = os.path.join(BACKUP_FOLDER, file_name)

        if os.path.isdir(file_path):
            continue

        file_size = os.path.getsize(file_path)
        modified_time = os.path.getmtime(file_path)

        file_key = file_name

        if file_key in log:
            saved_size = log[file_key]["size"]
            saved_modified_time = log[file_key]["modified_time"]

            if saved_size == file_size and saved_modified_time == modified_time:
                print(f"スキップ: {file_name}")
                continue

        print(f"アップロード中: {file_name}")

        uploaded_file = upload_file(service, file_path)

        log[file_key] = {
            "drive_file_id": uploaded_file["id"],
            "name": uploaded_file["name"],
            "url": uploaded_file.get("webViewLink"),
            "size": file_size,
            "modified_time": modified_time,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        save_log(log)

        print(f"完了: {file_name}")
        print(f"URL: {uploaded_file.get('webViewLink')}")

    print("バックアップ処理が完了しました。")


if __name__ == "__main__":
    backup_files()