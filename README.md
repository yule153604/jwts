# 教务系统脚本

## 概述

本项目包含两个 Python 脚本，用于与大学教务系统进行交互：

1.  `cjcx.py` (成绩查询脚本): 自动登录教务系统，获取学生成绩，与上次查询的成绩进行比较，并在成绩有更新时通过 PushPlus 推送通知。
2.  `jw.py` (课表查询脚本): 自动登录教务系统，获取当前周或当日的课表，并通过 PushPlus 推送通知。

## 功能特性

### 通用功能
*   自动登录教务系统。
*   通过 PushPlus 发送通知。

### `cjcx.py` (成绩查询脚本)
*   获取所有学期的成绩。
*   将当前获取的成绩与本地存储的先前成绩 (`previous_grades_data.json`) 进行比较。
*   仅当成绩发生变化时才发送推送通知。
*   自动保存最新成绩到本地文件。

### `jw.py` (课表查询脚本)
*   获取指定周的课表 (默认为当前周)。
*   如果不是周一，则仅推送当天的课表。
*   在周一推送整周课表。
*   需要手动在脚本中配置学期的第一周周一日期 (`first_week_monday`)。

## 先决条件

*   Python 3.x
*   必要的 Python 库:
    *   `requests`
    *   `beautifulsoup4`

## 安装与配置

1.  **获取脚本**:
    *   克隆本仓库或直接下载 `cjcx.py` 和 `jw.py` 文件。

2.  **安装依赖**:
    *   建议创建一个 `requirements.txt` 文件，内容如下：
        ```txt
        requests
        beautifulsoup4
        ```
    *   然后通过 pip 安装依赖：
        ```bash
        pip install -r requirements.txt
        ```

3.  **环境变量配置**:
    *   为了安全地管理您的凭据和令牌，请设置以下环境变量：
        *   `JW_USERNAME`: 您的教务系统学号。
        *   `JW_PASSWORD`: 您的教务系统密码。
        *   `PUSH_TOKEN`: 您的 PushPlus 令牌 (用于接收通知)。

4.  **脚本特定配置**:
    *   **`cjcx.py`**:
        *   `previous_grades_data.json`: 此文件由脚本自动创建和管理，用于存储上一次查询的成绩。无需手动配置。
    *   **`jw.py`**:
        *   `first_week_monday`: 打开 `jw.py` 文件，找到 `JWSystem` 类中的 `self.first_week_monday` 变量。根据您当前学期的实际开学第一周的周一日期修改它。例如：
            ```python
            self.first_week_monday = datetime(2025, 3, 3) # 修改为实际日期
            ```

## 使用方法

1.  **手动运行脚本**:
    *   确保已完成安装与配置步骤。
    *   打开终端或命令提示符，导航到脚本所在的目录。
    *   运行成绩查询脚本：
        ```bash
        python cjcx.py
        ```
    *   运行课表查询脚本：
        ```bash
        python jw.py
        ```

2.  **设置定时任务 (可选)**:
    *   您可以设置定时任务，让脚本定期自动运行。
    *   **Windows**: 可以使用 "任务计划程序 (Task Scheduler)"。
        *   例如，设置每30分钟运行一次 `cjcx.py`：
            *   触发器：每隔30分钟。
            *   操作：启动程序，程序或脚本填写 `python`，添加参数填写 `c:\path\to\your\script\cjcx.py` (替换为实际路径)。
    *   **Linux/macOS**: 可以使用 `cron`。
        *   例如，设置每30分钟运行一次 `cjcx.py`：
            *   打开 crontab 编辑器: `crontab -e`
            *   添加一行: `*/30 * * * * /usr/bin/python3 /path/to/your/script/cjcx.py` (替换为实际 Python 解释器路径和脚本路径)。

## 文件说明

*   **`cjcx.py`**:
    *   用于登录教务系统，抓取最新的成绩单。
    *   比较新成绩与上次保存的成绩，如果发生变化，则通过 PushPlus 推送通知，并更新本地成绩记录文件。
*   **`jw.py`**:
    *   用于登录教务系统，抓取当前周的课程表。
    *   格式化课表信息，并在周一推送整周课表，其他工作日推送当日课表（如果当天有课）。
*   **`previous_grades_data.json` (自动生成)**:
    *   由 `cjcx.py` 脚本生成，用于存储上一次成功获取的成绩数据，以便进行比较。
*   **`README.md`**:
    *   本项目说明文件。

## 故障排除

*   **登录失败**:
    *   检查您的 `JW_USERNAME` 和 `JW_PASSWORD` 环境变量是否设置正确。
    *   确认教务系统没有更新登录机制或增加验证码等。
    *   检查网络连接是否正常。
*   **获取信息失败**:
    *   可能是教务系统页面结构发生变化，导致 BeautifulSoup 解析失败。需要更新脚本中的解析逻辑。
    *   网络不稳定或请求超时。
*   **PushPlus 推送失败**:
    *   检查您的 `PUSH_TOKEN` 环境变量是否正确。
    *   确认 PushPlus 服务是否正常。
*   **`jw.py` 课表周次不正确**:
    *   请务必正确配置 `jw.py` 脚本中的 `first_week_monday` 变量。

---

祝您使用愉快！
