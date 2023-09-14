from datetime import datetime


def serialize_datetime(dt: datetime) -> str:
    return dt.isoformat()


def deserialize_datetime(fmt: str) -> datetime:
    return datetime.fromisoformat(fmt)
