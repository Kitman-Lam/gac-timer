# 规格说明（Spec）：会帮手 — Windows会议议题分段计时器

## 1. 背景与目标

### 1.1 背景

在日常办公会议中，普遍存在以下痛点：
- 会议超时严重，各议题缺乏精准的时间管控手段
- 汇报与答疑时长混乱，QA环节经常挤占后续议题时间
- 会议结束后无数据复盘能力，无法量化分析时间分配效率
- PPT全屏演示时无法同时查看计时信息，主持人需频繁切换窗口

### 1.2 业务目标

- 提供一款Windows桌面端会议专用计时器，精准管控会议各议题的计划用时与实际用时
- 实现PPT全屏放映时的顶层悬浮计时展示，消除窗口切换干扰
- 会议结束后自动生成完整时长统计报表，支持数据导出与历史复盘

### 1.3 用户/涉众目标

- **会议主持人**：精准控制每个议题每个阶段的用时，实时掌握超时情况，灵活调整会议节奏
- **汇报人**：直观查看当前阶段剩余时间，合理控制汇报节奏
- **会议组织者**：会后获取完整时间统计数据，用于会议效率分析与改进

## 2. 需求类型概览

| 类型          | 是否适用 | 依据（来源）            |
| ------------- | -------- | ----------------------- |
| 业务需求      | 是       | 任务描述：解决会议超时、时长混乱、无数据复盘问题 |
| 用户/涉众需求 | 是       | 任务描述：主持人精准管控、汇报人查看时间、组织者数据复盘 |
| 解决方案需求  | 是       | 分析结果：Windows桌面应用 + 双阶段计时引擎 + PPT置顶悬浮 |
| 功能需求      | 是       | Spec第3章：FR-001 ~ FR-012 |
| 非功能需求    | 是       | Spec第4章：NFR-001 ~ NFR-006 |
| 外部接口需求  | 是       | Spec第5章：Win32 API / 文件系统 / 音频 |
| 过渡需求      | 否       | 全新产品，无迁移需求 |

## 3. 功能需求

### FR-001：会议创建与议题配置

- **描述**：系统必须支持用户创建一场新会议，自主添加、删除、编辑多个会议议题，每个议题支持自定义名称。
- **验收标准**：
  - 可创建新会议并设置会议名称
  - 可在会议中添加议题，议题数量无固定上限
  - 可编辑已有议题的名称
  - 可删除已有议题（需二次确认）
  - 议题列表支持拖拽排序调整顺序
  - 新建议题时默认名称为"议题 1"、"议题 2"等（按序号自动递增），用户可编辑修改
  - 议题名称为空时自动恢复为默认名称
- **优先级**：必须（Must）
- **类型映射**：功能需求 / 用户需求
- **来源**：任务描述（二）1. / （三）1.

### FR-002：双阶段计划时长配置

- **描述**：系统必须支持为每个议题单独配置「主讲汇报阶段」和「QA答疑讨论阶段」的计划时长，单位为分钟，最小1分钟，支持整数自定义。
- **验收标准**：
  - 每个议题显示两个独立的时长输入框（主讲/QA）
  - 输入值必须为正整数，最小值为1
  - 非法输入（0、负数、非整数、空值）时给出明确提示
  - 两个阶段的时长独立配置，互不影响
  - 配置完成后可随时修改（会议未开始状态下）
- **优先级**：必须（Must）
- **类型映射**：功能需求
- **来源**：任务描述（二）2. / （三）2.

### FR-003：会议配置模板管理

- **描述**：系统必须支持将会议议题配置保存为模板，并可从历史模板加载配置，避免重复创建。
- **验收标准**：
  - 可将当前会议的议题列表（名称+双阶段时长）保存为模板
  - 模板支持自定义名称
  - 可从模板列表中选择模板加载，自动填充议题配置
  - 可删除已有模板（需二次确认）
  - 模板数据本地持久化存储
- **优先级**：应当（Should）
- **类型映射**：功能需求 / 用户需求
- **来源**：任务描述（二）3.

### FR-004：圆形可视化倒计时器

- **描述**：系统必须采用圆形可视化倒计时器UI，直观展示计时进度，适配桌面悬浮展示形态。
- **验收标准**：
  - 圆形进度环展示当前阶段计时进度
  - 圆环中心显示剩余时间（倒计时模式）或超时时间（正计时模式），格式为 MM:SS
  - 圆环进度与时间数值实时同步，刷新间隔不超过100ms
  - 当前议题名称和阶段名称（主讲/QA）清晰显示
  - 圆形计时器尺寸适配悬浮窗口，默认直径约200像素
- **优先级**：必须（Must）
- **类型映射**：功能需求 / 解决方案需求
- **来源**：任务描述（三）1.

### FR-005：倒计时与超时正计时自动切换

- **描述**：系统必须在计划时长倒计时结束后，自动无缝切换为正计时模式，持续统计超时时长。
- **验收标准**：
  - 启动计时后，按预设计划时长执行倒计时，时间递减
  - 倒计时归零后，自动切换为正计时模式，时间从00:00开始递增
  - 切换过程无需用户任何操作，无延迟、无卡顿
  - 正计时模式下持续累计超时秒数，无上限
  - 系统内部精确记录实际用时（含倒计时阶段用时+正计时超时时长）
- **优先级**：必须（Must）
- **类型映射**：功能需求 / 业务需求
- **来源**：任务描述（二）3. / （三）2. / （三）3.

### FR-006：阶段与议题切换

- **描述**：系统必须支持手动切换当前议题的阶段（主讲→QA），以及切换到下一个议题，所有议题依次完成两个阶段即为整场会议结束。
- **验收标准**：
  - 当前议题主讲阶段结束后，用户可手动切换至QA阶段
  - 当前议题QA阶段结束后，用户可手动切换至下一议题的主讲阶段
  - 支持「上一阶段」操作，可回退到前一阶段（回退后保留该阶段已计时长，从暂停状态恢复）
  - 支持「下一阶段」操作，前进到下一阶段
  - 最后一个议题的QA阶段结束后，标记整场会议完成
  - 阶段切换时，前一阶段的计时数据自动保存
- **优先级**：必须（Must）
- **类型映射**：功能需求
- **来源**：任务描述（三）4.

### FR-007：计时基础操作

- **描述**：系统必须支持全局启停、暂停、重置操作，适配会议临时停顿和节奏调整场景。
- **验收标准**：
  - 「开始」按钮启动当前阶段计时
  - 「暂停」按钮暂停计时，暂停期间时间冻结
  - 「继续」按钮从暂停时刻恢复计时
  - 「重置」按钮将当前阶段计时归零（需二次确认）
  - 暂停状态下按钮文字切换为「继续」，不可重复暂停
  - 重置操作仅影响当前阶段，不影响已完成阶段的数据
- **优先级**：必须（Must）
- **类型映射**：功能需求
- **来源**：任务描述（三）5.

### FR-008：PPT全屏置顶悬浮

- **描述**：计时器窗口必须支持系统顶层置顶，PPT全屏放映时始终悬浮可见，支持半透明模式和自由拖拽。
- **验收标准**：
  - 窗口可设置为系统顶层（TopMost），优先级高于PPT全屏放映窗口
  - PPT全屏幻灯片放映状态下，计时器不被遮挡，全程可见
  - 支持半透明模式，透明度可在10%~100%之间调节
  - 悬浮窗口可自由拖拽至屏幕任意位置
  - 无边框轻量化设计，仅展示核心计时数据
  - 支持在「配置模式」（完整界面）和「悬浮模式」（精简界面）之间切换
  - 窗口位置在软件重启后自动恢复至上次位置
- **优先级**：必须（Must）
- **类型映射**：功能需求 / 解决方案需求
- **来源**：任务描述（四）1. ~ 4.

### FR-009：超时视觉与音效提醒

- **描述**：系统必须在倒计时结束切换正计时时，提供温和的视觉提醒和分级提示音。
- **验收标准**：
  - 倒计时归零切换正计时时，圆环颜色从默认色变为警示色（如红色）
  - 正计时模式下数字高亮显示（如红色加粗）
  - 倒计时最后30秒时，圆环颜色渐变为预警色（如黄色），提前提醒
  - 内嵌3个温和提示音，可在设置中分别开启/关闭：
    1. **剩余X分钟提醒音**：倒计时剩余X分钟时播放（X可配置，默认5分钟）
    2. **时间到提示音**：倒计时归零、切换正计时时播放
    3. **超时X分钟提醒音**：正计时每过X分钟播放一次（X可配置，默认5分钟）
  - 提示音音量温和，不扰民、不突兀
- **优先级**：应当（Should）
- **类型映射**：功能需求 / 用户体验需求
- **来源**：任务描述（四）1.

### FR-010：全局热键支持

- **描述**：系统必须支持自定义全局热键，实现快速启停、重置计时、切换阶段等操作，无需鼠标点击窗口。
- **验收标准**：
  - 支持注册系统级全局热键，即使窗口不在焦点也能响应
  - 默认热键方案：开始/暂停（F5）、重置（F6）、下一阶段（F7）、上一阶段（F8）
  - 用户可在设置中自定义各功能的热键组合
  - 热键冲突时给出提示，不允许重复绑定
  - 支持组合键（如 Ctrl+Alt+X）
- **优先级**：应当（Should）
- **类型映射**：功能需求
- **来源**：任务描述（四）3.

### FR-011：会议数据统计与导出

- **描述**：系统必须在会议结束后自动统计完整时长数据，支持Excel/CSV格式导出。
- **验收标准**：
  - 会议结束后自动生成统计报表，包含：
    - 单议题明细：主讲阶段计划时长、实际用时、超时时长；QA阶段计划时长、实际用时、超时时长
    - 整场会议汇总：总计划时长、总实际耗时、整体超时时长、各议题耗时占比
  - 支持导出为CSV格式文件
  - 支持导出为Excel格式文件（.xlsx）
  - 文件默认命名规则：会议日期+会议名称（如 20260611_项目周会.xlsx）
  - 用户可自定义保存路径
  - 统计数据在软件内可预览
- **优先级**：必须（Must）
- **类型映射**：功能需求 / 业务需求
- **来源**：任务描述（五）1. ~ 3.

### FR-012：历史会议记录管理

- **描述**：系统必须支持本地数据留存，可查看历史所有会议的计时记录，支持单条删除。
- **验收标准**：
  - 所有已完成的会议计时记录自动保存到本地
  - 历史记录列表按时间倒序排列
  - 可查看单条会议记录的详细统计数据
  - 可对历史会议记录重新导出文件
  - 可删除单条会议记录（需二次确认）
  - 会议进行中意外关闭软件时，自动保存当前进度，下次启动可精确恢复到暂停时刻
- **优先级**：必须（Must）
- **类型映射**：功能需求 / 用户需求
- **来源**：任务描述（五）4.

## 4. 非功能需求

### NFR-001：性能与轻量化

- **描述**：软件运行时CPU占用不超过2%，内存占用不超过100MB，不卡顿PPT、视频、投屏等办公软件。
- **测量方式**：在Win10/Win11标准配置（8GB RAM、i5及以上CPU）下，同时运行PPT全屏放映+计时器，使用任务管理器监测资源占用。
- **优先级**：必须（Must）
- **来源**：任务描述（四）2.

### NFR-002：兼容性

- **描述**：软件必须兼容Windows 10（1809及以上）和Windows 11主流版本。
- **测量方式**：在Win10 1809、Win10 22H2、Win11 22H2、Win11 23H2上分别测试安装运行。
- **优先级**：必须（Must）
- **来源**：任务描述（一）

### NFR-003：独立部署

- **描述**：软件为独立exe程序（绿色免安装包），无需依赖第三方插件或运行时环境，可单独运行。
- **测量方式**：在未安装Python的干净Windows系统上双击exe可直接运行。
- **优先级**：必须（Must）
- **来源**：任务描述（一）

### NFR-004：计时精度

- **描述**：计时精度误差不超过±100ms/小时，UI刷新间隔不超过100ms，无可见延迟或卡顿。
- **测量方式**：与系统时钟对比，运行1小时后误差在±100ms以内；UI时间显示与内部计时器偏差不超过100ms。
- **优先级**：必须（Must）
- **来源**：任务描述（三）5. / （四）4.

### NFR-005：数据安全与完整性

- **描述**：会议计时数据本地持久化存储，软件异常退出时数据不丢失，最长丢失时间不超过5秒。
- **测量方式**：在计时过程中强制结束进程，重新启动后检查数据恢复情况。
- **优先级**：必须（Must）
- **来源**：分析推导（反向场景）

### NFR-006：可维护性与可扩展性

- **描述**：代码结构模块化，预留后续功能迭代空间（自定义皮肤、云端同步、多人共享查看等）。
- **测量方式**：代码审查，核心模块（计时引擎、UI、数据层）职责清晰、耦合度低。
- **优先级**：应当（Should）
- **来源**：任务描述（五）4.

## 5. 外部接口需求

### IF-001：Win32窗口管理接口

- **类型**：系统集成
- **端点/入口**：Win32 API - SetWindowPos (WS_EX_TOPMOST) / SetWindowLong (WS_EX_LAYERED) / SetLayeredWindowAttributes
- **交互逻辑**：
  - 调用 SetWindowPos 设置 HWND_TOPMOST 实现窗口置顶
  - 调用 SetLayeredWindowAttributes 设置窗口透明度（Alpha值0~255）
  - 调用 SetWindowLong 去除窗口边框（WS_POPUP样式）
- **错误处理**：API调用失败时降级为普通窗口模式，给出提示
- **来源**：任务描述（四）1. ~ 4.

### IF-002：Win32全局热键接口

- **类型**：系统集成
- **端点/入口**：Win32 API - RegisterHotKey / UnregisterHotKey
- **交互逻辑**：
  - 调用 RegisterHotKey 注册系统级热键
  - 监听 WM_HOTKEY 消息响应热键事件
  - 软件退出时调用 UnregisterHotKey 注销所有热键
- **错误处理**：热键注册失败（已被占用）时提示用户更换热键
- **来源**：任务描述（四）3.

### IF-003：文件系统导出接口

- **类型**：系统集成
- **端点/入口**：本地文件系统写入
- **交互逻辑**：
  - CSV导出：使用Python csv模块写入，UTF-8 BOM编码（兼容Excel中文）
  - Excel导出：使用openpyxl库生成.xlsx文件
  - 文件保存路径通过系统文件对话框选择
- **错误处理**：文件写入失败（权限不足、磁盘满）时给出明确错误提示
- **来源**：任务描述（五）3.

### IF-004：音频播放接口

- **类型**：系统集成
- **端点/入口**：系统音频播放
- **交互逻辑**：
  - 使用QSound或系统API播放提示音
  - 提示音文件内嵌于应用资源中
- **错误处理**：音频设备不可用时静默降级，不影响核心计时功能
- **来源**：任务描述（四）1.

## 6. 过渡需求

不适用（全新产品，无迁移需求）。

## 7. 约束与假设

### 7.1 技术约束

- 开发语言：Python 3.11+
- UI框架：PySide6（Qt for Python）
- 打包工具：PyInstaller，输出单目录绿色免安装包
- 数据存储：SQLite嵌入式数据库
- Excel导出：openpyxl库
- 目标平台：Windows 10 (1809+) / Windows 11
- 不使用Claude.md中定义的FastAPI + Next.js Web技术栈（因需求为原生桌面应用，Web技术栈无法满足PPT置顶、全局热键等系统级功能要求）

### 7.2 业务约束

- 单个议题阶段最小时长为1分钟，无最大时长限制
- 超时正计时无上限，持续累计直到用户手动切换阶段
- 不支持多用户并发或网络协同（单机本地应用）
- 不支持音视频会议集成（仅作为独立计时工具）

### 7.3 假设条件

- 用户电脑已安装Windows 10 1809及以上版本 – 来源：已验证（需求明确）
- 用户显示器分辨率不低于1280x720 – 来源：假设（主流办公显示器标准）
- 用户电脑音频设备可用（提示音功能依赖） – 来源：假设（降级方案：音频不可用时静默）
- 用户具有管理员权限（全局热键注册需要） – 来源：假设（标准办公环境通常具备）

## 8. 优先级与里程碑建议

| 标识    | 需求内容               | 优先级 | 理由                                     |
| ------- | ---------------------- | ------ | ---------------------------------------- |
| FR-001  | 会议创建与议题配置     | 必须   | 核心数据模型，所有功能的基础             |
| FR-002  | 双阶段计划时长配置     | 必须   | 核心业务逻辑，计时引擎的输入             |
| FR-004  | 圆形可视化倒计时器     | 必须   | 核心UI组件，用户交互的主要界面           |
| FR-005  | 倒计时与超时正计时切换 | 必须   | 核心计时逻辑，产品核心价值               |
| FR-006  | 阶段与议题切换         | 必须   | 核心流程控制，会议推进的关键操作         |
| FR-007  | 计时基础操作           | 必须   | 基础交互能力，暂停/继续/重置             |
| FR-008  | PPT全屏置顶悬浮        | 必须   | 核心差异化功能，解决PPT遮挡痛点          |
| FR-011  | 会议数据统计与导出     | 必须   | 核心业务价值，数据复盘能力               |
| FR-012  | 历史会议记录管理       | 必须   | 数据留存与复用能力                       |
| FR-003  | 会议配置模板管理       | 应当   | 效率提升功能，非核心路径                 |
| FR-009  | 超时视觉与音效提醒     | 应当   | 体验优化，增强可用性                     |
| FR-010  | 全局热键支持           | 应当   | 效率提升功能，非核心路径                 |
| NFR-001 | 性能与轻量化           | 必须   | 核心质量属性，影响用户体验               |
| NFR-002 | 兼容性                 | 必须   | 基础适配要求                             |
| NFR-003 | 独立部署               | 必须   | 交付要求                                 |
| NFR-004 | 计时精度               | 必须   | 核心质量属性                             |
| NFR-005 | 数据安全与完整性       | 必须   | 核心质量属性                             |
| NFR-006 | 可维护性与可扩展性     | 应当   | 长期维护考量                             |

- 建议里程碑：
  - **里程碑1（核心计时引擎）**：FR-001、FR-002、FR-004、FR-005、FR-006、FR-007 + NFR-001/004 —— 实现完整的计时核心功能，可在普通窗口模式下完成会议计时
  - **里程碑2（桌面集成与体验）**：FR-008、FR-009、FR-010 + NFR-002/003 —— 实现PPT置顶悬浮、超时提醒、全局热键，完成桌面端差异化体验
  - **里程碑3（数据与导出）**：FR-003、FR-011、FR-012 + NFR-005/006 —— 实现模板管理、数据统计导出、历史记录，完成数据闭环

## 9. 变更/设计提案（RFC）

### 9.1 现状分析

- **当前架构**：全新项目，无现有代码。工作目录仅有 Claude.md 全局规范文件。
- **现存问题**：
  - 无任何代码基础，需从零构建
  - Claude.md 定义的技术栈（FastAPI + Next.js）为Web架构，无法满足桌面应用需求
- **相关代码路径**：无

### 9.2 目标状态

- **提议架构**：Python + PySide6 桌面应用，PyInstaller 打包为独立 exe
- **核心变更**：
  - 采用 PySide6 作为 UI 框架，实现圆形计时器、悬浮窗口、透明度控制
  - 通过 Win32 API（ctypes）实现窗口置顶、无边框、全局热键
  - 使用 SQLite 嵌入式数据库存储会议配置、模板、历史记录
  - 使用 QTimer 驱动计时引擎，精度基于系统高精度时钟
  - 使用 openpyxl 导出 Excel，csv 模块导出 CSV

### 9.3 详细设计

#### 9.3.1 模块/组件设计

```
meeting_timer/
├── main.py                    # 应用入口
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── timer_engine.py    # 计时引擎（核心逻辑）
│   │   ├── models.py          # 数据模型定义
│   │   └── database.py        # SQLite 数据库管理
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py     # 主窗口（配置模式）
│   │   ├── float_widget.py    # 悬浮计时器窗口
│   │   ├── timer_circle.py    # 圆形计时器自定义绘制组件
│   │   ├── config_panel.py    # 会议议题配置面板
│   │   ├── stats_dialog.py    # 统计报表对话框
│   │   ├── history_panel.py   # 历史记录面板
│   │   ├── settings_dialog.py # 设置对话框（热键、提示音等）
│   │   └── theme.py           # 主题/样式管理
│   └── utils/
│       ├── __init__.py
│       ├── win32_api.py       # Win32 API 封装（置顶、热键、透明度）
│       ├── hotkey_manager.py  # 全局热键管理器
│       ├── audio_player.py    # 提示音播放
│       └── export.py          # CSV/Excel 导出工具
├── resources/
│   ├── icons/                 # 应用图标
│   └── sounds/                # 提示音文件
├── tests/
│   ├── test_timer_engine.py   # 计时引擎单元测试
│   ├── test_database.py       # 数据库操作测试
│   └── test_export.py         # 导出功能测试
├── pyproject.toml             # 项目配置（uv）
└── meeting_timer.spec         # PyInstaller 打包配置
```

#### 9.3.2 数据模型

```sql
-- 会议模板
CREATE TABLE meeting_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 模板议题
CREATE TABLE template_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    sort_order INTEGER NOT NULL,
    name TEXT NOT NULL,
    presentation_minutes INTEGER NOT NULL DEFAULT 10,
    qa_minutes INTEGER NOT NULL DEFAULT 5,
    FOREIGN KEY (template_id) REFERENCES meeting_templates(id) ON DELETE CASCADE
);

-- 会议记录
CREATE TABLE meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',  -- draft/in_progress/completed
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    current_topic_index INTEGER DEFAULT 0,
    current_phase TEXT DEFAULT 'presentation'  -- presentation/qa
);

-- 会议议题
CREATE TABLE meeting_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL,
    sort_order INTEGER NOT NULL,
    name TEXT NOT NULL,
    presentation_minutes INTEGER NOT NULL,
    qa_minutes INTEGER NOT NULL,
    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
);

-- 阶段计时记录
CREATE TABLE phase_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    phase TEXT NOT NULL,              -- presentation/qa
    planned_seconds INTEGER NOT NULL,
    actual_seconds INTEGER NOT NULL DEFAULT 0,
    overtime_seconds INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/running/paused/completed
    started_at TEXT,
    paused_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (topic_id) REFERENCES meeting_topics(id) ON DELETE CASCADE
);

-- 应用设置
CREATE TABLE app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

#### 9.3.3 核心流程

**会议计时主流程：**

```
用户创建会议 → 配置议题列表 → 点击"开始会议"
    ↓
进入第1个议题·主讲阶段 → 圆形计时器显示倒计时
    ↓
[计时循环]
    QTimer每50ms触发 → 更新内部计时器 → 刷新UI
    ↓
    倒计时归零？ → 是 → 自动切换正计时模式
                    → 圆环变红 + 数字高亮 + 可选提示音
    ↓
    用户操作？
    ├── 暂停 → 冻结计时器，按钮变为"继续"
    ├── 继续 → 从暂停时刻恢复
    ├── 下一阶段 → 保存当前阶段数据 → 进入QA阶段（或下一议题主讲阶段）
    ├── 上一阶段 → 回退到前一阶段（保留已计时长，从暂停状态恢复）
    └── 重置 → 当前阶段归零（二次确认）
    ↓
所有议题两阶段完成 → 标记会议完成 → 自动生成统计报表
    ↓
用户可查看/导出报表 → 数据存入历史记录
```

**计时引擎状态机：**

```
IDLE → (start) → COUNTDOWN → (time=0) → OVERTIME → (next_phase) → IDLE
  ↑                  ↓                        ↓
  │              (pause)                  (pause)
  │                  ↓                        ↓
  │              PAUSED_CD               PAUSED_OT
  │                  ↓                        ↓
  └──────── (reset) ──┴── (resume) ───────────┘
```

**PPT置顶悬浮流程：**

```
用户点击"悬浮模式" → 隐藏主窗口
    ↓
创建无边框悬浮窗口（Qt::FramelessWindowHint）
    ↓
调用Win32 SetWindowPos(HWND_TOPMOST) → 窗口置顶
    ↓
调用SetLayeredWindowAttributes → 设置透明度
    ↓
悬浮窗口仅显示：圆形计时器 + 议题名 + 阶段名
    ↓
支持拖拽移动（鼠标事件重写）
    ↓
双击悬浮窗口 → 切换回配置模式（主窗口）
```

#### 9.3.4 计时引擎核心设计

```python
class TimerEngine:
    IDLE = "idle"
    COUNTDOWN = "countdown"
    OVERTIME = "overtime"
    PAUSED_CD = "paused_countdown"
    PAUSED_OT = "paused_overtime"

    def __init__(self):
        self._state = self.IDLE
        self._planned_seconds = 0
        self._elapsed_seconds = 0.0
        self._reference_time = None  # time.perf_counter() reference
        self._paused_elapsed = 0.0

    def start(self, planned_seconds: int):
        self._planned_seconds = planned_seconds
        self._elapsed_seconds = 0.0
        self._reference_time = time.perf_counter()
        self._state = self.COUNTDOWN

    def pause(self):
        if self._state == self.COUNTDOWN:
            self._paused_elapsed = self._elapsed_seconds
            self._state = self.PAUSED_CD
        elif self._state == self.OVERTIME:
            self._paused_elapsed = self._elapsed_seconds
            self._state = self.PAUSED_OT

    def resume(self):
        self._reference_time = time.perf_counter()
        if self._state == self.PAUSED_CD:
            self._state = self.COUNTDOWN
        elif self._state == self.PAUSED_OT:
            self._state = self.OVERTIME

    def tick(self) -> dict:
        if self._state in (self.COUNTDOWN, self.OVERTIME):
            now = time.perf_counter()
            self._elapsed_seconds = self._paused_elapsed + (now - self._reference_time)

        remaining = max(0, self._planned_seconds - self._elapsed_seconds)
        overtime = max(0, self._elapsed_seconds - self._planned_seconds)

        if self._state == self.COUNTDOWN and self._elapsed_seconds >= self._planned_seconds:
            self._state = self.OVERTIME

        return {
            "state": self._state,
            "remaining_seconds": remaining,
            "overtime_seconds": overtime,
            "actual_seconds": self._elapsed_seconds,
            "progress": min(1.0, self._elapsed_seconds / self._planned_seconds) if self._planned_seconds > 0 else 1.0,
        }
```

### 9.4 备选方案评估

| 方案 | 优点 | 缺点 | 决策结果 |
| ---- | ---- | ---- | -------- |
| A: Python + PySide6 + PyInstaller | 延续Python技术栈；PySide6原生支持自定义绘制、透明窗口、系统托盘；PyInstaller打包为独立exe；Win32 API通过ctypes直接调用；开发效率高 | 打包体积较大（~50-80MB）；启动速度略慢于原生应用 | **选定** |
| B: C# WPF | Windows原生开发，最佳系统API支持；性能最优；启动快 | 偏离现有Python技术栈；需C#开发能力；XAML学习曲线 | 未选定 |
| C: Tauri + Web前端 | 轻量（~10MB）；现代UI能力 | 需Rust后端能力；Win32 API调用需Rust FFI；偏离技术栈 | 未选定 |
| D: Electron + Next.js | 延续Next.js前端能力 | 打包体积极大（~150MB+）；内存占用高（~200MB+）；与轻量化需求冲突 | 未选定 |

**选定方案A的理由**：
1. 延续Python技术栈，与Claude.md偏好一致
2. PySide6（Qt）是成熟的桌面UI框架，原生支持自定义绘制（圆形计时器）、窗口透明、无边框
3. 通过ctypes可完整调用Win32 API实现置顶、热键
4. PyInstaller打包后为独立exe，满足"绿色免安装"需求
5. 打包体积（~50-80MB）在可接受范围内，远小于Electron方案

### 9.5 实现与迁移计划

- **实现顺序**：
  1. 项目初始化：创建项目结构、配置pyproject.toml、搭建PySide6应用骨架
  2. 数据层：实现SQLite数据库管理、数据模型、CRUD操作
  3. 计时引擎：实现TimerEngine核心逻辑、状态机、精度控制
  4. 主窗口UI：实现会议配置界面、议题列表编辑、阶段时长配置
  5. 圆形计时器组件：实现自定义QPainter绘制、进度环、时间显示
  6. 悬浮窗口：实现无边框窗口、Win32置顶、透明度、拖拽
  7. 阶段切换与操作：实现开始/暂停/继续/重置/上一阶段/下一阶段
  8. 超时提醒：实现圆环变色、数字高亮、提示音
  9. 全局热键：实现Win32 RegisterHotKey、热键配置界面
  10. 模板管理：实现模板保存/加载/删除
  11. 统计与导出：实现报表生成、CSV/Excel导出
  12. 历史记录：实现历史列表、详情查看、删除
  13. 崩溃恢复：实现自动保存与恢复机制
  14. 打包发布：PyInstaller配置、测试、输出exe

- **风险缓解**：
  - PPT置顶兼容性问题 → 缓解策略：多种Win32置顶方法备选（HWND_TOPMOST、SetForegroundWindow、定时器刷新置顶），在多种PPT版本上测试
  - 全局热键冲突 → 缓解策略：支持自定义热键组合，冲突检测与提示
  - PyInstaller打包体积 → 缓解策略：排除不必要的Qt模块，使用UPX压缩
  - 计时精度漂移 → 缓解策略：使用time.perf_counter()高精度时钟，QTimer仅作UI刷新触发器

- **测试策略**：
  - 单元测试：TimerEngine状态机转换、计时精度、数据库CRUD、导出格式
  - 集成测试：UI与计时引擎联动、阶段切换数据保存、置顶/热键系统调用
  - 端到端（E2E）测试：完整会议流程（创建→配置→计时→切换→完成→导出）、PPT全屏下悬浮测试、崩溃恢复测试

- **回滚方案**：
  - 使用Git版本控制，每个里程碑打tag
  - 数据库使用版本号迁移，支持降级
  - 配置文件与数据文件分离，升级不影响历史数据

## 10. 待确认（TBD）清单

| 标识  | 事项 | 缺失信息 | 下一步行动 |
| ----- | ---- | -------- | ---------- |
| TBD-1 | 技术栈确认 | Claude.md定义的Web技术栈与桌面应用需求冲突 | ✅ 已确认：Python + PySide6 + PyInstaller |
| TBD-2 | 暂停恢复粒度 | 暂停后恢复是从暂停时刻继续还是重置 | ✅ 已确认：从暂停时刻继续 |
| TBD-3 | 上一阶段回退行为 | 回退后计时重置还是保留已计时长 | ✅ 已确认：保留已计时长，从暂停状态恢复 |
| TBD-4 | 崩溃恢复粒度 | 恢复到议题级别还是精确到暂停时刻 | ✅ 已确认：精确恢复到暂停时刻 |
| TBD-5 | 多显示器支持 | 是否需要跨屏拖拽和位置记忆 | ✅ 已确认：支持跨屏拖拽和位置记忆 |
| TBD-6 | 提示音资源 | 内嵌默认提示音还是用户自定义 | ✅ 已确认：内嵌3个提示音（剩余X分钟/时间到/超时X分钟），X可配置 |
