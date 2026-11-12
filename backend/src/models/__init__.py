"""ORM 模型聚合导出（Base 用于 create_all）。"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from src.models.user import User  # noqa: E402
from src.models.feed import Feed  # noqa: E402
from src.models.episode import Episode  # noqa: E402
from src.models.chapter import Chapter  # noqa: E402
from src.models.digest_task import DigestTask  # noqa: E402
from src.models.chapter_issue import ChapterIssue  # noqa: E402
from src.models.audit import AuditLog  # noqa: E402

__all__ = [
    "Base",
    "User",
    "Feed",
    "Episode",
    "Chapter",
    "DigestTask",
    "ChapterIssue",
    "AuditLog",
]
