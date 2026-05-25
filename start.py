#!/usr/bin/env python3
"""
XiaoHei Agent OS - 启动脚本
"""

import asyncio
import argparse
import sys
import os

from src.xiaohei.runtime import AgentOS
from src.xiaohei.gateway.cli import CLI


def main():
    parser = argparse.ArgumentParser(description="XiaoHei Agent OS")
    parser.add_argument(
        "--mode",
        choices=["web", "cli", "both"],
        default="cli",
        help="运行模式: web, cli, 或 both"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Web服务器主机地址"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3721,
        help="Web服务器端口"
    )
    args = parser.parse_args()

    os.makedirs("./data", exist_ok=True)
    os.makedirs("./logs", exist_ok=True)
    os.makedirs("./sandbox", exist_ok=True)

    agent_os = AgentOS()

    if args.mode == "cli":
        print("启动 XiaoHei CLI 模式...")
        cli = CLI()
        cli.cmdloop()

    elif args.mode == "web":
        print(f"启动 XiaoHei Web 模式... http://{args.host}:{args.port}")
        asyncio.run(agent_os.start())
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            print("正在停止...")
            asyncio.run(agent_os.stop())

    elif args.mode == "both":
        print("启动 XiaoHei 混合模式...")
        asyncio.run(agent_os.start())

        def run_cli():
            cli = CLI()
            cli.cmdloop()

        import threading
        cli_thread = threading.Thread(target=run_cli, daemon=True)
        cli_thread.start()

        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            print("正在停止...")
            asyncio.run(agent_os.stop())


if __name__ == "__main__":
    main()
