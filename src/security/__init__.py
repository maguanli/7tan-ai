"""
安全模块 — 完整性验证 + 许可证管理 + 安全修改门控 + 认证客户端
"""
from .integrity import generate_integrity_file, verify_integrity, check_security
from .license_verify import (
    verify_license,
    is_pro,
    get_license_info,
    LicenseError,
    LicenseExpired,
    LicenseInvalid,
    LicenseNotPro,
)
from .safe_modify import (
    pre_modify_check,
    restore_latest_backup,
    restore_all_from_backup,
    can_modify_self,
    check_write_permission,
    get_backup_count,
    ModifyRejected,
)
from .rsa_verify import rsa_verify
from .strings import get_public_key, get_api_url
from .auth_client import login, online_verify, refresh_token, LoginFailed, NetworkError, ServerError
from .token_store import save_token, load_token, clear_token, is_token_available
from .trial_store import get_trials_left, use_trial, has_trials, MAX_TRIALS
