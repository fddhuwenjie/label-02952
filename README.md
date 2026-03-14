# 拼音输入法引擎

## How to Run

### 一键启动 & 验证

```bash
bash run.sh
```

脚本会自动完成以下流程：
1. 检测系统环境（macOS / Linux / Windows Git Bash）
2. 未安装 Docker 时尝试自动安装
3. 构建镜像并启动容器
4. 运行 22 项自动化验证（单拼音、连续拼音切分、长句、搜索、异常输入等）

### Docker 手动启动

```bash
# 构建并启动
docker compose up --build -d

# 进入交互模式
docker exec -it pinyin-input-method python -m app

# 执行单次查询
docker exec pinyin-input-method python -m app query ni
docker exec pinyin-input-method python -m app query nihao          # 连续拼音自动切分
docker exec pinyin-input-method python -m app query woaibeijing    # 长连续拼音
docker exec pinyin-input-method python -m app convert ni hao shi jie

# 停止服务
docker compose down
```

### 本地启动

```bash
cd backend

# 交互模式
python -m app

# 命令行模式
python -m app query ni          # 查询拼音
python -m app search zh         # 搜索拼音前缀
python -m app convert ni hao    # 转换拼音句子
python -m app list              # 列出所有拼音
```

## Services

| 服务 | 说明 |
|------|------|
| pinyin-engine | 拼音输入法引擎，提供拼音到汉字的转换功能 |

## 测试账号

本项目为纯后端命令行工具，无需登录账号。

## 题目内容

使用python开发拼音输入法

---

## 功能特性

- 支持 400+ 常用拼音
- 每个拼音对应多个候选汉字
- 连续拼音自动切分（如 `nihao` → `ni` + `hao`，`woaibeijing` → `wo` + `ai` + `bei` + `jing`）
- 前缀模糊匹配
- 纯 Python 实现，无外部依赖
- Docker 跨平台支持（ARM64/AMD64）



## 项目结构

```
.
├── README.md
├── docker-compose.yml
├── run.sh               # 一键启动 & 验证脚本
├── .gitignore
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── __init__.py
        ├── __main__.py      # CLI 入口
        ├── main.py          # 主程序逻辑
        ├── pinyin_dict.py   # 拼音字典数据
        └── pinyin_engine.py # 拼音引擎核心
```

## 使用示例

```bash
# 查询单个拼音
$ python -m app query zhong
{
  "pinyin": "zhong",
  "candidates": ["中", "种", "重", "众", "终", "钟", "忠", "仲", "衷", "肿"],
  "count": 10
}

# 连续拼音自动切分
$ python -m app query nihao
{
  "pinyin": "nihao",
  "segments": ["ni", "hao"],
  "candidates": [["你", "泥", ...], ["好", "号", ...]],
  "all_segments": [["ni", "hao"]]
}

# 长连续拼音
$ python -m app query woaibeijing
{
  "pinyin": "woaibeijing",
  "segments": ["wo", "ai", "bei", "jing"],
  "candidates": [["我", ...], ["爱", ...], ["北", ...], ["京", ...]],
  "all_segments": [["wo", "ai", "bei", "jing"]]
}

# 空格分词转换
$ python -m app convert ni hao shi jie
{
  "input": "ni hao shi jie",
  "result": [
    ["你", "泥", "拟", "逆", "尼"],
    ["好", "号", "毫", "豪", "浩"],
    ["是", "时", "事", "十", "使"],
    ["就", "接", "结", "节", "解"]
  ]
}
```

## 开发指南

### 环境搭建

```bash
# 克隆项目
git clone <repository-url>
cd pinyin-input-method

# 本地开发（无需安装依赖）
cd backend
python -m app
```

### 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request
```
