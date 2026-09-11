"""Google Tasks 云同步 — 待办事项双向同步

首次使用需要 OAuth 授权（会打开浏览器登录 Google 账号），
之后 token 缓存在本地，无需重复登录。
"""

import os
import time
import uuid

DEFAULT_CLIENT_SECRET_PATH = os.path.expanduser("~/.config/voice_typing/google_client_secret.json")
TOKEN_PATH = os.path.expanduser("~/.config/voice_typing/google_token.json")
SCOPES = ["https://www.googleapis.com/auth/tasks"]
TASKLIST_TITLE = "个人语音工作助手 待办事项"


def _get_client_secret_path():
    """从配置读取凭证文件路径，未配置则用默认路径"""
    from voice_typing.core.config import load_config
    config = load_config()
    path = config.get("google_client_secret_path", "").strip()
    return os.path.expanduser(path) if path else DEFAULT_CLIENT_SECRET_PATH


def _get_credentials():
    """获取有效的 OAuth 凭证，首次会触发浏览器授权流程"""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    client_secret_path = _get_client_secret_path()

    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception as e:
            print(f"[GoogleSync] 读取本地 token 失败: {e}")
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"[GoogleSync] token 刷新失败: {e}")
            creds = None

    if not creds or not creds.valid:
        if not os.path.exists(client_secret_path):
            print(f"[GoogleSync] 未找到凭证文件: {client_secret_path}")
            return None
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print("[GoogleSync] 授权成功，token 已保存")

    return creds


def get_credential_status():
    """返回当前凭证配置状态，用于 UI 显示"""
    path = _get_client_secret_path()
    has_secret = os.path.exists(path)
    has_token = os.path.exists(TOKEN_PATH)
    return {
        "client_secret_path": path,
        "has_client_secret": has_secret,
        "has_token": has_token,
        "authorized": has_token,
    }


def _get_service():
    from googleapiclient.discovery import build
    creds = _get_credentials()
    if not creds:
        return None
    return build("tasks", "v1", credentials=creds)


def _get_or_create_tasklist(service):
    """获取或创建专用任务列表"""
    result = service.tasklists().list(maxResults=100).execute()
    for tl in result.get("items", []):
        if tl.get("title") == TASKLIST_TITLE:
            return tl["id"]
    created = service.tasklists().insert(body={"title": TASKLIST_TITLE}).execute()
    print(f"[GoogleSync] 已创建任务列表: {TASKLIST_TITLE}")
    return created["id"]


def push_todo_items(todo_items, todo_done):
    """将本地待办事项（未完成 + 已完成）推送到 Google Tasks

    Args:
        todo_items: 未完成待办列表 [{text, important, created_at, local_id, google_task_id}, ...]
        todo_done: 已完成待办列表 [{text, important, created_at, completed_at, local_id, google_task_id}, ...]

    Returns:
        (success: bool, message: str)

    说明：不再把 local_id 写入 notes（避免用户在 Google Tasks 里看到内部标识）。
    改为首次创建后，把 Google 返回的 task id 写回本地 item_data["google_task_id"]，
    后续同步直接用这个 id 判断更新还是新建。
    """
    try:
        service = _get_service()
        if not service:
            return False, "未能获取 Google 凭证，请检查凭证文件"

        from googleapiclient.errors import HttpError
        tasklist_id = _get_or_create_tasklist(service)

        pushed = 0
        failed = 0
        for item in todo_items + todo_done:
            title = ("★ " if item.get("important") else "") + item.get("text", "")
            is_done = item in todo_done
            body = {
                "title": title,
                "status": "completed" if is_done else "needsAction",
            }
            gtid = item.get("google_task_id")
            if gtid:
                body["id"] = gtid
                try:
                    service.tasks().update(tasklist=tasklist_id, task=gtid, body=body).execute()
                except HttpError as e:
                    if e.resp.status == 404:
                        # 远端任务确实已被删除，才退化为新建
                        print(f"[GoogleSync] 任务 {gtid} 在远端不存在(404)，新建: {title!r}")
                        body.pop("id", None)
                        created = service.tasks().insert(tasklist=tasklist_id, body=body).execute()
                        item["google_task_id"] = created["id"]
                    else:
                        # 其他错误（限流/网络抖动等）不新建，避免产生重复，记录失败继续下一条
                        print(f"[GoogleSync] 更新任务失败(非404，跳过不新建): {title!r}, 状态码={e.resp.status}, {e}")
                        failed += 1
                        continue
            else:
                created = service.tasks().insert(tasklist=tasklist_id, body=body).execute()
                item["google_task_id"] = created["id"]
            pushed += 1

        msg = f"已推送 {pushed} 条待办到 Google Tasks"
        if failed:
            msg += f"（{failed} 条更新失败已跳过，未产生重复）"
        return True, msg
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"推送失败: {e}"


def pull_todo_items():
    """从 Google Tasks 拉取待办事项

    Returns:
        (success: bool, message: str, todo_items: list, todo_done: list)
    """
    try:
        service = _get_service()
        if not service:
            return False, "未能获取 Google 凭证，请检查凭证文件", [], []

        tasklist_id = _get_or_create_tasklist(service)

        todo_items, todo_done = [], []
        page_token = None
        while True:
            resp = service.tasks().list(
                tasklist=tasklist_id, showCompleted=True, showHidden=True,
                pageToken=page_token, maxResults=100
            ).execute()
            for t in resp.get("items", []):
                title = t.get("title", "")
                important = title.startswith("★ ")
                text = title[2:] if important else title
                item = {
                    "text": text,
                    "important": important,
                    "local_id": str(uuid.uuid4()),
                    "google_task_id": t.get("id"),
                    "created_at": int(time.time() * 1000),
                }
                if t.get("status") == "completed":
                    item["completed_at"] = int(time.time() * 1000)
                    todo_done.append(item)
                else:
                    todo_items.append(item)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        return True, f"已拉取 {len(todo_items) + len(todo_done)} 条待办", todo_items, todo_done
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"拉取失败: {e}", [], []
