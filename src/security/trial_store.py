"""
试用模式 — 从 JWT Token 读取 AI 试用次数（服务端权威）
服务端 MySQL 计次，客户端只读不决策。

API:
    get_trials_left()  → 从本地 Token 的 JWT payload 读取 trial_ai_count
    has_trials()       → trial_ai_count > 0 ?
"""
from .token_store import load_token


MAX_TRIALS = 3  # 仅用于 UI 文案显示默认值


def get_trials_left() -> int:
    """
    从本地 Token 读取 AI 试用剩余次数。

    注意：此值是上次登录时从服务端获取的快照。
    实际扣减在服务端 trial.php 中执行，客户端只作展示用。
    如果值 > 0 但服务端已用完，trial.php 返回 402 并告知。

    Returns:
        剩余试用次数（0 = 已用完/未登录/读取失败）
    """
    token_data = load_token()
    if not token_data:
        return 0
    return token_data.get("trial_ai_count", 0)


def has_trials() -> bool:
    """是否还有试用次数"""
    return get_trials_left() > 0


def use_trial() -> int:
    """
    消耗一次试用（仅作客户端展示更新，实际扣次在服务端）。

    Returns:
        剩余次数（客户端估计值）
    """
    current = get_trials_left()
    if current <= 0:
        return 0
    return current - 1
