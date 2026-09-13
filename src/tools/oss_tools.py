"""
云存储工具 — OSS 上传/删除/外链获取
支持阿里云 OSS / 腾讯云 COS / 七牛 Kodo
"""
import hashlib
from pathlib import Path

from loguru import logger
from .registry import register_tool


@register_tool(
    name="oss_upload",
    description="上传文件到云存储，返回外链 URL。大文件自动分片上传。",
    parameters={
        "type": "object",
        "properties": {
            "local_path": {"type": "string", "description": "本地文件路径"},
            "remote_path": {"type": "string", "description": "云存储路径，如 games/slug/file.zip"},
            "content_type": {"type": "string", "description": "MIME 类型", "default": "application/octet-stream"},
        },
        "required": ["local_path", "remote_path"]
    },
    category="oss",
)
def oss_upload(local_path: str, remote_path: str, content_type: str = "application/octet-stream") -> str:
    """上传文件到 OSS"""
    from ..config.loader import load_config

    config = load_config()
    oss_cfg = config.get("oss", {})
    provider = oss_cfg.get("provider", "")

    local = Path(local_path)
    if not local.exists():
        return f"❌ 文件不存在: {local_path}"

    file_size_mb = local.stat().st_size / (1024 * 1024)

    try:
        if provider == "aliyun":
            return _upload_aliyun(local, remote_path, oss_cfg, content_type)
        elif provider == "tencent":
            return _upload_tencent(local, remote_path, oss_cfg, content_type)
        elif provider == "qiniu":
            return _upload_qiniu(local, remote_path, oss_cfg, content_type)
        elif provider == "none":
            return "⚠️ 未配置云存储，无法上传"
        else:
            return f"❌ 不支持的云存储: {provider}"
    except Exception as e:
        logger.error(f"❌ OSS 上传失败: {e}")
        return f"❌ 上传失败: {e}"


def _upload_aliyun(local_path: Path, remote_path: str, cfg: dict, content_type: str) -> str:
    """阿里云 OSS 上传"""
    import oss2

    auth = oss2.Auth(cfg["access_key"], cfg["secret_key"])
    bucket = oss2.Bucket(auth, f"https://{cfg['region']}.aliyuncs.com", cfg["bucket"])

    file_size = local_path.stat().st_size

    if file_size > 100 * 1024 * 1024:  # >100MB 分片上传
        logger.info(f"📤 分片上传: {local_path.name} ({file_size / 1024**2:.0f}MB)")
        upload_id = bucket.init_multipart_upload(remote_path).upload_id
        parts = []
        part_size = 10 * 1024 * 1024  # 10MB 每片
        part_number = 1

        with open(local_path, "rb") as f:
            while True:
                data = f.read(part_size)
                if not data:
                    break
                result = bucket.upload_part(remote_path, upload_id, part_number, data)
                parts.append(oss2.models.PartInfo(part_number, result.etag))
                part_number += 1

        bucket.complete_multipart_upload(remote_path, upload_id, parts)
    else:
        bucket.put_object_from_file(remote_path, str(local_path),
                                     headers={"Content-Type": content_type})

    domain = cfg.get("domain", "").rstrip("/")
    if domain:
        url = f"{domain}/{remote_path}"
    else:
        url = f"https://{cfg['bucket']}.{cfg['region']}.aliyuncs.com/{remote_path}"

    logger.info(f"✅ 上传成功: {url}")
    return f"✅ 上传成功\n  外链: {url}"


def _upload_tencent(local_path: Path, remote_path: str, cfg: dict, content_type: str) -> str:
    """腾讯云 COS 上传"""
    from qcloud_cos import CosConfig, CosS3Client

    cos_cfg = CosConfig(
        Region=cfg.get("region", "ap-guangzhou"),
        SecretId=cfg["access_key"],
        SecretKey=cfg["secret_key"],
    )
    client = CosS3Client(cos_cfg)
    client.put_object_from_local_file(
        Bucket=cfg["bucket"],
        LocalFilePath=str(local_path),
        Key=remote_path,
        ContentType=content_type,
    )

    domain = cfg.get("domain", "").rstrip("/")
    if domain:
        url = f"{domain}/{remote_path}"
    else:
        url = f"https://{cfg['bucket']}.cos.{cfg.get('region','ap-guangzhou')}.myqcloud.com/{remote_path}"

    return f"✅ 上传成功\n  外链: {url}"


def _upload_qiniu(local_path: Path, remote_path: str, cfg: dict, content_type: str) -> str:
    """七牛 Kodo 上传"""
    from qiniu import Auth, put_file

    q = Auth(cfg["access_key"], cfg["secret_key"])
    token = q.upload_token(cfg["bucket"], remote_path, 3600)
    ret, info = put_file(token, remote_path, str(local_path))

    if info.status_code != 200:
        return f"❌ 七牛上传失败: {info}"

    domain = cfg.get("domain", "").rstrip("/")
    url = f"{domain}/{remote_path}" if domain else f"https://{cfg['bucket']}.qiniucdn.com/{remote_path}"
    return f"✅ 上传成功\n  外链: {url}"


@register_tool(
    name="oss_delete",
    description="删除云存储上的文件",
    parameters={
        "type": "object",
        "properties": {
            "remote_path": {"type": "string", "description": "云存储路径"},
        },
        "required": ["remote_path"]
    },
    category="oss",
)
def oss_delete(remote_path: str) -> str:
    """删除 OSS 文件（简化版，仅支持阿里云）"""
    from ..config.loader import load_config
    config = load_config()
    oss_cfg = config.get("oss", {})

    if oss_cfg.get("provider") == "aliyun":
        import oss2
        auth = oss2.Auth(oss_cfg["access_key"], oss_cfg["secret_key"])
        bucket = oss2.Bucket(auth, f"https://{oss_cfg['region']}.aliyuncs.com", oss_cfg["bucket"])
        bucket.delete_object(remote_path)
        return f"✅ 已删除: {remote_path}"

    return "⚠️ 仅阿里云 OSS 支持此操作"
