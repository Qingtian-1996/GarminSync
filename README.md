# GarminSync

一个 Python 程序，用于将佳明（Garmin Connect）的活动数据自动同步到行者（行者 imxingzhe.com）。

## 功能

- 从 Garmin Connect 下载活动数据（FIT 格式）
- 自动上传到行者（行者）平台
- 支持本地运行和 GitHub Actions 定时自动同步
- 跳过已上传的重复活动

## 运行环境

- Python 3.9+

## 使用方法

### 本地运行

1. 克隆项目到本地：

   ```bash
   git clone https://github.com/Qingtian-1996/GarminSync.git
   cd GarminSync
   ```

2. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

3. 复制 `.env.example` 为 `.env` 并填写账号信息：

   ```bash
   cp .env.example .env
   ```

   编辑 `.env` 文件：

   ```
   GARMIN_EMAIL=your_garmin_email@example.com
   GARMIN_PASSWORD=your_garmin_password
   XINGZHE_USERNAME=your_xingzhe_username
   XINGZHE_PASSWORD=your_xingzhe_password
   # 同步最近几天的活动（默认为 1）
   SYNC_DAYS=1
   ```

4. 运行同步脚本：

   ```bash
   python main.py
   ```

### GitHub Actions 自动同步

1. Fork 本项目到自己的 GitHub 账号下。

2. 在 Fork 的项目中，进入 **Settings → Secrets and variables → Actions**，添加以下 Secrets：

   | 名称                | 说明                      |
   |---------------------|---------------------------|
   | `GARMIN_EMAIL`      | Garmin Connect 登录邮箱   |
   | `GARMIN_PASSWORD`   | Garmin Connect 登录密码   |
   | `XINGZHE_USERNAME`  | 行者账号（手机号/用户名）  |
   | `XINGZHE_PASSWORD`  | 行者登录密码              |

3. 进入项目的 **Actions** 页面，启用 Workflows。

4. 工作流将每天北京时间 14:00（UTC 06:00）自动运行，也可在 Actions 页面手动触发，并可指定同步的天数。

## 环境变量说明

| 变量名              | 必填 | 说明                                 |
|---------------------|------|--------------------------------------|
| `GARMIN_EMAIL`      | 是   | Garmin Connect 登录邮箱              |
| `GARMIN_PASSWORD`   | 是   | Garmin Connect 登录密码              |
| `XINGZHE_USERNAME`  | 是   | 行者账号（手机号或用户名）           |
| `XINGZHE_PASSWORD`  | 是   | 行者登录密码                         |
| `SYNC_DAYS`         | 否   | 同步最近几天的活动，默认为 `1`       |

## 注意事项

- 请妥善保管账号密码，切勿将 `.env` 文件提交到公开仓库（已添加至 `.gitignore`）。
- 行者接口可能随时更新，若上传失败请提交 Issue。
- 请遵守 Garmin 和行者的服务条款，仅用于个人数据同步。