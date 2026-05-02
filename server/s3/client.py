"""S3 client for Agent Dropbox file sync.

Single boto3 client connecting directly to AWS S3 (or S3-compatible storage).
Handles presigned URL generation, object listing, multipart uploads, and deletes.
"""
import math

import boto3
from botocore.config import Config as BotoConfig

from config import (
    MULTIPART_PART_SIZE,
    PRESIGNED_URL_EXPIRY,
    S3_ACCESS_KEY,
    S3_BUCKET,
    S3_ENDPOINT_URL,
    S3_REGION,
    S3_SECRET_KEY,
)

_BOTO_CONFIG = BotoConfig(
    signature_version="s3v4",
    s3={"addressing_style": "path"},
)

_client = None


def _get_client():
    global _client
    if _client is None:
        kwargs = {
            "aws_access_key_id": S3_ACCESS_KEY,
            "aws_secret_access_key": S3_SECRET_KEY,
            "region_name": S3_REGION,
            "config": _BOTO_CONFIG,
        }
        if S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = S3_ENDPOINT_URL
        _client = boto3.client("s3", **kwargs)
    return _client


# ── Path helpers ─────────────────────────────────────────────────────

def device_prefix(s3_prefix: str, folder_name: str) -> str:
    return f"{s3_prefix}{folder_name}/"


def is_hidden_path(rel_path: str) -> bool:
    return any(part.startswith(".") for part in rel_path.split("/") if part)


# ── Object listing ───────────────────────────────────────────────────

def list_objects(prefix: str, skip_hidden: bool = False) -> list[dict]:
    if skip_hidden:
        return _list_objects_skip_hidden(prefix)
    return _list_objects_flat(prefix)


def _list_objects_flat(prefix: str) -> list[dict]:
    client = _get_client()
    objects: list[dict] = []
    continuation_token = None

    while True:
        kwargs: dict = {"Bucket": S3_BUCKET, "Prefix": prefix, "MaxKeys": 1000}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        resp = client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            objects.append({
                "key": obj["Key"],
                "etag": obj["ETag"].strip('"'),
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            })

        if resp.get("IsTruncated"):
            continuation_token = resp["NextContinuationToken"]
        else:
            break

    return objects


def _list_objects_skip_hidden(prefix: str) -> list[dict]:
    client = _get_client()
    objects: list[dict] = []
    sub_prefixes: list[str] = []
    continuation_token = None

    while True:
        kwargs: dict = {"Bucket": S3_BUCKET, "Prefix": prefix, "Delimiter": "/", "MaxKeys": 1000}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        resp = client.list_objects_v2(**kwargs)

        for obj in resp.get("Contents", []):
            rel = obj["Key"][len(prefix):]
            if rel and not rel.startswith("."):
                objects.append({
                    "key": obj["Key"],
                    "etag": obj["ETag"].strip('"'),
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                })

        for cp in resp.get("CommonPrefixes", []):
            dir_prefix = cp["Prefix"]
            dir_name = dir_prefix[len(prefix):].rstrip("/")
            if not dir_name.startswith("."):
                sub_prefixes.append(dir_prefix)

        if resp.get("IsTruncated"):
            continuation_token = resp["NextContinuationToken"]
        else:
            break

    for sp in sub_prefixes:
        objects.extend(_list_objects_flat(sp))

    return objects


# ── Presigned URL generation ─────────────────────────────────────────

def generate_presigned_get(key: str, expiry: int = PRESIGNED_URL_EXPIRY) -> str:
    return _get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expiry,
    )


def generate_presigned_put(key: str, expiry: int = PRESIGNED_URL_EXPIRY) -> str:
    return _get_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expiry,
    )


# ── Multipart upload ────────────────────────────────────────────────

def initiate_multipart_upload(key: str) -> str:
    resp = _get_client().create_multipart_upload(Bucket=S3_BUCKET, Key=key)
    return resp["UploadId"]


def generate_presigned_upload_part(
    key: str, upload_id: str, part_number: int, expiry: int = PRESIGNED_URL_EXPIRY,
) -> str:
    return _get_client().generate_presigned_url(
        "upload_part",
        Params={
            "Bucket": S3_BUCKET,
            "Key": key,
            "UploadId": upload_id,
            "PartNumber": part_number,
        },
        ExpiresIn=expiry,
    )


def complete_multipart_upload(key: str, upload_id: str, parts: list[dict]) -> dict:
    return _get_client().complete_multipart_upload(
        Bucket=S3_BUCKET,
        Key=key,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts},
    )


def abort_multipart_upload(key: str, upload_id: str) -> None:
    _get_client().abort_multipart_upload(Bucket=S3_BUCKET, Key=key, UploadId=upload_id)


def compute_part_count(file_size: int) -> int:
    return math.ceil(file_size / MULTIPART_PART_SIZE)


# ── Delete operations ───────────────────────────────────────────────

def delete_object(key: str) -> None:
    _get_client().delete_object(Bucket=S3_BUCKET, Key=key)


def delete_objects(keys: list[str]) -> dict:
    if not keys:
        return {"Deleted": [], "Errors": []}
    objects = [{"Key": k} for k in keys]
    return _get_client().delete_objects(
        Bucket=S3_BUCKET,
        Delete={"Objects": objects, "Quiet": False},
    )


def head_object(key: str) -> dict | None:
    try:
        return _get_client().head_object(Bucket=S3_BUCKET, Key=key)
    except _get_client().exceptions.NoSuchKey:
        return None
    except Exception:
        return None
