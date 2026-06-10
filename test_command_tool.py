#!/usr/bin/env python3
"""测试 run_command 工具功能"""

import sys
sys.path.insert(0, '.')

from app import is_command_safe, execute_tool

def test_command_whitelist():
    """测试白名单"""
    print("测试白名单...")

    # 应该通过
    assert is_command_safe("pip install requests")[0] == True
    assert is_command_safe("npm test")[0] == True
    assert is_command_safe("python --version")[0] == True
    assert is_command_safe("ls -la")[0] == True
    assert is_command_safe("git status")[0] == True
    print("✅ 白名单测试通过")

def test_command_blacklist():
    """测试黑名单"""
    print("\n测试黑名单...")

    # 应该被拒绝
    assert is_command_safe("rm -rf /")[0] == False
    assert is_command_safe("sudo rm file")[0] == False
    assert is_command_safe("chmod 777 /")[0] == False
    assert is_command_safe("dd if=/dev/zero")[0] == False
    print("✅ 黑名单测试通过")

def test_non_whitelist():
    """测试非白名单命令"""
    print("\n测试非白名单命令...")

    assert is_command_safe("curl http://example.com")[0] == False
    assert is_command_safe("wget file")[0] == False
    assert is_command_safe("nc -l 8080")[0] == False
    print("✅ 非白名单测试通过")

def test_execute():
    """测试命令执行"""
    print("\n测试命令执行...")

    # 测试成功执行
    result = execute_tool("run_command", {"command": "echo hello"})
    assert result.get("status") == "ok"
    assert "hello" in result.get("stdout", "")
    assert result.get("returncode") == 0
    print("✅ 成功执行: echo hello")

    # 测试被拒绝
    result = execute_tool("run_command", {"command": "sudo rm file"})
    assert "error" in result
    assert "拒绝执行" in result["error"]
    print("✅ 成功拒绝: sudo rm file")

    # 测试命令失败
    result = execute_tool("run_command", {"command": "ls /nonexistent"})
    assert result.get("returncode") != 0
    print("✅ 正确处理失败命令")

def test_existing_tools():
    """测试现有工具不受影响"""
    print("\n测试现有工具...")

    # 测试 git_status
    result = execute_tool("git_status", {})
    assert "error" not in result or "output" in result
    print("✅ git_status 正常")

    # 测试 get_project_structure
    result = execute_tool("get_project_structure", {})
    assert "files" in result or "error" in result
    print("✅ get_project_structure 正常")

if __name__ == "__main__":
    try:
        test_command_whitelist()
        test_command_blacklist()
        test_non_whitelist()
        test_execute()
        test_existing_tools()

        print("\n" + "="*50)
        print("🎉 所有测试通过！")
        print("="*50)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
