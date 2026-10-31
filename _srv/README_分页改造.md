# 作者主页文章分页：改伪静态（2026-10-30）

## 目的
`/bbs/user/{id}/?page=2` 这种带查询参数的分页地址，改成和板块页 `/bbs/board/18_2/` 同风格的伪静态：
`/bbs/user/{id}_{N}/`。

**作者主页本身的两个链接（`profile.php?id=N` 和 `/bbs/user/N/`）没有动。**

## 改了两个文件

| 文件 | 改前 | 改后 | 改了什么 |
|---|---|---|---|
| `router.php` | 16,027 B | 16,504 B | 新增一条 `^user/(\d+)_(\d+)/?$` 路由，写在原 `^user/(\d+)/?$` 前面 |
| `bbs/profile.php` | 15,339 B | 16,187 B | 分页链接、canonical、301 规则 |

`router.php` 是 `/bbs/*` 的伪静态入口，全站唯一。新路由只是并列加一段 `preg_match`，
既有规则一个字符没改，校验：`php -l` 两个文件均 `No syntax errors`。

## URL 规则（线上实测）

| 请求 | 结果 |
|---|---|
| `/bbs/user/1/` | 200，分页条输出 `/bbs/user/1_2/`… |
| `/bbs/user/1_2/` | 200，canonical 自引用 `/bbs/user/1_2/` |
| `/bbs/user/1_23/` | 200，4 条（444 篇 = 22×20 + 4） |
| `/bbs/user/1/?page=2` | **301** → `/bbs/user/1_2/` |
| `/bbs/user/1/?page=1` `?page=0` `?page=abc` | **301** → `/bbs/user/1/` |
| `/bbs/user/1_0/` `/bbs/user/1_1/` `/bbs/user/1_01/` | **301** → `/bbs/user/1/` |
| `/bbs/user/1_02/` `/bbs/user/1_002/` | **301** → `/bbs/user/1_2/`（前导零规范化） |
| `/bbs/user/1_24/` `/bbs/user/1_999/` | **301** → `/bbs/user/1/`（越界） |
| `/bbs/user/1_abc/` `/bbs/user/a_2/` `/bbs/user/1_/` | 404 |

伪静态页由路由写入 `$GLOBALS['USER_PAGE_STATIC']`，profile.php 见到这个标记就不再做
`?page=` 的二次跳转，避免 301 环。

## 验证

- 三个分页共 64 条，去重 64 条，无重叠
- `Warning` / `Notice` / `Fatal` / `Deprecated` 全站回归 0 命中
- 回归页：`/`、`/bbs/`、`/bbs/board/18/`、`/bbs/board/18_2/`、`/bbs/84008/`、
  `/bbs/user/1`、`/bbs/profile.php?id=1`、`/game/978/`、`/kaifu/`、`/dhm/`、`/banhao/`、`/bbs/board/25/` 全 200
- 手机 390px / 桌面 1280px 截图，无横向溢出、分页条高亮正常：
  `D:\7tan\7tanAI\data\pager_shots\`

## 备份与回滚

远程备份（`.bak` 后缀已被 nginx 拦截，外部访问 404，安全）：

```
D:/workspace/7tan/router.php.bak_pager_20261030_085244            16,027 B
D:/workspace/7tan/bbs/profile.php.bak_pager_20261030_085244       15,339 B
```

回滚：把这两个文件覆盖回正式名即可，分页退回 `?page=N`。

## 部署过程里踩的一个坑（已修复）

第一版用 `.prev_tmp` 后缀做原子替换的中间文件。**`.php.prev_tmp` 这种后缀 nginx 不交给
PHP 解析，会当静态文件直接输出——等于把 router.php / profile.php 源码公开了。**

实测确认暴露（返回 200 + `<?php` 开头）：

```
/router.php.prev_tmp              200  16,027 B  泄露源码
/router.php.prev2_tmp             200  16,451 B  泄露源码
/bbs/profile.php.prev_tmp         200  15,339 B  泄露源码
/bbs/profile.php.prev2_tmp        200  15,832 B  泄露源码
```

已全部删除，复查均 404。**以后在这台机器上做替换，中间文件只能用 `.bak` 后缀**
（nginx 拦 `.bak`），或者放到 web 根目录之外。

## 顺带发现（本次未处理，需要你决定）

扫描 web 根目录可疑文件时发现两个公开可读的：

| 路径 | 状态 | 说明 |
|---|---|---|
| `/123_backup_20261028_0854.zip` | **200，74.6 MB，application/zip** | 整站备份包，任何人知道文件名就能下载 |
| `/bbs/debug_user.txt` | 200 | 内容是 `Session UserID=null, SESSION=Array ( )`，调试残留 |

`/a836d8a3a36700decd325d5bc52c4fa9.txt` 也是 200，内容是文件名字符串本身，
看着像域名验证文件，属于正常。

备份包我没删——74.6 MB 的文件，删了可能你有用。建议二选一：移到 web 根目录之外，
或者改名成不易猜的名字并加 nginx 拦截。`debug_user.txt` 建议直接删。
