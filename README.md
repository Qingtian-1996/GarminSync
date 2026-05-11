# GarminSync

将 Garmin Connect 中的活动数据同步到行者（Xingzhe）。

## 功能
- 登录 Garmin Connect
- 拉取最近活动
- 下载原始活动文件
- 自动提取 `.fit`
- 调用行者开放平台上传接口注册上传
- 尝试上传 FIT 文件到行者

## 依赖
- Python 3.10+
- requests
- garminconnect

安装依赖：

```bash
pip install -r requirements.txt
```

## 环境变量

需要配置以下环境变量：

- `GARMIN_EMAIL`：Garmin 账号
- `GARMIN_PASSWORD`：Garmin 密码
- `XINGZHE_ACCESS_TOKEN`：行者开放平台 access token
- `GARMIN_LIMIT`：拉取最近多少条活动，默认 `10`
- `EXPORT_DIR`：导出目录，默认 `./exports`
- `XINGZHE_UPLOADS_API`：行者上传接口，默认 `https://openapi.imxingzhe.com/openapi/v1/uploads/`

### Linux / macOS

```bash
export GARMIN_EMAIL="your_garmin_email"
export GARMIN_PASSWORD="your_garmin_password"
export XINGZHE_ACCESS_TOKEN="your_xingzhe_access_token"
export GARMIN_LIMIT="5"
export EXPORT_DIR="./exports"
```

### Windows PowerShell

```powershell
$env:GARMIN_EMAIL="your_garmin_email"
$env:GARMIN_PASSWORD="your_garmin_password"
$env:XINGZHE_ACCESS_TOKEN="your_xingzhe_access_token"
$env:GARMIN_LIMIT="5"
$env:EXPORT_DIR="./exports"
```

## 运行

```bash
python sync_garmin_to_xingzhe.py
```

## 运行流程
1. 登录 Garmin Connect
2. 获取最近 N 条活动
3. 下载原始活动文件
4. 从压缩包中提取 `.fit`
5. 调用行者上传接口注册上传
6. 尝试上传 FIT 文件

## 注意事项
- 行者上传接口需要有效的 OAuth access token
- 当前脚本对“文件真正上传”的响应结构做了兼容处理，但如果行者返回结构不同，可能需要按实际 JSON 做小修改
- 如果脚本卡在上传步骤，请查看日志中的“行者注册上传响应文本”

## 常见问题

### 1. 401 Unauthorized
说明 access token 无效、过期，或 scope 不足。

### 2. 409 Conflict
通常表示活动重复上传，或文件重复。

### 3. 无法识别上传方式
说明行者注册上传接口返回的 JSON 结构与脚本当前兼容逻辑不一致，需要根据返回内容补充上传逻辑。
