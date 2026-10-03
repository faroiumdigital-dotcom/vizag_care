"""Emergency check that runs BEFORE the model. Pure Python, no dependencies.

Uses phrases (not single words) so 'accident insurance' or 'bleeding gums'
do not trigger it. Covers English, Telugu and Hindi (native script and
common English-letter spellings).
"""
import re

EMERGENCY_NUMBER = "0891-400-1108"
AMBULANCE_NUMBER = "0891-400-1102"

EN = [
    r"chest (pain|pressure|tightness)", r"heart attack", r"can'?t breathe", r"cannot breathe",
    r"difficulty (in )?breathing", r"trouble breathing", r"short(ness)? of breath",
    r"\bstroke\b", r"face drooping", r"slurred speech", r"sudden weakness",
    r"unconscious", r"not responding", r"passed out", r"fainted", r"seizure", r"fits\b",
    r"(severe|heavy|a lot of|too much) bleeding", r"won'?t stop bleeding", r"bleeding (heavily|badly|a lot)",
    r"(had|met with|got in|got into|was in|there was|there is) an? accident", r"accident (just )?happened",
    r"poison", r"snake ?bite", r"bitten by (a )?snake", r"severe burn", r"burnt badly", r"overdose",
    r"suicid", r"want to (die|kill myself)",
]
# Telugu (native script + common transliterations)
TE = [
    r"ఛాతీ ?నొప్పి", r"గుండెపోటు", r"శ్వాస ?(ఆడ|తీసుకోవడం కష్టం)", r"ఊపిరి ?(ఆడ|ఆగ)", r"స్పృహ ?(తప్ప|లేదు|కోల్పో)",
    r"ప్రమాదం ?జరిగింది", r"యాక్సిడెంట్", r"విపరీతమైన రక్తస్రావం", r"రక్తం ఆగ", r"పాము ?కాటు", r"విషం", r"పక్షవాతం",
    r"fits vachay", r"gundepotu", r"chaati noppi", r"oopiri ?(aadatam|aadatledu|aadadu)", r"spruha ?(tappindi|ledu)",
    r"accident ayyindi", r"paamu ?kaatu",
]
# Hindi (native script + common transliterations)
HI = [
    r"सीने (में )?दर्द", r"दिल का दौरा", r"हार्ट अटैक", r"सांस (लेने )?में (तकलीफ|दिक्कत)", r"सांस नहीं (आ|ले)",
    r"बेहोश", r"दौरा पड़", r"एक्सीडेंट", r"दुर्घटना", r"बहुत (ज्यादा )?खून", r"खून (नहीं )?रुक", r"सांप ने काटा",
    r"जहर", r"लकवा", r"seene mein dard", r"saans nahi", r"behosh", r"khoon bah", r"saanp ne kata",
]

_PATTERN = re.compile("|".join(EN + TE + HI), re.IGNORECASE)

MESSAGES = {
    "en": (
        f"This may be an emergency. Please call {EMERGENCY_NUMBER} now or go to the Emergency "
        f"entrance (Ground Floor, Main Entrance) right away. For an ambulance call {AMBULANCE_NUMBER}. "
        "Do not wait for an appointment."
    ),
    "te": (
        f"ఇది అత్యవసర పరిస్థితి కావచ్చు. వెంటనే {EMERGENCY_NUMBER} కు కాల్ చేయండి లేదా ఎమర్జెన్సీ విభాగానికి "
        f"(గ్రౌండ్ ఫ్లోర్, మెయిన్ ఎంట్రన్స్) రండి. అంబులెన్స్ కోసం {AMBULANCE_NUMBER} కు కాల్ చేయండి. "
        "అపాయింట్‌మెంట్ కోసం వేచి ఉండకండి."
    ),
    "hi": (
        f"यह आपातकाल हो सकता है। कृपया तुरंत {EMERGENCY_NUMBER} पर कॉल करें या इमरजेंसी विभाग "
        f"(ग्राउंड फ्लोर, मेन एंट्रेंस) पहुंचें। एम्बुलेंस के लिए {AMBULANCE_NUMBER} पर कॉल करें। "
        "अपॉइंटमेंट का इंतज़ार न करें।"
    ),
}


def detect_language(text: str) -> str:
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "te"
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    return "en"


def is_emergency(text: str) -> bool:
    return bool(_PATTERN.search(text))


def emergency_reply(text: str) -> str:
    return MESSAGES[detect_language(text)]
