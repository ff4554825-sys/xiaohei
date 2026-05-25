# 快速开始

## 环境要求

- Python >= 3.11
- DeepSeek API Key ([获取](https://platform.deepseek.com/))

## 安装

```bash
git clone https://github.com/ff4554825-sys/xiaohei.git
cd xiaohei
pip install -e .
```

## 配置

```bash
# 方式1: 环境变量
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 方式2: 配置文件
echo 'DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"' > .env
```

## 运行

```bash
# Web UI 模式 (打开 http://localhost:3721)
python start.py --mode web

# CLI 模式
python start.py --mode cli

# 双模式
python start.py --mode both
```

## Docker

```bash
export DEEPSEEK_API_KEY="sk-xxx"
docker-compose up -d
```

## 验证

```bash
curl http://localhost:3721/api/health
# {"status":"ok","agent":"XiaoHei","version":"1.0.0"}
```
