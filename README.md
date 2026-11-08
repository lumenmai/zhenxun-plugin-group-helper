# 群聊管理

为真寻机器人提供群成员禁言、解除禁言和踢人命令，支持分钟、天数形式的禁言时间，踢人操作需要二次确认。

## 运行环境

- Python 3.10 或更高版本。
- 已正常运行的[绪山真寻](https://github.com/zhenxun-org/zhenxun_bot)项目。
- NoneBot2 和 OneBot V11 适配器。
- 机器人在目标群拥有管理员或群主身份，协议端支持群成员信息查询、禁言和踢人接口。

插件使用真寻的配置、插件元数据和菜单接口；普通 NoneBot 项目需要先提供对应宿主接口。

## 安装

可以直接将插件目录放入真寻的 `zhenxun/plugins/`，安装依赖后重启，**不需要配置 `EXT_PATH`**。

下载本仓库后，将其中的 `group_helper/` 文件夹复制到 `zhenxun/plugins/`。复制的是插件文件夹，不是整个仓库，最终结构应为：

```text
zhenxun/
└── plugins/
    └── group_helper/
        └── __init__.py
```

也可以在真寻项目根目录执行以下命令，仓库会克隆到真寻项目的同级目录：

```bash
git clone https://github.com/lumenmai/zhenxun-plugin-group-helper.git ../zhenxun-plugin-group-helper
uv pip install -r ../zhenxun-plugin-group-helper/requirements.txt
cp -R ../zhenxun-plugin-group-helper/group_helper zhenxun/plugins/
```

依赖应安装到运行真寻的虚拟环境中。完成后重启真寻，检查“群聊管理”是否加载成功。

如果已有同名插件，先备份旧目录，再用新的插件目录替换，保留原有运行数据；同一插件只保留一种加载方式，避免重复加载。

## 命令

在群内使用以下命令，命令前缀以真寻的 `COMMAND_START` 设置为准：

| 命令 | 作用 |
|---|---|
| `mute @用户` | 禁言 1 分钟 |
| `mute @用户 5` | 禁言 5 分钟 |
| `mute @用户 5m` | 禁言 5 分钟 |
| `mute @用户 5d` | 禁言 5 天 |
| `unmute @用户` | 解除禁言 |
| `kick @用户` | 发起踢人操作，等待二次确认 |

时间必须为正整数，后缀 `m`、`d` 不区分大小写；最终可执行的时长以 QQ 平台及协议端允许范围为准。目标必须通过 @ 指定；多次 @ 时取首个有效用户。

发起 `kick` 后，回复“是”“好”“确定”或“确定是”继续，其他回复取消。确认时会再次检查目标和操作权限，成功踢出时不设置禁止再次申请入群。

## 权限与行为

- 仅处理群消息，群主、管理员或超级用户可触发命令。
- 操作前会查询机器人的群身份；机器人不是管理员或群主时，不执行操作。
- 普通管理员只能操作普通成员，不能操作管理员或群主。
- 群主或超级用户通过插件权限检查后，实际操作仍受机器人自身权限和 QQ 协议端限制。
- 未指定有效 @ 时提示用法；权限查询失败或操作接口失败时静默结束。成功禁言、解除禁言和踢人不额外发送成功消息。

插件不创建数据库或额外配置文件，使用真寻的超级用户和机器人昵称设置。

## 作者与许可

作者：[lumen](https://github.com/lumenmai)。使用 [MIT License](LICENSE)。
