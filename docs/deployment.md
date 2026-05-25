# 部署

## Docker

```bash
# 启动
export DEEPSEEK_API_KEY="sk-xxx"
docker-compose up -d

# 查看日志
docker logs -f xiaohei

# 停止
docker-compose down
```

## Dockerfile (手动构建)

```bash
docker build -t xiaohei .
docker run -d -p 3721:3721 -e DEEPSEEK_API_KEY=sk-xxx xiaohei
```

## 裸机部署

```bash
pip install -e .
python start.py --mode web --host 0.0.0.0 --port 3721
```

## 开机自启

### Linux (systemd)

```ini
[Unit]
Description=XiaoHei Agent OS
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/xiaohei
ExecStart=/usr/bin/python start.py --mode web
Restart=always

[Install]
WantedBy=multi-user.target
```

### Windows

启动 `start.py` 后, 系统托盘自动运行。
