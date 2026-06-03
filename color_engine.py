"""
color_engine.py
---------------
خوارزمية مطابقة الألوان — منفصلة تماماً عن واجهة المستخدم.
يمكن استيرادها واستخدامها في أي مشروع آخر.
"""

import colorsys

# ============= ثوابت الخوارزمية =============

# نطاقات العلاقات بين الألوان (بالدرجات على عجلة الألوان)
EXACT_MATCH_THRESHOLD       = 15    # نفس اللون تقريباً
ANALOGOUS_THRESHOLD         = 40    # ألوان مجاورة
COMPLEMENTARY_TOLERANCE     = 20    # هامش اللون المكمل
TRIADIC_TOLERANCE           = 15    # هامش الألوان المثلثية
SPLIT_COMP_TOLERANCE        = 20    # هامش المكمل المنقسم

# مكافأة تنوع العلاقات
DIVERSITY_BONUS_PER_REL     = 0.05
MAX_DIVERSITY_BONUS         = 0.15

# درجات التشبع
SAT_SCORE_CLOSE     = 0.9   # فرق < 0.2
SAT_SCORE_MEDIUM    = 0.7   # فرق < 0.4
SAT_SCORE_FAR       = 0.5   # فرق < 0.6
SAT_SCORE_VERY_FAR  = 0.3   # فرق >= 0.6

# درجات الإضاءة
VAL_SCORE_CLOSE     = 0.95  # فرق < 0.15
VAL_SCORE_MEDIUM    = 0.75  # فرق < 0.3
VAL_SCORE_FAR       = 0.55  # فرق < 0.5
VAL_SCORE_VERY_FAR  = 0.35  # فرق >= 0.5

# درجات التباين
CONTRAST_SCORE_IDEAL    = 0.9   # تباين مثالي (0.2 - 0.6)
CONTRAST_SCORE_LOW      = 0.6   # تباين منخفض (ممل)
CONTRAST_SCORE_HIGH     = 0.7   # تباين عالٍ (صارخ)

# أوزان الألوان الدافئة في الإدراك البشري
WARMTH = {
    'red':      1.30,
    'orange':   1.20,
    'yellow':   1.15,
    'green':    1.00,
    'blue':     0.90,
    'purple':   0.95,
}

# ============= دوال التحويل =============

def rgb_to_hsv(rgb: tuple) -> tuple[float, float, float]:
    """تحويل RGB (0-255) إلى HSV — Hue بالدرجات (0-360)"""
    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s, v


def hue_distance(h1: float, h2: float) -> float:
    """
    المسافة الحقيقية بين لونين على العجلة (تأخذ الـ wrap-around بعين الاعتبار).
    النتيجة دائماً بين 0 و 180.
    """
    diff = abs(h1 - h2) % 360
    return min(diff, 360 - diff)

# ============= عائلات الألوان =============

def get_color_family(hue: float) -> str:
    """
    تصنيف اللون لعائلة بناءً على Hue.
    الحدود متسقة مع ANALOGOUS_THRESHOLD (40 درجة لكل عائلة تقريباً).
    """
    if hue < 20 or hue >= 340:  return "أحمر"
    elif hue < 60:               return "برتقالي"
    elif hue < 100:              return "أصفر"
    elif hue < 140:              return "أخضر مصفر"
    elif hue < 180:              return "أخضر"
    elif hue < 220:              return "أخضر مزرق"
    elif hue < 260:              return "أزرق"
    elif hue < 300:              return "بنفسجي"
    else:                        return "أرجواني"

# ============= علاقات عجلة الألوان =============

def complementary(hue: float) -> float:
    return (hue + 180) % 360

def split_complementary(hue: float) -> list[float]:
    return [(hue + 150) % 360, (hue + 210) % 360]

def triadic(hue: float) -> list[float]:
    return [(hue + 120) % 360, (hue + 240) % 360]

def tetradic(hue: float) -> list[float]:
    """مربع الألوان — علاقة رابعة لم تكن موجودة سابقاً"""
    return [(hue + 90) % 360, (hue + 180) % 360, (hue + 270) % 360]

# ============= حساب العلاقة =============

def calculate_color_relationship(hue1: float, hue2: float) -> tuple[str, float]:
    """
    تحديد أفضل علاقة لونية بين لونين.
    الإرجاع: (نوع العلاقة، درجة القوة 0-1)
    """
    dist = hue_distance(hue1, hue2)
    relationships = []

    # 1. نفس اللون
    if dist <= EXACT_MATCH_THRESHOLD:
        score = 1.0 - (dist / EXACT_MATCH_THRESHOLD) * 0.3
        relationships.append(("exact", score))

    # 2. نفس العائلة
    if get_color_family(hue1) == get_color_family(hue2):
        strength = 0.8 if dist <= 45 else 0.6
        relationships.append(("family", strength))

    # 3. مجاور
    if dist <= ANALOGOUS_THRESHOLD:
        relationships.append(("analogous", 0.7))

    # 4. مكمل
    if hue_distance(complementary(hue1), hue2) <= COMPLEMENTARY_TOLERANCE:
        relationships.append(("complementary", 0.9))

    # 5. مثلثي
    if any(hue_distance(t, hue2) <= TRIADIC_TOLERANCE for t in triadic(hue1)):
        relationships.append(("triadic", 0.75))

    # 6. مكمل منقسم
    if any(hue_distance(s, hue2) <= SPLIT_COMP_TOLERANCE for s in split_complementary(hue1)):
        relationships.append(("split_complementary", 0.85))

    # 7. رباعي (جديد — يغطي حالات لم تكن محسوبة)
    if any(hue_distance(t, hue2) <= COMPLEMENTARY_TOLERANCE for t in tetradic(hue1)):
        relationships.append(("tetradic", 0.80))

    # افتراضي إذا لم توجد علاقة
    if not relationships:
        relationships.append(("normal", max(0.0, 1 - dist / 180) * 0.5))

    return max(relationships, key=lambda x: x[1])

# ============= الوزن الإدراكي =============

def get_perceptual_weight(rgb: tuple) -> float:
    """
    كيف يرى العين البشرية هذا اللون — الألوان الدافئة تلفت الانتباه أكثر.
    الشروط مرتبة من الأخص للأعم لتفادي التداخل.
    """
    r, g, b = rgb[0] / 255, rgb[1] / 255, rgb[2] / 255
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    if h < 0.05 or h > 0.95:   warmth = WARMTH['red']
    elif h < 0.12:              warmth = WARMTH['orange']
    elif h < 0.18:              warmth = WARMTH['yellow']
    elif h < 0.45:              warmth = WARMTH['green']
    elif h < 0.75:              warmth = WARMTH['blue']
    else:                       warmth = WARMTH['purple']

    saturation_factor = 0.8 + (s * 0.5)
    value_factor      = 1.0 - abs(v - 0.5) * 0.5   # أفضل عند الإضاءة المتوسطة

    return warmth * saturation_factor * value_factor

# ============= مطابقة لونين =============

def smart_color_match(color1: tuple, color2: tuple) -> tuple[float, str]:
    """
    مقارنة لونين وإرجاع (نسبة التطابق 0-100، نوع العلاقة).
    تأخذ بعين الاعتبار: العلاقة اللونية، التشبع، الإضاءة، الإدراك، التباين.
    """
    try:
        h1, s1, v1 = rgb_to_hsv(color1)
        h2, s2, v2 = rgb_to_hsv(color2)
    except Exception:
        return 0.0, "invalid"

    rel_type, rel_score = calculate_color_relationship(h1, h2)

    # --- تشابه التشبع ---
    sd = abs(s1 - s2)
    sat_score = (SAT_SCORE_CLOSE   if sd < 0.2 else
                 SAT_SCORE_MEDIUM  if sd < 0.4 else
                 SAT_SCORE_FAR     if sd < 0.6 else
                 SAT_SCORE_VERY_FAR)

    # --- تشابه الإضاءة ---
    vd = abs(v1 - v2)
    val_score = (VAL_SCORE_CLOSE    if vd < 0.15 else
                 VAL_SCORE_MEDIUM   if vd < 0.3  else
                 VAL_SCORE_FAR      if vd < 0.5  else
                 VAL_SCORE_VERY_FAR)

    # --- التوافق الإدراكي ---
    pw1, pw2 = get_perceptual_weight(color1), get_perceptual_weight(color2)
    perceptual = min(pw1, pw2) / max(pw1, pw2) if max(pw1, pw2) > 0 else 0.0

    # --- التباين ---
    contrast = abs(v1 - v2)
    contrast_score = (CONTRAST_SCORE_IDEAL if 0.2 < contrast < 0.6 else
                      CONTRAST_SCORE_LOW   if contrast <= 0.2       else
                      CONTRAST_SCORE_HIGH)

    # --- أوزان مختلفة حسب نوع العلاقة ---
    weights = {
        "exact":              {'rel': 0.40, 'sat': 0.20, 'val': 0.20, 'p': 0.10, 'c': 0.10},
        "complementary":      {'rel': 0.35, 'sat': 0.15, 'val': 0.20, 'p': 0.10, 'c': 0.20},
        "split_complementary":{'rel': 0.30, 'sat': 0.20, 'val': 0.20, 'p': 0.15, 'c': 0.15},
        "tetradic":           {'rel': 0.30, 'sat': 0.20, 'val': 0.20, 'p': 0.15, 'c': 0.15},
    }.get(rel_type, {'rel': 0.25, 'sat': 0.25, 'val': 0.25, 'p': 0.15, 'c': 0.10})

    score = (
        rel_score     * weights['rel'] +
        sat_score     * weights['sat'] +
        val_score     * weights['val'] +
        perceptual    * weights['p']   +
        contrast_score* weights['c']
    )

    return score * 100, rel_type

# ============= مطابقة باليتات =============

def match_palettes(
    palette1: list[tuple],
    palette2: list[tuple],
) -> float:
    """
    مقارنة باليتتين وإرجاع نسبة التناسق (0-100).
    كل باليتة: قائمة من [(rgb_tuple, weight), ...]
    """
    if not palette1 or not palette2:
        return 0.0

    total_score  = 0.0
    total_weight = 0.0
    relationships_found = []

    for a_color, a_weight in palette1:
        if a_weight <= 0:
            continue

        best_score = 0.0
        best_rel   = None

        for b_color, b_weight in palette2:
            if b_weight <= 0:
                continue

            score, rel_type = smart_color_match(a_color, b_color)

            # مكافأة تطابق الأوزان النسبية
            max_w        = max(a_weight, b_weight)
            weight_match = min(a_weight, b_weight) / max_w if max_w > 0 else 0.0
            final        = score * (0.7 + 0.3 * weight_match)

            if final > best_score:
                best_score = final
                best_rel   = rel_type

        total_score  += best_score * a_weight
        total_weight += a_weight
        if best_rel:
            relationships_found.append(best_rel)

    if total_weight == 0:
        return 0.0

    # مكافأة تنوع العلاقات
    unique_rels     = len(set(relationships_found))
    diversity_bonus = 1 + min((unique_rels - 1) * DIVERSITY_BONUS_PER_REL, MAX_DIVERSITY_BONUS)

    return min((total_score / total_weight) * diversity_bonus, 100.0)
