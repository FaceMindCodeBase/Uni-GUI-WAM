import gradio as gr
import uuid
import time
import shutil
import json
import requests
import subprocess
import atexit
import sys
from pathlib import Path

from tools.api_client import infer
from tools.adb_client import MuMuExecutor
from tools.image_utils import visualize

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
TASK_LIST = [
    "在B站搜索关于志愿填报的视频，按播放多排序，任选一个视频点赞收藏，然后在该视频评论区发送评论“今天是7月28日”",
    "把b站历史记录第一个视频分享给任意一个B站好友，并且留言“好看”",
    "在B站找到好友芝芝的晴小姐，给他发送消息“关注叠叠社谢谢喵”",
    "打开B站搜索“搞笑视频”，筛选播放多，选择第一个视频并给该视频点赞和收藏，投币一个硬币，评论该视频“好玩哈哈哈哈”，最后将该视频分享给好友“林允儿最美了”。",
    "打开B站进入会员购，将购物车中的商品全部删除，删除后在会员购中搜索罗小黑，筛选现货，任意选择一个商品加入购物车。",
    "打开B站进入番剧板块，筛选日本，漫画改，正片，免费。任意选择一个番剧进入，点击追番按钮进行追番。",
    "打开小红书，找一个上海旅游的帖子，点赞收藏然后发给私信好友列表里最近聊过天的好友，留言“这个看着还行”",
    "在小红书上发布一条动态，选择第一张人物图片，文字部分写“纯美”，设为仅自己可见后发布，然后给这条动态点赞",
    "打开小红书进入购物车，将购物车内的商品全部删除。删除完成后进入市集搜索初音未来，筛选条件为价格升序。选择第一个商品加入购物车，之后进入购物车将刚才加入购物车的商品进行下单，收货地址填写“张三，上海市奉贤区南桥镇金昊丽苑4号楼7002，17889927709”，只提交订单不支付。",
    "小红书把字体调大一点，然后去搜索上海旅游的帖子，随便点一个，点赞收藏并且分享给最近聊天的好友",
    "打开小红书给好友“故渊”发送一条消息，消息内容为“你在干什么呐”，之后将浏览记录的第一条帖子发送给他，并留言“漂亮”",
    "在小红书市集里搜索绝区零薇薇安相关的商品，筛选价格最高的商品加入购物车，分享给最近聊过天的私信好友，并留言“送我”",
    "小红书集市搜索送给女生最好的小礼物，然后记住名字，到b站会员购里看一下有没有的卖，有的话就放到购物车里",
    "在QQ空间中发布一条说说，内容为“他真好看”，选择相册中第一张人物图像作为配图，设置为仅自己可见后发布，发布后给这条说说点赞，并且评论“确实”",
    "打开微信给好友“柒”发送2条消息内容分别为“AITest”，“赛里木湖很美”，然后发送最近使用过的第一个黄脸emoji",
    "在腾讯地图中查找从当前位置到上海南站的路线，选择地铁优先路线，并开始导航",
    "打开美团外卖搜索蜜雪冰城，筛选4.5星以上的店铺，筛选后随意选择一家店，将两份蜜桃四季春加入购物车，若不足起送费用则添加其他商品凑单，停留在提交订单的页面",
    "在美团中新增地址，地址：上海市奉贤区南桥镇杨王高新技术产业园区，门牌号：美团外卖柜，姓名：小柒，手机号：15515555151",
    "打开美团给最近的一单“老乡鸡”的订单进行评价，给商家五星好评以及骑手好评，并评论“吃过好多次了，感觉很好吃，推荐推荐”。",
    "打开美团将我收藏的店铺中关于“米粉”的店铺全部取消收藏。",
    "打开美团找到我上次点的老乡鸡的订单，再下一单一样套餐的订单只提交订单不支付。",
    "打开美团购买一张今天的“功夫女足”的电影票。",
    "打开美团点击外卖搜索“一点点”，进入第一个店铺下单一杯奶茶，只提交订单不支付",
    "在12306中买一张8月5日从沈阳到长春的火车票，筛选高铁动车、智能动车、二等座。买一张耗时最短车票，选择乘车人但不要提交订单",
    "在12306上查询8月5日从北京飞往杭州的机票，按价格从低到高排序，找一个下午两点到下午七点出发的最便宜机票，选择出行人，停在提交订单页面",
    "在淘宝搜索零食，筛选包邮，50元以下，然后任选两件商品加入购物车，然后去购物车下单这两个商品，停留在提交订单页面",
    "在淘宝搜索短袖，筛选尺码XL，成分纯棉；把前两件商品的黑色款式加入购物车，然后进入购物车删除他们",
    "在淘宝中使用粘贴板快速新增收货地址，内容为小涛，19974549437，浙江省杭州市钱塘区悦邻中心666号",
    "在QQ群“FM测试群”中@mizuki，发送消息“我不去了”",
    "打开微信创建一个群聊，选择“柒”，“梦想要坚持比如uzi”这2位好友，创建完成后在群里@柒，发送“群建好了来聊天”",
    "把小红书深色模式切换一下"
]

SERVER_URL="http://36.213.164.160:8302/api/plan"
ADB_SERVER="http://127.0.0.1:5000"
ADB_PROCESS = None

def start_adb_server():
    global ADB_PROCESS
    if ADB_PROCESS is not None:
        return
    adb_server_path = Path(__file__).parent / "adb_server.py"
    ADB_PROCESS = subprocess.Popen(
        [
            sys.executable,
            str(adb_server_path)
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(2)

    print("ADB Server 已启动")

def stop_adb_server():

    global ADB_PROCESS

    if ADB_PROCESS:

        ADB_PROCESS.terminate()

        ADB_PROCESS = None

        print("ADB Server 已关闭")

def wait_adb_server():

    for _ in range(20):
        try:
            r = requests.get(
                f"{ADB_SERVER}/health",
                timeout=1
            )
            if r.status_code == 200:
                return True

        except:
            pass
        time.sleep(0.5)
    return False

def find_latest_image():
    screenshot_dir = Path("screenshots")
    imgs = list(screenshot_dir.glob("*.png"))
    if not imgs:
        raise RuntimeError("没有找到截图")
    return str(
        max(
            imgs,
            key=lambda x: x.stat().st_mtime
        )
    )

def get_devices():
    try:
        r = requests.get(
            "http://127.0.0.1:5000/device/list",
            timeout=3
        )
        data = r.json()
        return data.get(
            "devices",
            []
        )
    except Exception as e:
        print("获取设备失败:", e)
        return []

def select_device(device_id):
    try:
        r=requests.post(
            f"{ADB_SERVER}/device/select",
            json={
                "device_id":device_id
            },
            timeout=10
        )

        return (
            f"已切换设备:{device_id}"
        )

    except Exception as e:

        return (
            f"设备切换失败:{e}"
        )

def auto_select_device():

    devices = get_devices()

    if len(devices) == 1:

        device_id = devices[0]

        try:
            requests.post(
                f"{ADB_SERVER}/device/select",
                json={
                    "device_id": device_id
                },
                timeout=10
            )

            return (
                gr.update(
                    value=device_id,
                    choices=devices
                ),
                f"自动选择设备:{device_id}"
            )

        except Exception as e:

            return (
                gr.update(
                    choices=devices
                ),
                f"设备切换失败:{e}"
            )


    return (
        gr.update(
            choices=devices
        ),
        "检测到多个设备，请手动选择"
    )

def run_agent(task_select, custom_task, seed,device_id):
    task = custom_task.strip()
    if not task:
        raise gr.Error("任务不能为空")

    task_id = f"{time.strftime('%Y%m%d-%H%M%S')}_{task.replace(' ', '_')}"

    task_dir = OUTPUT_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)


    adb = MuMuExecutor(
        host="127.0.0.1",
        port=5000
    )

    adb.screenshot("step_0")
    before_image = find_latest_image()
    current_image = task_dir / "step_0.png"
    shutil.copy(before_image, current_image)

    config = {
        "seed": int(seed)
    }

    MAX_STEP = 50
    
    action_history = []
    plan = ""
    final_visualize = str(current_image)
    yield (
        "任务启动中...",
        {},
        final_visualize
    )
    for step in range(1, MAX_STEP + 1):
        print(f"STEP {step}:",end=" ")

        step_before = current_image

        # 请求模型
        yield (
            f"Step {step}: 模型推理中...",
            {},
            final_visualize
        )
        try:
            result = infer(
                image_path=str(step_before),
                task=task,
                task_id=task_id,
                step=step,
                action_history=action_history,
                plan=plan,
                config=config,
                server_url=SERVER_URL
            )

        except Exception as e:
            error_text = str(e)

            try:
                error_json = json.loads(error_text)
            except:
                error_json = {"error": error_text}

            print("模型请求失败:", error_json)

            yield (
                "模型请求失败:\n" + json.dumps(error_json, ensure_ascii=False, indent=2),
                error_json,
                final_visualize
            )

            return
        # print(result)
        if "action" not in result:
            raise RuntimeError(f"模型返回错误:{result}")
        yield (
            f"Step {step}: 推理完成",
            result,
            final_visualize
        )
        print(result["action"])
        raw_action = result["action"]

        # 兼容action格式
        if isinstance(raw_action, str):
            action = {
                "action": raw_action,
                "coordinates": result.get("coordinates", []),
                "text": result.get("text", "")
            }
        else:
            action = raw_action

        if "plan" in result:
            plan = result["plan"]

        history_item = {
            "step": step,
            "action": action,
            "result": None
        }

        # 保存action
        with open(
            task_dir / f"step_{step}_action.txt",
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                action,
                f,
                ensure_ascii=False,
                indent=4
            )

        # 完成
        if action.get("action") in ["STOP"]:
            action_history.append(history_item)
            print("*"*50)
            print("任务结束")
            print("*"*50)
            yield (
                "任务结束",
                action,
                final_visualize
            )
            break

        # 执行动作
        yield (
            f"Step {step}: 执行动作 {action['action']}",
            action,
            final_visualize
        )
        execute_result = adb.execute(action)
        history_item["result"] = execute_result
        action_history.append(history_item)
        time.sleep(2)

        # 获取执行后截图

        adb.screenshot(f"step_{step}")

        after_image = find_latest_image()

        after_save = task_dir / f"step_{step}.png"

        shutil.copy(
            after_image,
            after_save
        )


        # 生成可视化图片
        visualize_path = task_dir / f"step_{step}_pred_{action['action']}.png"

        visualize(
            before=str(step_before),
            after=str(after_save),
            action=action,
            save_path=str(visualize_path)
        )

        final_visualize = str(visualize_path)

        # 下一step输入
        current_image = after_save
        # 实时刷新Gradio
        yield (
            f"Step {step}: 执行完成",
            action,
            final_visualize
        )

start_adb_server()

if not wait_adb_server():
    raise RuntimeError("ADB Server启动失败")

atexit.register(
    stop_adb_server
)

with gr.Blocks() as demo:
    gr.Markdown("# FM GUI Client")

    # Task
    with gr.Row():

        task_select = gr.Dropdown(
            choices=TASK_LIST,
            value=TASK_LIST[0],
            label="任务模板"
        )

        custom_task = gr.Textbox(
            value=TASK_LIST[0],
            label="执行任务",
            lines=5
        )


    # 推理参数
    with gr.Row():
        seed = gr.Number(value=42,label="Seed")

    # adb配置
    gr.Markdown("ADB设备")
    device_dropdown = gr.Dropdown(
        choices=[],
        label="选择设备",
        interactive=True
    )

    refresh_btn = gr.Button(
        "刷新设备"
    )

    device_status = gr.Textbox(
        label="设备状态",
        interactive=False
    )
    refresh_btn.click(
        fn=auto_select_device,
        outputs=[
            device_dropdown,
            device_status
        ]
    )
    device_dropdown.change(
        fn=select_device,
        inputs=device_dropdown,
        outputs=device_status
    )
    run_btn = gr.Button(
        "执行",
        variant="primary"
    )


    with gr.Row():
        with gr.Column(scale=1):

            status_output = gr.Textbox(
                label="运行状态",
                value="等待执行",
                interactive=False
            )

            action_output = gr.JSON(
                label="当前Action"
            )


        with gr.Column(scale=1):

            image_output = gr.Image(
                label="执行结果",
                type="filepath",
                image_mode="contain",
                height=700,
                width=700
            )
    task_select.change(
        fn=lambda x: x,
        inputs=task_select,
        outputs=custom_task
    )
    run_btn.click(
        fn=run_agent,
        inputs=[
            task_select,
            custom_task,
            seed,
            device_dropdown
        ],
        outputs=[
            status_output,
            action_output,
            image_output
        ]
    )
    demo.load(
        fn=auto_select_device,
        outputs=[
            device_dropdown,
            device_status
        ]
    )
    
demo.launch(
    server_name="127.0.0.1",
    server_port=8123
)