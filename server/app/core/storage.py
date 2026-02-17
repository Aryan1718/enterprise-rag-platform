from __future__ import annotations

from urllib.parse import quote

import httpx
from supabase import Client, create_client

from app.config import settings


def get_supabase_storage_client() -> Client:
    if not settings.SUPABASE_URL or not settings.supabase_service_key:
        raise ValueError("Supabase storage is not configured")
    return create_client(settings.SUPABASE_URL, settings.supabase_service_key)


def _storage_headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }


def _create_bucket_if_missing(bucket: str) -> None:
    create_bucket_url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/bucket"
    payload = {
        "id": bucket,
        "name": bucket,
        "public": False,
    }
    response = httpx.post(create_bucket_url, headers=_storage_headers(), json=payload, timeout=20.0)
    if response.status_code in {200, 201, 409}:
        return
    if response.status_code == 400:
        body = response.text.lower()
        # Some storage deployments return 400 (not 409) when bucket already exists.
        if "already exists" in body or "duplicate" in body:
            return
    raise ValueError(f"Supabase bucket ensure failed ({response.status_code}): {response.text}")


def generate_signed_upload_url(bucket: str, path: str, expires: int) -> str:
    try:
        client = get_supabase_storage_client()
        storage = client.storage.from_(bucket)
        try:
            payload = storage.create_signed_upload_url(path=path, expires_in=expires)
        except TypeError:
            payload = storage.create_signed_upload_url(path, expires)

        if isinstance(payload, dict):
            signed_url = (
                payload.get("signed_url")
                or payload.get("signedURL")
                or payload.get("url")
                or payload.get("path")
            )
        else:
            signed_url = getattr(payload, "signed_url", None) or getattr(payload, "url", None)

        if signed_url:
            if isinstance(signed_url, str) and signed_url.startswith("http"):
                return signed_url
            return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1{signed_url}"
    except TypeError as exc:
        if "proxy" not in str(exc):
            raise

    # Fallback to direct Storage REST API when supabase client/auth-client incompatibility occurs.
    api_url = (
        f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/upload/sign/"
        f"{quote(bucket, safe='')}/{quote(path, safe='/')}"
    )
    headers = _storage_headers()
    # Proactively ensure bucket exists for first-run environments.
    _create_bucket_if_missing(bucket)
    response = httpx.post(api_url, headers=headers, json={"expiresIn": expires}, timeout=20.0)
    if response.status_code in {400, 404}:
        # Retry once after create in case bucket creation was eventually consistent.
        _create_bucket_if_missing(bucket)
        response = httpx.post(api_url, headers=headers, json={"expiresIn": expires}, timeout=20.0)
    if response.status_code >= 400:
        detail = response.text
        raise ValueError(f"Supabase storage signed upload URL failed ({response.status_code}): {detail}")
    payload = response.json()

    signed_url = (
        payload.get("signedURL")
        or payload.get("signedUrl")
        or payload.get("signed_url")
        or payload.get("url")
        or payload.get("path")
    )
    if isinstance(signed_url, str) and signed_url:
        if signed_url.startswith("http"):
            return signed_url
        if signed_url.startswith("/storage/v1"):
            return f"{settings.SUPABASE_URL.rstrip('/')}{signed_url}"
        if signed_url.startswith("/"):
            return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1{signed_url}"
        return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/{signed_url}"

    token = payload.get("token")
    if isinstance(token, str) and token:
        return (
            f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/upload/sign/"
            f"{quote(bucket, safe='')}/{quote(path, safe='/')}?token={quote(token, safe='')}"
        )
    raise ValueError("Failed to generate signed upload URL")


def object_exists(bucket: str, path: str) -> bool | None:
    folder, _, filename = path.rpartition("/")

    try:
        client = get_supabase_storage_client()
        storage = client.storage.from_(bucket)
        if folder:
            items = storage.list(folder, {"search": filename, "limit": 100})
        else:
            items = storage.list("", {"search": filename, "limit": 100})
    except TypeError as exc:
        if "proxy" not in str(exc):
            return None
        list_url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/list/{quote(bucket, safe='')}"
        headers = _storage_headers()
        payload = {"prefix": folder, "search": filename, "limit": 100, "offset": 0}
        try:
            response = httpx.post(list_url, headers=headers, json=payload, timeout=20.0)
            response.raise_for_status()
            items = response.json()
        except Exception:  # noqa: BLE001
            return None
    except Exception:  # noqa: BLE001
        return None

    if not isinstance(items, list):
        return None

    return any(item.get("name") == filename for item in items if isinstance(item, dict))


def delete_object(bucket: str, path: str) -> bool:
    try:
        client = get_supabase_storage_client()
        storage = client.storage.from_(bucket)
        storage.remove([path])
    except Exception as exc:  # noqa: BLE001
        message = str(exc).lower()
        if "proxy" in message:
            headers = _storage_headers()
            # Try direct object delete first.
            delete_url = (
                f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/"
                f"{quote(bucket, safe='')}/{quote(path, safe='/')}"
            )
            response = httpx.delete(delete_url, headers=headers, timeout=20.0)
            if response.status_code in {200, 204}:
                return True
            if response.status_code == 404:
                return False

            # Fallback for API variants that require batch remove endpoint.
            remove_url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{quote(bucket, safe='')}"
            response = httpx.delete(
                remove_url,
                headers=headers,
                json={"prefixes": [path]},
                timeout=20.0,
            )
            if response.status_code in {200, 204}:
                return True
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
        if "not found" in message or "no such file" in message:
            return False
        raise
    return True


def download_object_bytes(bucket: str, path: str) -> bytes:
    try:
        client = get_supabase_storage_client()
        storage = client.storage.from_(bucket)
        data = storage.download(path)
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        if isinstance(data, memoryview):
            return data.tobytes()
    except Exception as exc:  # noqa: BLE001
        message = str(exc).lower()
        if "proxy" not in message:
            raise

    headers = _storage_headers()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{quote(bucket, safe='')}/{quote(path, safe='/')}"
    response = httpx.get(url, headers=headers, timeout=60.0)
    if response.status_code >= 400:
        raise ValueError(f"Supabase storage download failed ({response.status_code}): {response.text}")
    return response.content
