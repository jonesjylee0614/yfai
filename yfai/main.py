"""程序主入口"""

import sys
import asyncio
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from qasync import QEventLoop

from .app.main_window import MainWindow
from .core import ConfigManager
from .core import Orchestrator


def main():
    """主函数"""
    # 创建Qt应用
    app = QApplication(sys.argv)
    app.setApplicationName("YFAI")
    app.setApplicationVersion("0.1.0")

    # 设置样式
    app.setStyle("Fusion")

    # 创建异步事件循环
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    try:
        # 加载配置
        config_manager = ConfigManager()
        config = config_manager.get_all()

        # 创建核心调度器
        orchestrator = Orchestrator(config)

        # 初始化数据库
        orchestrator.db_manager.init_builtin_assistants()

        # 创建主窗口
        window = MainWindow(orchestrator, config)
        window.show()

        # 运行事件循环
        with loop:
            sys.exit(loop.run_forever())

    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

