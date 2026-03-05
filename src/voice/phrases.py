"""Phrase pool for voice enrollment and verification.

100 phrases per language (fa/en), 5-8 words each, phonetically diverse.
"""

from __future__ import annotations

import secrets

PHRASES_EN: list[str] = [
    "The morning sun warms the river bank",
    "Purple flowers bloom beside the garden wall",
    "Children play together in the open field",
    "A gentle breeze moves through the trees",
    "Fresh bread baking fills the whole kitchen",
    "The mountain trail leads to a waterfall",
    "Bright stars appear across the dark sky",
    "Old books carry wisdom from past ages",
    "The silver moon rises above the hills",
    "Colorful birds sing from the tall branches",
    "Warm coffee steams in the ceramic cup",
    "The wooden bridge crosses a narrow stream",
    "Deep snow covers the village rooftops quietly",
    "A small boat drifts along the coast",
    "Thunder echoes through the wide green valley",
    "The baker shapes the dough with care",
    "Quiet waves wash over the sandy beach",
    "An old clock chimes every single hour",
    "Wild horses run across the open prairie",
    "The painter mixes colors on the palette",
    "Tall grass sways gently in the wind",
    "A red fox crosses the frozen lake",
    "The market square buzzes with busy shoppers",
    "Soft rain falls on the window pane",
    "The farmer harvests wheat before the storm",
    "Golden leaves drift slowly to the ground",
    "A lantern glows warmly through the darkness",
    "The sculptor carves figures from smooth marble",
    "Clear water flows down from the spring",
    "Musicians gather to play in the park",
    "The lighthouse guides ships through the fog",
    "Ripe apples hang from every single branch",
    "A quiet path winds through the forest",
    "The weaver creates patterns with bright thread",
    "Morning frost sparkles on the garden fence",
    "Distant mountains turn pink at the sunset",
    "The potter shapes clay on the wheel",
    "Autumn leaves crunch beneath our walking feet",
    "A curious owl watches from the oak",
    "The fisherman casts his net at dawn",
    "Sweet honey drips from the wooden spoon",
    "Ancient walls surround the peaceful old town",
    "The dancer moves gracefully across the stage",
    "Blue butterflies hover near the rose bush",
    "A shepherd leads his flock down the hill",
    "The blacksmith hammers iron into useful shapes",
    "Crisp morning air fills the entire valley",
    "Fireflies glow softly in the summer night",
    "The teacher writes equations on the board",
    "Smooth pebbles line the bottom of the creek",
    "A train whistle echoes through the canyon",
    "The gardener plants seeds in neat rows",
    "Warm sunlight filters through the curtain lace",
    "Migrating geese fly south for the winter",
    "The carpenter measures wood before each cut",
    "Dewdrops cling to every blade of grass",
    "A violin melody floats through the hallway",
    "The sailor navigates using the north star",
    "Thick fog rolls in from the harbor",
    "Sparrows gather crumbs near the park bench",
    "The clockmaker repairs watches with tiny tools",
    "Lavender fields stretch far beyond the farmhouse",
    "A stone tower stands on the hilltop",
    "The astronomer studies patterns among the stars",
    "Maple syrup pours slowly over warm pancakes",
    "An eagle soars above the rocky cliffs",
    "The librarian arranges books on the shelf",
    "Gentle snowflakes land softly on the ground",
    "A candle flame flickers in the window",
    "The pilot checks instruments before each flight",
    "Pine trees stand tall against the winter",
    "A winding road leads to the village",
    "The jeweler polishes each gem with precision",
    "Calm waters reflect the clouds above them",
    "Children build sandcastles near the rolling waves",
    "The mechanic tightens bolts under the hood",
    "Fragrant herbs grow along the kitchen window",
    "A wooden fence borders the country lane",
    "The chemist measures liquids in glass tubes",
    "Pumpkins ripen in the autumn harvest field",
    "A hawk circles slowly overhead in silence",
    "The musician tunes the guitar before playing",
    "Icicles hang from the roof in winter",
    "A cobblestone street leads to the square",
    "The beekeeper collects honey from the hives",
    "Wildflowers grow along the dusty hiking trail",
    "A seagull glides above the crashing waves",
    "The architect draws plans for new buildings",
    "Freshly cut grass scents the afternoon breeze",
    "A rainbow appears after the afternoon rain",
    "The watchmaker works with delicate small springs",
    "Cattails grow at the edge of ponds",
    "A gentle stream runs through the meadow",
    "The storyteller captivates everyone around the fire",
    "Heavy rain drums against the tin roof",
    "A wooden door opens to the courtyard",
    "The tailor measures fabric for the dress",
    "Sunflowers turn their faces toward the light",
    "A narrow path descends toward the shore",
    "The glassblower shapes vessels with steady breath",
]

PHRASES_FA: list[str] = [
    "آفتاب صبحگاهی ساحل رودخانه را گرم می‌کند",
    "گل‌های بنفش کنار دیوار باغ شکوفه می‌دهند",
    "بچه‌ها با هم در دشت باز بازی می‌کنند",
    "نسیم ملایمی از میان درختان می‌گذرد",
    "بوی نان تازه تمام آشپزخانه را پر کرده",
    "مسیر کوهستانی به یک آبشار زیبا می‌رسد",
    "ستاره‌های درخشان در آسمان تاریک پدیدار می‌شوند",
    "کتاب‌های قدیمی حکمت گذشتگان را حمل می‌کنند",
    "ماه نقره‌ای بالای تپه‌ها طلوع می‌کند",
    "پرندگان رنگارنگ از شاخه‌های بلند آواز می‌خوانند",
    "قهوه گرم در فنجان سرامیکی بخار می‌کند",
    "پل چوبی از روی نهر باریکی عبور می‌کند",
    "برف سنگین پشت‌بام‌های روستا را پوشانده است",
    "قایق کوچکی در امتداد ساحل حرکت می‌کند",
    "رعد و برق در دره سبز وسیع می‌پیچد",
    "نانوا با دقت خمیر را شکل می‌دهد",
    "موج‌های آرام روی ساحل شنی می‌خزند",
    "ساعت قدیمی هر ساعت زنگ می‌زند",
    "اسب‌های وحشی در دشت باز می‌تازند",
    "نقاش رنگ‌ها را روی پالت مخلوط می‌کند",
    "علف‌های بلند آرام در باد تاب می‌خورند",
    "روباه قرمزی از روی دریاچه یخ‌زده عبور می‌کند",
    "میدان بازار پر از خریداران پرمشغله است",
    "باران نرم روی شیشه پنجره می‌بارد",
    "کشاورز پیش از طوفان گندم را برداشت می‌کند",
    "برگ‌های طلایی آهسته روی زمین می‌افتند",
    "فانوسی در تاریکی با گرما می‌درخشد",
    "مجسمه‌ساز از سنگ مرمر صاف شکل می‌تراشد",
    "آب زلال از چشمه سرازیر می‌شود",
    "نوازندگان برای اجرا در پارک جمع می‌شوند",
    "فانوس دریایی کشتی‌ها را از مه عبور می‌دهد",
    "سیب‌های رسیده از هر شاخه‌ای آویزان هستند",
    "مسیر آرامی از میان جنگل می‌گذرد",
    "بافنده با نخ‌های رنگی نقش می‌آفریند",
    "یخبندان صبحگاهی روی حصار باغ می‌درخشد",
    "کوه‌های دوردست در غروب صورتی می‌شوند",
    "کوزه‌گر روی چرخ ظرف خاکی می‌سازد",
    "برگ‌های پاییزی زیر قدم‌ها خش‌خش می‌کنند",
    "جغد کنجکاوی از روی درخت بلوط نگاه می‌کند",
    "ماهیگیر سپیده‌دم تورش را پرتاب می‌کند",
    "عسل شیرین از قاشق چوبی می‌چکد",
    "دیوارهای باستانی شهر آرام قدیمی را محصور کرده‌اند",
    "رقصنده با ظرافت روی صحنه حرکت می‌کند",
    "پروانه‌های آبی نزدیک بوته گل رز پرواز می‌کنند",
    "چوپان گله‌اش را از تپه پایین می‌آورد",
    "آهنگر آهن را به شکل‌های مفید می‌کوبد",
    "هوای خنک صبحگاهی تمام دره را پر می‌کند",
    "کرم‌های شب‌تاب در شب تابستان می‌درخشند",
    "معلم معادلات را روی تخته می‌نویسد",
    "سنگریزه‌های صاف کف نهر را پوشانده‌اند",
    "سوت قطار در دره‌ها طنین‌انداز می‌شود",
    "باغبان بذرها را در ردیف‌های منظم می‌کارد",
    "نور آفتاب گرم از پرده توری عبور می‌کند",
    "غازهای مهاجر برای زمستان به جنوب پرواز می‌کنند",
    "نجار قبل از هر برش چوب را اندازه می‌گیرد",
    "قطرات شبنم روی هر برگ سبزی می‌نشینند",
    "ملودی ویولن در راهرو خانه شناور می‌شود",
    "ملوان با کمک ستاره قطبی مسیریابی می‌کند",
    "مه غلیظ از سمت بندرگاه وارد می‌شود",
    "گنجشک‌ها نزدیک نیمکت پارک دانه جمع می‌کنند",
    "ساعت‌ساز با ابزار ریز ساعت‌ها را تعمیر می‌کند",
    "مزارع اسطوخودوس تا دوردست‌ها کشیده شده‌اند",
    "برج سنگی روی نوک تپه ایستاده است",
    "ستاره‌شناس الگوهای میان ستارگان را مطالعه می‌کند",
    "شیره افرا آهسته روی پنکیک گرم ریخته می‌شود",
    "عقابی بالای صخره‌های سنگی اوج می‌گیرد",
    "کتابدار کتاب‌ها را در قفسه مرتب می‌کند",
    "دانه‌های برف نرم آرام روی زمین می‌نشینند",
    "شعله شمع در پشت پنجره می‌لرزد",
    "خلبان قبل از هر پرواز ابزارها را بررسی می‌کند",
    "درختان کاج در برابر زمستان سرپا ایستاده‌اند",
    "جاده پرپیچ‌وخم به سوی روستا می‌رود",
    "جواهرساز هر سنگ قیمتی را با دقت صیقل می‌دهد",
    "آب‌های آرام ابرهای بالای سر را منعکس می‌کنند",
    "بچه‌ها نزدیک امواج قلعه شنی می‌سازند",
    "مکانیک زیر کاپوت پیچ‌ها را سفت می‌کند",
    "گیاهان معطر در کنار پنجره آشپزخانه رشد می‌کنند",
    "حصار چوبی دور کوچه روستایی کشیده شده است",
    "شیمیدان مایعات را در لوله‌های شیشه‌ای اندازه می‌گیرد",
    "کدوها در مزرعه برداشت پاییزی رسیده می‌شوند",
    "شاهینی آرام و بی‌صدا در آسمان دور می‌زند",
    "نوازنده قبل از اجرا گیتار را کوک می‌کند",
    "قندیل‌های یخ در زمستان از سقف آویزان می‌شوند",
    "کوچه سنگفرش به سمت میدان شهر می‌رود",
    "زنبوردار عسل را از کندوها جمع‌آوری می‌کند",
    "گل‌های وحشی در امتداد مسیر پیاده‌روی رشد می‌کنند",
    "مرغ دریایی بالای امواج خروشان سر می‌خورد",
    "معمار نقشه‌های ساختمان‌های جدید را ترسیم می‌کند",
    "بوی چمن تازه بریده در نسیم بعدازظهر می‌پیچد",
    "رنگین‌کمان بعد از باران بعدازظهر ظاهر می‌شود",
    "ساعت‌ساز با فنرهای ظریف و کوچک کار می‌کند",
    "لویی‌ها در لبه برکه‌ها رشد می‌کنند",
    "نهر ملایمی از میان چمنزار جاری می‌شود",
    "قصه‌گو همه را دور آتش مجذوب می‌کند",
    "باران شدید روی سقف حلبی می‌کوبد",
    "در چوبی به سوی حیاط باز می‌شود",
    "خیاط پارچه را برای دوخت لباس اندازه می‌گیرد",
    "آفتابگردان‌ها صورت خود را به سمت نور برمی‌گردانند",
    "مسیر باریکی به سمت ساحل سرازیر می‌شود",
    "شیشه‌گر با نفس ثابت ظروف شکل می‌دهد",
]


def select_phrases(
    locale: str,
    count: int,
    exclude_ids: list[int] | None = None,
) -> list[int]:
    """Select `count` random phrase IDs for the given locale.

    Args:
        locale: "fa" or "en".
        count: Number of phrases to select.
        exclude_ids: Phrase IDs to exclude (already used/failed).

    Returns:
        List of phrase indices (0-based) into the phrase pool.
    """
    pool = PHRASES_FA if locale == "fa" else PHRASES_EN
    available = list(range(len(pool)))
    if exclude_ids:
        available = [i for i in available if i not in set(exclude_ids)]

    if len(available) < count:
        raise ValueError(f"Not enough phrases: need {count}, have {len(available)}")

    selected: list[int] = []
    remaining = list(available)
    for _ in range(count):
        idx = secrets.randbelow(len(remaining))
        selected.append(remaining.pop(idx))
    return selected


def get_phrase(locale: str, phrase_id: int) -> str:
    """Get phrase text by locale and ID."""
    pool = PHRASES_FA if locale == "fa" else PHRASES_EN
    if phrase_id < 0 or phrase_id >= len(pool):
        raise ValueError(f"Invalid phrase_id {phrase_id} for locale {locale}")
    return pool[phrase_id]
