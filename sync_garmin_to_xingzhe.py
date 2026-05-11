import os
import sys
import json
import time
import hashlib
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, Any, List

import requests
from garminconnect import Garmin


GARMIN_EMAIL = os.getenv("GARMIN_EMAIL", "")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD", "")
XINGZHE_ACCESS_TOKEN = os.getenv("XINGZHE_ACCESS_TOKEN", "")

XINGZHE_UPLOADS_API = os.getenv(
    "XINGZHE_UPLOADS_API",
    "https://openapi.imxingzhe.com/openapi/v1/uploads/"
)

EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "./exports"))
GARMIN_LIMIT = int(os.getenv("GARMIN_LIMIT", "10"))

ALLOWED_ACTIVITY_TYPES = {
    "running",
    "cycling",
    "walking",
    "trail_running",
    "hiking",
    "mountain_biking",
    "road_biking",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def require_env(name: str, value: str) -> None:
    if not value:
        raise RuntimeError(f"缺少环境变量: {name}")


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_filename(name: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, "_")
    return name.strip() or "activity"


def login_garmin() -> Garmin:
    require_env("GARMIN_EMAIL", GARMIN_EMAIL)
    require_env("GARMIN_PASSWORD", GARMIN_PASSWORD)

    log("正在登录 Garmin Connect...")
    client = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
    client.login()
    log("Garmin 登录成功")
    return client


def get_recent_activities(client: Garmin, limit: int = 10) -> List[Dict[str, Any]]:
    log(f"获取最近 {limit} 条 Garmin 活动...")
    activities = client.get_activities(0, limit)
    log(f"共获取到 {len(activities)} 条活动")
    return activities


def normalize_activity_type(activity: Dict[str, Any]) -> str:
    activity_type = activity.get("activityType", {})
    if isinstance(activity_type, dict):
        type_key = activity_type.get("typeKey", "")
        if type_key:
            return str(type_key).lower()
    return str(activity.get("activityType", "")).lower()


def download_original_activity(client: Garmin, activity_id: str) -> bytes:
    log(f"下载 Garmin 原始活动文件: activity_id={activity_id}")
    content = client.download_activity(
        activity_id,
        dl_fmt=client.ActivityDownloadFormat.ORIGINAL,
    )
    if not content:
        raise RuntimeError(f"下载活动失败，activity_id={activity_id}")
    return content


def extract_fit_from_original(content: bytes, activity_id: str) -> bytes:
    if content[:4] == b".FIT" or b".FIT" in content[:16]:
        return content

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / f"{activity_id}.zip"
        zip_path.write_bytes(content)

        if not zipfile.is_zipfile(zip_path):
            return content

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            fit_names = [n for n in names if n.lower().endswith(".fit")]
            if not fit_names:
                raise RuntimeError(f"zip 中未找到 .fit 文件: {names}")
            fit_name = fit_names[0]
            log(f"从 zip 中提取 FIT 文件: {fit_name}")
            return zf.read(fit_name)


def save_fit_file(activity: Dict[str, Any], fit_bytes: bytes, export_dir: Path) -> Path:
    ensure_dir(export_dir)

    activity_id = str(activity.get("activityId"))
    activity_name = safe_filename(activity.get("activityName", "activity"))
    start_time = str(activity.get("startTimeLocal", "unknown")).replace(":", "-").replace(" ", "_")

    filename = f"{start_time}_{activity_id}_{activity_name}.fit"
    filepath = export_dir / filename
    filepath.write_bytes(fit_bytes)
    log(f"FIT 文件已保存: {filepath}")
    return filepath


def build_xingzhe_headers(access_token: str) -> Dict[str, str]:
    require_env("XINGZHE_ACCESS_TOKEN", access_token)
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def create_xingzhe_upload_record(
    access_token: str,
    fit_filename: str,
    fit_bytes: bytes,
    activity_name: str,
    detail: str = "",
) -> Dict[str, Any]:
    headers = build_xingzhe_headers(access_token)
    payload = {
        "name": activity_name[:32] if activity_name else "Garmin活动",
        "detail": detail[:1500],
        "file_type": "fit",
        "fit_filename": fit_filename,
        "md5": md5_bytes(fit_bytes),
    }

    log("向行者注册上传任务...")
    log("请求地址: " + XINGZHE_UPLOADS_API)
    log("请求体: " + json.dumps(payload, ensure_ascii=False))

    resp = requests.post(XINGZHE_UPLOADS_API, headers=headers, json=payload, timeout=60)
    log(f"行者注册上传响应状态码: {resp.status_code}")
    log(f"行者注册上传响应文本: {resp.text}")

    resp.raise_for_status()
    return resp.json()


def try_upload_file_by_url(upload_url: str, fit_bytes: bytes) -> requests.Response:
    log(f"尝试直接 PUT 到上传地址: {upload_url}")
    resp = requests.put(
        upload_url,
        data=fit_bytes,
        headers={"Content-Type": "application/octet-stream"},
        timeout=300,
    )
    return resp


def try_upload_file_by_post_form(upload_url: str, fields: Dict[str, Any], fit_filename: str, fit_bytes: bytes) -> requests.Response:
    log(f"尝试 multipart/form-data 上传到: {upload_url}")
    files = {
        "file": (fit_filename, fit_bytes, "application/octet-stream")
    }
    resp = requests.post(upload_url, data=fields, files=files, timeout=300)
    return resp


def upload_fit_to_xingzhe(upload_meta: Dict[str, Any], fit_filename: str, fit_bytes: bytes) -> None:
    log("开始解析行者上传响应，准备上传文件...")

    for key in ["upload_url", "put_url", "url"]:
        if isinstance(upload_meta.get(key), str) and upload_meta[key]:
            resp = try_upload_file_by_url(upload_meta[key], fit_bytes)
            log(f"文件上传响应状态码: {resp.status_code}")
            log(f"文件上传响应文本: {resp.text}")
            resp.raise_for_status()
            log("文件上传成功")
            return

    data = upload_meta.get("data")
    if isinstance(data, dict):
        for key in ["upload_url", "put_url", "url"]:
            if isinstance(data.get(key), str) and data[key]:
                resp = try_upload_file_by_url(data[key], fit_bytes)
                log(f"文件上传响应状态码: {resp.status_code}")
                log(f"文件上传响应文本: {resp.text}")
                resp.raise_for_status()
                log("文件上传成功")
                return

    upload = upload_meta.get("upload")
    if isinstance(upload, dict):
        upload_url = upload.get("url")
        fields = upload.get("fields", {})
        if upload_url and isinstance(fields, dict):
            resp = try_upload_file_by_post_form(upload_url, fields, fit_filename, fit_bytes)
            log(f"文件上传响应状态码: {resp.status_code}")
            log(f"文件上传响应文本: {resp.text}")
            if resp.status_code not in (200, 201, 204):
                resp.raise_for_status()
            log("文件上传成功")
            return

    if isinstance(data, dict):
        upload = data.get("upload")
        if isinstance(upload, dict):
            upload_url = upload.get("url")
            fields = upload.get("fields", {})
            if upload_url and isinstance(fields, dict):
                resp = try_upload_file_by_post_form(upload_url, fields, fit_filename, fit_bytes)
                log(f"文件上传响应状态码: {resp.status_code}")
                log(f"文件上传响应文本: {resp.text}")
                if resp.status_code not in (200, 201, 204):
                    resp.raise_for_status()
                log("文件上传成功")
                return

    raise RuntimeError(
        "无法从行者响应中识别文件上传方式。请检查注册上传接口返回的 JSON 结构。"
    )


def sync_one_activity(client: Garmin, activity: Dict[str, Any]) -> None:
    activity_id = str(activity.get("activityId"))
    activity_name = str(activity.get("activityName", "Garmin活动"))
    activity_type = normalize_activity_type(activity)

    log("=" * 80)
    log(f"处理活动: id={activity_id}, name={activity_name}, type={activity_type}")

    if activity_type and activity_type not in ALLOWED_ACTIVITY_TYPES:
        log(f"跳过不在允许列表中的活动类型: {activity_type}")
        return

    original_bytes = download_original_activity(client, activity_id)
    fit_bytes = extract_fit_from_original(original_bytes, activity_id)
    fit_path = save_fit_file(activity, fit_bytes, EXPORT_DIR)

    detail = f"从 Garmin Connect 同步导入，activity_id={activity_id}"
    upload_meta = create_xingzhe_upload_record(
        access_token=XINGZHE_ACCESS_TOKEN,
        fit_filename=fit_path.name,
        fit_bytes=fit_bytes,
        activity_name=activity_name,
        detail=detail,
    )

    upload_fit_to_xingzhe(upload_meta, fit_path.name, fit_bytes)
    log(f"活动同步完成: {activity_id}")


def main() -> None:
    try:
        ensure_dir(EXPORT_DIR)

        client = login_garmin()
        activities = get_recent_activities(client, GARMIN_LIMIT)

        if not activities:
            log("没有找到可同步的活动")
            return

        for activity in activities:
            try:
                sync_one_activity(client, activity)
                time.sleep(1)
            except Exception as e:
                log(f"处理活动失败: {activity.get('activityId')} -> {e}")

        log("全部任务执行完成")

    except Exception as e:
        log(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
