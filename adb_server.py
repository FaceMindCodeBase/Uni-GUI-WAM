# adb_server.py
# 运行在Windows机器上，提供HTTP API接口

import subprocess
import time
import os
import shlex
import sys
import json
import threading
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许跨域请求

class MuMuController:
    """MuMu 模拟器控制器 - 支持通过ADB控制"""
    
    # 机型配置
    DEVICE_CONFIGS = {
        "pixel_4": {"width": 1080, "height": 2280, "dpi": 440, "name": "Google Pixel 4"},
        "pixel_6": {"width": 1080, "height": 2400, "dpi": 411, "name": "Google Pixel 6"},
        "samsung_s21": {"width": 1080, "height": 2400, "dpi": 421, "name": "Samsung Galaxy S21"},
        "xiaomi_12": {"width": 1080, "height": 2400, "dpi": 419, "name": "Xiaomi 12"},
        "oneplus_9": {"width": 1080, "height": 2400, "dpi": 402, "name": "OnePlus 9"},
        "default": {"width": 720, "height": 1280, "dpi": 320, "name": "Default"}
    }
    
    def __init__(self, device_id: str = None, screenshot_dir: str = "./screenshots"):
        self.device_id = device_id
        self.screenshot_dir = screenshot_dir
        self.device_config = self.DEVICE_CONFIGS["default"]
        self.adb_path = os.path.join(
            os.path.dirname(__file__),
            "platform-tools",
            "adb.exe"
        )
        os.makedirs(screenshot_dir, exist_ok=True)
        self._connect_device()
        self.screen_width, self.screen_height = self._get_screen_size()
        
        print(f"✅ MuMu模拟器初始化成功")
        print(f"   设备: {self.device_id}")
        print(f"   屏幕尺寸: {self.screen_width}x{self.screen_height}")
    
    def restart_device(self, device_id: str):
        print(f"切换ADB设备: {device_id}")

        self.device_id = device_id

        subprocess.run(
            f'"{self.adb_path}" kill-server',
            shell=True
        )

        time.sleep(1)

        subprocess.run(
            f'"{self.adb_path}" start-server',
            shell=True
        )

        time.sleep(1)

        self._connect_device()

        self.screen_width, self.screen_height = self._get_screen_size()

        return {
            "success": True,
            "device_id": self.device_id,
            "size": [
                self.screen_width,
                self.screen_height
            ]
        }
    def change_device(self, device_name: str) -> Dict:
        """更换机型（通过修改ADB属性）"""
        if device_name not in self.DEVICE_CONFIGS:
            return {"success": False, "message": f"未知机型: {device_name}"}
        
        config = self.DEVICE_CONFIGS[device_name]
        self.device_config = config
        
        # 修改系统属性来模拟机型
        self._run_adb(f"shell setprop ro.product.model \"{config['name']}\"")
        self._run_adb(f"shell wm size {config['width']}x{config['height']}")
        self._run_adb(f"shell wm density {config['dpi']}")
        
        self.screen_width = config['width']
        self.screen_height = config['height']
        
        return {"success": True, "message": f"已切换到 {config['name']}", "config": config}
    
    def _run_adb(self, cmd: str, capture_output: bool = True) -> subprocess.CompletedProcess:
        """执行 ADB 命令 - 修复编码问题"""
        full_cmd = f'"{self.adb_path}" -s {self.device_id} {cmd}'
        if capture_output:
            return subprocess.run(
                full_cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                encoding='utf-8',  # 指定 UTF-8 编码
                errors='ignore'    # 忽略无法解码的字符
            )
        else:
            return subprocess.run(full_cmd, shell=True)
    
    def _connect_device(self):
        subprocess.run(f'"{self.adb_path}" connect {self.device_id}', shell=True, capture_output=True)
        time.sleep(1)
    
    def _get_screen_size(self) -> Tuple[int, int]:
        result = self._run_adb("shell wm size")
        output = result.stdout.strip()
        if ":" in output:
            size_str = output.split(":")[-1].strip()
            return map(int, size_str.split("x"))
        return 720, 1280
    
    def click(self, x: int, y: int):
        x = x / 1000 * self.screen_width
        y = y / 1000 * self.screen_height
        self._run_adb(f"shell input tap {x} {y}")
        print(f"🖱️ 点击: ({x}, {y})")

        
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500):
        """
        滑动屏幕 - 针对 MuMu 模拟器优化
        """
        # 1. 坐标边界检查和修正
        start_x = start_x / 1000 * self.screen_width
        start_y = start_y / 1000 * self.screen_height
        end_x = end_x / 1000 * self.screen_width
        end_y = end_y / 1000 * self.screen_height
        start_x = max(0, min(start_x, self.screen_width))
        start_y = max(0, min(start_y, self.screen_height))
        end_x = max(0, min(end_x, self.screen_width))
        end_y = max(0, min(end_y, self.screen_height))

        # 确保滑动距离足够大（至少 200 像素），否则可能无效
        if abs(end_x - start_x) < 50 and abs(end_y - start_y) < 50:
            print(f"⚠️ 滑动距离过短 ({abs(end_x - start_x)}, {abs(end_y - start_y)})，可能无效")
            # 如果是上下滑动，强制增加滑动距离
            if abs(end_y - start_y) < 50:
                end_y = start_y + 400 if end_y > start_y else start_y - 400
                end_y = max(0, min(end_y, self.screen_height))
                print(f"   已自动调整为: ({start_x},{start_y}) -> ({end_x},{end_y})")

        print(f"👆 执行滑动: ({start_x},{start_y}) -> ({end_x},{end_y}) 时长={duration}ms")

        # 2. 滑动前先确保获取了焦点 (点击一下滑动起始点)

        # 3. 依次尝试三种滑动指令，直到成功
        commands = [
            f"shell input touchscreen swipe {start_x} {start_y} {end_x} {end_y} {duration}",
            f"shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}",
            f"shell input swipe {start_x} {start_y} {end_x} {end_y}",  # 不带时长参数的版本
        ]

        for i, cmd in enumerate(commands):
            print(f"   尝试方式 {i+1}: {cmd}")
            result = self._run_adb(cmd)
            if result.returncode == 0:
                print(f"   ✅ 方式 {i+1} 执行成功")
                break
            else:
                print(f"   ❌ 方式 {i+1} 失败: {result.stderr}")

        # 等待滑动动画和界面响应完成（关键！）
        time.sleep(0.8)
        print(f"✅ 滑动流程完成")
    
    def input_text(self, text: str):
        """输入文本 - 最终可用版本"""
        # 确保 ADBKeyboard 是当前输入法
        self._run_adb("shell ime set com.android.adbkeyboard/.AdbIME")
        time.sleep(0.1)

        escaped_text = shlex.quote(text)

        self._run_adb(
            f"shell am broadcast -a ADB_INPUT_TEXT --es msg {escaped_text}"
        )
        
        # 发送文本
        # self._run_adb(f'shell am broadcast -a ADB_INPUT_TEXT --es msg "{text}"')
        print(f"⌨️ 输入: {text}")
    
    def press_home(self):
        self._run_adb("shell input keyevent KEYCODE_HOME")
        print("🏠 返回主页")
    
    def press_back(self):
        self._run_adb("shell input keyevent KEYCODE_BACK")
        print("🔙 返回")
    
    def clear_all_tasks(self):
        """清除所有后台进程"""
        self._run_adb("shell input keyevent KEYCODE_APP_SWITCH")
        time.sleep(0.5)
        self._run_adb("shell input keyevent KEYCODE_MENU")
        time.sleep(0.5)
        self.press_home()
        print("🗑️ 清除所有后台任务")
    
    def shutdown_app(self, package_name: str = None):
        """关闭指定应用"""
        if package_name:
            self._run_adb(f"shell am force-stop {package_name}")
            print(f"⛔ 关闭应用: {package_name}")
    
    def screenshot(self, filename: str = None) -> str:
        """截取屏幕并保存 - 修复编码问题"""
        if filename is None:
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        local_path = os.path.abspath(os.path.join(self.screenshot_dir, f"{filename}.png"))
        
        # 使用 shell 重定向，避免编码问题
        cmd = f'"{self.adb_path}" -s {self.device_id} exec-out screencap -p > "{local_path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        if os.path.exists(local_path) and os.path.getsize(local_path) > 100:
            print(f"📸 截图成功: {local_path}")
            return local_path
        else:
            print(f"❌ 截图失败: 文件不存在或太小")
            return None
    
    def install_app(self, apk_path: str) -> bool:
        """安装APK"""
        if not os.path.exists(apk_path):
            return False
        result = self._run_adb(f"install -r \"{apk_path}\"")
        return "Success" in result.stdout
    
    def start_app(self, package_name: str):
        """启动应用"""
        self._run_adb(f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
        print(f"🚀 启动: {package_name}")
    
    def execute_command(self, command: Dict) -> Dict:
        """执行命令"""
        action = command.get('action', '').upper()
        coordinates = command.get('coordinates', [])
        text = command.get('text', '')
        
        result = {
            'success': True,
            'action': action,
            'message': '',
            'screenshot_path': None
        }
        
        try:
            if action == 'CLICK':
                if coordinates and len(coordinates[0]) == 2:
                    self.click(coordinates[0][0], coordinates[0][1])
                else:
                    raise ValueError("需要有效坐标")
            
            elif action == 'SCROLL':
                if len(coordinates) >= 2:
                    self.swipe(coordinates[0][0], coordinates[0][1],
                              coordinates[1][0], coordinates[1][1])
                else:
                    raise ValueError("需要起始和结束坐标")
            
            elif action == 'TEXT':
                if text:
                    self.input_text(text)
                else:
                    raise ValueError("需要文本内容")
            
            elif action == 'HOME':
                self.press_home()
            
            elif action == 'BACK':
                self.press_back()
            
            elif action == 'SHUTDOWN':
                self.shutdown_app(text if text else None)
            
            elif action == 'CLEAR_TASKS':
                self.clear_all_tasks()
            
            elif action == 'SCREENSHOT':
                save_name = text if text else None
                screenshot_path = self.screenshot(save_name)
                result['screenshot_path'] = screenshot_path
            
            else:
                raise ValueError(f"不支持的操作: {action}")
            
            result['message'] = f"命令执行成功"
            
        except Exception as e:
            result['success'] = False
            result['message'] = str(e)
        
        return result


# 全局控制器实例
controller = None


# ========== HTTP API 接口 ==========

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


@app.route('/device/info', methods=['GET'])
def device_info():
    """获取设备信息"""
    return jsonify({
        'device_id': controller.device_id,
        'screen_width': controller.screen_width,
        'screen_height': controller.screen_height,
        'current_config': controller.device_config
    })

@app.route('/device/list', methods=['GET'])
def device_list():
    result = subprocess.run(
        f'"{controller.adb_path}" devices',
        shell=True,
        capture_output=True,
        text=True
    )

    devices=[]

    for line in result.stdout.splitlines():
        if "\tdevice" in line:
            devices.append(
                line.split("\t")[0]
            )

    return jsonify({
        "devices":devices
    })


@app.route('/device/select', methods=['POST'])
def device_select():

    data=request.json

    device_id=data.get(
        "device_id"
    )

    result=controller.restart_device(
        device_id
    )

    return jsonify(result)

@app.route('/device/change', methods=['POST'])
def change_device():
    """更换机型"""
    data = request.json
    device_name = data.get('device_name', 'default')
    result = controller.change_device(device_name)
    return jsonify(result)


@app.route('/execute', methods=['POST'])
def execute():
    """
    执行控制命令
    请求体格式: {"action": "CLICK", "coordinates": [[734, 926]], "text": ""}
    """
    command = request.json
    result = controller.execute_command(command)
    return jsonify(result)


@app.route('/execute/batch', methods=['POST'])
def execute_batch():
    """批量执行命令"""
    commands = request.json.get('commands', [])
    results = []
    for cmd in commands:
        result = controller.execute_command(cmd)
        results.append(result)
        time.sleep(0.3)  # 避免执行过快
    return jsonify({'results': results, 'count': len(results)})


@app.route('/screenshot/latest', methods=['GET'])
def latest_screenshot():
    """获取最新截图路径"""
    screenshots = sorted(os.listdir(controller.screenshot_dir))
    if screenshots:
        latest = screenshots[-1]
        return jsonify({
            'path': os.path.join(controller.screenshot_dir, latest),
            'filename': latest,
            'timestamp': latest.replace('screenshot_', '').replace('.png', '')
        })
    return jsonify({'error': '没有截图'}), 404


@app.route('/app/install', methods=['POST'])
def install_app():
    """安装APK"""
    data = request.json
    apk_path = data.get('apk_path', '')
    result = controller.install_app(apk_path)
    return jsonify({'success': result, 'apk_path': apk_path})


@app.route('/app/start', methods=['POST'])
def start_app():
    """启动应用"""
    data = request.json
    package_name = data.get('package_name', '')
    controller.start_app(package_name)
    return jsonify({'success': True, 'package_name': package_name})


@app.route('/app/stop', methods=['POST'])
def stop_app():
    """停止应用"""
    data = request.json
    package_name = data.get('package_name', '')
    controller.shutdown_app(package_name)
    return jsonify({'success': True, 'package_name': package_name})

if __name__ == '__main__':
    if sys.stdout:
        sys.stdout.reconfigure(
            encoding="utf-8"
        )

    if sys.stderr:
        sys.stderr.reconfigure(
            encoding="utf-8"
        )
    controller = MuMuController()

    print("="*50)
    print("🚀 MuMu 模拟器 API 服务器启动")
    print("="*50)
    print(f"📱 设备: {controller.device_id}")
    print(f"📐 分辨率: {controller.screen_width}x{controller.screen_height}")
    print(f"🌐 API地址: http://localhost:5000")
    print(f"📸 截图目录: {controller.screenshot_dir}")
    print("="*50)
    print("\n可用接口:")
    print("  POST /execute        - 执行单条命令")
    print("  POST /execute/batch  - 批量执行命令")
    print("  GET  /device/info    - 获取设备信息")
    print("  POST /device/change  - 更换机型")
    print("  GET  /health         - 健康检查")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)