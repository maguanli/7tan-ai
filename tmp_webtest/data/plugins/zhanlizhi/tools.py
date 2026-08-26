"""
战力值插件 — 记录、查看、刷新战力值数据
数据保存到软件 SQLite 数据库，支持刷新重新加载
"""
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.tools.registry import register_tool

# 数据库路径
DB_PATH = ROOT / "data" / "zhanlizhi.db"


def _get_conn():
    """获取数据库连接"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    """初始化数据库表"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS zhanlizhi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            value INTEGER NOT NULL DEFAULT 0,
            category TEXT DEFAULT '默认',
            remark TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# 初始化数据库
_init_db()


@register_tool(
    name="zhanlizhi_add",
    description="添加战力值记录。输入名称和战力值，可选分类和备注。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "角色/玩家名称"},
            "value": {"type": "integer", "description": "战力值数值"},
            "category": {"type": "string", "description": "分类（如：战士、法师、公会等）", "default": "默认"},
            "remark": {"type": "string", "description": "备注信息", "default": ""}
        },
        "required": ["name", "value"]
    },
    category="custom"
)
def zhanlizhi_add(name: str, value: int, category: str = "默认", remark: str = "") -> str:
    """添加战力值记录"""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO zhanlizhi (name, value, category, remark, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name, value, category, remark, now, now)
        )
        conn.commit()
        record_id = cur.lastrowid
        conn.close()
        return f"✅ 添加成功！\n   ID: {record_id}\n   名称: {name}\n   战力值: {value:,}\n   分类: {category}\n   备注: {remark or '无'}\n   时间: {now}"
    except Exception as e:
        return f"❌ 添加失败: {e}"


@register_tool(
    name="zhanlizhi_list",
    description="查看所有战力值记录，支持按分类筛选和排序。",
    parameters={
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "按分类筛选（留空显示全部）", "default": ""},
            "sort_by": {"type": "string", "description": "排序方式: value_desc(战力降序)/value_asc(战力升序)/time_desc(最新)/time_asc(最早)", "default": "value_desc"},
            "limit": {"type": "integer", "description": "显示数量限制", "default": 50}
        },
        "required": []
    },
    category="custom"
)
def zhanlizhi_list(category: str = "", sort_by: str = "value_desc", limit: int = 50) -> str:
    """查看战力值列表"""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        
        # 构建查询
        sql = "SELECT * FROM zhanlizhi"
        params = []
        if category:
            sql += " WHERE category = ?"
            params.append(category)
        
        # 排序
        sort_map = {
            "value_desc": "value DESC",
            "value_asc": "value ASC",
            "time_desc": "updated_at DESC",
            "time_asc": "updated_at ASC"
        }
        sql += f" ORDER BY {sort_map.get(sort_by, 'value DESC')}"
        sql += " LIMIT ?"
        params.append(limit)
        
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            return "📭 暂无战力值记录"
        
        # 统计
        total = len(rows)
        total_value = sum(r["value"] for r in rows)
        avg_value = total_value // total if total else 0
        max_value = max(r["value"] for r in rows) if rows else 0
        
        lines = [
            f"⚔️ 战力值排行榜 (共 {total} 条记录)",
            f"   总战力: {total_value:,} | 平均: {avg_value:,} | 最高: {max_value:,}",
            ""
        ]
        
        for i, row in enumerate(rows, 1):
            medal = ""
            if i == 1: medal = "🥇 "
            elif i == 2: medal = "🥈 "
            elif i == 3: medal = "🥉 "
            else: medal = f"{i:2d}. "
            
            lines.append(
                f"{medal}{row['name']:12s} | 战力: {row['value']:>10,} | "
                f"分类: {row['category']:8s} | 更新: {row['updated_at'][:16]}"
            )
            if row['remark']:
                lines.append(f"      └─ 备注: {row['remark']}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 查询失败: {e}"


@register_tool(
    name="zhanlizhi_update",
    description="更新指定名称的战力值。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "要更新的角色/玩家名称"},
            "value": {"type": "integer", "description": "新的战力值"},
            "remark": {"type": "string", "description": "新备注（可选）", "default": ""}
        },
        "required": ["name", "value"]
    },
    category="custom"
)
def zhanlizhi_update(name: str, value: int, remark: str = "") -> str:
    """更新战力值"""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查是否存在
        cur.execute("SELECT id, value FROM zhanlizhi WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return f"❌ 未找到名称: {name}"
        
        old_value = row["value"]
        
        # 更新
        if remark:
            cur.execute(
                "UPDATE zhanlizhi SET value = ?, remark = ?, updated_at = ? WHERE name = ?",
                (value, remark, now, name)
            )
        else:
            cur.execute(
                "UPDATE zhanlizhi SET value = ?, updated_at = ? WHERE name = ?",
                (value, now, name)
            )
        
        conn.commit()
        conn.close()
        
        change = value - old_value
        change_str = f"+{change:,}" if change > 0 else f"{change:,}"
        return (
            f"✅ 更新成功！\n"
            f"   名称: {name}\n"
            f"   原战力: {old_value:,}\n"
            f"   新战力: {value:,}\n"
            f"   变化: {change_str}\n"
            f"   时间: {now}"
        )
    except Exception as e:
        return f"❌ 更新失败: {e}"


@register_tool(
    name="zhanlizhi_delete",
    description="删除指定名称的战力值记录。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "要删除的角色/玩家名称"}
        },
        "required": ["name"]
    },
    category="custom"
)
def zhanlizhi_delete(name: str) -> str:
    """删除战力值记录"""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, value FROM zhanlizhi WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return f"❌ 未找到名称: {name}"
        
        cur.execute("DELETE FROM zhanlizhi WHERE name = ?", (name,))
        conn.commit()
        conn.close()
        return f"✅ 已删除: {name} (原战力: {row['value']:,})"
    except Exception as e:
        return f"❌ 删除失败: {e}"


@register_tool(
    name="zhanlizhi_search",
    description="搜索战力值记录，支持模糊匹配名称。",
    parameters={
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "搜索关键词"}
        },
        "required": ["keyword"]
    },
    category="custom"
)
def zhanlizhi_search(keyword: str) -> str:
    """搜索战力值"""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM zhanlizhi WHERE name LIKE ? OR category LIKE ? OR remark LIKE ? ORDER BY value DESC",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%")
        )
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            return f"🔍 未找到匹配 '{keyword}' 的记录"
        
        lines = [f"🔍 搜索 '{keyword}' 结果 ({len(rows)} 条):", ""]
        for i, row in enumerate(rows, 1):
            lines.append(
                f"{i:2d}. {row['name']:12s} | 战力: {row['value']:>10,} | "
                f"分类: {row['category']} | 备注: {row['remark'] or '无'}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 搜索失败: {e}"


@register_tool(
    name="zhanlizhi_refresh",
    description="刷新战力值数据，重新从数据库加载最新记录。相当于刷新按钮功能。",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    category="custom"
)
def zhanlizhi_refresh() -> str:
    """刷新战力值数据（重新加载）"""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        
        # 获取统计信息
        cur.execute("SELECT COUNT(*) as cnt, SUM(value) as total, AVG(value) as avg, MAX(value) as max FROM zhanlizhi")
        stats = cur.fetchone()
        
        # 获取分类统计
        cur.execute("SELECT category, COUNT(*) as cnt, SUM(value) as total FROM zhanlizhi GROUP BY category ORDER BY total DESC")
        categories = cur.fetchall()
        
        # 获取最新记录
        cur.execute("SELECT * FROM zhanlizhi ORDER BY updated_at DESC LIMIT 5")
        recent = cur.fetchall()
        
        conn.close()
        
        cnt = stats["cnt"] or 0
        total = stats["total"] or 0
        avg = int(stats["avg"] or 0)
        max_v = stats["max"] or 0
        
        lines = [
            "🔄 战力值数据已刷新！",
            f"   刷新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"📊 数据统计:",
            f"   总记录数: {cnt}",
            f"   总战力值: {total:,}",
            f"   平均战力: {avg:,}",
            f"   最高战力: {max_v:,}",
            ""
        ]
        
        if categories:
            lines.append("📁 分类统计:")
            for cat in categories:
                lines.append(f"   {cat['category'] or '未分类':10s}: {cat['cnt']:3d} 人 | 总战力 {cat['total']:,}")
            lines.append("")
        
        if recent:
            lines.append("🕐 最近更新:")
            for row in recent:
                lines.append(f"   {row['name']:12s} | 战力 {row['value']:>10,} | {row['updated_at'][:16]}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 刷新失败: {e}"


@register_tool(
    name="zhanlizhi_export",
    description="导出所有战力值数据为 JSON 格式。",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    category="custom"
)
def zhanlizhi_export() -> str:
    """导出战力值数据"""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM zhanlizhi ORDER BY value DESC")
        rows = cur.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                "id": row["id"],
                "name": row["name"],
                "value": row["value"],
                "category": row["category"],
                "remark": row["remark"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })
        
        return f"📤 导出数据 ({len(data)} 条):\n\n```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```"
    except Exception as e:
        return f"❌ 导出失败: {e}"


@register_tool(
    name="zhanlizhi_clear",
    description="清空所有战力值记录（危险操作，请确认后执行）。",
    parameters={
        "type": "object",
        "properties": {
            "confirm": {"type": "boolean", "description": "确认清空，必须设为 true", "default": False}
        },
        "required": ["confirm"]
    },
    category="custom"
)
def zhanlizhi_clear(confirm: bool = False) -> str:
    """清空所有战力值记录"""
    if not confirm:
        return "⚠️ 危险操作！请设置 confirm=True 确认清空所有战力值记录。"
    
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM zhanlizhi")
        cnt = cur.fetchone()["cnt"]
        cur.execute("DELETE FROM zhanlizhi")
        conn.commit()
        conn.close()
        return f"✅ 已清空 {cnt} 条战力值记录"
    except Exception as e:
        return f"❌ 清空失败: {e}"
