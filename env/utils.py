import sys
import re
import os
import numpy as np
import time
import json
from sklearn.cluster import HDBSCAN
from sklearn.preprocessing import MinMaxScaler
from javascript import require, On

import logging
import colorlog

sys.path.append(os.getcwd())
from common.logging import init_logger


def building_material_load(path,bot,dig_needed=False,inventory_load=False,agent_names=[]):
    # Return the number of blocks to mine
    import json
    with open(path, 'r') as f:
        map = json.load(f)
    material_pair = {}
    material_pair["dirt"] = 128
    material_pair["ladder"] = 128
    for block in map["blocks"]:
        if block["name"] == "water" or block["name"] == "lava":
            continue
        if ("log" in block["name"] or "stone" in block["name"]) and dig_needed:
            continue
        if block["name"] in material_pair:
            material_pair[block["name"]] += 1
        else:
            material_pair[block["name"]] = 1

    slot = 0
    #[DEBUG] print(material_pair)
    unStackable_items = ["bed"]
    for k,v in material_pair.items():
        name = k
        amount = v
        for agent_name in agent_names:
            bot.chat(f"/give {agent_name} {name} {amount}")
            time.sleep(.1)
        while amount > 0:
            # print(k,v)
            time.sleep(.1)
            hit = False
            if "potted" in name:
                name = name.replace("potted_","")
                bot.chat(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {64}')
                #[DEBUG] 
                # print(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {64}')
                slot += 1
                name = "flower_pot"
                bot.chat(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {64}')
                #[DEBUG] print(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {64}')
                amount -= 64
            elif "_wall_" in name:
                name = name.replace("_wall_","_")
                if "banner" in name:
                    bot.chat(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {16}')
                    #[DEBUG] print(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {16}')
                    amount -= 16
                else:
                    bot.chat(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {64}')
                    #[DEBUG] print(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {64}')
                    amount -= 64
            else:
                for tag in unStackable_items:
                    if tag in name:
                        hit = True
                        break
                if hit:
                    bot.chat(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {1}')
                    #[DEBUG] print(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {1}')
                    amount -= 1
                elif "banner" in name:
                    bot.chat(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {16}')
                    #[DEBUG] print(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {16}')
                    amount -= 16
                else:
                    bot.chat(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {64}')
                    #[DEBUG] 
                    # print(f'/item replace block -4 -60 0 container.{slot} with minecraft:{name} {64}')
                    amount -= 64
            slot += 1
            if slot >= 27:
                bot.chat('chest is full')
                
    # bot.chat(f'building material loaded to chest at -4 -60 0')

def material_factory_load(path,bot,envs_info,mcData,center_pos=[0,-60,0],rate = 0.5):
    import json
    with open(path, 'r') as f:
        map = json.load(f)
    
    material_pairs = []
    for block in map["blocks"]:
        if "log" not in block["name"] and "stone" not in block["name"]:
            continue
        material_pairs.append(block)
    
    # Calculate a pyramid-shaped H
    h_ = 0
    volume = 0
    for i in range(1,100,2):
        height = i
        width = int(rate * i)
        for j in range(-width//2,width//2):
            for k in range(-height//2,height//2):
                volume += 1
        h_ += 1
        if volume >= len(material_pairs):
            break
    size = h_ * 2
    
    # place the material
    idx = 0
    for i in range(1,100,2):
        h_ -= 1
        height = i
        width = int(rate * i)
        for j in range(-width//2,width//2):
            for k in range(-height//2,height//2):
                if idx >= len(material_pairs):
                    pos = (center_pos[0]+j,center_pos[1]+h_,center_pos[2]+k)
                    bot.chat(f'/setblock {pos[0]} {pos[1]} {pos[2]} {material_pairs[-1]["name"]}')
                else:
                    pos = (center_pos[0]+j,center_pos[1]+h_,center_pos[2]+k)
                    bot.chat(f'/setblock {pos[0]} {pos[1]} {pos[2]} {material_pairs[idx]["name"]}')
                idx += 1
        if idx >= len(material_pairs):
            break
    # set area dirt ground
    bot.chat(f'/fill {center_pos[0]-size//2} {center_pos[1]-1} {center_pos[2]-size//2} {center_pos[0]+size//2} {center_pos[1]-1} {center_pos[2]+size//2} podzol')

    # set fence and chest
    bot.chat(f'/fill {center_pos[0]-size//2} {center_pos[1]} {center_pos[2]-size//2} {center_pos[0]-size//2} {center_pos[1]+1} {center_pos[2]+size//2} oak_fence')
    bot.chat(f'/fill {center_pos[0]+size//2} {center_pos[1]} {center_pos[2]-size//2} {center_pos[0]+size//2} {center_pos[1]+1} {center_pos[2]+size//2} oak_fence')
    bot.chat(f'/fill {center_pos[0]-size//2} {center_pos[1]} {center_pos[2]-size//2} {center_pos[0]+size//2} {center_pos[1]+1} {center_pos[2]-size//2} oak_fence')
    bot.chat(f'/fill {center_pos[0]-size//2} {center_pos[1]} {center_pos[2]+size//2} {center_pos[0]+size//2} {center_pos[1]+1} {center_pos[2]+size//2} oak_fence')
    
    # set chest
    bot.chat(f'/setblock {center_pos[0] + size//2 - 1} {center_pos[1]} {center_pos[2] - size//2 + 1} chest')
    # set tools and cloth in chest
    bot.chat(f'/item replace block {center_pos[0] + size//2 - 1} {center_pos[1]} {center_pos[2] - size//2 + 1} container.1 with minecraft:iron_axe 1')
    bot.chat(f'/item replace block {center_pos[0] + size//2 - 1} {center_pos[1]} {center_pos[2] - size//2 + 1} container.2 with minecraft:iron_shovel 1')
    bot.chat(f'/item replace block {center_pos[0] + size//2 - 1} {center_pos[1]} {center_pos[2] - size//2 + 1} container.0 with minecraft:iron_pickaxe 1')
    bot.chat(f'/item replace block {center_pos[0] + size//2 - 1} {center_pos[1]} {center_pos[2] - size//2 + 1} container.3 with minecraft:iron_hoe 1')
    bot.chat(f'/item replace block {center_pos[0] + size//2 - 1} {center_pos[1]} {center_pos[2] - size//2 + 1} container.4 with minecraft:iron_sword 1')
    bot.chat(f'/item replace block {center_pos[0] + size//2 - 1} {center_pos[1]} {center_pos[2] - size//2 + 1} container.5 with minecraft:shield 1')
    bot.chat(f'/item replace block {center_pos[0] + size//2 - 1} {center_pos[1]} {center_pos[2] - size//2 + 1} container.6 with minecraft:leather_helmet 1')
    bot.chat(f'/item replace block {center_pos[0] + size//2 - 1} {center_pos[1]} {center_pos[2] - size//2 + 1} container.7 with minecraft:leather_chestplate 1')
    bot.chat(f'/item replace block {center_pos[0] + size//2 - 1} {center_pos[1]} {center_pos[2] - size//2 + 1} container.8 with minecraft:leather_leggings 1')

    # set door
    bot.chat(f'/setblock {center_pos[0]} {center_pos[1]} {center_pos[2] + size//2} minecraft:air')
    bot.chat(f'/setblock {center_pos[0]} {center_pos[1]+1} {center_pos[2] + size//2} minecraft:air')

    # set sign
    bot.chat(f'/setblock {center_pos[0]} {center_pos[1]} {center_pos[2] + size//2 + 1} minecraft:oak_wall_sign[facing=south]')
    bot.chat(f"/data merge block {center_pos[0]} {center_pos[1]} {center_pos[2] + size//2 + 1} {{Text1:'{{\"text\":\"Material Factory\"}}',Text2:'{{\"text\":\"Get materials from here\"}}',Text3:'{{\"text\":\"\"}}',Text4:'{{\"text\":\"\"}}'}}")
    return material_pairs

def split_structure(building):
    from common.optional import optional_dependencies
    with optional_dependencies("construction"):
        from FlagEmbedding import LLMEmbedder
    print("Loading model...")
    model = LLMEmbedder('BAAI/llm-embedder', use_fp16=True)

    minecraftData = require('minecraft-data')
    mcData = minecraftData('1.19.2')
    # Create a MinMaxScaler object
    scaler = MinMaxScaler()

    building = building["blocks"]
    for block in building:
        block["faceId"] = 0
        face2faceId = {
            "A": 0,
            "N": 0.1,
            "S": 0.2,
            "E": 0.3,
            "W": 0.4,
            "x": 0.5,
            "y": 0.6,
            "z": 0.7,
        }
        block["faceId"] = face2faceId[block["facing"]]

        if block["name"] in mcData.itemsByName:
            block["id"] = mcData.itemsByName[block["name"]]["id"]
            emb = model.encode_queries(block["name"], task="qa")
            length = len(emb)
            embeddings = []
            for i in range(0, length, length // 3):
                embeddings.append(emb[i:i + length // 3].mean(0) + 0.3)
            block["embeddings"] = embeddings
        elif block["name"] in mcData.blocksByName:
            block["id"] = mcData.blocksByName[block["name"]]["id"]
            emb = model.encode_queries(block["name"], task="qa")
            length = len(emb)
            embeddings = []
            for i in range(0, length, length // 3):
                embeddings.append(emb[i:i + length // 3].mean(0) + 0.3)
            block["embeddings"] = embeddings
        else:
            block["id"] = 0
            block["embeddings"] = [0] * 3

    data = []
    for block in building:
        data.append([block["faceId"]] + block["position"] + [block["id"]] + block["embeddings"])
    data = np.array(data)
    # Normalize data using MinMaxScaler's fit_transform method
    data_normalized = scaler.fit_transform(data)

    hdb = HDBSCAN(min_cluster_size=2, min_samples=2, cluster_selection_epsilon=0.3, max_cluster_size=6)
    hdb.fit(data_normalized)
    labels = hdb.labels_
    data_clustered = []
    for j in range(len(labels)): # Handle noise terms separately
        if labels[j] == -1:
            data_clustered.append([[data_normalized[j],building[j]]])

    for i in range(0, max(labels) + 1):
        cluster = []
        for j in range(len(labels)):
            if labels[j] == i:
                cluster.append([data_normalized[j],building[j]])
        data_clustered.append(cluster)

    done = False
    solve_id = -1
    while not done:
        done = True
        # print("HDBSCAN")
        for i in range(len(data_clustered)):
            if len(data_clustered[i]) > 6 and solve_id < i:
                solve_id = i
                # Cluster larger clusters
                hdb = HDBSCAN(min_cluster_size=3, min_samples=3, cluster_selection_epsilon=0.2, max_cluster_size=6)
                data = [x[0] for x in data_clustered[i]]
                hdb.fit(data)
                labels = hdb.labels_
                for j in range(-1, max(labels) + 1):
                    cluster = []
                    for k in range(len(labels)):
                        if labels[k] == j:
                            cluster.append(data_clustered[i][k])
                    data_clustered.append(cluster)
                data_clustered.pop(i)
                done = False
    # save
    save_data = []
    for i in range(len(data_clustered)):
        cluster = []
        for j in range(len(data_clustered[i])):
            cluster.append({"position": data_clustered[i][j][1]["position"], "name": data_clustered[i][j][1]["name"], "facing": data_clustered[i][j][1]["facing"]})
        save_data.append(cluster)
    return reorder_cluster(clusters=save_data)

def reorder_cluster(clusters):
    # First calculate the mean coordinates of all squares to determine the center point
    total_x, total_y, total_z, total_count = 0, 0, 0, 0
    for cluster in clusters:
        for item in cluster:
            total_x += item["position"][0]
            total_y += item["position"][1]
            total_z += item["position"][2]
            total_count += 1
    center_x = total_x / total_count
    center_y = total_y / total_count
    center_z = total_z / total_count

    clusters = [cluster for cluster in clusters if len(cluster) > 0]
    # Sort within each cluster by y-coordinate from low to high
    for i, cluster in enumerate(clusters):
        clusters[i] = sorted(cluster, key=lambda item: item["position"][1])

    clusters = [cluster for cluster in clusters if len(cluster) > 0]
    # Then sort the entire list of clusters
    clusters.sort(key=lambda cluster: (
        min(item["position"][1] for item in cluster),  # Sort by minimum y-coordinate
        # If y-coordinates are the same, sort by distance to the center point
        min((item["position"][0] - center_x) ** 2 + (item["position"][1] - center_y) ** 2 + (item["position"][2] - center_z) ** 2 for item in cluster)
    ))
    
    # Construct sorted cluster data
    save_data = []
    for cluster in clusters:
        sorted_data = [{"position": item["position"], "name": item["name"], "facing": item["facing"]} for item in cluster]
        save_data.append(sorted_data)
    return save_data

describe_prompt = """
You are given a task to describe structure in a Minecraft world using a JSON format. The structures are used for various purposes like enclosures or platforms. To save space and tokens, you need to compress the information about these structures while maintaining all the necessary details for reconstruction. Here are the descriptions of the structures:

Using the information provided, create a compressed JSON representation of these structures that includes their material, facing direction, positions, and any other relevant details.

---

**Expected JSON Output:**
Example JSON output 1:
```json
[
    {
        "material": "cut_sandstone",
        "facing": "y",
        "position": [-10, -60, 2]
    }
]

Example JSON output 2:
```json
[
    {
        "material": "dark_oak_log",
        "facing": "y",
        "positions": [
            { "start": [-10, -60, 2], "end": [-9, -58, 2] },
            { "start": [-11, -60, 0], "end": [-11, -58, 1] }
        ],
    }
]
```
Example JSON output 3:
```json
[
    {
        "material": "dark_oak_slab",
        "facing": "A",
        "height": -57,
        "shape": "square",
        "corners": [
            [-11, -57, -1],
            [-8, -57, -1],
            [-11, -57, 2],
            [-8, -57, 2]
        ],
    }
]
```

Please generate the JSON output based on the prompt provided.
"""

def describe_map(building):
    mode = os.environ.get("VILLAGER_LOCAL_GENERATION_ONLY")
    if mode == "1":
        from model.init_model import init_language_model
        local_config = {"provider": "ollama", "api_model": os.environ["VILLAGER_LOCAL_MODEL"],
                        "api_base": os.environ["VILLAGER_LOCAL_BASE_URL"], "role_name": "JUDGER",
                        "timeout": float(os.environ.get("VILLAGER_LOCAL_TIMEOUT", "300"))}
        if os.environ.get("VILLAGER_LOCAL_NUM_CTX"):
            local_config["num_ctx"] = int(os.environ["VILLAGER_LOCAL_NUM_CTX"])
        llm = init_language_model(local_config)
    elif mode == "0":
        from model.init_model import init_language_model
        from model.google_model import (DEFAULT_GEMINI_MODEL, DEFAULT_GEMINI_THINKING_LEVEL,
                                        GOOGLE_OPENAI_BASE_URL, load_google_api_keys)
        keys = load_google_api_keys()
        llm = init_language_model({"api_model": DEFAULT_GEMINI_MODEL, "api_base": GOOGLE_OPENAI_BASE_URL,
                                   "thinking_level": DEFAULT_GEMINI_THINKING_LEVEL,
                                   "api_key_list": keys, "role_name": "JUDGER"})
    else:
        from model.init_model import init_language_model
        from model.role_models import standalone_model_config
        llm = init_language_model(standalone_model_config())
    new_building = []
    for structure in building:
        if len(structure) == 0:
            continue
        if len(structure) == 1:
            new_building.append(f"material: {structure[0]['name']} facing: {structure[0]['facing']} position: {structure[0]['position']}")
            continue
        new_prompt = describe_prompt + """structure-data:\n{structure}\nPlease generate the JSON output based on the prompt provided.""".format(structure=json.dumps(structure))
        print(new_prompt)
        response = llm.few_shot_generate_thoughts("", new_prompt, max_tokens=256, temperature=0.0, cache_enabled=False)
        if "```json\n" in response:
            response = response[response.find("```json\n") + 8:response.find("\n```")]
        response = json.loads(response)
        print(response)
        new_building.append(response)

    return new_building

def parse_token_text(text):
    text = str(text)
    # Use regular expressions to match required information
    tokens_used = re.findall(r'Tokens Used: (\d+)', text)
    prompt_tokens = re.findall(r'Prompt Tokens: (\d+)', text)
    completion_tokens = re.findall(r'Completion Tokens: (\d+)', text)
    successful_requests = re.findall(r'Successful Requests: (\d+)', text)
    total_cost = re.findall(r'Total Cost \(USD\): (\$[\d\.]+)', text)

    # Convert extracted information to integer or float
    tokens_used = [int(i) for i in tokens_used]
    prompt_tokens = [int(i) for i in prompt_tokens]
    completion_tokens = [int(i) for i in completion_tokens]
    successful_requests = [int(i) for i in successful_requests]
    total_cost = [float(i[1:]) for i in total_cost]  # Remove dollar sign

    # Returns a dictionary containing all extracted information
    return {
        'tokens_used': tokens_used[0],
        'prompt_tokens': prompt_tokens[0],
        'completion_tokens': completion_tokens[0],
        'successful_requests': successful_requests[0],
        'total_cost': total_cost[0]
    }
