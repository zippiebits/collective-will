# Collective Will — FAQ Page Content
> Both EN (`/en/faq`) and FA (`/fa/faq`) copy, plus homepage additions and implementation notes.

---

## English — `/en/faq`

### Safety & Privacy

**Can I be identified from my submission?**
Your submission is linked to a randomly generated ID — not your name, Telegram username, email, or location. We do not log IP addresses. The connection between your identity and your anonymous ID is never exposed.

**Is it safe to participate from inside Iran?**
We have designed the platform to minimize what we know about you. That said, we won't tell you it is risk-free — no digital tool is. We recommend using a VPN when accessing the platform or the Telegram bot. Assess your own situation carefully before participating.

**Why do you need my voice?**
To ensure one person, one vote. Voice verification exists only to prevent bots and duplicate accounts from distorting the results. It is not used to identify you, and no human ever listens to your recordings.

**What exactly happens to my voice recordings?**
You send 3 short voice messages via Telegram. The system converts them into a mathematical fingerprint — a set of numbers that represents acoustic patterns — and then permanently discards the recordings. The fingerprint is encrypted and stored linked only to your anonymous ID. It cannot be reversed to recover your voice, your Telegram account, or your identity.

**Can my voice fingerprint be matched against other databases?**
No. The fingerprint we generate is produced by our own system and is not compatible with or exportable to external voice recognition systems.

**What data do you store about me?**
- An anonymous UUID (random identifier)
- Your encrypted voice fingerprint (irreversible, not linked to your name; encrypted at rest)
- Your submitted concern text (publicly visible, not linked to your name)
- Your votes (counted anonymously)

We do not store your Telegram username, phone number, IP address, or email in connection with your submissions or votes.

**What if I want my data deleted?**
Contact us via the Telegram bot. We will delete your anonymous record. Because your data is not linked to your name, we will ask you to verify ownership through the same voice enrollment.

---

### How It Works

**How does AI organize concerns without editorializing?**
When you submit a concern, an AI model reads the meaning of your text and groups it with other concerns that express similar ideas — regardless of how they're phrased or what language they use. No human decides which concerns are grouped together or which are made more visible. You can inspect every clustering decision in the Audit Trail.

**Who counts as "the community" that votes?**
Anyone who completes voice verification. We do not require proof of Iranian citizenship or residency. The platform is open equally to Iranians inside Iran and in the diaspora.

**Can I submit in Farsi, English, or another language?**
Yes. Submit in whatever language feels natural. The AI processes meaning across languages.

**What is the Audit Trail?**
A tamper-evident log of every action in the system — every submission, every clustering decision, every vote count. Anyone can inspect it to verify that results have not been altered.

**Can concerns be edited or removed after submission?**
Concerns are not edited by anyone after submission. You can request deletion of your own submission by contacting us through the Telegram bot.

---

### About the Project

**Who built this?**
An anonymous collective of independent developers and civil society advocates. We have no affiliation with any government, political party, media organization, or foreign state actor.

**Why anonymous?**
Some members of our collective are in situations where public association with this project would put them at risk. Anonymity protects them — and it models the same principle we apply to users.

**Can I trust an anonymous team?**
You don't have to. The full source code is open at [github.com/civil-whisper/collective-will](https://github.com/civil-whisper/collective-will). Every part of the system — how submissions are processed, how voices are handled, how votes are counted — can be independently verified by any developer.

**Is this platform affiliated with any political movement?**
No. We have no position on which political outcomes Iranians should want. Our only goal is to give Iranians a trustworthy way to express and aggregate their own views.

**What happens to the final results?**
Results are compiled into a public report and published openly. They are available to journalists, researchers, and the international community. We do not filter, editorialize, or selectively publish results.

**How is this funded?**
<!-- TODO: Fill in before launch. Even "self-funded by the collective, no external funding currently" is better than silence. -->

---

---

## فارسی — `/fa/faq`

### ایمنی و حریم خصوصی

**آیا می‌توان از طریق ارسال من هویتم را شناسایی کرد؟**
ارسال شما به یک شناسه تصادفی مرتبط می‌شود — نه به نام، نام کاربری تلگرام، ایمیل، یا موقعیت مکانی شما. آدرس IP ثبت نمی‌شود. هیچ‌گاه ارتباطی بین هویت شما و شناسه ناشناس‌تان فاش نمی‌شود.

**آیا شرکت از داخل ایران امن است؟**
پلتفرم را طراحی کرده‌ایم تا حداقل اطلاعات ممکن را درباره شما بدانیم. با این حال، نمی‌گوییم که بدون ریسک است — هیچ ابزار دیجیتالی نیست. استفاده از VPN را هنگام دسترسی به پلتفرم یا ربات تلگرام توصیه می‌کنیم. پیش از شرکت، وضعیت خودتان را با دقت ارزیابی کنید.

**چرا به صدای من نیاز دارید؟**
برای اطمینان از یک نفر، یک رأی. تأیید صدا فقط برای جلوگیری از ربات‌ها و حساب‌های تکراری وجود دارد. برای شناسایی هویت شما استفاده نمی‌شود و هیچ انسانی ضبط‌های شما را نمی‌شنود.

**دقیقاً چه اتفاقی برای ضبط‌های صوتی من می‌افتد؟**
سه پیام صوتی کوتاه از طریق تلگرام ارسال می‌کنید. سیستم آن‌ها را به یک اثر انگشت ریاضی تبدیل می‌کند — مجموعه‌ای از اعداد که الگوهای صوتی را نشان می‌دهد — و سپس ضبط‌ها را برای همیشه حذف می‌کند. اثر انگشت رمزگذاری شده و فقط به شناسه ناشناس شما مرتبط ذخیره می‌شود. این اثر انگشت قابل بازگشت نیست و نمی‌توان از آن صدا، حساب تلگرام، یا هویت شما را بازسازی کرد.

**آیا اثر انگشت صوتی‌ام می‌تواند با پایگاه‌های داده دیگر تطبیق داده شود؟**
خیر. اثر انگشتی که ما تولید می‌کنیم با سیستم‌های تشخیص صوت خارجی سازگار نیست و قابل صدور به آن‌ها نیست.

**چه داده‌ای درباره من ذخیره می‌شود؟**
- یک شناسه تصادفی ناشناس (UUID)
- اثر انگشت صوتی رمزگذاری‌شده (غیرقابل بازگشت، بدون ارتباط با نام شما)
- متن دغدغه ارسالی شما (عمومی، بدون ارتباط با نام شما)
- رأی‌های شما (شمارش ناشناس)

نام کاربری تلگرام، شماره تلفن، آدرس IP، یا ایمیل شما را در ارتباط با ارسال‌ها یا رأی‌ها ذخیره نمی‌کنیم.

**اگر بخواهم داده‌هایم حذف شود چه کار کنم؟**
از طریق ربات تلگرام با ما تماس بگیرید. پرونده ناشناس شما را حذف می‌کنیم. چون داده‌هایتان به نامتان مرتبط نیست، از شما می‌خواهیم مالکیت را از طریق همان ثبت‌نام صوتی تأیید کنید.

---

### نحوه کارکرد

**هوش مصنوعی چگونه بدون جانبداری سازمان‌دهی می‌کند؟**
هنگامی که دغدغه‌ای ارسال می‌کنید، یک مدل هوش مصنوعی معنای متن شما را می‌خواند و آن را با دغدغه‌های مشابه از سایر کاربران گروه‌بندی می‌کند — صرف‌نظر از نحوه بیان یا زبان آن‌ها. هیچ انسانی تصمیم نمی‌گیرد کدام دغدغه‌ها گروه‌بندی شوند. می‌توانید هر تصمیم خوشه‌بندی را در مسیر بررسی مشاهده کنید.

**«جامعه» که رأی می‌دهد چه کسانی هستند؟**
هر کسی که تأیید صدا را کامل کند. نیازی به اثبات تابعیت یا اقامت ایرانی نداریم. پلتفرم به طور مساوی برای ایرانیان داخل و خارج از کشور باز است.

**می‌توانم به فارسی، انگلیسی، یا زبان دیگری ارسال کنم؟**
بله. به هر زبانی که راحت هستید ارسال کنید. هوش مصنوعی معنا را در چندین زبان پردازش می‌کند.

**مسیر بررسی چیست؟**
یک گزارش ضد دستکاری از هر اقدام در سیستم — هر ارسال، هر تصمیم خوشه‌بندی، هر شمارش رأی. هر کسی می‌تواند آن را بررسی کند تا تأیید کند نتایج تغییر نکرده‌اند.

**آیا دغدغه‌ها بعد از ارسال می‌توانند ویرایش یا حذف شوند؟**
دغدغه‌ها توسط هیچ‌کس بعد از ارسال ویرایش نمی‌شوند. می‌توانید از طریق ربات تلگرام درخواست حذف ارسال خودتان را بدهید.

---

### درباره پروژه

**چه کسی این پروژه را ساخته؟**
یک گروه ناشناس از توسعه‌دهندگان مستقل و فعالان جامعه مدنی. هیچ وابستگی به هیچ دولت، حزب سیاسی، سازمان رسانه‌ای، یا بازیگر دولتی خارجی نداریم.

**چرا ناشناس؟**
برخی از اعضای گروه ما در شرایطی هستند که ارتباط عمومی با این پروژه آن‌ها را در معرض خطر قرار می‌دهد. ناشناس بودن از آن‌ها محافظت می‌کند — و همان اصلی را که برای کاربران اعمال می‌کنیم الگوسازی می‌کند.

**آیا می‌توانم به یک تیم ناشناس اعتماد کنم؟**
لازم نیست. کد منبع کامل در [github.com/civil-whisper/collective-will](https://github.com/civil-whisper/collective-will) باز است. هر بخش از سیستم — نحوه پردازش ارسال‌ها، نحوه مدیریت صداها، نحوه شمارش رأی‌ها — توسط هر توسعه‌دهنده‌ای قابل تأیید مستقل است.

**آیا این پلتفرم به جنبش سیاسی خاصی وابسته است؟**
خیر. ما هیچ موضعی درباره اینکه ایرانیان چه نتایج سیاسی‌ای باید بخواهند نداریم. هدف ما فقط این است که به ایرانیان روشی قابل اعتماد برای بیان و تجمیع دیدگاه‌های خودشان بدهیم.

**نتایج نهایی چه می‌شوند؟**
نتایج در یک گزارش عمومی جمع‌آوری و به صورت آزاد منتشر می‌شوند. در دسترس خبرنگاران، پژوهشگران، و جامعه بین‌المللی هستند. نتایج را فیلتر، ویرایش، یا به صورت انتخابی منتشر نمی‌کنیم.

**این پروژه چگونه تأمین مالی می‌شود؟**
<!-- TODO: پیش از راه‌اندازی پر شود. حتی "خودتأمین‌مالی توسط گروه، بدون تأمین مالی خارجی فعلی" بهتر از سکوت است. -->

---

---

## Homepage Additions

### Mission statement (below headline, above CTA)

**EN:**
> Collective Will is an independent, open-source platform built by an anonymous collective of developers and civil society advocates. Our goal is simple: give every Iranian — inside the country and in the diaspora — an equal, censorship-resistant voice to document what they want and need. No editors decide what matters. No government can manipulate the results. AI organizes, the community votes, and the findings are published openly for the world to see.

**FA:**
> اراده جمعی یک پلتفرم مستقل و متن‌باز است که توسط یک گروه ناشناس از توسعه‌دهندگان و فعالان جامعه مدنی ساخته شده است. هدف ما ساده است: به هر ایرانی — چه داخل کشور، چه در خارج — یک صدای برابر و مقاوم در برابر سانسور بدهیم تا بگوید چه می‌خواهد. هیچ سردبیری تصمیم نمی‌گیرد چه چیزی مهم است. هیچ دولتی نمی‌تواند نتایج را دستکاری کند. هوش مصنوعی سازمان‌دهی می‌کند، جامعه رأی می‌دهد، و نتایج برای همه جهانیان منتشر می‌شود.

---

### Safety one-liner (below mission statement, above CTA)

**EN:** Your submissions are anonymous. Your voice cannot be traced back to you.

**FA:** ارسال‌های شما ناشناس هستند. صدای شما قابل ردیابی به شما نیست.

---

### FAQ link (below "How it works" section)

**EN:** Have questions about safety, privacy, or how your voice data is handled? [Read the FAQ →](/en/faq)

**FA:** سؤالی درباره ایمنی، حریم خصوصی، یا نحوه استفاده از داده صوتی دارید؟ [سؤالات متداول ←](/fa/faq)

---

## Implementation Notes

### Navigation
- Add "FAQ" / "سؤالات متداول" to the main nav between Home and My Activity
- Add to footer
- Must be accessible from the mobile/hamburger menu

### Suggested homepage section order
1. Headline + tagline
2. Mission statement
3. Safety one-liner
4. CTA (Join Now)
5. How it works
6. Voice verification explainer (3 voice samples → fingerprint → discarded → anonymous ID)
7. FAQ link
8. Audit trail
9. "Built by an anonymous open-source collective" + GitHub link
10. Footer

### Before launch checklist
- [ ] Fill in the funding answer in both EN and FA FAQ
- [x] Verify the voice data claims in the FAQ match actual code behavior
- [ ] Style the EN/FA language toggle as a clearly clickable button
- [ ] Confirm Telegram bot link is correct in both locales
