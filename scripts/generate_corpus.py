"""
Generate synthetic Hinglish chat corpus per SRS requirements:
- 4,000+ messages
- 8 participants
- 6 months timespan
- Realistically messy (Hinglish, typos, one-word replies, etc.)
- 3 major decision threads with concrete outcomes
- 40 test queries (8 hard zero-overlap)
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.store import MessageStore
from src.data.models import Message


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PARTICIPANTS = [
    "Priya", "Rahul", "Amit", "Sneha", 
    "Vikram", "Neha", "Rohan", "Anjali"
]

NUM_MESSAGES = 4200
MONTHS_SPAN = 6
START_DATE = datetime(2024, 10, 1, 9, 0)  # Oct 1, 2024

# Output paths
OUTPUT_DIR = ROOT / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MESSAGES_FILE = OUTPUT_DIR / "synthetic_messages.json"
QUERIES_FILE = OUTPUT_DIR / "queries.json"
GROUND_TRUTH_FILE = ROOT / "data" / "evaluation" / "ground_truth.json"
HARD_QUERIES_FILE = ROOT / "data" / "evaluation" / "hard_queries.json"


# ---------------------------------------------------------------------------
# Message Templates (Realistically Messy)
# ---------------------------------------------------------------------------

# Decision Thread 1: Manali Trip (Oct-Nov 2024)
MANALI_THREAD = [
    ("Priya", "guys kya plan hai is winter?"),
    ("Rahul", "kuch nahi yaar, bore ho raha hu"),
    ("Amit", "ghumne chalein kahin?"),
    ("Sneha", "haan yaar! kaha chalein?"),
    ("Priya", "Manali ka plan kaisa rahega?"),
    ("Vikram", "Manali accha hai, thanda milega"),
    ("Neha", "budget kitna hoga?"),
    ("Rohan", "around 40-50k per person"),
    ("Anjali", "itna mehnga?"),
    ("Priya", "haan yaar, flights + hotels"),
    ("Rahul", "chalo Manali fix hai?"),
    ("Amit", "haan final kar dete hain"),
    ("Sneha", "kab chalein? dates?"),
    ("Vikram", "Dec end ya Jan first week"),
    ("Neha", "Dec 28 se Jan 2 sahi rahega"),
    ("Priya", "ok toh Manali final hai!"),
    ("Rohan", "chalo Manali fix hai!!"),
    ("Anjali", "yay! excited"),
]

# Decision Thread 2: Budget Finalization (Nov-Dec 2024)
BUDGET_THREAD = [
    ("Amit", "budget thoda tight hai yaar"),
    ("Priya", "kya kar sakte hain kam karne ke liye?"),
    ("Rahul", "hotels saste dekh lete hain"),
    ("Sneha", "yaar 45k per person final hai"),
    ("Vikram", "thoda aur kam kar sakte hain?"),
    ("Neha", "nahi yaar, yehi sahi hai"),
    ("Rohan", "45k mein sab cover ho jayega"),
    ("Anjali", "ok budget finalise kar diya, 45k per person"),
    ("Priya", "haan 45k fix kiya hai"),
    ("Amit", "per person 45k decide hua"),
]

# Decision Thread 3: Hotel & Flight Booking (Dec 2024 - Jan 2025)
BOOKING_THREAD = [
    ("Sneha", "hotels dekh lete hain"),
    ("Vikram", "Hill View Homestay kaisa rahega?"),
    ("Neha", "Hill View Homestay book kar lete hain"),
    ("Rohan", "haan chalo, Hill View Homestay final"),
    ("Anjali", "Hill View Homestay confirm kar diya"),
    ("Priya", "flights check ki?"),
    ("Rahul", "haan, 12k aa rahi hai"),
    ("Amit", "flight book kar di"),
    ("Sneha", "flight book kar di, bas hotel pending tha, ab done"),
    ("Vikram", "flight tickets book ho gaye"),
    ("Neha", "flight confirm ho gayi"),
    ("Rohan", "tickets book ho gaye hain"),
]

# Random Filler Messages (Hinglish, Messy, Realistic)
FILLER_MESSAGES = [
    "haan", "nai", "ok", "done", "chalo", "theek hai", "accha", "wow",
    "kya baat hai", "badhiya", "perfect", "great", "awesome yaar",
    "kal baat karte hain", "baad mein batata hu", "wait check karta hu",
    "haan sahi kaha", "bilkul", "exactly", "yes yes", "no no",
    "kya plan hai?", "kuch nahi", "busy hu yaar", "meeting hai",
    "location bhej de", "phone pe baat karte hain", "message kar de",
    "traffic bahut hai", "late ho jaunga", "nikal gaya", "pahunch gaya",
    "bhook lagi hai", "khaana kha liya?", "chai pe chalein?",
    "movie dekhne chalein?", "weekend pe kya plan hai?",
    "bhai log suno", "koi suggestions?", "what say guys?", "thoughts?",
    "lol", "haha", "😂", "👍", "🎉", "🙏", "❤️",
    "yaar", "bro", "dude", "arre", "oye", "sun",
    "sahi hai", "mast hai", "gajab hai", "zabardast",
    "pata nahi", "pata hai", "pata chalega", "dekhenge",
    "ho jayega", "nhi hoga", "shayad", "pakka", "maybe",
    "thanks!", "thank you", "no problem", "anytime",
    "sorry yaar", "my bad", "oops", "mistake ho gayi",
    "confirm hai?", "pakka?", "sure?", "really?",
    "abhi busy hu", "baad mein", "later", "soon",
    "kahan ho?", "kab aaoge?", "ready ho?", "jaldi aao",
    "boring hai", "fun hai", "mazaa aa raha hai", "timepass",
]

# Typo variants (to make it realistic)
TYPO_VARIANTS = {
    "haan": ["han", "haa", "ha", "hnn"],
    "nai": ["na", "nahi", "nh", "nhi"],
    "ok": ["oke", "okee", "oky", "k"],
    "theek": ["thik", "tik", "thk"],
    "kya": ["kya", "k", "ky"],
    "hai": ["he", "hy", "h"],
    "yaar": ["yar", "yr", "yrr"],
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def apply_typos(text: str, probability: float = 0.15) -> str:
    """Randomly apply typos to make text realistic."""
    words = text.split()
    result = []
    for word in words:
        if random.random() < probability and word.lower() in TYPO_VARIANTS:
            word = random.choice(TYPO_VARIANTS[word.lower()])
        result.append(word)
    return " ".join(result)


def generate_timestamp(base: datetime, offset_hours: int) -> str:
    """Generate ISO timestamp."""
    ts = base + timedelta(hours=offset_hours)
    return ts.isoformat()


def create_message(msg_id: int, text: str, sender: str, timestamp: str) -> dict:
    """Create a message dict."""
    return {
        "msg_id": msg_id,
        "text": text,
        "sender": sender,
        "timestamp": timestamp,
        "thread_id": None,
    }


# ---------------------------------------------------------------------------
# Data Generation
# ---------------------------------------------------------------------------
def generate_corpus() -> list[dict]:
    """Generate the complete synthetic corpus."""
    messages = []
    msg_id = 1
    current_time = START_DATE
    
    print("📝 Generating synthetic chat corpus...")
    print(f"   Target: {NUM_MESSAGES} messages over {MONTHS_SPAN} months")
    
    # 1. Add decision threads (spread across timeline)
    print("   Adding 3 major decision threads...")
    
    # Manali thread (Oct-Nov 2024)
    for i, (sender, text) in enumerate(MANALI_THREAD):
        offset = i * 2 + random.randint(0, 5)  # Spread over ~40 hours
        ts = generate_timestamp(START_DATE, offset)
        text_with_typos = apply_typos(text)
        messages.append(create_message(msg_id, text_with_typos, sender, ts))
        msg_id += 1
    
    # Budget thread (Nov-Dec 2024)
    budget_start = START_DATE + timedelta(days=45)
    for i, (sender, text) in enumerate(BUDGET_THREAD):
        offset = i * 3 + random.randint(0, 8)
        ts = generate_timestamp(budget_start, offset)
        text_with_typos = apply_typos(text)
        messages.append(create_message(msg_id, text_with_typos, sender, ts))
        msg_id += 1
    
    # Booking thread (Dec 2024 - Jan 2025)
    booking_start = START_DATE + timedelta(days=90)
    for i, (sender, text) in enumerate(BOOKING_THREAD):
        offset = i * 4 + random.randint(0, 12)
        ts = generate_timestamp(booking_start, offset)
        text_with_typos = apply_typos(text)
        messages.append(create_message(msg_id, text_with_typos, sender, ts))
        msg_id += 1
    
    # 2. Add random filler messages (bulk of corpus)
    print(f"   Adding {NUM_MESSAGES - msg_id + 1} filler messages...")
    
    total_hours = MONTHS_SPAN * 30 * 24  # Total hours in 6 months
    hours_per_message = total_hours / NUM_MESSAGES
    
    while msg_id <= NUM_MESSAGES:
        # Random time within the 6-month span
        offset_hours = int((msg_id - 1) * hours_per_message) + random.randint(-12, 12)
        offset_hours = max(0, min(offset_hours, total_hours))
        
        ts = generate_timestamp(START_DATE, offset_hours)
        
        # Random sender and message
        sender = random.choice(PARTICIPANTS)
        text = random.choice(FILLER_MESSAGES)
        
        # Sometimes add multi-word messages
        if random.random() < 0.3:
            text = f"{text} {random.choice(FILLER_MESSAGES)}"
        
        # Apply typos
        text = apply_typos(text, probability=0.2)
        
        messages.append(create_message(msg_id, text, sender, ts))
        msg_id += 1
        
        if msg_id % 500 == 0:
            print(f"     Generated {msg_id}/{NUM_MESSAGES} messages...")
    
    # 3. Sort by timestamp and reassign IDs
    print("   Sorting messages by timestamp...")
    messages.sort(key=lambda x: x["timestamp"])
    for i, msg in enumerate(messages, 1):
        msg["msg_id"] = i
    
    # 4. Add some forwarded/media messages
    print("   Adding media/forwarded messages...")
    media_messages = [
        "[Image]",
        "[Video]",
        "[Document]",
        "[Forwarded]",
        "[Audio message]",
        "📍 Location shared",
    ]
    
    for _ in range(50):
        idx = random.randint(0, len(messages) - 1)
        msg = messages[idx]
        if random.random() < 0.5:
            msg["text"] = random.choice(media_messages)
    
    print(f"   ✅ Generated {len(messages)} messages")
    
    # Print statistics
    print(f"\n📊 Statistics:")
    print(f"   Total messages: {len(messages)}")
    print(f"   Participants: {len(PARTICIPANTS)}")
    print(f"   Date range: {messages[0]['timestamp'][:10]} to {messages[-1]['timestamp'][:10]}")
    print(f"   Decision threads: 3 (Manali, Budget, Booking)")
    
    return messages


def generate_queries_and_ground_truth(messages: list[dict]) -> tuple[list, list, list]:
    """Generate 40 test queries with ground truth mappings."""
    print("\n📝 Generating 40 test queries...")
    
    # Find key decision messages by content
    manali_msg = None
    budget_msg = None
    hotel_msg = None
    flight_msg = None
    
    for msg in messages:
        text_lower = msg["text"].lower()
        if "manali" in text_lower and ("fix" in text_lower or "final" in text_lower):
            manali_msg = msg
        if "45k" in text_lower and "per person" in text_lower:
            budget_msg = msg
        if "hill view" in text_lower:
            hotel_msg = msg
        if "flight book" in text_lower:
            flight_msg = msg
    
    # If not found, use fallback IDs from original data
    if not manali_msg:
        manali_msg = {"msg_id": 499, "text": "chalo Manali fix hai", "sender": "Priya"}
    if not budget_msg:
        budget_msg = {"msg_id": 1334, "text": "45k per person final", "sender": "Anjali"}
    if not hotel_msg:
        hotel_msg = {"msg_id": 2136, "text": "Hill View Homestay final", "sender": "Priya"}
    if not flight_msg:
        flight_msg = {"msg_id": 2170, "text": "flight book kar di", "sender": "Arjun"}
    
    # 8 HARD queries (zero word overlap)
    hard_queries = [
        {
            "query_id": 1,
            "query": "When did we decide on the trip destination?",
            "ground_truth_msg_ids": [manali_msg["msg_id"]],
            "is_hard": True,
            "category": "meaning",
            "notes": f"Zero overlap with '{manali_msg['text'][:30]}'",
        },
        {
            "query_id": 2,
            "query": "What was the final budget amount we agreed on?",
            "ground_truth_msg_ids": [budget_msg["msg_id"]],
            "is_hard": True,
            "category": "meaning",
            "notes": f"Zero overlap with '{budget_msg['text'][:30]}'",
        },
        {
            "query_id": 3,
            "query": "Which hotel or stay did we book?",
            "ground_truth_msg_ids": [hotel_msg["msg_id"]],
            "is_hard": True,
            "category": "meaning",
            "notes": "Zero overlap",
        },
        {
            "query_id": 4,
            "query": "Have the tickets already been purchased?",
            "ground_truth_msg_ids": [flight_msg["msg_id"]],
            "is_hard": True,
            "category": "meaning",
            "notes": f"Zero overlap with '{flight_msg['text'][:30]}'",
        },
        {
            "query_id": 5,
            "query": "Where are we going for the holiday?",
            "ground_truth_msg_ids": [manali_msg["msg_id"]],
            "is_hard": True,
            "category": "meaning",
        },
        {
            "query_id": 6,
            "query": "How much money per person was locked?",
            "ground_truth_msg_ids": [budget_msg["msg_id"]],
            "is_hard": True,
            "category": "meaning",
        },
        {
            "query_id": 7,
            "query": "What accommodation place was confirmed?",
            "ground_truth_msg_ids": [hotel_msg["msg_id"]],
            "is_hard": True,
            "category": "meaning",
        },
        {
            "query_id": 8,
            "query": "Did someone already reserve the flights?",
            "ground_truth_msg_ids": [flight_msg["msg_id"]],
            "is_hard": True,
            "category": "meaning",
        },
    ]
    
    # 32 regular queries (warm-up)
    regular_queries = [
        {"query_id": 9, "query": "What did Priya say about the budget?", "ground_truth_msg_ids": [budget_msg["msg_id"]], "is_hard": False, "category": "person"},
        {"query_id": 10, "query": "What did Rahul say about Manali?", "ground_truth_msg_ids": [manali_msg["msg_id"]], "is_hard": False, "category": "person"},
        {"query_id": 11, "query": "Amit ne budget ke baare me kya kaha?", "ground_truth_msg_ids": [budget_msg["msg_id"]], "is_hard": False, "category": "person"},
        {"query_id": 12, "query": "What did we discuss about the trip last month?", "ground_truth_msg_ids": [manali_msg["msg_id"]], "is_hard": False, "category": "time"},
        {"query_id": 13, "query": "Budget wali baat kab hui thi?", "ground_truth_msg_ids": [budget_msg["msg_id"]], "is_hard": False, "category": "time"},
        {"query_id": 14, "query": "Manali ka plan final hua kya?", "ground_truth_msg_ids": [manali_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 15, "query": "45k per person decide hua tha?", "ground_truth_msg_ids": [budget_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 16, "query": "hotel ka naam kya final hua?", "ground_truth_msg_ids": [hotel_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 17, "query": "flight book ho gayi kya?", "ground_truth_msg_ids": [flight_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 18, "query": "trip destination kya decide kiya?", "ground_truth_msg_ids": [manali_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 19, "query": "budget kitna fix hua?", "ground_truth_msg_ids": [budget_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 20, "query": "stay kahan book kiya?", "ground_truth_msg_ids": [hotel_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 21, "query": "tickets book hue kya?", "ground_truth_msg_ids": [flight_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 22, "query": "chalo Manali fix hai – kab bola?", "ground_truth_msg_ids": [manali_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 23, "query": "Budget finalise kar diya – kisne?", "ground_truth_msg_ids": [budget_msg["msg_id"]], "is_hard": False, "category": "person"},
        {"query_id": 24, "query": "Hill View Homestay final – confirm?", "ground_truth_msg_ids": [hotel_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 25, "query": "yaar budget thoda kam kar lete hain – kisi ne kaha?", "ground_truth_msg_ids": [budget_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 26, "query": "all inclusive roughly – budget me include?", "ground_truth_msg_ids": [budget_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 27, "query": "confirmation aagayi – hotel booking?", "ground_truth_msg_ids": [hotel_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 28, "query": "per person kitna finalised?", "ground_truth_msg_ids": [budget_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 29, "query": "destination decide karo pehle – baad me kya hua?", "ground_truth_msg_ids": [manali_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 30, "query": "travel + stay + food mila ke – amount?", "ground_truth_msg_ids": [budget_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 31, "query": "next month possible hai – trip ke liye?", "ground_truth_msg_ids": [manali_msg["msg_id"]], "is_hard": False, "category": "time"},
        {"query_id": 32, "query": "2.2k pe mil raha – konsa stay?", "ground_truth_msg_ids": [hotel_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 33, "query": "winter me Manali better – agree hua?", "ground_truth_msg_ids": [manali_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 34, "query": "bas hotel pending – ab status?", "ground_truth_msg_ids": [flight_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 35, "query": "Snow Valley Resort ke baare me kya baat hui?", "ground_truth_msg_ids": [hotel_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 36, "query": "Goa option discuss hua tha kya?", "ground_truth_msg_ids": [manali_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 37, "query": "booking.com pe check kiya – result?", "ground_truth_msg_ids": [hotel_msg["msg_id"]], "is_hard": False, "category": "meaning"},
        {"query_id": 38, "query": "snow dekhne ko milega – kisne suggest kiya?", "ground_truth_msg_ids": [manali_msg["msg_id"]], "is_hard": False, "category": "person"},
        {"query_id": 39, "query": "What did Sneha suggest for hotels?", "ground_truth_msg_ids": [hotel_msg["msg_id"]], "is_hard": False, "category": "person"},
        {"query_id": 40, "query": "What was decided about flights last week?", "ground_truth_msg_ids": [flight_msg["msg_id"]], "is_hard": False, "category": "time"},
    ]
    
    all_queries = hard_queries + regular_queries
    
    # Create ground truth format for evaluation harness
    ground_truth = [{"query_id": q["query_id"], "correct_msg_id": q["ground_truth_msg_ids"][0]} for q in all_queries]
    hard_query_ids = [q["query_id"] for q in hard_queries]
    
    print(f"   ✅ Generated {len(all_queries)} queries ({len(hard_queries)} hard)")
    
    return all_queries, ground_truth, hard_query_ids


# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------
def main():
    print("="*80)
    print("HINGLISH SEMANTIC CHAT SEARCH - CORPUS GENERATOR")
    print("="*80)
    
    # 1. Generate messages
    messages = generate_corpus()
    
    # 2. Generate queries
    queries, ground_truth, hard_ids = generate_queries_and_ground_truth(messages)
    
    # 3. Save messages to JSON
    print(f"\n💾 Saving to {MESSAGES_FILE}...")
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Saved {len(messages)} messages")
    
    # 4. Save queries
    print(f"\n💾 Saving queries to {QUERIES_FILE}...")
    with open(QUERIES_FILE, "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Saved {len(queries)} queries")
    
    # 5. Save ground truth
    print(f"\n💾 Saving ground truth to {GROUND_TRUTH_FILE}...")
    with open(GROUND_TRUTH_FILE, "w") as f:
        json.dump(ground_truth, f, indent=2)
    print(f"   ✅ Saved ground truth for {len(ground_truth)} queries")
    
    # 6. Save hard query IDs
    print(f"\n💾 Saving hard query IDs to {HARD_QUERIES_FILE}...")
    with open(HARD_QUERIES_FILE, "w") as f:
        json.dump(hard_ids, f, indent=2)
    print(f"   ✅ Saved {len(hard_ids)} hard query IDs")
    
    # 7. Load into SQLite
    print(f"\n💾 Loading into SQLite database...")
    store = MessageStore()
    
    # Clear existing data
    conn = store._get_conn()
    conn.execute("DELETE FROM messages")
    conn.commit()
    
    # Convert to Message objects
    message_objects = []
    for m in messages:
        message_objects.append(Message(
            msg_id=m["msg_id"],
            text=m["text"],
            sender=m["sender"],
            timestamp=datetime.fromisoformat(m["timestamp"]),
            thread_id=m.get("thread_id"),
        ))
    
    store.upsert_messages(message_objects)
    print(f"   ✅ Loaded {store.count()} messages into SQLite")
    
    # 8. Summary
    print("\n" + "="*80)
    print("✅ CORPUS GENERATION COMPLETE!")
    print("="*80)
    print(f"\n📁 Files created:")
    print(f"   • {MESSAGES_FILE}")
    print(f"   • {QUERIES_FILE}")
    print(f"   • {GROUND_TRUTH_FILE}")
    print(f"   • {HARD_QUERIES_FILE}")
    print(f"\n📊 Corpus statistics:")
    print(f"   • Total messages: {len(messages)}")
    print(f"   • Participants: {len(PARTICIPANTS)}")
    print(f"   • Time span: {MONTHS_SPAN} months")
    print(f"   • Decision threads: 3")
    print(f"   • Test queries: {len(queries)} (Hard: {len(hard_ids)})")
    print(f"\n🚀 Next steps:")
    print(f"   1. python scripts/build_index.py")
    print(f"   2. python scripts/run_evaluation.py --top-k 5")
    print("="*80)


if __name__ == "__main__":
    main()