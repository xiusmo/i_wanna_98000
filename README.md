# 自动提交 Mi Fit 步数脚本

本项目用于自动向华米（Mi Fit）接口提交伪造步数，可在本地或通过 GitHub Actions 定时执行。支持多账号、北京时间计算步数区间，并可自定义上传 JSON 模板。

---
## 功能说明
- 支持多账号（使用 `#` 分隔多个用户名与密码）
- 根据北京时间（UTC+8）按 3 小时一档生成随机步数区间
- 从 `upload_json.txt` 文件中读取原始 `data_json` 模板，并替换日期与步数字段
- 可在本地运行，也可配置 GitHub Actions 自动执行
- 支持自定义执行时间，通过 GitHub Actions `cron` 定时触发

---
## 使用前准备
1. Fork 本仓库到你的 GitHub 账号
2. 克隆到本地：
   ```bash
   git clone https://github.com/<你的用户名>/<仓库名>.git
   cd <仓库名>
   ```
3. 安装依赖（需 Python 3.x）：
   ```bash
   pip install --upgrade pip
   pip install requests
   ```
4. 准备 `upload_json.txt`：
   - 在 Mi Fit App 或抓包工具中获取向 `band_data.json` 接口提交的原始 `data_json` 参数
   - 将完整的 `data_json` 内容（URL 编码后的 JSON 字符串）粘贴到项目根目录下的 `upload_json.txt` 文件中

5. 本地测试运行：
   ```bash
   python main.py 用户A#用户B 密码A#密码B
   ```
   脚本会输出详细的 DEBUG 日志，并显示每个账号的提交结果。

---
## GitHub Actions 自动化
1. 在仓库设置中创建 Secrets：
   - `USERS`：用户名列表，用 `#` 分隔
   - `PASSWORDS`：对应密码列表，用 `#` 分隔
2. 工作流文件在 `.github/workflows/submit_steps.yml`，已配置为北京时间 **8:00、10:00、12:00**（对应 UTC `0:00`、`2:00`、`4:00`）定时执行。
3. 手动触发或定时执行时，会自动安装依赖并运行脚本：
   ```yaml
   - name: 提交步数
     env:
       USERS: ${{ secrets.USERS }}
       PASSWORDS: ${{ secrets.PASSWORDS }}
     run: python main.py "$USERS" "$PASSWORDS"
   ```

---
## 参数说明
- 脚本位置参数：
  1. `users`：用户名或手机号列表，多个账号之间用 `#` 分隔。
  2. `passwords`：与用户名一一对应的密码列表，用 `#` 分隔。

---
## 时区说明
- 脚本内部使用北京时间（UTC+8）计算随机步数档位与输出日志。
- GitHub Actions 的定时器默认基于 UTC，工作流已手动将 UTC `0:00`、`2:00`、`4:00` 对应到北京时间 `8:00`、`10:00`、`12:00`。

---
## 常见问题
**为什么要配置 `upload_json.txt`？** 该文件保存 API 请求中原始的 `data_json` 参数模板，脚本只负责替换日期与步数，不会对 JSON 做其他解析，以确保与官方上报格式一致。

**我需要自己抓包吗？** 如果你使用 Android/iOS 上的 Mi Fit App，可通过抓包工具（如 Charles、Fiddler）获取一次正常的请求，将其中的 `data_json` 原文写入 `upload_json.txt`。

**为什么显示登录失败？** 目前已知一天内数据发生异常时会封号一天。12点解，所以不要进行多次调试。

