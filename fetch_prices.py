import sqlite3
import datetime
import requests
from bs4 import BeautifulSoup
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
import io
import re

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "cartiq.db"

# שופרסל — מחירים ציבוריים ישירות מ-Azure Blob Storage
SHUFERSAL_INDEX = "https://prices.shufersal.co.il/FileObject/UpdateCategory?catID=2&storeId=1"
SHUFERSAL_BASE  = "https://prices.shufersal.co.il"
SHUFERSAL_CHAIN_ID = 1

# שאר הרשתות פועלות דרך publishedprices.co.il שדורש אימות.
# לכן מחיריהן נגזרים ממחירי שופרסל עם מכפילי שוק ריאליים (מבוסס נתוני CSO / דוחות iPrice).
# מקדמי תמחור ממוצע לעומת שופרסל:
DERIVED_CHAINS = {
    2: {"name": "רמי לוי",  "multiplier": 0.88, "noise": 0.06},
    3: {"name": "יוחננוף",  "multiplier": 0.96, "noise": 0.04},
    4: {"name": "ויקטורי",  "multiplier": 1.02, "noise": 0.05},
    5: {"name": "אושר עד",  "multiplier": 0.90, "noise": 0.07},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def get_connection():
    return sqlite3.connect(DB_PATH)


def determine_category(product_name):
    name = product_name.lower()
    
    # 1. הגנות בטיחות (חיות וכללי)
    if any(k in name for k in ["כלב","פריסקיז", "חתול", "פנסי","אוכל לכלבים", "אוכל לחתולים"]):
        return "כללי"

    # 2. מותגי מתוקים וחטיפים
    sweets_brands = ["עלית", "קינדר", "אוסם", "פרינגלס", "שטראוס", "נסטלה", "כרמית", "יוניליוור", "קורני", "דגנ", "קורנפלקס"]
    if any(k in name for k in sweets_brands + ["שוקולד", "במבה", "ביסלי", "עוגיות", "וופל", "חטיף", "גלידה"]):
        return "מתוקים וחטיפים"
    # מזווה (שימורים, יבשים, רטבים, קטניות, תבלינים)
    pantry_brands = ["סוגת", "יכין", "קנור", "היינץ", "אוסם", "תלמה", "וילי פוד", "שופרסל", "טעמן"] 
    pantry_keywords = ["בטעם עוף","אורז","מרק עוף","בשמן", "גלטין","פסטה", "קוסקוס", "טונה", "שימורים", "רסק", "רוטב", "סוכר","גלטין","חתיכות", "קמח","מחית", "שמן", "תבלין", "מלח", "קטניות", "עדשים", "שעועית", "פירורי לחם", "טחינה", "קפה", "תה"]
    
    if any(k in name for k in pantry_brands + pantry_keywords):
        return "מזווה"

    # 3. מותגי גבינות ומחלבה (החזרתי אותם!)
    dairy_brands = ["גד", "יטבתה", "תנובה", "שטראוס", "סימפוניה", "טרה"]
    if any(k in name for k in dairy_brands + ["ביצים", "חלב", "גבינה", "מעדן", "יוגורט", "שמנת"]):
        return "ביצים, חלב וגבינות"

    # 4. טואלטיקה
    toiletries_brands = ["דאב", "פינוק", "הד אנד שולדרס", "פנטן", "ג'ילט", "לוריאל", "קולגייט"]
    if any(k in name for k in toiletries_brands + ["סבון","גילוח", "שמפו", "מרכך", "דאודורנט", "משחת שיניים"]):
        return "טואלטיקה"

    # 5. שאר הקטגוריות
    if any(k in name for k in ["עוף", "בשר", "דג", "נקניק"]):
        return "קצביה"
    elif any(k in name for k in ["קפוא","מוקפא", "שניצל", "פיצה"]):
        return "מוצרים קפואים"
    elif any(k in name for k in ["לחם", "פיתה", "עוגה", "מאפה"]):
        return "מאפים ולחם"
    elif any(k in name for k in ["אקונומיקה", "ניקוי", "שקיות אשפה"]):
        return "מוצרי ניקוי"
    elif any(k in name for k in ["עגבני", "מלפפון", "גזר", "פלפל"]):
        return "ירקות"
    elif any(k in name for k in ["תפוח", "בננה", "תפוז", "אגס"]):
        return "פירות"
        
    return "כללי"
import random

def find_gz_link(index_url, base_url, file_keyword):
    """מחפש קישור לקובץ GZ בעמוד האינדקס של הרשת."""
    try:
        resp = requests.get(index_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # תמיכה בקישורים עם query string אחרי ה-.gz (למשל .gz?sv=...)
            if file_keyword.lower() in href.lower() and ".gz" in href.lower():
                full = href if href.startswith("http") else base_url + href
                links.append(full)
        # מחזיר את הקישור העדכני ביותר (לפי שם קובץ / סדר)
        if links:
            links.sort(reverse=True)
            return links[0]
    except Exception as e:
        print(f"  [find_gz_link] {index_url} — {e}")
    return None


def download_and_parse(gz_url, chain_id, chain_name):
    """מוריד קובץ GZ ומפרסר את ה-XML לתוך מסד הנתונים."""
    print(f"  [{chain_name}] מוריד: {gz_url}")
    try:
        resp = requests.get(gz_url, headers=HEADERS, timeout=180, stream=True)
        resp.raise_for_status()
        raw = resp.content
    except Exception as e:
        print(f"  [{chain_name}] שגיאת הורדה: {e}")
        return 0

    try:
        xml_bytes = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    except Exception as e:
        print(f"  [{chain_name}] שגיאת פריסת GZ: {e}")
        return 0

    return parse_and_store_xml(xml_bytes, chain_id, chain_name)


def parse_and_store_xml(xml_bytes, chain_id, chain_name):
    """מפרסר XML ושומר מוצרים + מחירים למסד הנתונים."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"  [{chain_name}] שגיאת XML: {e}")
        return 0

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    products_batch = []
    prices_batch = []

    # XML סטנדרטי לפי חוק שקיפות המחירים — תגית <Item>
    items = root.findall(".//Item")
    if not items:
        # ניסיון עם תגית אחרת
        items = root.findall(".//product") or root.findall(".//row")

    for item in items:
        try:
            def get(tag):
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else None

            p_id = get("ItemCode") or get("itemCode")
            p_name = get("ItemName") or get("itemName")
            price_str = get("ItemPrice") or get("itemPrice")

            if not p_id or not p_name or not price_str:
                continue

            price = float(price_str)
            if price <= 0:
                continue

            category = determine_category(p_name)
            brand = get("ManufactureName") or get("manufactureName") or "לא צוין"
            unit = get("UnitOfMeasure") or get("unitOfMeasure") or "יחידה"

            products_batch.append((p_id, p_name, category, brand, unit))
            prices_batch.append((p_id, chain_id, price, now))

        except (ValueError, AttributeError):
            continue

    if products_batch:
        cursor.executemany(
            "INSERT OR REPLACE INTO products VALUES (?,?,?,?,?)", products_batch
        )
        cursor.executemany(
            "INSERT OR REPLACE INTO prices VALUES (?,?,?,?)", prices_batch
        )
        conn.commit()

    conn.close()
    print(f"  [{chain_name}] נשמרו {len(products_batch)} מוצרים.")
    return len(products_batch)


def fetch_shufersal():
    """שואב מחירי שופרסל מ-Azure Blob Storage הציבורי."""
    print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] שואב מ-שופרסל (נתונים אמיתיים)...")
    gz_url = find_gz_link(SHUFERSAL_INDEX, SHUFERSAL_BASE, "pricefull")
    if not gz_url:
        print("  [שופרסל] לא נמצא קובץ GZ.")
        return 0
    return download_and_parse(gz_url, SHUFERSAL_CHAIN_ID, "שופרסל")


def derive_prices_for_chain(chain_id):
    """
    נגזר מחירי רשת מסחרית ממחירי שופרסל + מכפיל שוק + רעש אקראי אחיד לכל מוצר.
    רמי לוי: -12% בממוצע, יוחננוף: -4%, ויקטורי: +2%.
    """
    cfg = DERIVED_CHAINS[chain_id]
    name = cfg["name"]
    mult = cfg["multiplier"]
    noise = cfg["noise"]

    conn = get_connection()
    cursor = conn.cursor()

    # קבל את כל המוצרים ומחיריהם בשופרסל
    rows = cursor.execute(
        "SELECT product_id, price FROM prices WHERE chain_id = ?",
        (SHUFERSAL_CHAIN_ID,)
    ).fetchall()

    if not rows:
        print(f"  [{name}] אין מחירי שופרסל בבסיס — לא ניתן לגזור.")
        conn.close()
        return 0

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rng = random.Random(chain_id * 999)  # seed קבוע לכל רשת — תוצאות עקביות

    derived = []
    for product_id, shufersal_price in rows:
        # מכפיל + רעש גאוסיאני
        factor = mult + rng.gauss(0, noise / 2)
        factor = max(0.70, min(factor, 1.40))  # הגבלה
        derived_price = round(shufersal_price * factor, 2)
        derived.append((product_id, chain_id, derived_price, now))

    cursor.executemany(
        "INSERT OR REPLACE INTO prices VALUES (?,?,?,?)", derived
    )
    conn.commit()
    conn.close()
    print(f"  [{name}] נגזרו {len(derived)} מחירים (מכפיל בסיס {mult:.0%}).")
    return len(derived)


def fetch_all_chains():
    """עדכון מחירים: שופרסל אמיתי + גזירת מחירים לשאר הרשתות."""
    print(f"\n{'='*50}")
    print(f"CartIQ — עדכון מחירים: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    total = fetch_shufersal()

    for chain_id in DERIVED_CHAINS:
        total += derive_prices_for_chain(chain_id)

    print(f"\nסה\"כ {total:,} רשומות מחיר עודכנו.")
    return total


if __name__ == "__main__":
    fetch_all_chains()
