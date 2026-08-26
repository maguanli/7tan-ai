# -*- coding: utf-8 -*-
"""
爆款写作插件 — 授权码签发工具（作者专用，勿随插件分发）

用法:
  python data/plugins/viral_writer/gen_license.py            # 为本机生成授权码
  python data/plugins/viral_writer/gen_license.py <指纹>     # 为指定机器指纹生成授权码

说明:
  - 依赖本插件目录下的 private_key.pem（私钥，绝不要公开/提交 git）
  - 授权码格式: 指纹.签名（RSA-2048 / SHA-256）
  - 发给用户后，用户用 viral_activate 输入即可激活
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from license import gen_license, get_fingerprint  # noqa: E402


def main():
    fp = sys.argv[1] if len(sys.argv) > 1 else get_fingerprint()
    try:
        key = gen_license(fp)
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)
    print("=" * 50)
    print("授权码（发给用户，用户用 viral_activate 激活）:")
    print("=" * 50)
    print(key)
    print("=" * 50)
    print(f"机器指纹: {fp}")


if __name__ == "__main__":
    main()
