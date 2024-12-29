import os
from douzero.env.game import GameEnv
from .deep_agent import DeepAgent

global env_list
env_list = {}

RealCard2EnvCard = {
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "T": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14,
    "2": 17,
    "X": 20,
    "D": 30,
}

AllEnvCard = [
    3,
    3,
    3,
    3,
    4,
    4,
    4,
    4,
    5,
    5,
    5,
    5,
    6,
    6,
    6,
    6,
    7,
    7,
    7,
    7,
    8,
    8,
    8,
    8,
    9,
    9,
    9,
    9,
    10,
    10,
    10,
    10,
    11,
    11,
    11,
    11,
    12,
    12,
    12,
    12,
    13,
    13,
    13,
    13,
    14,
    14,
    14,
    14,
    17,
    17,
    17,
    17,
    20,
    30,
]

WP_model = {
    "landlord": "douzero_WP/landlord.ckpt",
    "landlord_up": "douzero_WP/landlord_up.ckpt",
    "landlord_down": "douzero_WP/landlord_down.ckpt",
}
ADP_model = {
    "landlord": "douzero_ADP/landlord.ckpt",
    "landlord_up": "douzero_ADP/landlord_up.ckpt",
    "landlord_down": "douzero_ADP/landlord_down.ckpt",
}


def init(data):
    global env_list
    res_type = "init"
    res_action = ""
    res_data = {}
    res_status = ""
    res_msg = ""
    res_game_over = False

    try:
        pid = ""
        pid = str(data["pid"])
        ai_amount = data["ai_amount"]

        if ai_amount == 1:
            (
                use_hand_cards_env,
                user_position,
                user_position_code,
                three_landlord_cards_env,
                ai_model,
            ) = get_init_data(data, 0)

            # 整副牌减去玩家手上的牌，就是其他人的手牌,再随机分配给另外两个角色 **如何分配对AI判断没有影响**
            other_hand_cards = []
            for i in set(AllEnvCard):
                other_hand_cards.extend(
                    [i] * (AllEnvCard.count(i) - use_hand_cards_env.count(i))
                )

            card_play_data_list = [{}]
            card_play_data_list[0].update(
                {
                    "three_landlord_cards": three_landlord_cards_env,
                    ["landlord_up", "landlord", "landlord_down"][
                        (user_position_code + 0) % 3
                    ]: use_hand_cards_env,
                    ["landlord_up", "landlord", "landlord_down"][
                        (user_position_code + 1) % 3
                    ]: (
                        other_hand_cards[0:17]
                        if (user_position_code + 1) % 3 != 1
                        else other_hand_cards[17:]
                    ),
                    ["landlord_up", "landlord", "landlord_down"][
                        (user_position_code + 2) % 3
                    ]: (
                        other_hand_cards[0:17]
                        if (user_position_code + 1) % 3 == 1
                        else other_hand_cards[17:]
                    ),
                }
            )
            # print(f"card_play_data_list: {card_play_data_list}")
            # 生成手牌结束，校验手牌数量

            if len(card_play_data_list[0]["three_landlord_cards"]) != 3:
                error = Exception("底牌必须是3张")
                raise error
            if (
                len(card_play_data_list[0]["landlord_up"]) != 17
                or len(card_play_data_list[0]["landlord_down"]) != 17
                or len(card_play_data_list[0]["landlord"]) != 20
            ):
                error = Exception("初始手牌数目有误")
                raise error

            players = {}
            cards = []
            players[user_position] = DeepAgent(user_position, ai_model)
            env = GameEnv(players)
            for idx, card_play_data in enumerate(card_play_data_list):
                env.card_play_init(card_play_data)
                print("initialize success, game start\n")

            # print(f"env.players.keys(): {env.players.keys()}")
            if (
                env.acting_player_position == list(env.players.keys())[0]
            ):  # 如果下一位是AI，则直接获取建议出牌
                cards, confidence = env.tips(data)
                res_data = {
                    "pid": pid,
                    "game_over": res_game_over,
                    "tips": [
                        {
                            "cards": cards,
                            "confidence": confidence,
                        }
                    ],
                }
                res_action = "tips"
            else:
                res_data = {"pid": pid, "game_over": res_game_over}
                res_action = "receive"

            env_list[pid] = env
            res_status = "ok"

    except Exception as err:
        res_action = "init"
        res_status = "fail"
        res_msg = str(err)
        res_data = {"pid": pid}

    result = {
        "type": res_type,
        "action": res_action,
        "data": res_data,
        "status": res_status,
        "msg": res_msg,
    }
    return result


def next(data):  # 收到他人出牌
    res_type = "step"
    res_action = ""
    res_data = {}
    res_status = ""
    res_msg = ""
    res_game_over = False

    global env_list
    try:
        pid = ""
        pid = str(data["pid"])

        if pid not in env_list.keys():
            error = Exception(f"此窗口并未初始化游戏进程")
            raise error

        player = data["player"]  # int 0/1/2
        env = env_list[pid]
        res_action = ""

        if (
            env.acting_player_position
            != ["landlord_up", "landlord", "landlord_down"][player]
        ):
            acting_player = {
                "landlord_up": "地主上家",
                "landlord": "地主",
                "landlord_down": "地主下家",
            }[env.acting_player_position]
            error = Exception(f"非此玩家回合，当前为{acting_player}的回合")
            raise error

        env.step(data) # 上报玩家出牌
        if env.game_over:
            res_game_over = True
            del env_list[pid]
            res_action="receive"
            res_data={
                "pid": pid,
                "game_over": res_game_over
            }
        else:
            if (
                env.acting_player_position in list(env.players.keys())
            ):  # 如果下一位是AI，则直接获取建议出牌
                cards_pd, confidence_pd = env.tips(data)  # ai建议
                res_action = "tips"
                res_data = {
                    "pid": pid,
                    "game_over": res_game_over,
                    "tips": [
                        {
                            "cards": cards_pd,
                            "confidence": confidence_pd,
                        }
                    ],
                }
            else:
                res_data = {"pid": pid, "game_over": res_game_over}
                res_action = "receive"

        if not res_game_over :
            env_list[pid] = env
        res_status = "ok"
    except Exception as err:
        res_action = "step"
        res_data = {"pid": pid}
        res_status = "fail"
        res_msg = str(err)
    result = {
        "type": res_type,
        "action": res_action,
        "data": res_data,
        "status": res_status,
        "msg": res_msg,
    }
    return result

def close(data):
    global env_list
    res_type = "close"
    res_action = ""
    res_data = {}
    res_status = ""
    res_msg = ""

    try:
        pid = ""
        pid = str(data["pid"])
        del env_list[pid]
        print(f"close pid:{pid}")
        res_status = "ok"
        res_msg = "closed"
    except Exception as err:
        res_status = "fail"
        res_msg = str(err)
        res_data = {"pid": pid}

    result = {
        "type": res_type,
        "action": res_action,
        "data": res_data,
        "status": res_status,
        "msg": res_msg,
    }
    return result

def check_model(model):
    if model == "WP":
        return [
            f"baselines/{WP_model['landlord_up']}",
            f"baselines/{WP_model['landlord']}",
            f"baselines/{WP_model['landlord_down']}",
        ]
    elif model == "ADP":
        return [
            f"baselines/{ADP_model['landlord_up']}",
            f"baselines/{ADP_model['landlord']}",
            f"baselines/{ADP_model['landlord_down']}",
        ]
    else:
        # 其它模型
        if (
            os.path.exists(f"baselines/{model}/landlord.ckpt")
            and os.path.exists(f"baselines/{model}/landlord_up.ckpt")
            and os.path.exists(f"baselines/{model}/landlord_down.ckpt")
        ):
            return [
                f"baselines/{model}/landlord_down.ckpt",
                f"baselines/{model}/landlord.ckpt",
                f"baselines/{model}/landlord_up.ckpt",
            ]
        else:
            return None


def get_init_data(data, index):
    use_hand_cards_env = user_position = three_landlord_cards_env = ai_model = None
    # 玩家手牌
    user_hand_cards_real = data["player_data"][index]["hand_cards"]
    use_hand_cards_env = [RealCard2EnvCard[c] for c in list(user_hand_cards_real)]
    # 玩家角色
    user_position_code = data["player_data"][index]["position_code"]
    user_position = ["landlord_up", "landlord", "landlord_down"][user_position_code]
    # 三张底牌
    three_landlord_cards_real = data["three_landlord_cards"]
    three_landlord_cards_env = [
        RealCard2EnvCard[c] for c in list(three_landlord_cards_real)
    ]
    # 模型
    ai_model_name = data["player_data"][index]["model"]
    ai_model_list = check_model(ai_model_name)
    if ai_model_list == None:
        error = Exception(f"找不到此模型：{ai_model_name}")
        raise error
    else:
        ai_model = ai_model_list[user_position_code]

    return (
        use_hand_cards_env,
        user_position,
        user_position_code,
        three_landlord_cards_env,
        ai_model,
    )
