import asyncio
import aiohttp

BASE_URL = "https://tryhackme.com/api/v2/hacktivities/extended-search"
PARAMS = {
    "kind": "all",
    "difficulty": "all",
    "order": "most-popular",
    "roomType": "all",
    "povTagFilter": "all",
    "page": 1,
    "searchText": "",
    "userProgress": "all",
    "limit": 20,
    "from": "searchPage",
}

DIFFICULTY_COLORS = {
    "info": "white",
    "easy": "green",
    "medium": "yellow",
    "hard": "orange",
    "insane": "red"
}

DIFFICULTY_EMOJIS = {
    "info": "ℹ️",
    "easy": "🟢",
    "novice":"🟢",
    "medium": "🟡",
    "intermediate": "🟡",
    "hard": "🟠",
    "insane": "🔴"
}

def format_difficulty(difficulty):
    if not difficulty:
        return "❔"
    return f"{DIFFICULTY_EMOJIS.get(difficulty.lower(), "❔")} {difficulty.capitalize()}"

async def fetch_json(session, url, params=None, retries=5, delay=20):
    for _ in range(retries):
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError:
            await asyncio.sleep(delay)
    return {}


async def fetch_rooms_page(session, page):
    params = PARAMS.copy()
    params["page"] = page
    return await fetch_json(session, BASE_URL, params) or {"data": {"docs": []}}


async def fetch_scoreboard(session, room_code, limit=50):
    url = "https://tryhackme.com/api/v2/rooms/scoreboard"
    params = {"roomCode": room_code, "limit": limit, "page": 1}
    return await fetch_json(session, url, params) or {}


async def get_minimum_score(session, room_code):
    data = await fetch_scoreboard(session, room_code)
    entries = data.get("data", [])
    if not entries:
        return 0

    scores = []
    for entry in entries:
        try:
            tasks = entry.get("tasks", {})
            if all(all(task.get("correct") in (True, "true") for task in tasks[k]) for k in tasks):
                scores.append(entry.get("score", 0))
        except Exception:
            continue

    return min(scores) if scores else 0


async def export_rooms_markdown():
    async with aiohttp.ClientSession() as session:
        page = 1
        markdown = "| Solved | Name | Difficulty | Time | Type | Free | Score | Badge |\n"
        markdown += "| --- | --- | --- | --- | --- | --- | --- | --- |\n"

        while True:
            page_data = await fetch_rooms_page(session, page)
            rooms = page_data["data"]["docs"]
            if not rooms:
                break

            scores = await asyncio.gather(*(get_minimum_score(session, room["code"]) for room in rooms))

            for room, score in zip(rooms, scores):
                markdown += (
                    f"| [-] | [{room.get('title')}](https://tryhackme.com/room/{room.get('code')}) | "
                    f"{format_difficulty(room.get('difficulty'))} | {room.get('timeToComplete')} | "
                    f"{room.get('type')} | {'Yes' if room.get('freeToUse') else 'No'} | "
                    f"{score if score else 'X'} |   |\n"
                )

            print(f"✅ Page {page} processed")
            page += 1
            await asyncio.sleep(5)

        with open("table.md", "w", encoding="utf-8") as f:
            f.write(markdown)


if __name__ == "__main__":
    asyncio.run(export_rooms_markdown())
