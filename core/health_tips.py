"""
CareFirst Medical Center - Health Tips Engine
Daily rotating health tips with Indian context
"""
import random
from datetime import date
from typing import List, Dict


HEALTH_TIPS = {
    "general": [
        {"title": "💧 Stay Hydrated", "tip": "Drink at least 8 glasses (2-3 litres) of water daily. In Indian summers, increase to 3-4 litres. Add nimbu (lemon) for electrolytes.", "category": "hydration"},
        {"title": "🚶 Walk Daily", "tip": "Walk 30 minutes daily. A brisk walk after dinner aids digestion and controls blood sugar — especially important for Indian diets rich in carbs.", "category": "fitness"},
        {"title": "😴 Sleep Well", "tip": "Adults need 7-8 hours of sleep. Avoid screen time 1 hour before bed. Irregular sleep increases diabetes and heart disease risk.", "category": "sleep"},
        {"title": "🧘 Manage Stress", "tip": "Practice pranayama or meditation for 10 minutes daily. Chronic stress raises BP and weakens immunity.", "category": "mental_health"},
        {"title": "🪥 Oral Health", "tip": "Brush twice daily and floss. Gum disease is linked to heart disease — a growing concern in India.", "category": "dental"},
        {"title": "🧼 Hand Hygiene", "tip": "Wash hands for 20 seconds with soap. Prevents 80% of infections. Critical during monsoon season in India.", "category": "hygiene"},
        {"title": "☀️ Vitamin D", "tip": "Get 15-20 minutes of morning sunlight. 70% of Indians are Vitamin D deficient. Consider supplements after testing.", "category": "nutrition"},
        {"title": "🥦 Eat More Vegetables", "tip": "Fill half your plate with vegetables. Indian thalis are great — add more sabzi, less rice/roti for balanced nutrition.", "category": "nutrition"},
    ],
    "heart": [
        {"title": "❤️ Heart Health", "tip": "Limit oil usage to 3-4 tsp per person per day. Switch to mustard oil or olive oil. Avoid deep-fried foods daily.", "category": "heart"},
        {"title": "🫀 Blood Pressure", "tip": "Get BP checked monthly. Normal is 120/80. Hypertension has no symptoms — called the 'silent killer' in India.", "category": "heart"},
        {"title": "🧂 Reduce Salt", "tip": "Limit salt to 5g/day (1 tsp). Indian diets average 10g+ — mainly from pickles, papad, and processed foods.", "category": "heart"},
        {"title": "🥜 Healthy Fats", "tip": "Include walnuts (akhrot), almonds (badam), and flaxseeds (alsi) daily. These reduce cholesterol naturally.", "category": "heart"},
        {"title": "🩺 Cholesterol Check", "tip": "Get lipid profile done annually after age 30. Family history of heart disease? Start at 25.", "category": "heart"},
    ],
    "diabetes": [
        {"title": "🩸 Blood Sugar", "tip": "Check fasting sugar regularly. Normal: 70-100 mg/dL. Pre-diabetic: 100-125. Indian population has high genetic risk.", "category": "diabetes"},
        {"title": "🍚 Control Carbs", "tip": "Reduce white rice and maida. Switch to brown rice, millets (bajra, jowar, ragi). Millets are low-GI and traditional Indian grains.", "category": "diabetes"},
        {"title": "🍵 Cinnamon Tea", "tip": "Drink cinnamon (dalchini) water daily — half tsp in warm water. Studies show it helps control blood sugar levels.", "category": "diabetes"},
        {"title": "🏃 Post-Meal Walk", "tip": "Walk 10-15 minutes after every meal. This simple habit can reduce blood sugar spikes by 30%.", "category": "diabetes"},
    ],
    "monsoon": [
        {"title": "🌧️ Monsoon Health", "tip": "Avoid street food during monsoons. Waterborne diseases peak June-September. Drink only boiled/filtered water.", "category": "monsoon"},
        {"title": "🦟 Mosquito Prevention", "tip": "Use repellents and wear full sleeves. Dengue and malaria cases spike in Indian monsoons. Remove stagnant water.", "category": "monsoon"},
        {"title": "🍲 Immunity Foods", "tip": "Have tulsi (holy basil), haldi (turmeric) milk, and adrak (ginger) tea daily. These boost immunity naturally.", "category": "monsoon"},
        {"title": "🍛 Light Meals", "tip": "Eat lighter during monsoons. Khichdi, dal-rice, and soup are easier to digest than heavy curries.", "category": "monsoon"},
    ],
    "mental": [
        {"title": "🧠 Mental Health", "tip": "Talk about your feelings. India has 150M+ people with mental health issues, yet stigma prevents 80% from seeking help.", "category": "mental_health"},
        {"title": "📵 Digital Detox", "tip": "Take 1-hour break from screens daily. Social media comparison increases anxiety. Practice gratitude instead.", "category": "mental_health"},
        {"title": "👨‍👩‍👧 Social Connection", "tip": "Spend quality time with family daily. Strong social bonds reduce depression risk by 50%. Eat meals together.", "category": "mental_health"},
    ],
    "women": [
        {"title": "👩 Women's Health", "tip": "Annual health checkups are essential: Pap smear, breast exam, thyroid, and bone density after 40.", "category": "womens_health"},
        {"title": "🦴 Bone Health", "tip": "Women need 1200mg calcium daily post-menopause. Include ragi, sesame seeds (til), dairy, and leafy greens.", "category": "womens_health"},
        {"title": "🩸 Iron Intake", "tip": "Menstruating women need 18mg iron daily. Eat spinach (palak), jaggery (gur), and Dates (khajoor) regularly.", "category": "womens_health"},
    ],
    "eldercare": [
        {"title": "👴 Elder Care", "tip": "Annual full body checkup after 60: BP, sugar, cholesterol, eye, hearing, and cancer screening.", "category": "elderly"},
        {"title": "🦴 Fall Prevention", "tip": "Remove loose carpets and install bathroom grab bars. Falls are the #1 cause of injury in seniors.", "category": "elderly"},
        {"title": "💊 Medication Management", "tip": "Use a weekly pill organizer. Keep a updated medication list. Never skip doses without consulting doctor.", "category": "elderly"},
    ],
}


def get_daily_tips(count: int = 3) -> List[Dict]:
    """Get rotating daily tips based on date seed"""
    today = date.today()
    seed = today.year * 1000 + today.month * 100 + today.day
    random.seed(seed)

    all_tips = []
    for category_tips in HEALTH_TIPS.values():
        all_tips.extend(category_tips)

    selected = random.sample(all_tips, min(count, len(all_tips)))
    return selected


def get_tips_by_category(category: str) -> List[Dict]:
    """Get tips for a specific category"""
    return HEALTH_TIPS.get(category, [])


def get_all_categories() -> List[str]:
    """Get all available tip categories"""
    return list(HEALTH_TIPS.keys())


def get_seasonal_tip() -> Dict:
    """Get a seasonal tip based on current month"""
    month = date.today().month
    if month in [6, 7, 8, 9]:  # Monsoon
        category = "monsoon"
    elif month in [3, 4, 5]:  # Summer
        return {"title": "☀️ Summer Care", "tip": "Drink nimbu paani (lemon water) with salt and sugar. Avoid going out 12-3 PM. Wear light cotton clothes. Use sunscreen."}
    elif month in [12, 1, 2]:  # Winter
        return {"title": " Winter Health", "tip": "Exercise indoors if foggy. Eat seasonal: carrots, peanuts, til (sesame). Cover head and ears when going out."}
    else:  # Autumn
        return {"title": "🍂 Autumn Wellness", "tip": "Season change = allergy season. Wash fruits/veggies thoroughly. Keep inhaler handy if asthmatic."}

    tips = HEALTH_TIPS.get(category, HEALTH_TIPS["general"])
    return random.choice(tips)
