import os
import json
from collections import defaultdict
import openpyxl
import re
from openpyxl.styles import Font, Alignment
import shutil

# Define path
base_dir = './'
# base_dir = './../processed_result/base_agent_multi/qwen2.5-7B-Instruct/supplement/2/'
output_excel_path = 'SFT base agent.xlsx'

def base_agent_filter():

    # Initialize statistics
    score_100_distribution = defaultdict(int)  # Number of folders with score of 100

    # Traverse all folders in the current path
    for folder_name in os.listdir(base_dir):
        if os.path.isdir(os.path.join(base_dir, folder_name)):
            # Parse folder name
            parts = folder_name.split('_')
            category = parts[0]

            # If it is the interact category, further parse the subcategory
            if category == 'interact' and len(parts) > 1:
                subcategory = parts[1]
                category = f"interact_{subcategory}"  # Use interact_subcategory as the category name

            # Check score.json file
            score_json_path = os.path.join(base_dir, folder_name, 'score.json')
            folder_path = os.path.join(base_dir, folder_name)
            if os.path.exists(score_json_path):
                with open(score_json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                # Check if 'score' field exists and equals 100
                if data.get('score') == 100:
                    score_100_distribution[category] += 1
                # else:
                #     # Delete folders where value is not 100
                #     shutil.rmtree(folder_path)  # <-- Modified: delete this folder
                #     print(f"Deleted folder: {folder_name}")  # <-- Modified: log message
            else:
                shutil.rmtree(folder_path)  # <-- Modified: delete this folder
                print(f"已删除文件夹：{folder_name}")

    # Create Excel file
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "QWEN"

    # Write header
    ws.append(["类别", "score 为 100 的文件夹数量"])

    # Write distribution for score of 100
    for category, count in score_100_distribution.items():
        ws.append([category, count])

    # Save Excel file
    wb.save(output_excel_path)

    print(f"统计结果已保存到 {output_excel_path}")


def base_agent_multi_filter():
    folders = [os.path.join(base_dir, f) for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    construction_results = []
    farming_results = []

    for folder in sorted(folders):  # Lexicographical order
        score_path = os.path.join(folder, "score.json")
        if not os.path.exists(score_path):
            continue

        match = re.search(r"task(\d+)", folder)
        task_idx = int(match.group(1)) if match else None

        with open(score_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if "construction" in folder.lower():
            construction_results.append({
                "task_idx": task_idx,
                "block_hit_rate": data.get("block_hit_rate", 0.0),
                "view_hit_rate": data.get("view_hit_rate", 0.0)
            })
        elif "farming" in folder.lower():
            farming_results.append({
                "task_idx": task_idx,
                "score": data.get("score", 0.0),
                "cooperation": data.get("cooperation", 0.0),
                "efficiency": data.get("efficiency", 0.0),
                "balance": data.get("balance", 0.0)
            })

    wb = openpyxl.Workbook()

    # Style definition
    font = Font(name="SimHei")  # Bold
    align = Alignment(horizontal="center", vertical="center")

    # ===== Construction Sheet =====
    ws1 = wb.active
    ws1.title = "construction"
    ws1.append(["task_idx", "bhr", "vhr"])
    for r in sorted(construction_results, key=lambda x: x["task_idx"]):
        ws1.append([
            r["task_idx"],
            round(r["block_hit_rate"], 3),
            round(r["view_hit_rate"], 3)
        ])
    if construction_results:
        avg_block = sum(r["block_hit_rate"] for r in construction_results) / len(construction_results)
        avg_view = sum(r["view_hit_rate"] for r in construction_results) / len(construction_results)
        ws1.append(["Average", round(avg_block, 3), round(avg_view, 3)])

    # ===== Farming Sheet =====
    ws2 = wb.create_sheet("farming")
    ws2.append(["task_idx", "score", "cooperation", "efficiency", "balance"])
    for r in sorted(farming_results, key=lambda x: x["task_idx"]):
        ws2.append([r["task_idx"], round(r["score"], 3), round(r["cooperation"], 3), round(r["efficiency"], 3), round(r["balance"], 3)])
    if farming_results:
        avg_score = sum(r["score"] for r in farming_results) / len(farming_results)
        avg_cooperation = sum(r["cooperation"] for r in farming_results) / len(farming_results)
        avg_efficiency = sum(r["efficiency"] for r in farming_results) / len(farming_results)
        avg_balance = sum(r["balance"] for r in farming_results) / len(farming_results)
        ws2.append(["Average", round(avg_score, 3), round(avg_cooperation, 3), round(avg_efficiency, 3), round(avg_balance, 3)])

    # ===== Apply format =====
    for ws in [ws1, ws2]:
        for row in ws.iter_rows():
            for cell in row:
                cell.font = font
                cell.alignment = align

    wb.save(base_dir + "base agent multi.xlsx")
    print("✅ 结果已保存到 base agent multi.xlsx")

# Run
if __name__ == "__main__":
    # base_agent_filter()
    base_agent_multi_filter()
