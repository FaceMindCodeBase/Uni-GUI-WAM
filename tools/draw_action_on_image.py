
from PIL import Image, ImageDraw
import numpy as np
from pathlib import Path
def load_image(image_path: str) -> Image.Image:
    """读取本地图片，转成 RGB。"""
    return Image.open(image_path).convert("RGB")

def get_pix_dist(gt_x, gt_y, pred_x, pred_y, image_path):
    image = load_image(image_path)
    w, h = image.size

    tx = gt_x / 1000 * w
    ty = gt_y / 1000 * h
    px = pred_x / 1000 * w
    py = pred_y / 1000 * h
    dist = ((tx - px) ** 2 + (ty - py) ** 2) ** 0.5

    return dist

def norm_to_pixel(x, y, w, h):
    """
    将 0-1000 归一化坐标转换成图像像素坐标。
    注意：这里按 image1 的尺寸转换，因为绘图都画在左侧 image1 上。
    """
    px = int(round(float(x) / 1000 * w))
    py = int(round(float(y) / 1000 * h))
    return px, py

def draw_circle(draw, x, y, color, radius=10):
    draw.ellipse(
        [
            x - radius,
            y - radius,
            x + radius,
            y + radius,
        ],
        fill=color
    )

def draw_arrow(draw, start, end, color, width=5, arrow_len=25, arrow_width=12):
    """
    绘制从 start 到 end 的箭头。
    """
    x1, y1 = start
    x2, y2 = end

    draw.line([start, end], fill=color, width=width)

    dx = x2 - x1
    dy = y2 - y1
    length = (dx ** 2 + dy ** 2) ** 0.5

    if length < 1e-6:
        return

    ux = dx / length
    uy = dy / length

    # 垂直方向
    nx = -uy
    ny = ux

    p1 = (
        x2 - ux * arrow_len + nx * arrow_width,
        y2 - uy * arrow_len + ny * arrow_width,
    )
    p2 = (
        x2 - ux * arrow_len - nx * arrow_width,
        y2 - uy * arrow_len - ny * arrow_width,
    )

    draw.polygon([end, p1, p2], fill=color)

def draw_action_on_layer(
    layer,
    action,
    coordinates,
    image_w,
    image_h,
    color,
    point_radius=10,
    line_width=5,
):
    """
    在单独的透明 layer 上绘制一个 action。
    坐标基于 image1，也就是拼接图左半部分。
    """
    if action is None:
        return

    action = action.upper()
    draw = ImageDraw.Draw(layer)

    if coordinates is None:
        return

    if action in ["CLICK", "LONG_PRESS"]:
        if len(coordinates) < 1:
            return
        if (
            len(coordinates) == 2
            and isinstance(coordinates[0], (int, float))
            and isinstance(coordinates[1], (int, float))
        ):
            x, y = coordinates

        else:
            x, y = coordinates[0]
        px, py = norm_to_pixel(x, y, image_w, image_h)

        draw_circle(
            draw,
            px,
            py,
            color=color,
            radius=point_radius,
        )

    elif action == "SCROLL":
        if len(coordinates) < 2:
            return

        x1, y1 = coordinates[0]
        x2, y2 = coordinates[1]

        start = norm_to_pixel(x1, y1, image_w, image_h)
        end = norm_to_pixel(x2, y2, image_w, image_h)

        # 先画箭头，再画起点圆点，避免圆点被线覆盖。
        draw_arrow(
            draw,
            start,
            end,
            color=color,
            width=line_width,
        )

        draw_circle(
            draw,
            start[0],
            start[1],
            color=color,
            radius=point_radius,
        )

    elif action == "TEXT":
        # 文本输入事件无需绘图。
        return
    
def draw_eval_visualization(
    image1_path,
    image2_path,
    gt_action,
    gt_coordinates,
    pred_action,
    pred_coordinates,
    save_path,
    point_radius=10,
    line_width=5,
):
    """
    1. 将 image1 拼接到左边，image2 拼接到右边。
    2. gt 用红色绘制。
    3. pred 用绿色绘制。
    4. 红绿重叠区域用紫色绘制。
    """
    image1 = load_image(image1_path).convert("RGB")
    image2 = load_image(image2_path).convert("RGB")

    w, h = image1.size

    # 用户说了两张图尺寸完全一致，所以这里不做尺寸检查。
    canvas = Image.new("RGB", (w * 2, h))
    canvas.paste(image1, (0, 0))
    canvas.paste(image2, (w, 0))

    canvas_rgba = canvas.convert("RGBA")

    # 分别画真实值图层和预测值图层。
    gt_layer = Image.new("RGBA", canvas_rgba.size, (0, 0, 0, 0))
    pred_layer = Image.new("RGBA", canvas_rgba.size, (0, 0, 0, 0))

    red = (255, 0, 0, 180)
    green = (0, 255, 0, 180)

    draw_action_on_layer(
        gt_layer,
        gt_action,
        gt_coordinates,
        w,
        h,
        color=red,
        point_radius=point_radius,
        line_width=line_width,
    )

    draw_action_on_layer(
        pred_layer,
        pred_action,
        pred_coordinates,
        w,
        h,
        color=green,
        point_radius=point_radius,
        line_width=line_width,
    )

    # 用 alpha mask 判断红绿是否重叠。
    gt_arr = np.array(gt_layer)
    pred_arr = np.array(pred_layer)

    gt_mask = gt_arr[..., 3] > 0
    pred_mask = pred_arr[..., 3] > 0

    only_gt = gt_mask & ~pred_mask
    only_pred = pred_mask & ~gt_mask
    overlap = gt_mask & pred_mask

    overlay_arr = np.zeros_like(gt_arr)

    overlay_arr[only_gt] = np.array([255, 0, 0, 180], dtype=np.uint8)
    overlay_arr[only_pred] = np.array([0, 255, 0, 180], dtype=np.uint8)
    overlay_arr[overlap] = np.array([160, 0, 255, 220], dtype=np.uint8)

    overlay = Image.fromarray(overlay_arr, mode="RGBA")
    result = Image.alpha_composite(canvas_rgba, overlay).convert("RGB")

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(save_path)

    