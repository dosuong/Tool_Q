"""Kết nối Postgres (Supabase) qua SQLAlchemy. Nếu chưa cấu hình secrets (vd
lúc mới tải code về, chưa tạo project Supabase), tự rơi về 1 file SQLite cục
bộ để vẫn chạy/test được app — CHỈ dùng cho phát triển, không phù hợp triển
khai thật (dữ liệu SQLite nằm trên đĩa cục bộ, mất khi đổi máy/deploy lại).
"""
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from online_exam.db_models import Base

_DEV_SQLITE_URL = "sqlite:///online_exam_dev.db"


def _get_db_url() -> str:
    try:
        return st.secrets["database"]["url"]
    except Exception:
        return _DEV_SQLITE_URL


@st.cache_resource(show_spinner=False)
def get_engine():
    db_url = _get_db_url()
    is_sqlite = db_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine_kwargs = {"pool_pre_ping": True, "connect_args": connect_args}
    if not is_sqlite:
        # Kích thước pool tường minh cho Postgres qua pooler Supabase (cổng 6543) — mặc định
        # của SQLAlchemy (pool_size=5, max_overflow=10) dễ nghẽn khi ~50 HS thao tác đồng thời
        # trong 1 lớp thi, vì toàn bộ session Streamlit trong CÙNG 1 process chia sẻ chung 1
        # engine (cache qua st.cache_resource) nên chia sẻ chung pool này.
        engine_kwargs.update(pool_size=10, max_overflow=20, pool_recycle=300)
    engine = create_engine(db_url, **engine_kwargs)
    Base.metadata.create_all(engine)
    return engine


def get_session() -> Session:
    session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return session_factory()


def using_dev_sqlite() -> bool:
    return _get_db_url() == _DEV_SQLITE_URL
