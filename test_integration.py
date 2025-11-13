"""集成测试脚本

测试各个模块是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_config():
    """测试配置管理"""
    print("[*] Testing Config Manager...")
    from yfai.core import ConfigManager

    try:
        config = ConfigManager()
        assert config.get("app.default_provider") is not None
        print("  [OK] Config Manager working")
        return True
    except Exception as e:
        print(f"  [FAIL] Config Manager failed: {e}")
        return False


async def test_database():
    """测试数据库"""
    print("[*] Testing Database...")
    from yfai.store import DatabaseManager

    try:
        db = DatabaseManager("data/test.db")
        db.init_builtin_assistants()
        stats = db.get_stats()
        print(f"  [OK] Database working - {stats}")
        return True
    except Exception as e:
        print(f"  [FAIL] Database failed: {e}")
        return False


async def test_providers():
    """测试Provider"""
    print("[*] Testing Providers...")
    from yfai.core import ConfigManager
    from yfai.providers import ProviderManager

    try:
        config = ConfigManager().get_all()
        manager = ProviderManager(config)

        # 测试健康检查
        health = await manager.check_health_all()
        print(f"  [OK] Providers working - {health}")
        return True
    except Exception as e:
        print(f"  [FAIL] Providers failed: {e}")
        return False


async def test_localops():
    """测试本地操作"""
    print("[*] Testing Local Operations...")
    from yfai.localops import FileSystemOps, ProcessOps, NetworkOps

    try:
        # 测试文件系统
        fs = FileSystemOps()
        result = fs.list_dir(".")
        assert result["success"]

        # 测试进程
        proc = ProcessOps()
        result = proc.get_system_info()
        assert result["success"]

        # 测试网络
        net = NetworkOps()
        result = net.get_local_ip()
        assert result["success"]

        print("  [OK] Local Operations working")
        return True
    except Exception as e:
        print(f"  [FAIL] Local Operations failed: {e}")
        return False


async def test_security():
    """测试安全模块"""
    print("[*] Testing Security Module...")
    from yfai.core import ConfigManager
    from yfai.security import SecurityGuard

    try:
        config = ConfigManager().get_all()
        guard = SecurityGuard(config)

        # 测试权限检查
        allowed = guard.check_permission("fs.read", "local", {}, "low")
        assert allowed

        print("  [OK] Security Module working")
        return True
    except Exception as e:
        print(f"  [FAIL] Security Module failed: {e}")
        return False


async def test_orchestrator():
    """测试核心调度器"""
    print("[*] Testing Orchestrator...")
    from yfai.core import ConfigManager, Orchestrator

    try:
        config = ConfigManager().get_all()
        orch = Orchestrator(config)

        # 创建会话
        session_id = await orch.create_session("Test Session")
        assert session_id is not None

        # 健康检查
        health = await orch.health_check()
        print(f"  [OK] Orchestrator working - Session ID: {session_id[:8]}...")
        return True
    except Exception as e:
        print(f"  [FAIL] Orchestrator failed: {e}")
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("YFAI 集成测试")
    print("=" * 60)
    print()

    tests = [
        ("配置管理", test_config()),
        ("数据库", test_database()),
        ("Provider", test_providers()),
        ("本地操作", test_localops()),
        ("安全模块", test_security()),
        ("核心调度器", test_orchestrator()),
    ]

    results = []
    for name, test in tests:
        try:
            result = await test
            results.append((name, result))
        except Exception as e:
            print(f"[ERROR] {name} test exception: {e}")
            results.append((name, False))
        print()

    # 总结
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")

    print()
    print(f"Total: {passed}/{total} passed")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

