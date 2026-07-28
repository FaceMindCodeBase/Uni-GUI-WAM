from pathlib import Path

from tools.draw_action_on_image import draw_eval_visualization

def visualize(
    before,
    after,
    action,
    save_path
):

    draw_eval_visualization(
        image1_path=before,
        image2_path=after,
        pred_action=
            action["action"],
        pred_coordinates=
            action.get(
                "coordinates",
                []
            ),
        gt_action=None,
        gt_coordinates=None,
        save_path=save_path,
        point_radius=50,
        line_width=25
    )
    return save_path