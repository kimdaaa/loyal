version = "2.80"
# Never write decoded Riot presence payloads to logs by default. These payloads
# can contain account and session data; enable only for local debugging.
enablePrivateLogging = False
hide_names = True
hide_levels = True


gamemodes = {
    "newmap": "New Map",
    "competitive": "Competitive",
    "unrated": "Unrated",
    "swiftplay": "Swiftplay",
    "spikerush": "Spike Rush",
    "deathmatch": "Deathmatch",
    "ggteam": "Escalation",
    "onefa": "Replication",
    "hurm": "Team Deathmatch",
    "custom": "Custom",
    "snowball": "Snowball Fight",
    "": "Custom",
}

before_ascendant_seasons = [
    "0df5adb9-4dcb-6899-1306-3e9860661dd3",
    "3f61c772-4560-cd3f-5d3f-a7ab5abda6b3",
    "0530b9c4-4980-f2ee-df5d-09864cd00542",
    "46ea6166-4573-1128-9cea-60a15640059b",
    "fcf2c8f4-4324-e50b-2e23-718e4a3ab046",
    "97b6e739-44cc-ffa7-49ad-398ba502ceb0",
    "ab57ef51-4e59-da91-cc8d-51a5a2b9b8ff",
    "52e9749a-429b-7060-99fe-4595426a0cf7",
    "71c81c67-4fae-ceb1-844c-aab2bb8710fa",
    "2a27e5d2-4d30-c9e2-b15a-93b8909a442c",
    "4cb622e1-4244-6da3-7276-8daaf1c01be2",
    "a16955a5-4ad0-f761-5e9e-389df1c892fb",
    "97b39124-46ce-8b55-8fd1-7cbf7ffe173f",
    "573f53ac-41a5-3a7d-d9ce-d6a6298e5704",
    "d929bc38-4ab6-7da4-94f0-ee84f8ac141e",
    "3e47230a-463c-a301-eb7d-67bb60357d4f",
    "808202d6-4f2b-a8ff-1feb-b3a0590ad79f",
]
sockets = {
    "skin": "bcef87d6-209b-46c6-8b19-fbe40bd95abc",
    "skin_level": "e7c63390-eda7-46e0-bb7a-a6abdacd2433",
    "skin_chroma": "3ad1b2b2-acdb-4524-852f-954a76ddae0a",
    "skin_buddy": "77258665-71d1-4623-bc72-44db9bd5b3b3",
    "skin_buddy_level": "dd3bf334-87f3-40bd-b043-682a57a8dc3a"
}



AGENTCOLORLIST = {
    "none": (100, 100, 100),
    "astra": (113, 42, 232),
    "breach": (217, 122, 46),
    "brimstone": (217, 122, 46),
    "cypher": (245, 240, 230),
    "chamber": (200, 200, 200),
    "deadlock": (102, 119, 176),
    "fade": (92, 92, 94),
    "jett": (154, 222, 255),
    "kay/o": (133, 146, 156),
    "killjoy": (255, 217, 31),
    "omen": (71, 80, 143),
    "phoenix": (254, 130, 102),
    "raze": (217, 122, 46),
    "reyna": (181, 101, 181),
    "sage": (90, 230, 213),
    "skye": (192, 230, 158),
    "sova": (37, 143, 204),
    "neon": (28, 69, 161),
    "viper": (48, 186, 135),
    "yoru": (52, 76, 207),
    "harbor": (0, 128, 128),
    "gekko": (60, 179, 113),
    "vyse": (97, 83, 183),
    "iso": (154, 222, 255),
    "clove": (191, 158, 227),
    "tejo": (255, 183, 97),
}


tierDict = {
            "0cebb8be-46d7-c12a-d306-e9907bfc5a25": (0, 149, 135),
            "e046854e-406c-37f4-6607-19a9ba8426fc": (241, 184, 45),
            "60bca009-4182-7998-dee7-b8a2558dc369": (209, 84, 141),
            "12683d76-48d7-84a3-4e09-6985794f0445": (90, 159, 226),
            "411e4a55-4e59-7757-41f0-86a53f101bb5": (239, 235, 101),
            None: None
        }

WEAPONS = [
    "Classic",
    "Shorty",
    "Frenzy",
    "Ghost",
    "Sheriff",
    "Stinger",
    "Spectre",
    "Bucky",
    "Judge",
    "Bulldog",
    "Guardian",
    "Phantom",
    "Vandal",
    "Marshal",
    "Outlaw",
    "Operator",
    "Ares",
    "Odin",
    "Melee",
]

DEFAULT_CONFIG = {
        "cooldown": 10,
        "port": 1100,
        "weapon": "Vandal",
        "chat_limit": 5,
        "table": {
            "skin": True,
            "rr": True,
            "earned_rr": True,
            "peakrank": True,
            "previousrank" : False,
            "leaderboard": True,
            "headshot_percent": True,
            "winrate": True,
            "kd": False,
            "level": True
        },
        "flags": {
            "last_played": True,
            "auto_hide_leaderboard": True,
            "pre_cls": False,
            "game_chat": True,
            "peak_rank_act": True,
            "discord_rpc": True,
            "aggregate_rank_rr": True
        }
    }
RANK_NAMES = [
    "Unranked", "Unranked", "Unranked",
    "Iron 1", "Iron 2", "Iron 3",
    "Bronze 1", "Bronze 2", "Bronze 3",
    "Silver 1", "Silver 2", "Silver 3",
    "Gold 1", "Gold 2", "Gold 3",
    "Platinum 1", "Platinum 2", "Platinum 3",
    "Diamond 1", "Diamond 2", "Diamond 3",
    "Ascendant 1", "Ascendant 2", "Ascendant 3",
    "Immortal 1", "Immortal 2", "Immortal 3",
    "Radiant",
]

# Hex equivalents of the RGB tuples already used in NUMBERTORANKS above, by rank tier index (0-27).
RANK_COLORS_HEX = [
    "#2E2E2E", "#2E2E2E", "#2E2E2E",
    "#48453E", "#48453E", "#48453E",
    "#BB8F5A", "#BB8F5A", "#BB8F5A",
    "#AEB2B2", "#AEB2B2", "#AEB2B2",
    "#C5BA3F", "#C5BA3F", "#C5BA3F",
    "#18A7B9", "#18A7B9", "#18A7B9",
    "#D864C7", "#D864C7", "#D864C7",
    "#189452", "#189452", "#189452",
    "#DD4444", "#DD4444", "#DD4444",
    "#FFFDCD",
]

# Hex equivalents of PARTYICONLIST's fore=(r,g,b) tuples, in the same order, for use in a Tkinter GUI (ANSI color codes from `colr` are not usable there).
PARTY_COLORS_HEX = [
    "#E34343",
    "#D843E3",
    "#4346E3",
    "#43E3D0",
    "#5EE343",
    "#E2ED39",
    "#D452CF",
]

characters = {
    "e370fa57-4757-3604-3648-499e1f642d3f": "Gekko",
    "dade69b4-4f5a-8528-247b-219e5a1facd6": "Fade",
    "5f8d3a7f-467b-97f3-062c-13acf203c006": "Breach",
    "cc8b64c8-4b25-4ff9-6e7f-37b4da43d235": "Deadlock",
    "b444168c-4e35-8076-db47-ef9bf368f384": "Tejo",
    "f94c3b30-42be-e959-889c-5aa313dba261": "Raze",
    "22697a3d-45bf-8dd7-4fec-84a9e28c69d7": "Chamber",
    "601dbbe7-43ce-be57-2a40-4abd24953621": "KAY/O",
    "6f2a04ca-43e0-be17-7f36-b3908627744d": "Skye",
    "117ed9e3-49f3-6512-3ccf-0cada7e3823b": "Cypher",
    "320b2a48-4d9b-a075-30f1-1f93a9b638fa": "Sova",
    "1e58de9c-4950-5125-93e9-a0aee9f98746": "Killjoy",
    "95b78ed7-4637-86d9-7e41-71ba8c293152": "Harbor",
    "efba5359-4016-a1e5-7626-b1ae76895940": "Vyse",
    "707eab51-4836-f488-046a-cda6bf494859": "Viper",
    "eb93336a-449b-9c1b-0a54-a891f7921d69": "Phoenix",
    "41fb69c1-4189-7b37-f117-bcaf1e96f1bf": "Astra",
    "9f0d8ba9-4140-b941-57d3-a7ad57c6b417": "Brimstone",
    "0e38b510-41a8-5780-5e8f-568b2a4f2d6c": "Iso",
    "1dbf2edd-4729-0984-3115-daa5eed44993": "Clove",
    "bb2a4828-46eb-8cd1-e765-15848195d751": "Neon",
    "7f94d92c-4234-0a36-9646-3a87eb8b5c89": "Yoru",
    "df1cb487-4902-002e-5c17-d28e83e78588": "Waylay",
    "569fdd95-4d10-43ab-ca70-79becc718b46": "Sage",
    "a3bfb853-43b2-7238-a4f1-ad90e9e46bcc": "Reyna",
    "8e253930-4c05-31dd-1b6c-968525494517": "Omen",
    "add6443a-41bd-e414-f6ad-e58d267f4e95": "Jett"
}
