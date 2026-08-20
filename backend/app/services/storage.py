import asyncio
from functools import lru_cache

import boto3
from botocore.config import Config

from app.config import settings


@lru_cache
def client():
    return boto3.client("s3", endpoint_url=settings.s3_endpoint_url, aws_access_key_id=settings.s3_access_key,
                        aws_secret_access_key=settings.s3_secret_key, region_name=settings.s3_region,
                        config=Config(s3={"addressing_style": "path" if settings.s3_force_path_style else "auto"}))


@lru_cache
def signing_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_public_endpoint_url or settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(s3={"addressing_style": "path" if settings.s3_force_path_style else "auto"}),
    )


async def put_bytes(key: str, data: bytes, content_type: str) -> None:
    await asyncio.to_thread(client().put_object, Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type)


async def get_bytes(key: str) -> bytes:
    response = await asyncio.to_thread(client().get_object, Bucket=settings.s3_bucket, Key=key)
    return await asyncio.to_thread(response["Body"].read)


async def delete_key(key: str) -> None:
    await asyncio.to_thread(client().delete_object, Bucket=settings.s3_bucket, Key=key)


def signed_get_url(key: str) -> str:
    return signing_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=settings.signed_url_ttl_seconds,
    )
