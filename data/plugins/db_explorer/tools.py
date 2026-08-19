"""
数据库探索器 — 查看项目数据库结构、执行查询、生成 ORM 模型
支持 SQLite、MySQL、PostgreSQL
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool
import os
import sqlite3


@register_tool(
    name="explore_db",
    description="探索 SQLite/MySQL/PostgreSQL 数据库：列出所有表、查看表结构、显示行数。自动检测项目中的 .db/.sqlite 文件。",
    parameters={
        "type": "object",
        "properties": {
            "db_path": {"type": "string", "description": "数据库文件路径或连接字符串。SQLite: .db文件路径；MySQL: mysql://user:pass@host/db；PostgreSQL: postgresql://user:pass@host/db", "default": ""},
            "project_root": {"type": "string", "description": "项目根目录（自动搜索 .db 文件）", "default": "."},
        },
        "required": []
    },
    category="db"
)
def explore_db(db_path: str = "", project_root: str = ".") -> str:
    """探索数据库"""
    # 自动检测 SQLite 文件
    if not db_path:
        import glob
        candidates = glob.glob(os.path.join(project_root, "**/*.db"), recursive=True) + \
                     glob.glob(os.path.join(project_root, "**/*.sqlite"), recursive=True) + \
                     glob.glob(os.path.join(project_root, "**/*.sqlite3"), recursive=True)
        candidates = [c for c in candidates if "node_modules" not in c and "__pycache__" not in c]
        if not candidates:
            return "未在项目中找到 .db/.sqlite 文件。请手动指定 db_path 或连接字符串。"
        db_path = candidates[0]

    # SQLite 处理
    if db_path.endswith((".db", ".sqlite", ".sqlite3")):
        return _explore_sqlite(db_path)

    # MySQL/PostgreSQL 连接字符串
    if "://" in db_path:
        return _explore_url(db_path)

    return f"不支持的数据库格式: {db_path}"


def _explore_sqlite(path: str) -> str:
    """探索 SQLite"""
    if not os.path.isfile(path):
        return f"数据库文件不存在: {path}"
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]

        results = [f"📊 SQLite: {os.path.basename(path)} ({os.path.getsize(path)/1024:.0f}KB)",
                   f"   表: {len(tables)} 个\n"]

        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM [{table}]")
                count = cur.fetchone()[0]
                cur.execute(f"PRAGMA table_info([{table}])")
                cols = cur.fetchall()
                results.append(f"  📋 {table} ({count} 行, {len(cols)} 列)")
                for col in cols[:8]:  # cid, name, type, notnull, default, pk
                    pk = "🔑" if col[5] else "  "
                    nn = " NOT NULL" if col[3] else ""
                    results.append(f"     {pk} {col[1]:25s} {col[2]:10s}{nn}")
                if len(cols) > 8:
                    results.append(f"     ... 还有 {len(cols)-8} 列")
                results.append("")
            except Exception as e:
                results.append(f"  ⚠️ {table}: 读取失败 ({e})")

        conn.close()
        return "\n".join(results)
    except Exception as e:
        return f"SQLite 连接失败: {e}"


def _explore_url(url: str) -> str:
    """探索远程数据库"""
    try:
        import urllib.parse as up
        parsed = up.urlparse(url)
        scheme = parsed.scheme
        results = [f"📊 {scheme.upper()} 数据库: {parsed.hostname}/{parsed.path.lstrip('/')}"]

        if scheme == "mysql":
            try:
                import pymysql
                conn = pymysql.connect(
                    host=parsed.hostname, port=parsed.port or 3306,
                    user=parsed.username, password=parsed.password or "",
                    database=parsed.path.lstrip("/"))
                cur = conn.cursor()
                cur.execute("SHOW TABLES")
                tables = [r[0] for r in cur.fetchall()]
                results.append(f"   表: {len(tables)} 个")
                for t in tables[:20]:
                    cur.execute(f"SELECT COUNT(*) FROM `{t}`")
                    count = cur.fetchone()[0]
                    cur.execute(f"DESCRIBE `{t}`")
                    cols = cur.fetchall()
                    results.append(f"  📋 {t} ({count} 行, {len(cols)} 列)")
                    for col in cols[:5]:
                        results.append(f"     {col[0]:20s} {col[1]:15s}")
                conn.close()
            except ImportError:
                results.append("  ⚠️ 未安装 pymysql: pip install pymysql")
            except Exception as e:
                results.append(f"  ❌ 连接失败: {e}")

        elif scheme in ("postgresql", "postgres"):
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=parsed.hostname, port=parsed.port or 5432,
                    user=parsed.username, password=parsed.password or "",
                    dbname=parsed.path.lstrip("/"))
                cur = conn.cursor()
                cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
                tables = [r[0] for r in cur.fetchall()]
                results.append(f"   表: {len(tables)} 个")
                for t in tables[:20]:
                    cur.execute(f"SELECT count(*) FROM \"{t}\"")
                    count = cur.fetchone()[0]
                    cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{t}'")
                    cols = cur.fetchall()
                    results.append(f"  📋 {t} ({count} 行, {len(cols)} 列)")
                conn.close()
            except ImportError:
                results.append("  ⚠️ 未安装 psycopg2: pip install psycopg2")
            except Exception as e:
                results.append(f"  ❌ 连接失败: {e}")

        return "\n".join(results)
    except Exception as e:
        return f"连接解析失败: {e}"


@register_tool(
    name="query_db",
    description="对 SQLite 数据库执行 SQL 查询（仅 SELECT，安全只读）。支持自动检测项目中的数据库文件。",
    parameters={
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "SELECT 查询语句"},
            "db_path": {"type": "string", "description": "数据库文件路径（可选，不填则自动查找）", "default": ""},
            "project_root": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": ["sql"]
    },
    category="db"
)
def query_db(sql: str, db_path: str = "", project_root: str = ".") -> str:
    """执行 SQL 查询"""
    if not sql.strip().upper().startswith("SELECT"):
        return "⚠️ 仅支持 SELECT 查询（安全限制）"

    if not db_path:
        import glob
        candidates = glob.glob(os.path.join(project_root, "**/*.db"), recursive=True)
        candidates = [c for c in candidates if "node_modules" not in c]
        if not candidates:
            return "未找到数据库文件"
        db_path = candidates[0]

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        conn.close()

        if not rows:
            return "查询结果为空"

        # 格式化输出
        lines = [f"📊 {len(rows)} 行 x {len(cols)} 列"]
        if cols:
            lines.append(" | ".join(cols))
            lines.append("-" * 60)
        for row in rows[:50]:
            lines.append(" | ".join(str(v)[:60] for v in row))
        if len(rows) > 50:
            lines.append(f"... 还有 {len(rows)-50} 行")
        return "\n".join(lines)
    except Exception as e:
        return f"查询失败: {e}"


@register_tool(
    name="generate_model",
    description="根据数据库表结构生成 Python SQLAlchemy ORM 模型代码。",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "表名（不填则为所有表生成）", "default": ""},
            "db_path": {"type": "string", "description": "SQLite 数据库文件路径", "default": ""},
            "project_root": {"type": "string", "description": "项目根目录", "default": "."},
        },
        "required": []
    },
    category="db"
)
def generate_model(table_name: str = "", db_path: str = "",
                   project_root: str = ".") -> str:
    """生成 ORM 模型"""
    if not db_path:
        import glob
        candidates = glob.glob(os.path.join(project_root, "**/*.db"), recursive=True)
        candidates = [c for c in candidates if "node_modules" not in c]
        if not candidates:
            return "未找到数据库文件"
        db_path = candidates[0]

    type_map = {"INTEGER": "int", "TEXT": "str", "REAL": "float",
                "BLOB": "bytes", "NUMERIC": "float", "BOOLEAN": "bool",
                "DATETIME": "datetime", "VARCHAR": "str", "INT": "int"}

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]

        if table_name and table_name not in tables:
            return f"表 '{table_name}' 不存在。可用: {', '.join(tables)}"

        target = [table_name] if table_name and table_name in tables else tables
        lines = ["from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, create_engine",
                 "from sqlalchemy.orm import declarative_base",
                 "from datetime import datetime\n",
                 "Base = declarative_base()\n"]

        for t in target:
            class_name = "".join(w.capitalize() for w in t.split("_"))
            cur.execute(f"PRAGMA table_info([{t}])")
            cols = cur.fetchall()

            lines.append(f"\nclass {class_name}(Base):")
            lines.append(f'    __tablename__ = "{t}"\n')
            for col in cols:
                name = col[1]
                col_type = col[2].upper().split("(")[0]
                py_type = type_map.get(col_type, "str")
                is_pk = "primary_key=True" if col[5] else ""
                nullable = "" if col[3] else ", nullable=True"
                parts = [f"Column({py_type}"]
                if is_pk:
                    parts.append(is_pk)
                if nullable:
                    parts.append(nullable.strip(", "))
                lines.append(f"    {name} = {', '.join(parts)})")

        conn.close()
        return "\n".join(lines)
    except Exception as e:
        return f"生成失败: {e}"
