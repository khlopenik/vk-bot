"""
FRAME VK Bot — AI-фотосессии для ВКонтакте
Общая Supabase БД с TG-ботом (VK user_id смещён на +10_000_000_000 чтобы не пересекаться с TG).
"""

import os
import time
import threading
import json
import requests
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api import VkUpload
from typing import Optional

# ─── Env ──────────────────────────────────────────────────────────────────────
VK_TOKEN        = os.environ.get("VK_TOKEN", "")           # токен сообщества
MUAPI_KEY       = os.environ.get("MUAPI_KEY", "")
SUPABASE_URL    = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY    = os.environ.get("SUPABASE_KEY", "")
YOKASSA_SHOP_ID = os.environ.get("YOKASSA_SHOP_ID", "")
YOKASSA_KEY     = os.environ.get("YOKASSA_KEY", "")
ADMIN_VK_ID     = int(os.environ.get("ADMIN_VK_ID", "0"))

MUAPI_URL = "https://api.muapi.ai/api/v1"
MUAPI_HEADERS = {"x-api-key": MUAPI_KEY}

# VK user_id смещается, чтобы не пересекаться с TG user_id в Supabase
VK_ID_OFFSET = 10_000_000_000

# ─── Модели ───────────────────────────────────────────────────────────────────
GALLERY_MODELS = {
    "std": ("nano-banana-edit",        "images_list",  True,  "⭐ Стандарт"),
    "v2":  ("nano-banana-2-edit",      "images_list",  True,  "✨ Версия 2"),
    "pro": ("nano-banana-pro-edit",    "images_list",  True,  "💎 Про"),
}

DIAMOND_MODELS = {
    "nb_edit":   ("nano-banana-edit",              79,  "⭐ Nano Banana",    "images_list"),
    "nb2_edit":  ("nano-banana-2-edit",            99,  "✨ Nano Banana 2",  "images_list"),
    "nbpro":     ("nano-banana-pro-edit",         149,  "💎 Nano Banana Pro","images_list"),
    "gpt4o":     ("gpt4o-image-to-image",          99,  "🤖 GPT-4o",        "images_list"),
    "gpt_img2":  ("gpt-image-2-image-to-image",   199,  "🤖 GPT Image 2",   "images_list"),
    "seedream":  ("bytedance-seedream-v4.5-edit",  99,  "🌱 Seedream",      "images_list"),
    "grok_i2i":  ("grok-imagine-image-to-image",   99,  "🧠 Grok",          "images_list"),
    "kling_o3":  ("kling-o3-image-edit",           79,  "🎬 Kling O3",      "images_list"),
    "flux_pro":  ("flux-kontext-pro-i2i",          79,  "⚡ Flux Pro",      "images_list"),
    "flux_max":  ("flux-kontext-max-i2i",          99,  "⚡ Flux Max",      "images_list"),
    "pulid":     ("flux-pulid",                    99,  "🎭 PuLID",         "image_url"),
}

TARIFF_PRICES = {
    "trial":    ("🎁 Пробный — 3 фото",        {"std": 1, "v2": 1, "pro": 1},  None,  149),
    "std_1":    ("⭐ Стандарт — 1 фото",        "std",   1,   79),
    "std_10":   ("⭐ Стандарт — 10 фото",       "std",  10,  590),
    "std_30":   ("⭐ Стандарт — 30 фото",       "std",  30, 1490),
    "std_50":   ("⭐ Стандарт — 50 фото",       "std",  50, 1990),
    "v2_1":     ("✨ Версия 2 — 1 фото",        "v2",    1,   99),
    "v2_10":    ("✨ Версия 2 — 10 фото",       "v2",   10,  790),
    "v2_30":    ("✨ Версия 2 — 30 фото",       "v2",   30, 1890),
    "v2_50":    ("✨ Версия 2 — 50 фото",       "v2",   50, 2490),
    "pro_1":    ("💎 Про — 1 фото",             "pro",   1,  149),
    "pro_10":   ("💎 Про — 10 фото",            "pro",  10, 1190),
    "pro_30":   ("💎 Про — 30 фото",            "pro",  30, 2490),
    "pro_50":   ("💎 Про — 50 фото",            "pro",  50, 3990),
    "nude_3":   ("🔞 Ню — 3 фото",             "nude",  3,  249),
    "nude_5":   ("🔞 Ню — 5 фото",             "nude",  5,  390),
    "nude_10":  ("🔞 Ню — 10 фото",            "nude", 10,  690),
    "nude_20":  ("🔞 Ню — 20 фото",            "nude", 20, 1190),
    "family_1": ("👨‍👩‍👧 Семья — 1 портрет",     "family", 1,   390),
    "family_3": ("👨‍👩‍👧 Семья — 3 портрета",    "family", 3,   990),
    "family_5": ("👨‍👩‍👧 Семья — 5 портретов",   "family", 5,  1490),
    "mix_start": ("📦 Начальный набор",  {"std": 10, "nude": 3, "family": 1}, 1,   990),
    "mix_full":  ("📦 Полный набор",     {"std": 25, "nude": 7, "family": 3}, 1,  2490),
    "mix_pro":   ("📦 Про набор",        {"std": 20, "pro": 10, "nude": 5, "family": 3}, 1, 3490),
    "couples_std_1":  ("👫 Пары ⭐ — 1 фото",  "std",  1,   99),
    "couples_std_3":  ("👫 Пары ⭐ — 3 фото",  "std",  3,  270),
    "couples_std_5":  ("👫 Пары ⭐ — 5 фото",  "std",  5,  420),
    "couples_std_10": ("👫 Пары ⭐ — 10 фото", "std", 10,  750),
    "couples_v2_1":   ("👫 Пары ✨ — 1 фото",  "v2",   1,  119),
    "couples_v2_3":   ("👫 Пары ✨ — 3 фото",  "v2",   3,  330),
    "couples_v2_5":   ("👫 Пары ✨ — 5 фото",  "v2",   5,  520),
    "couples_v2_10":  ("👫 Пары ✨ — 10 фото", "v2",  10,  950),
    "couples_pro_1":  ("👫 Пары 💎 — 1 фото",  "pro",  1,  169),
    "couples_pro_3":  ("👫 Пары 💎 — 3 фото",  "pro",  3,  470),
    "couples_pro_5":  ("👫 Пары 💎 — 5 фото",  "pro",  5,  745),
    "couples_pro_10": ("👫 Пары 💎 — 10 фото", "pro", 10, 1390),
    "diamond_500":  ("💎 500 алмазов",   "diamond",  500,  490),
    "diamond_1500": ("💎 1500 алмазов",  "diamond", 1500, 1290),
    "diamond_3000": ("💎 3000 алмазов",  "diamond", 3000, 2490),
    "diamond_6000": ("💎 6000 алмазов",  "diamond", 6000, 3990),
}

FAILED_SENTINEL = "__FAILED__"

# ─── Состояния пользователей (в памяти) ──────────────────────────────────────
user_data: dict = {}
user_lock = threading.Lock()

def get_user(vk_id: int) -> dict:
    with user_lock:
        if vk_id not in user_data:
            user_data[vk_id] = {
                "waiting_for":     None,
                "face_url":        None,
                "selected_model":  "std",
                "std_credits":     0,
                "v2_credits":      0,
                "pro_credits":     0,
                "diamond_credits": 0,
                "gift_credits":    0,
                "ref_count":       0,
                "ref_paid_count":  0,
                "is_partner":      False,
                "partner_pct":     0,
                "partner_paid":    0.0,
                "pd_consent":      False,
            }
            _load_credits_from_db(vk_id)
        return user_data[vk_id]

def _db_id(vk_id: int) -> int:
    return VK_ID_OFFSET + vk_id

# ─── Supabase ─────────────────────────────────────────────────────────────────
def _sb_headers() -> dict:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }

def _load_credits_from_db(vk_id: int) -> None:
    if not SUPABASE_URL:
        return
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/user_credits",
            headers=_sb_headers(),
            params={"user_id": f"eq.{_db_id(vk_id)}",
                    "select": "std_credits,v2_credits,pro_credits,diamond_credits,gift_credits,ref_count,ref_paid_count,is_partner,partner_pct,partner_paid"},
            timeout=10,
        )
        if r.ok and r.json():
            row = r.json()[0]
            u = user_data[vk_id]
            for k in ("std_credits","v2_credits","pro_credits","diamond_credits","gift_credits",
                      "ref_count","ref_paid_count","partner_pct"):
                if row.get(k) is not None:
                    u[k] = row[k]
            if row.get("is_partner") is not None:
                u["is_partner"] = bool(row["is_partner"])
            if row.get("partner_paid") is not None:
                u["partner_paid"] = float(row["partner_paid"] or 0)
            if any(row.get(k, 0) for k in ("std_credits","v2_credits","pro_credits","diamond_credits")):
                u["pd_consent"] = True
    except Exception as e:
        print(f"[DB] load_credits error: {e}")

def _save_credits_to_db(vk_id: int) -> None:
    if not SUPABASE_URL:
        return
    u = user_data[vk_id]
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/user_credits",
            headers={**_sb_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
            json={
                "user_id":         _db_id(vk_id),
                "std_credits":     u.get("std_credits", 0),
                "v2_credits":      u.get("v2_credits", 0),
                "pro_credits":     u.get("pro_credits", 0),
                "nude_credits":    0,
                "family_credits":  0,
                "couples_credits": 0,
                "video_credits":   0,
                "music_credits":   0,
                "diamond_credits": u.get("diamond_credits", 0),
                "gift_credits":    u.get("gift_credits", 0),
            },
            timeout=10,
        )
    except Exception as e:
        print(f"[DB] save_credits error: {e}")

def _save_history(vk_id: int, prompt: str, result_url: str) -> None:
    if not SUPABASE_URL:
        return
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/generation_history",
            headers=_sb_headers(),
            json={
                "user_id":    _db_id(vk_id),
                "result_url": result_url,
                "prompt":     str(prompt)[:200],
            },
            timeout=10,
        )
    except Exception as e:
        print(f"[DB] save_history error: {e}")

# ─── MuAPI ────────────────────────────────────────────────────────────────────
SIZE_MAP = {
    "sq":    "square_hd",
    "34":    "portrait_4_3",
    "vert":  "portrait_16_9",
    "43":    "landscape_4_3",
    "horiz": "landscape_16_9",
}

def start_generation(prompt: str, model_slug: str, image_url: str,
                     input_type: str = "image_url", size: str = "vert") -> Optional[str]:
    body: dict = {}
    if prompt:
        body["prompt"] = prompt
    if image_url:
        # images_list требует массив, image_url — строку
        body[input_type] = [image_url] if input_type == "images_list" else image_url
    # image_size поддерживается только text-to-image моделями, не i2i
    try:
        resp = requests.post(f"{MUAPI_URL}/{model_slug}",
                             headers=MUAPI_HEADERS, json=body, timeout=30)
        print(f"[MuAPI] POST /{model_slug} → {resp.status_code}: {resp.text[:300]}")
        if not resp.ok:
            return None
        data = resp.json()
        return data.get("request_id") or data.get("id")
    except Exception as e:
        print(f"[MuAPI] start_generation error: {e}")
        return None

def poll_result(request_id: str, max_attempts: int = 60) -> Optional[str]:
    for _ in range(max_attempts):
        time.sleep(3)
        try:
            r = requests.get(f"{MUAPI_URL}/predictions/{request_id}/result",
                             headers=MUAPI_HEADERS, timeout=10)
            r.raise_for_status()
            data = r.json()
            status = data.get("status", "")
            if status == "completed":
                outputs = data.get("outputs", [])
                return outputs[0] if outputs else FAILED_SENTINEL
            if status in ("failed", "error"):
                return FAILED_SENTINEL
        except Exception as e:
            print(f"[MuAPI] poll error: {e}")
    return None

# ─── Кредиты ──────────────────────────────────────────────────────────────────
CREDIT_KEY = {"std": "std_credits", "v2": "v2_credits", "pro": "pro_credits"}
QUALITY_DIA_COST = {"std": 79, "v2": 99, "pro": 149}  # алмазов за 1 генерацию

def has_credits(vk_id: int, model_key: str) -> bool:
    u = get_user(vk_id)
    if model_key in DIAMOND_MODELS:
        cost = DIAMOND_MODELS[model_key][1]
        return u.get("diamond_credits", 0) >= cost
    ckey = CREDIT_KEY.get(model_key, "std_credits")
    if u.get(ckey, 0) > 0 or u.get("gift_credits", 0) > 0:
        return True
    # Fallback: списать алмазами если пакета нет
    dia_cost = QUALITY_DIA_COST.get(model_key, 79)
    return u.get("diamond_credits", 0) >= dia_cost

def deduct_credit(vk_id: int, model_key: str) -> None:
    u = get_user(vk_id)
    if model_key in DIAMOND_MODELS:
        cost = DIAMOND_MODELS[model_key][1]
        u["diamond_credits"] = max(0, u.get("diamond_credits", 0) - cost)
    else:
        ckey = CREDIT_KEY.get(model_key, "std_credits")
        if u.get(ckey, 0) > 0:
            u[ckey] -= 1
        elif u.get("gift_credits", 0) > 0:
            u["gift_credits"] -= 1
        else:
            # Fallback: списываем алмазами
            dia_cost = QUALITY_DIA_COST.get(model_key, 79)
            u["diamond_credits"] = max(0, u.get("diamond_credits", 0) - dia_cost)
    _save_credits_to_db(vk_id)

def add_credits(vk_id: int, tariff_key: str) -> str:
    u = get_user(vk_id)
    t = TARIFF_PRICES.get(tariff_key)
    if not t:
        return "Тариф не найден"
    label, ctype, amount, price = t
    if isinstance(ctype, dict):
        for k, v in ctype.items():
            u[CREDIT_KEY.get(k, k + "_credits")] = u.get(CREDIT_KEY.get(k, k + "_credits"), 0) + v
    elif ctype == "diamond":
        u["diamond_credits"] = u.get("diamond_credits", 0) + amount
    else:
        u[CREDIT_KEY.get(ctype, ctype + "_credits")] = u.get(CREDIT_KEY.get(ctype, ctype + "_credits"), 0) + amount
    _save_credits_to_db(vk_id)
    return f"✅ Начислено: {label}"

def credits_text(vk_id: int) -> str:
    u = get_user(vk_id)
    std  = u.get("std_credits", 0)
    v2   = u.get("v2_credits", 0)
    pro  = u.get("pro_credits", 0)
    dia  = u.get("diamond_credits", 0)
    gift = u.get("gift_credits", 0)
    lines = ["💳 Ваш баланс:"]
    if std:  lines.append(f"  ⭐ Стандарт: {std} фото")
    if v2:   lines.append(f"  ✨ Версия 2: {v2} фото")
    if pro:  lines.append(f"  💎 Про: {pro} фото")
    if dia:  lines.append(f"  🔷 Алмазы: {dia} 💎")
    if gift: lines.append(f"  🎁 Подарочные: {gift} фото")
    if len(lines) == 1:
        lines.append("  Кредитов нет — купите тариф!")
    return "\n".join(lines)

# ─── Динамические тарифы конструктора (build_) ────────────────────────────────
def _builder_unit_price(cat: str, qty: int) -> int:
    """Цена за единицу с учётом объёмной скидки (совпадает с фронтом)."""
    if cat == "std":
        if qty >= 50: return 39
        if qty >= 30: return 49
        if qty >= 10: return 59
        return 79
    if cat == "v2":
        if qty >= 50: return 49
        if qty >= 30: return 63
        if qty >= 10: return 79
        return 99
    if cat == "pro":
        if qty >= 50: return 80
        if qty >= 30: return 83
        if qty >= 10: return 119
        return 149
    if cat == "nude":
        if qty >= 20: return 59
        if qty >= 10: return 69
        if qty >= 5:  return 78
        if qty >= 3:  return 83
        return 89
    if cat == "family":
        if qty >= 5: return 298
        if qty >= 3: return 330
        return 390
    if cat == "video":
        if qty >= 3: return 330
        return 390
    if cat == "couples":
        if qty >= 10: return 119
        if qty >= 5:  return 129
        if qty >= 3:  return 139
        return 149
    return 0

def ensure_dynamic_tariff(tariff_key: str) -> bool:
    """Восстанавливает build_-тариф из ключа в TARIFF_PRICES. True если ключ валиден."""
    if tariff_key in TARIFF_PRICES:
        return True
    # build_{std}_{v2}_{pro}_{nude}_{family}_{video}
    if tariff_key.startswith("build_"):
        parts = tariff_key.split("_")
        if len(parts) == 7:
            try:
                std_q, v2_q, pro_q, nude_q, fam_q, vid_q = (int(x) for x in parts[1:])
            except ValueError:
                return False
            total = (_builder_unit_price("std",    std_q) * std_q +
                     _builder_unit_price("v2",     v2_q)  * v2_q  +
                     _builder_unit_price("pro",    pro_q) * pro_q +
                     _builder_unit_price("nude",   nude_q) * nude_q +
                     _builder_unit_price("family", fam_q) * fam_q +
                     _builder_unit_price("video",  vid_q) * vid_q)
            if total <= 0:
                return False
            desc = []
            ctype: dict = {}
            for q, key, lbl in ((std_q,"std","стандарт"), (v2_q,"v2","версия 2"),
                                 (pro_q,"pro","про"), (nude_q,"nude","ню"),
                                 (fam_q,"family","семейных"), (vid_q,"video","оживлений")):
                if q:
                    desc.append(f"{q} {lbl}")
                    ctype[key] = q
            if not ctype:
                return False
            name = "🎛 Свой набор: " + " · ".join(desc)
            TARIFF_PRICES[tariff_key] = (name, ctype, None, total)
            return True
        return False
    return False

# ─── YooKassa платёж ──────────────────────────────────────────────────────────
def create_yookassa_link(vk_id: int, tariff_key: str):
    """Возвращает (confirmation_url, error_str)."""
    ensure_dynamic_tariff(tariff_key)
    t = TARIFF_PRICES.get(tariff_key)
    if not t or not YOKASSA_SHOP_ID or not YOKASSA_KEY:
        return None, "env_not_set"
    label, _, _, price = t
    discounted = int(price * 0.5)
    try:
        import uuid
        r = requests.post(
            "https://api.yookassa.ru/v3/payments",
            auth=(YOKASSA_SHOP_ID, YOKASSA_KEY),
            headers={"Idempotence-Key": str(uuid.uuid4()),
                     "Content-Type": "application/json"},
            json={
                "amount": {"value": f"{discounted}.00", "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": "https://vk.com/app54628838"},
                "capture": True,
                "description": f"FRAME VK: {label} (vk_id={vk_id})",
                "metadata": {"vk_id": str(vk_id), "tariff": tariff_key},
            },
            timeout=15,
        )
        data = r.json()
        print(f"[YK] status={r.status_code} response={str(data)[:500]}")
        url = data.get("confirmation", {}).get("confirmation_url")
        if not url:
            err = data.get("description") or data.get("code") or str(data)[:200]
            print(f"[YK] ❌ No confirmation_url. YK error: {err}")
            return None, err
        return url, None
    except Exception as e:
        print(f"[YooKassa] error: {e}")
        return None, str(e)

# ─── Клавиатуры ───────────────────────────────────────────────────────────────
MINIAPP_URL  = "https://vk-bot-miniapp.onrender.com"
VK_APP_ID    = 54628838
VK_GROUP_ID  = 239444342   # числовой ID сообщества

def _open_app_btn(label: str, hash_val: str) -> dict:
    return {
        "action": {
            "type":     "open_app",
            "app_id":   VK_APP_ID,
            "owner_id": -VK_GROUP_ID,
            "label":    label,
            "hash":     hash_val,
        }
    }

def kb_main() -> str:
    keyboard = {
        "one_time": False,
        "buttons": [
            # Строка 1 — единственная open_app кнопка (ВК поддерживает только одну)
            [_open_app_btn("✨ Открыть приложение FRAME", "")],
            # Строка 2 — текстовые кнопки разделов
            [
                {"action": {"type": "text", "label": "⭐ Новичок"},      "color": "secondary"},
                {"action": {"type": "text", "label": "💎 Профи"},        "color": "secondary"},
                {"action": {"type": "text", "label": "🛒 Тарифы"},       "color": "secondary"},
            ],
            # Строка 3
            [
                {"action": {"type": "text", "label": "💳 Мой счёт"},    "color": "secondary"},
                {"action": {"type": "text", "label": "👤 Профиль"},      "color": "secondary"},
                {"action": {"type": "text", "label": "💬 Поддержка"},    "color": "secondary"},
            ],
        ]
    }
    return json.dumps(keyboard, ensure_ascii=False)

def kb_model_choice() -> str:
    kb = VkKeyboard(one_time=True)
    kb.add_button("⭐ Стандарт", VkKeyboardColor.SECONDARY)
    kb.add_button("✨ Версия 2", VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("💎 Про", VkKeyboardColor.PRIMARY)
    kb.add_button("🔷 Профи (алмазы)", VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("❌ Отмена", VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()

def kb_diamond_models() -> str:
    kb = VkKeyboard(one_time=True)
    keys = list(DIAMOND_MODELS.keys())
    for i, key in enumerate(keys):
        slug, cost, name = DIAMOND_MODELS[key]
        kb.add_button(f"{name} ({cost}💎)", VkKeyboardColor.SECONDARY)
        if (i + 1) % 2 == 0 and i < len(keys) - 1:
            kb.add_line()
    kb.add_line()
    kb.add_button("❌ Отмена", VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()

def kb_tariffs_basic() -> str:
    kb = VkKeyboard(one_time=True)
    kb.add_button("🎁 Пробный 149₽", VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("⭐ Станд. 10 фото 590₽", VkKeyboardColor.SECONDARY)
    kb.add_button("✨ Версия2 10 фото 790₽", VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("💎 Про 10 фото 1190₽", VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🔷 Алмазы 500шт 490₽", VkKeyboardColor.SECONDARY)
    kb.add_button("🔷 Алмазы 1500шт 1290₽", VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("❌ Отмена", VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()

def kb_cancel() -> str:
    kb = VkKeyboard(one_time=True)
    kb.add_button("❌ Отмена", VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()

def kb_pay_link(link: str, label: str) -> str:
    """Клавиатура с кнопкой open_link для оплаты — НЕ голая ссылка."""
    kb = VkKeyboard(one_time=True)
    kb.add_openlink_button(f"💳 Оплатить — {label[:28]}", link)
    kb.add_line()
    kb.add_button("🔙 Главное меню", VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def kb_support_link(admin_link: str) -> str:
    """Клавиатура с кнопкой перехода в личку поддержки."""
    kb = VkKeyboard(one_time=True)
    kb.add_openlink_button("💬 Написать напрямую", admin_link)
    kb.add_line()
    kb.add_button("🔙 Главное меню", VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

# ─── Редирект-прокси (чтобы open_link кнопки работали через наш домен) ──────
import secrets as _secrets
_redirects: dict = {}

def make_redirect_url(url: str) -> str:
    token = _secrets.token_urlsafe(8)
    _redirects[token] = url
    return f"https://vk-bot-2vns.onrender.com/go/{token}"

# ─── VK утилиты ───────────────────────────────────────────────────────────────
_rand = __import__("random").randint

def send(vk, peer_id: int, text: str, keyboard: str = None, attachment: str = None) -> None:
    kwargs = {"peer_id": peer_id, "message": text, "random_id": _rand(0, 2**31)}
    if keyboard:
        kwargs["keyboard"] = keyboard
    if attachment:
        kwargs["attachment"] = attachment
    try:
        vk.messages.send(**kwargs)
    except Exception as e:
        if keyboard:
            print(f"[send] keyboard rejected ({e}), retrying without keyboard")
            kwargs.pop("keyboard")
            vk.messages.send(**kwargs)
        else:
            raise

def get_photo_url(vk, event) -> Optional[str]:
    """Извлекаем URL максимального размера из вложений фото."""
    for att in getattr(event, "attachments", {}) if hasattr(event, "attachments") else []:
        pass
    # Attachments в LongPoll приходят по-другому — читаем из message
    for att in event.message_data.get("attachments", []) if hasattr(event, "message_data") else []:
        if att.get("type") == "photo":
            sizes = att["photo"].get("sizes", [])
            if sizes:
                best = sorted(sizes, key=lambda s: s.get("width", 0))[-1]
                return best.get("url")
    return None

def upload_result_to_vk(vk, upload: VkUpload, group_id: int, result_url: str) -> Optional[str]:
    """Скачиваем результат и загружаем в VK как attachment."""
    try:
        resp = requests.get(result_url, timeout=30)
        resp.raise_for_status()
        # Сохраняем во временный файл
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(resp.content)
            tmp_path = f.name
        photos = upload.photo_messages(tmp_path)
        os.unlink(tmp_path)
        p = photos[0]
        return f"photo{p['owner_id']}_{p['id']}"
    except Exception as e:
        print(f"[VK upload] error: {e}")
        return None

# ─── Логика сообщений ─────────────────────────────────────────────────────────
def handle_text(vk, upload, group_id: int, vk_id: int, text: str, event) -> None:
    u = get_user(vk_id)
    t = text.strip().lower()

    # ── Команды администратора ────────────────────────────────────────────────
    if vk_id == ADMIN_VK_ID:
        # /add 50std — начислить себе кредиты без оплаты
        if t.startswith("/add "):
            parts = t[5:].strip().split()
            try:
                amount = int(parts[0])
                ctype  = parts[1] if len(parts) > 1 else "std"
                key = CREDIT_KEY.get(ctype, ctype + "_credits")
                u[key] = u.get(key, 0) + amount
                _save_credits_to_db(vk_id)
                send(vk, vk_id, f"✅ Начислено: +{amount} [{ctype}]\n\n{credits_text(vk_id)}", keyboard=kb_main())
            except Exception as e:
                send(vk, vk_id, f"❌ Ошибка: {e}\nФормат: /add 50 std", keyboard=kb_main())
            return
        # /add_tariff trial — начислить тариф целиком
        if t.startswith("/add_tariff "):
            key = t[12:].strip()
            msg = add_credits(vk_id, key)
            send(vk, vk_id, f"✅ Тариф применён\n{msg}\n\n{credits_text(vk_id)}", keyboard=kb_main())
            return

    # ── Команды навигации (сбрасывают waiting_for) ───────────────────────────
    if t in ("начать", "старт", "/start", "привет", "start", "🔙 главное меню", "главное меню", "меню"):
        u["waiting_for"] = None
        if not u.get("pd_consent"):
            u["pd_consent"] = True
        send(vk, vk_id,
             "👋 Привет! Я FRAME — бот AI-фотосессий.\n\n"
             "Нажми кнопку ниже чтобы открыть приложение, или выбери действие:",
             keyboard=kb_main())
        return

    SECTION_LINKS = {
        "⭐ новичок":   ("novichok", "⭐ Открыть «Новичок»"),
        "новичок":      ("novichok", "⭐ Открыть «Новичок»"),
        "💎 профи":     ("profi",    "💎 Открыть «Профи»"),
        "профи":        ("profi",    "💎 Открыть «Профи»"),
        "профессионал": ("profi",    "💎 Открыть «Профи»"),
        "🛒 тарифы":   ("tariffs",  "🛒 Открыть «Тарифы»"),
        "тарифы":       ("tariffs",  "🛒 Открыть «Тарифы»"),
        "👤 профиль":  ("profile",  "👤 Открыть «Профиль»"),
        "профиль":      ("profile",  "👤 Открыть «Профиль»"),
    }
    if t in SECTION_LINKS:
        u["waiting_for"] = None
        hash_val, btn_label = SECTION_LINKS[t]
        kb_section = json.dumps({
            "one_time": True,
            "buttons": [
                [_open_app_btn(btn_label, hash_val)],
                [{"action": {"type": "text", "label": "🔙 Главное меню"}, "color": "secondary"}],
            ]
        }, ensure_ascii=False)
        send(vk, vk_id, "👇", keyboard=kb_section)
        return

    if t in ("💎 мой тариф", "мой тариф", "💳 мой счёт", "мой счёт", "баланс", "balance"):
        u["waiting_for"] = None
        send(vk, vk_id, credits_text(vk_id), keyboard=kb_main())
        return

    if t in ("💬 поддержка", "поддержка"):
        u["waiting_for"] = None
        support_url = f"https://vk.com/im?sel={ADMIN_VK_ID}" if ADMIN_VK_ID else "https://vk.com/im?sel=l_khlopenik"
        send(vk, vk_id,
             "💬 Поддержка FRAME\n\n"
             "Нажми кнопку ниже — откроется личный чат с поддержкой 🙌",
             keyboard=kb_support_link(support_url))
        if ADMIN_VK_ID:
            try:
                send(vk, ADMIN_VK_ID,
                     f"🆘 ПОДДЕРЖКА ВК\n\n"
                     f"Пользователь vk.com/id{vk_id} написал в поддержку.\n"
                     f"Напиши ему 👉 vk.com/id{vk_id}")
            except Exception:
                pass
        return

    if t in ("📄 оферта и правила", "оферта и правила", "оферта"):
        u["waiting_for"] = None
        send(vk, vk_id,
             "📄 Оферта и правила:\n\nПользуясь ботом, вы соглашаетесь с правилами сервиса FRAME.\n"
             "По вопросам: vk.com/club239444342",
             keyboard=kb_main())
        return

    if t in ("ℹ️ о боте", "о боте", "помощь", "help", "/help"):
        u["waiting_for"] = None
        send(vk, vk_id,
             "🖼 FRAME — AI-нейрофотосессии\n\n"
             "Как работает:\n"
             "1. Нажми «📸 Генерация фото»\n"
             "2. Отправь своё фото\n"
             "3. Выбери модель (стиль)\n"
             "4. Получи результат через ~30 сек\n\n"
             "Типы кредитов:\n"
             "⭐ Стандарт — базовое качество\n"
             "✨ Версия 2 — улучшенное\n"
             "💎 Про — максимальное\n"
             "🔷 Алмазы — для Профи-моделей\n\n"
             "По вопросам пишите в сообщения сообщества.",
             keyboard=kb_main())
        return

    if t in ("💳 баланс", "баланс", "balance"):
        u["waiting_for"] = None
        send(vk, vk_id, credits_text(vk_id), keyboard=kb_main())
        return

    if t in ("🛒 купить кредиты", "купить кредиты", "купить", "тарифы"):
        u["waiting_for"] = "tariff_select"
        send(vk, vk_id,
             "💳 Выберите тариф:\n\n"
             "🎁 Пробный — 1⭐+1✨+1💎 за 149₽\n"
             "⭐ Стандарт 10 — 590₽\n"
             "✨ Версия2 10 — 790₽\n"
             "💎 Про 10 — 1190₽\n"
             "🔷 500 алмазов — 490₽\n"
             "🔷 1500 алмазов — 1290₽",
             keyboard=kb_tariffs_basic())
        return

    if t in ("📸 генерация фото", "генерация фото", "генерировать", "генерация"):
        u["waiting_for"] = "photo"
        send(vk, vk_id,
             "📷 Отправьте ваше фото (лицо должно быть чётко видно):",
             keyboard=kb_cancel())
        return

    if t in ("❌ отмена", "отмена", "cancel"):
        u["waiting_for"] = None
        send(vk, vk_id, "Отменено.", keyboard=kb_main())
        return

    # ── Выбор тарифа ──────────────────────────────────────────────────────────
    if u.get("waiting_for") == "tariff_select":
        tariff_map = {
            "🎁 пробный 149₽":             "trial",
            "⭐ станд. 10 фото 590₽":      "std_10",
            "✨ версия2 10 фото 790₽":     "v2_10",
            "💎 про 10 фото 1190₽":        "pro_10",
            "🔷 алмазы 500шт 490₽":        "diamond_500",
            "🔷 алмазы 1500шт 1290₽":      "diamond_1500",
        }
        tariff_key = tariff_map.get(t)
        if tariff_key:
            u["waiting_for"] = None
            label_t = TARIFF_PRICES[tariff_key][0]
            price = TARIFF_PRICES[tariff_key][3]
            link, _ = create_yookassa_link(vk_id, tariff_key)
            if link:
                send(vk, vk_id,
                     f"💳 {label_t} — {price}₽\n\n"
                     "Нажми кнопку ниже для безопасной оплаты через ЮKassa.\n"
                     "После оплаты кредиты зачислятся автоматически 💎",
                     keyboard=kb_pay_link(make_redirect_url(link), label_t))
            else:
                send(vk, vk_id,
                     "⚠️ Не удалось создать ссылку для оплаты. Напишите в сообщения сообщества.",
                     keyboard=kb_main())
        else:
            send(vk, vk_id, "Выберите тариф из списка:", keyboard=kb_tariffs_basic())
        return

    # ── Выбор модели (галерея) ────────────────────────────────────────────────
    if u.get("waiting_for") == "model_select":
        model_map = {
            "⭐ стандарт": "std",
            "✨ версия 2": "v2",
            "💎 про":      "pro",
        }
        if t in model_map:
            key = model_map[t]
            if not has_credits(vk_id, key):
                send(vk, vk_id,
                     f"❌ Нет кредитов '{GALLERY_MODELS[key][3]}'.\nКупите тариф или выберите другую модель.",
                     keyboard=kb_model_choice())
                return
            u["selected_model"] = key
            u["waiting_for"] = "prompt"
            send(vk, vk_id,
                 f"✅ Модель: {GALLERY_MODELS[key][3]}\n\n"
                 "Введите промпт (описание желаемого стиля, образа).\n"
                 "Или отправьте «-» чтобы использовать стандартный стиль:",
                 keyboard=kb_cancel())
            return

        if t in ("🔷 профи (алмазы)", "профи", "алмазы"):
            u["waiting_for"] = "diamond_model_select"
            dia = u.get("diamond_credits", 0)
            send(vk, vk_id,
                 f"🔷 Ваш баланс: {dia} 💎\n\nВыберите Профи-модель:",
                 keyboard=kb_diamond_models())
            return

        send(vk, vk_id, "Выберите модель из предложенных:", keyboard=kb_model_choice())
        return

    # ── Выбор Профи-модели (алмазы) ──────────────────────────────────────────
    if u.get("waiting_for") == "diamond_model_select":
        matched_key = None
        for key, (slug, cost, name) in DIAMOND_MODELS.items():
            btn_label = f"{name} ({cost}💎)".lower()
            if t == btn_label:
                matched_key = key
                break
        if matched_key:
            if not has_credits(vk_id, matched_key):
                cost = DIAMOND_MODELS[matched_key][1]
                dia = u.get("diamond_credits", 0)
                send(vk, vk_id,
                     f"❌ Нужно {cost}💎, у вас {dia}💎.\nКупите алмазы или выберите другую модель.",
                     keyboard=kb_diamond_models())
                return
            u["selected_model"] = matched_key
            u["waiting_for"] = "prompt"
            name = DIAMOND_MODELS[matched_key][2]
            cost = DIAMOND_MODELS[matched_key][1]
            send(vk, vk_id,
                 f"✅ Модель: {name} ({cost}💎)\n\n"
                 "Введите промпт (описание стиля).\nИли «-» для стандартного:",
                 keyboard=kb_cancel())
            return
        send(vk, vk_id, "Выберите модель из списка:", keyboard=kb_diamond_models())
        return

    # ── Промпт → запуск генерации ─────────────────────────────────────────────
    if u.get("waiting_for") == "prompt":
        prompt = "" if t == "-" else text.strip()
        face_url = u.get("face_url")
        model_key = u.get("selected_model", "std")

        if not face_url:
            u["waiting_for"] = "photo"
            send(vk, vk_id, "❌ Фото не найдено. Отправьте фото заново:", keyboard=kb_cancel())
            return

        u["waiting_for"] = None
        send(vk, vk_id, "⏳ Генерация запущена, ждите ~30-60 секунд...")

        def _generate():
            if model_key in DIAMOND_MODELS:
                slug, cost, name = DIAMOND_MODELS[model_key]
                inp_type = "image_url"
            else:
                slug, inp_type, needs_prompt, name = GALLERY_MODELS[model_key]

            request_id = start_generation(prompt, slug, face_url, inp_type)
            if not request_id:
                send(vk, vk_id, "❌ Ошибка запуска генерации. Попробуйте позже.", keyboard=kb_main())
                return

            result_url = poll_result(request_id)
            if not result_url or result_url == FAILED_SENTINEL:
                send(vk, vk_id, "❌ Генерация не удалась. Кредит не списан. Попробуйте снова.", keyboard=kb_main())
                return

            deduct_credit(vk_id, model_key)
            _save_history(vk_id, prompt or "стандартный стиль", result_url)

            att = upload_result_to_vk(vk, upload, group_id, result_url)
            if att:
                send(vk, vk_id, "✅ Готово! Вот ваше фото:", keyboard=kb_main(), attachment=att)
            else:
                send(vk, vk_id, f"✅ Готово! Ваше фото:\n{result_url}", keyboard=kb_main())

        threading.Thread(target=_generate, daemon=True).start()
        return

    # ── Неизвестная команда ───────────────────────────────────────────────────
    send(vk, vk_id, "Выберите действие:", keyboard=kb_main())


def handle_photo(vk, upload, group_id: int, vk_id: int, photo_url: str) -> None:
    u = get_user(vk_id)
    u["face_url"] = photo_url

    if u.get("waiting_for") == "photo":
        u["waiting_for"] = "model_select"
        send(vk, vk_id, "📸 Фото получено! Выберите модель (стиль):", keyboard=kb_model_choice())
    else:
        u["waiting_for"] = "model_select"
        send(vk, vk_id, "📸 Фото сохранено! Выберите модель:", keyboard=kb_model_choice())

# ─── Webhook для YooKassa (нужен Flask) ──────────────────────────────────────
def make_flask_app(vk):
    """Flask для получения YooKassa webhook."""
    try:
        from flask import Flask, request as freq, jsonify
    except ImportError:
        return None

    app = Flask(__name__)

    @app.route("/go/<token>", methods=["GET"])
    def _go(token):
        from flask import redirect as flask_redirect
        url = _redirects.get(token)
        if url:
            return flask_redirect(url, code=302)
        return "Link expired", 410

    @app.route("/ping", methods=["GET"])
    def _ping():
        return jsonify({"ok": True}), 200

    @app.after_request
    def _cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return resp

    @app.route("/api/<path:_p>", methods=["OPTIONS"])
    def _api_opts(_p):
        return jsonify(ok=True)

    # ── Mini App API ──────────────────────────────────────────────────────
    def _proxy_image(src: str, as_download: bool = False):
        """Общая логика прокси-изображений."""
        from flask import Response
        import urllib.request
        if not src:
            return "missing src", 400
        try:
            req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
                ct = r.headers.get("Content-Type", "image/jpeg")
            headers = {
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*",
            }
            if as_download:
                headers["Content-Disposition"] = "attachment; filename=\"frame_photo.jpg\""
            return Response(data, content_type=ct, headers=headers)
        except Exception as e:
            return f"proxy error: {e}", 502

    @app.route("/api/img", methods=["GET"])
    def api_img_proxy():
        """Проксируем изображение через наш сервер — скрываем источник."""
        src = freq.args.get("src", "")
        return _proxy_image(src, as_download=freq.args.get("download") == "1")

    @app.route("/api/photo.jpg", methods=["GET"])
    def api_photo_download():
        """Чистый URL для VKWebAppDownloadFile — всегда отдаёт как скачивание."""
        src = freq.args.get("src", "")
        return _proxy_image(src, as_download=True)

    @app.route("/api/upload-photo", methods=["POST"])
    def api_upload_photo():
        """Принимает файл изображения, сохраняет временно, отдаёт публичный URL."""
        import uuid, os, pathlib
        f = freq.files.get("photo")
        if not f:
            return jsonify(error="no file"), 400
        ext = pathlib.Path(f.filename or "x.jpg").suffix or ".jpg"
        uid = uuid.uuid4().hex
        tmp_dir = "/tmp/frame_uploads"
        os.makedirs(tmp_dir, exist_ok=True)
        path = f"{tmp_dir}/{uid}{ext}"
        f.save(path)
        public_url = f"https://vk-bot-2vns.onrender.com/api/photo/{uid}{ext}"
        return jsonify(url=public_url)

    @app.route("/api/photo/<filename>", methods=["GET"])
    def api_photo(filename):
        import os
        from flask import send_file
        path = f"/tmp/frame_uploads/{filename}"
        if not os.path.exists(path):
            return "Not found", 404
        return send_file(path)

    @app.route("/api/me", methods=["GET"])
    def api_me():
        try:
            vk_id = int(freq.args.get("vk_id", "0"))
        except ValueError:
            return jsonify(error="bad vk_id"), 400
        if not vk_id:
            return jsonify(error="vk_id required"), 400
        u = get_user(vk_id)
        _load_credits_from_db(vk_id)  # всегда свежие данные из базы
        return jsonify(
            vk_id=vk_id,
            std_credits=u.get("std_credits", 0),
            v2_credits=u.get("v2_credits", 0),
            pro_credits=u.get("pro_credits", 0),
            diamond_credits=u.get("diamond_credits", 0),
            gift_credits=u.get("gift_credits", 0),
            ref_count=u.get("ref_count", 0),
            ref_paid_count=u.get("ref_paid_count", 0),
            is_partner=u.get("is_partner", False),
            partner_pct=u.get("partner_pct", 0),
            partner_paid=u.get("partner_paid", 0.0),
        )

    @app.route("/api/support", methods=["POST"])
    def api_support():
        data = freq.get_json(silent=True) or {}
        try:
            vk_id = int(data.get("vk_id", 0))
        except (TypeError, ValueError):
            return jsonify(error="bad vk_id"), 400
        if not vk_id:
            return jsonify(error="vk_id required"), 400
        kind = data.get("kind", "support")  # support | partner

        admin_link = f"https://vk.com/im?sel={ADMIN_VK_ID}" if ADMIN_VK_ID else "https://vk.com/l_khlopenik"

        if kind == "partner":
            u = get_user(vk_id)
            already = u.get("is_partner", False)
            if not already:
                # Upsert — создаёт строку если нет, обновляет если есть
                if SUPABASE_URL:
                    try:
                        requests.post(
                            f"{SUPABASE_URL}/rest/v1/user_credits",
                            headers={**_sb_headers(),
                                     "Prefer": "resolution=merge-duplicates,return=minimal"},
                            json={"user_id": _db_id(vk_id),
                                  "is_partner": True, "partner_pct": 30},
                            timeout=10,
                        )
                    except Exception as e:
                        print(f"[PARTNER] ⚠️ DB upsert error: {e}")
                u["is_partner"] = True
                u["partner_pct"] = 30
                # Уведомляем админа
                if ADMIN_VK_ID:
                    try:
                        send(vk, ADMIN_VK_ID,
                             f"💰 НОВЫЙ ПАРТНЁР\n\nvk.com/id{vk_id} стал партнёром FRAME 🤝\n"
                             f"Процент: 30%")
                    except Exception as e:
                        print(f"[PARTNER] ⚠️ Notify admin error: {e}")
            return jsonify(
                ok=True,
                is_partner=True,
                partner_pct=u.get("partner_pct", 30),
                partner_paid=u.get("partner_paid", 0.0),
                ref_count=u.get("ref_count", 0),
            )

        # kind == support — бот шлёт кнопку перехода в личку
        if ADMIN_VK_ID:
            try:
                send(vk, vk_id,
                     "💬 Поддержка FRAME\n\n"
                     "Нажми кнопку ниже — откроется личный чат с поддержкой.\n"
                     "Напиши свой вопрос напрямую 🙌",
                     keyboard=kb_support_link(f"https://vk.com/im?sel={ADMIN_VK_ID}"))
                # Уведомление админу — сразу при нажатии
                send(vk, ADMIN_VK_ID,
                     f"🆘 ПОДДЕРЖКА ВК\n\n"
                     f"Пользователь vk.com/id{vk_id} нажал кнопку поддержки.\n"
                     f"Напиши ему первым 👉 vk.com/id{vk_id}")
            except Exception as e:
                print(f"[SUPPORT] ⚠️ Could not send: {e}")
        return jsonify(ok=True, admin_link=admin_link)

    @app.route("/api/tariffs", methods=["GET"])
    def api_tariffs():
        out = []
        for key, t in TARIFF_PRICES.items():
            label, ctype, amount, price = t
            out.append({"key": key, "label": label, "amount": amount, "price": price})
        return jsonify(tariffs=out)

    @app.route("/api/models", methods=["GET"])
    def api_models():
        gallery = [{"key": k, "label": v[3]} for k, v in GALLERY_MODELS.items()]
        diamond = [{"key": k, "label": v[2], "cost": v[1]} for k, v in DIAMOND_MODELS.items()]
        return jsonify(gallery=gallery, diamond=diamond)

    @app.route("/api/history", methods=["GET"])
    def api_history():
        try:
            vk_id = int(freq.args.get("vk_id", "0"))
        except ValueError:
            return jsonify(error="bad vk_id"), 400
        if not vk_id or not SUPABASE_URL:
            return jsonify(history=[])
        try:
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/generation_history",
                headers=_sb_headers(),
                params={"user_id": f"eq.{_db_id(vk_id)}",
                        "select": "prompt,result_url,created_at",
                        "order": "created_at.desc",
                        "limit": "30"},
                timeout=15,
            )
            return jsonify(history=r.json() if r.ok else [])
        except Exception as e:
            print(f"[API] history error: {e}")
            return jsonify(history=[])

    @app.route("/api/send-photo", methods=["POST"])
    def api_send_photo():
        """Отправляет фото из истории в VK-чат пользователя."""
        data = freq.get_json(silent=True) or {}
        try:
            vk_id = int(data.get("vk_id", 0))
        except (TypeError, ValueError):
            return jsonify(error="bad vk_id"), 400
        photo_url = data.get("photo_url", "")
        if not vk_id or not photo_url:
            return jsonify(error="missing params"), 400
        try:
            # Если это наш прокси — достаём оригинальный URL
            import urllib.parse as _up
            if "/api/img?" in photo_url:
                from urllib.parse import urlparse, parse_qs
                qs = parse_qs(urlparse(photo_url).query)
                src = qs.get("src", [photo_url])[0]
            else:
                src = photo_url
            att = upload_result_to_vk(vk, vk_api.VkUpload(vk), 0, src)
            if att:
                send(vk, vk_id, "📸 Вот твоё фото!", attachment=att)
                return jsonify(ok=True)
            return jsonify(error="upload_failed"), 500
        except Exception as e:
            print(f"[API] send-photo error: {e}")
            return jsonify(error="internal_error"), 500

    @app.route("/api/pay", methods=["POST"])
    def api_pay():
        data = freq.get_json(silent=True) or {}
        try:
            vk_id = int(data.get("vk_id", 0))
        except (TypeError, ValueError):
            return jsonify(error="bad vk_id"), 400
        tariff_key = data.get("tariff")
        if not vk_id or not tariff_key:
            return jsonify(error="vk_id and tariff required"), 400

        if not YOKASSA_SHOP_ID or not YOKASSA_KEY:
            print(f"[PAY] ❌ YOKASSA env vars not set!")
            return jsonify(error="payment_not_configured",
                           detail="YOKASSA_SHOP_ID / YOKASSA_KEY не заданы в Render env vars"), 503

        ensure_dynamic_tariff(tariff_key)
        if tariff_key not in TARIFF_PRICES:
            print(f"[PAY] ❌ Unknown tariff_key: {tariff_key!r}")
            return jsonify(error="unknown_tariff"), 400

        print(f"[PAY] Creating payment vk_id={vk_id} tariff={tariff_key}")
        link, yk_err = create_yookassa_link(vk_id, tariff_key)
        if not link:
            return jsonify(error="payment_link_error", detail=yk_err), 500
        print(f"[PAY] ✅ Link created: {link[:60]}...")

        # Отправляем кнопку open_link — пользователь видит красивую кнопку, не голую ссылку
        try:
            label_text = TARIFF_PRICES.get(tariff_key, ("Пакет",))[0]
            short_link = make_redirect_url(link)
            send(vk, vk_id,
                 f"💳 Оплата: {label_text}\n\n"
                 f"Нажми кнопку ниже — откроется безопасная оплата через ЮKassa.\n"
                 f"После оплаты кредиты зачислятся автоматически 💎",
                 keyboard=kb_pay_link(short_link, label_text))
            print(f"[PAY] ✉️ Button sent to vk_id={vk_id}")
        except Exception as e:
            print(f"[PAY] ⚠️ Could not send: {e}")

        return jsonify(ok=True, sent_to_chat=True)

    @app.route("/api/generate", methods=["POST"])
    def api_generate():
        data = freq.get_json(silent=True) or {}
        try:
            vk_id = int(data.get("vk_id", 0))
        except (TypeError, ValueError):
            return jsonify(error="bad vk_id"), 400
        photo_url  = data.get("photo_url")
        model_key  = data.get("model_key")
        prompt     = data.get("prompt", "") or ""
        size       = data.get("size", "vert") or "vert"
        if not (vk_id and photo_url and model_key):
            return jsonify(error="vk_id, photo_url, model_key required"), 400

        if model_key in DIAMOND_MODELS:
            entry = DIAMOND_MODELS[model_key]
            slug, cost, label = entry[0], entry[1], entry[2]
            param_name = entry[3] if len(entry) > 3 else "image_url"
            supports_image = True
        elif model_key in GALLERY_MODELS:
            slug, param_name, supports_image, label = GALLERY_MODELS[model_key]
        else:
            return jsonify(error="unknown model"), 400

        if not has_credits(vk_id, model_key):
            return jsonify(error="no_credits"), 402

        try:
            req_id = start_generation(prompt, slug, photo_url, param_name, size)
            if not req_id:
                return jsonify(error="generation_start_failed"), 500
            result_url = poll_result(req_id)
            if not result_url or result_url == FAILED_SENTINEL:
                return jsonify(error="generation_failed"), 500
            deduct_credit(vk_id, model_key)
            # Прячем источник — отдаём URL через наш прокси
            import urllib.parse
            proxied_url = f"https://vk-bot-2vns.onrender.com/api/img?src={urllib.parse.quote(result_url, safe='')}"
            _save_history(vk_id, prompt, proxied_url)
            # Отправляем результат в чат пользователю без сжатия (как документ)
            try:
                import urllib.request, tempfile, os
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    urllib.request.urlretrieve(result_url, tmp.name)  # оригинал для отправки
                    tmp_path = tmp.name
                upload = vk_api.VkUpload(vk)
                docs = upload.document_message(tmp_path, peer_id=vk_id, title="FRAME фото")
                os.unlink(tmp_path)
                attach = f"doc{docs[0]['owner_id']}_{docs[0]['id']}"
                send(vk, vk_id, "✨ Ваше фото готово!", attachment=attach)
            except Exception as se:
                print(f"[API] doc upload failed, trying photo: {se}")
                try:
                    att = upload_result_to_vk(vk, vk_api.VkUpload(vk), 0, result_url)
                    if att:
                        send(vk, vk_id, "✨ Ваше фото готово!", attachment=att)
                    else:
                        send(vk, vk_id, "✨ Ваше фото готово! Смотри в разделе История.")
                except Exception as se2:
                    print(f"[API] photo upload also failed: {se2}")
            return jsonify(result_url=proxied_url)
        except Exception as e:
            print(f"[API] generate error: {e}")
            return jsonify(error="internal_error"), 500

    # ── Gallery API (shared Supabase — same data as TG mini app) ─────────────

    @app.route("/api/categories", methods=["GET"])
    def api_categories():
        if not SUPABASE_URL:
            return jsonify([])
        try:
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/gallery_categories",
                headers=_sb_headers(),
                params={"order": "sort_order.asc", "select": "cat_key,cat_name"},
                timeout=10,
            )
            result = []
            for row in (r.json() if r.ok else []):
                name = row.get("cat_name", "")
                parts = name.split(" ", 1)
                if len(parts) == 2 and len(parts[0]) <= 3:
                    emoji, label = parts[0], parts[1]
                else:
                    emoji, label = "📁", name
                result.append({"key": row["cat_key"], "emoji": emoji, "name": label})
            return jsonify(result)
        except Exception as e:
            print(f"[API] categories error: {e}")
            return jsonify([])

    @app.route("/api/styles/<category_key>", methods=["GET"])
    def api_styles(category_key):
        if not SUPABASE_URL:
            return jsonify([])
        try:
            params = {
                "active": "eq.true",
                "order":  "hot.desc,created_at.desc",
                "select": "id,name,prompt,photo_url,input_label,photo_count,photo_hint,collage_example_url,quality_modes,category_key,hot",
            }
            if category_key != "all":
                params["category_key"] = f"eq.{category_key}"
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/styles",
                headers=_sb_headers(),
                params=params,
                timeout=10,
            )
            styles = r.json() if r.ok else []
            import urllib.parse as _up
            proxy = "https://vk-bot-2vns.onrender.com/api/img?src="
            for s in styles:
                if s.get("photo_url"):
                    s["photo_url"] = proxy + _up.quote(s["photo_url"], safe="")
                if s.get("collage_example_url"):
                    s["collage_example_url"] = proxy + _up.quote(s["collage_example_url"], safe="")
            return jsonify(styles)
        except Exception as e:
            print(f"[API] styles error: {e}")
            return jsonify([])

    @app.route("/api/style-one/<int:style_id>", methods=["GET"])
    def api_style_one(style_id):
        if not SUPABASE_URL:
            return jsonify(ok=False), 404
        try:
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/styles",
                headers={**_sb_headers(), "Accept": "application/vnd.pgrst.object+json"},
                params={"id": f"eq.{style_id}"},
                timeout=10,
            )
            s = r.json() if r.ok else {}
            if not s or "id" not in s:
                return jsonify(ok=False), 404
            import urllib.parse as _up2
            proxy = "https://vk-bot-2vns.onrender.com/api/img?src="
            def _p(u): return (proxy + _up2.quote(u, safe="")) if u else ""
            return jsonify(
                ok=True,
                id=s.get("id"),
                name=s.get("name", ""),
                photo_url=_p(s.get("photo_url", "")),
                input_label=s.get("input_label", ""),
                photo_count=s.get("photo_count", 1) or 1,
                photo_hint=s.get("photo_hint", ""),
                collage_example_url=_p(s.get("collage_example_url", "")),
                quality_modes=s.get("quality_modes", "std,v2,pro") or "std,v2,pro",
                category_key=s.get("category_key", ""),
            )
        except Exception as e:
            print(f"[API] style-one error: {e}")
            return jsonify(ok=False), 500

    @app.route("/yookassa-webhook-vk", methods=["POST"])
    def yk_webhook():
        data = freq.get_json(silent=True) or {}
        obj = data.get("object", {})
        if data.get("event") != "payment.succeeded":
            return jsonify(ok=True)
        meta = obj.get("metadata", {})
        vk_id_str = meta.get("vk_id")
        tariff_key = meta.get("tariff")
        if not vk_id_str or not tariff_key:
            return jsonify(ok=True)
        vk_id = int(vk_id_str)
        ensure_dynamic_tariff(tariff_key)
        msg = add_credits(vk_id, tariff_key)
        send(vk, vk_id, f"✅ Оплата получена!\n{msg}\n\n{credits_text(vk_id)}", keyboard=kb_main())
        return jsonify(ok=True)

    return app

# ─── Главный цикл ─────────────────────────────────────────────────────────────
def main():
    if not VK_TOKEN:
        print("❌ VK_TOKEN не задан в env!")
        # Нет токена — запускаем только Flask (чтобы Render не убил сервис)
        port = int(os.environ.get("PORT", "") or "5000")
        from flask import Flask
        app = Flask(__name__)
        @app.route("/ping")
        def _ping(): return "no token"
        app.run(host="0.0.0.0", port=port, use_reloader=False)
        return

    print(f"🚀 Старт бота (Python {__import__('sys').version})")

    try:
        vk_session = vk_api.VkApi(token=VK_TOKEN)
        vk = vk_session.get_api()
        upload = VkUpload(vk_session)
    except Exception as e:
        print(f"❌ Ошибка инициализации VK API: {e}")
        import traceback; traceback.print_exc()
        # Запускаем Flask чтобы Render не убил сервис из-за отсутствия порта
        port = int(os.environ.get("PORT", "") or "5000")
        from flask import Flask
        app = Flask(__name__)
        @app.route("/ping")
        def _ping2(): return "vk init error"
        app.run(host="0.0.0.0", port=port, use_reloader=False)
        return

    # Определяем group_id из токена
    try:
        group_info = vk.groups.getById()
        group_id = group_info[0]["id"]
        print(f"✅ Бот запущен: {group_info[0]['name']} (id{group_id})")
    except Exception as e:
        print(f"⚠️ Не удалось получить group_id: {e}")
        group_id = 0

    # Flask для YooKassa webhook (запускаем в фоне)
    port = int(os.environ.get("PORT", "") or "5000")
    flask_app = make_flask_app(vk)
    if flask_app:
        t = threading.Thread(
            target=lambda: flask_app.run(host="0.0.0.0", port=port, use_reloader=False),
            daemon=True
        )
        t.start()
        print(f"✅ Flask webhook на порту {port}")

    while True:
        try:
            print(f"🔄 Инициализация Long Poll (group_id={group_id})...")
            longpoll = VkBotLongPoll(vk_session, group_id, wait=25)
            print("🔄 Long Poll запущен, жду сообщений...")

            for event in longpoll.listen():
                print(f"📩 Событие: {event.type}")
                if event.type != VkBotEventType.MESSAGE_NEW:
                    continue

                msg = event.object.message
                vk_id = msg["from_id"]
                text = msg.get("text", "")

                # Извлекаем фото из вложений
                photo_url = None
                for att in msg.get("attachments", []):
                    if att.get("type") == "photo":
                        sizes = att["photo"].get("sizes", [])
                        if sizes:
                            best = sorted(sizes, key=lambda s: s.get("width", 0))[-1]
                            photo_url = best.get("url")
                        break

                try:
                    if photo_url:
                        handle_photo(vk, upload, group_id, vk_id, photo_url)
                        if text:
                            handle_text(vk, upload, group_id, vk_id, text, event)
                    elif text:
                        handle_text(vk, upload, group_id, vk_id, text, event)
                except Exception as e:
                    print(f"[main] error for vk_id={vk_id}: {e}")
                    try:
                        send(vk, vk_id, "❌ Произошла ошибка. Попробуйте снова.", keyboard=kb_main())
                    except Exception:
                        pass

        except (KeyboardInterrupt, SystemExit):
            print("🛑 Остановка бота")
            break
        except Exception as e:
            print(f"❌ Long Poll error: {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()
            print("⏳ Перезапуск через 5 секунд...")
            time.sleep(5)


if __name__ == "__main__":
    main()
