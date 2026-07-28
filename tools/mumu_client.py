# mumu_client.py
# 在 Linux 机器上运行，通过 HTTP API 控制 Windows 上的 MuMu 模拟器

import requests
import time
from typing import List, Optional, Dict, Any

class MuMuRemoteClient:
    """远程 MuMu 模拟器客户端 - 用于 Linux 机器调用 Windows API"""
    
    def __init__(self, host: str, port: int = 5000, timeout: int = 30):
        """
        初始化客户端
        
        Args:
            host: Windows 机器的 IP 地址
            port: API 服务端口，默认 5000
            timeout: 请求超时时间（秒）
        """
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        
    def _post(self, action: str, coordinates: Optional[List] = None, text: str = "") -> Dict[str, Any]:
        """发送命令到 API 服务器"""
        command = {
            "action": action,
            "coordinates": coordinates or [],
            "text": text
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/execute",
                json=command,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "action": action,
                "message": f"请求失败: {e}",
                "screenshot_path": None
            }
    
    def _get(self, endpoint: str) -> Dict[str, Any]:
        """GET 请求"""
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    # ========== 核心操作方法 ==========
    
    def click(self, x: int, y: int) -> Dict[str, Any]:
        """
        点击指定坐标
        
        Args:
            x: X 坐标
            y: Y 坐标
        """
        return self._post("CLICK", [[x, y]])
    
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500) -> Dict[str, Any]:
        """
        滑动屏幕
        
        Args:
            start_x, start_y: 起始坐标
            end_x, end_y: 结束坐标
            duration: 滑动时长（毫秒）
        """
        return self._post("SCROLL", [[start_x, start_y], [end_x, end_y]], text=str(duration))
    
    def input_text(self, text: str) -> Dict[str, Any]:
        """
        输入文本（需要模拟器中安装 ADBKeyboard）
        
        Args:
            text: 要输入的文本
        """
        return self._post("TEXT", text=text)
    
    def home(self) -> Dict[str, Any]:
        """返回主页"""
        return self._post("HOME")
    
    def back(self) -> Dict[str, Any]:
        """返回上一页"""
        return self._post("BACK")
    
    def clear_tasks(self) -> Dict[str, Any]:
        """清除所有后台任务"""
        return self._post("CLEAR_TASKS")
    
    def screenshot(self, filename: str = None) -> Dict[str, Any]:
        """
        截图并保存
        
        Args:
            filename: 文件名（不含扩展名），默认使用时间戳
            
        Returns:
            包含截图路径的结果字典
        """
        return self._post("SCREENSHOT", text=filename or "")
    
    def shutdown_app(self, package_name: str = None) -> Dict[str, Any]:
        """
        关闭指定应用
        
        Args:
            package_name: 应用包名，如 com.tencent.mm
        """
        return self._post("SHUTDOWN", text=package_name or "")
    
    def start_app(self, package_name: str) -> Dict[str, Any]:
        """
        启动指定应用
        
        Args:
            package_name: 应用包名
        """
        return self._post("START_APP", text=package_name)
    
    def change_device(self, device_name: str) -> Dict[str, Any]:
        """
        更换机型
        
        Args:
            device_name: 机型名称 (pixel_4, pixel_6, samsung_s21, default)
        """
        return self._post("CHANGE_DEVICE", text=device_name)
    
    # ========== 设备信息方法 ==========
    
    def health(self) -> Dict[str, Any]:
        """健康检查"""
        return self._get("health")
    
    def device_info(self) -> Dict[str, Any]:
        """获取设备信息"""
        return self._get("device/info")
    
    def latest_screenshot(self) -> Dict[str, Any]:
        """获取最新截图信息"""
        return self._get("screenshot/latest")
    
    # ========== 批量执行 ==========
    
    def execute_batch(self, commands: List[Dict]) -> Dict[str, Any]:
        """
        批量执行命令
        
        Args:
            commands: 命令列表，每个命令格式与单条相同
        
        Returns:
            批量执行结果
        """
        try:
            response = requests.post(
                f"{self.base_url}/execute/batch",
                json={"commands": commands},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "results": [], "count": 0}
    
    # ========== 便捷方法 ==========
    
    def wait(self, seconds: float):
        """等待指定秒数"""
        time.sleep(seconds)
    
    def click_center(self) -> Dict[str, Any]:
        """点击屏幕中心（需要先获取屏幕尺寸）"""
        info = self.device_info()
        if info.get("success", True):
            width = info.get("screen_width", 720)
            height = info.get("screen_height", 1280)
            return self.click(width // 2, height // 2)
        return self.click(360, 640)
    
    def swipe_up(self, duration: int = 300) -> Dict[str, Any]:
        """向上滑动"""
        info = self.device_info()
        if info.get("success", True):
            height = info.get("screen_height", 1280)
            return self.swipe(360, height - 200, 360, 200, duration)
        return self.swipe(360, 1000, 360, 300, duration)
    
    def swipe_down(self, duration: int = 300) -> Dict[str, Any]:
        """向下滑动"""
        info = self.device_info()
        if info.get("success", True):
            height = info.get("screen_height", 1280)
            return self.swipe(360, 200, 360, height - 200, duration)
        return self.swipe(360, 300, 360, 1000, duration)
    
    def swipe_left(self, duration: int = 300) -> Dict[str, Any]:
        """向左滑动"""
        info = self.device_info()
        if info.get("success", True):
            width = info.get("screen_width", 720)
            return self.swipe(width - 100, 640, 100, 640, duration)
        return self.swipe(600, 640, 100, 640, duration)
    
    def swipe_right(self, duration: int = 300) -> Dict[str, Any]:
        """向右滑动"""
        info = self.device_info()
        if info.get("success", True):
            width = info.get("screen_width", 720)
            return self.swipe(100, 640, width - 100, 640, duration)
        return self.swipe(100, 640, 600, 640, duration)


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 初始化客户端（替换为 Windows 机器的 IP）
    mumu = MuMuRemoteClient(host="127.0.0.1", port=5000)
    
    # # 1. 健康检查
    # print("=" * 50)
    # print("1. 健康检查")
    # print("=" * 50)
    # result = mumu.health()
    # print(f"结果: {result}\n")
    
    # # 2. 获取设备信息
    # print("=" * 50)
    # print("2. 设备信息")
    # print("=" * 50)
    # result = mumu.device_info()
    # print(f"设备: {result}\n")
    
    # # 3. 返回主页
    # print("=" * 50)
    # print("3. 返回主页")
    # print("=" * 50)
    # result = mumu.home()
    # print(f"结果: {result}\n")
    # mumu.wait(1)
    
    # # 4. 截图
    # print("=" * 50)
    # print("4. 截图")
    # print("=" * 50)
    # result = mumu.screenshot("linux_test")
    # print(f"结果: {result}\n")
    
    # # 5. 滑动测试
    # print("=" * 50)
    # print("5. 向右滑动")
    # print("=" * 50)
    # result = mumu.swipe_right()
    # print(f"结果: {result}\n")
    # mumu.wait(1)
    
    # 6. 批量执行命令
    print("=" * 50)
    print("6. 批量执行")
    print("=" * 50)
    commands = [
        # {"action": "CLICK", "coordinates": [[500, 500]], "text": ""},
        {"action": "TEXT", "coordinates": [], "text": "你好"},
        # {"action": "HOME", "coordinates": [], "text": ""},
        # {"action": "SCREENSHOT", "coordinates": [], "text": "batch_test_1"},
        # {"action": "SCROLL", "coordinates": [[200, 840], [200, 50]], "text": ""},
        # {"action": "SCREENSHOT", "coordinates": [], "text": "batch_test_2"},
        # {"action": "HOME", "coordinates": [], "text": ""},
    ]
    result = mumu.execute_batch(commands)
    print(f"执行数量: {result.get('count', 0)}")
    print(f"结果: {result.get('results', [])}\n")
    
    # print("=" * 50)
    # print("✅ 测试完成")
    # print("=" * 50)