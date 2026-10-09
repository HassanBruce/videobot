# videobot — topic do, video khud bane aur upload ho

Bot khud ye sab karta hai:
1. **Topic chunta hai.** Queue khali ho to AI tumhari playlist ke hisaab se naye topics sochta hai.
2. **Script likhta hai** (Gemini): slides (English headings/bullets/code) aur narration (Urdu).
3. **Voice lagata hai:** Microsoft Edge ki neural Urdu voice (`ur-PK-AsadNeural`), free.
4. **Video jodta hai:** saaf slides + voice + thumbnail (ffmpeg).
5. **YouTube pe upload** karta hai (private) aur Telegram pe link bhejta hai.
6. Tum dekh lo, phir **YouTube Studio mein Public** karo, aur `approve` se **Facebook Page** pe bhi chala jata hai.

Schedule: Mon/Wed/Fri shaam 6 baje (badal sakte ho). Sab free hai.

## Do zaroori sach baatein
- **YouTube API ki videos private rehti hain** jab tak Google tumhare API project ka free audit na kar de (2020 ke baad bane projects ke liye rule). Is liye bot private upload karta hai aur tum 1 click se Public karte ho. Baad mein chahe to audit form bhar dena ("YouTube API Services Audit and Quota Extension Form").
- **YouTube monetization:** 2025 se "inauthentic content" policy hai. Bina insani input wale, mass-produced AI slideshow channels monetization se nikale ja rahe hain. Isse bachne ke liye:
  - Hafte mein 3 video, roz 10 nahi
  - Har video **publish se pehle dekho**, galti theek karo, apni baat add karo
  - Kabhi kabhi apni screen recording ya apni awaz wali video bhi dalo
  - Bot upload pe "synthetic media" ka flag khud lagata hai (imaandari, aur YouTube yahi chahta hai)

## Setup

### 1. Gemini key
Wahi key jo baqi bots mein hai → `.env` mein `AI_API_KEY`.

### 2. YouTube (15 minute, ek dafa)
1. **console.cloud.google.com** → naya project (jaise `videobot`)
2. **APIs & Services → Library** → "YouTube Data API v3" → **Enable**
3. **OAuth consent screen** → External → app ka naam, apni email → Save. **Test users** mein apna Gmail add karo (jo YouTube channel ka hai)
4. **Credentials → Create credentials → OAuth client ID → Desktop app** → Client ID aur Client Secret copy karo
5. Apne **laptop** pe (VPS pe nahi, browser chahiye):
   ```
   python scripts/youtube_auth.py CLIENT_ID CLIENT_SECRET
   ```
   Browser mein login → "Allow" → terminal mein `YT_REFRESH_TOKEN` aa jayega
6. Teeno values VPS ki `.env` mein daalo

> Consent screen "Testing" mode mein ho to Google refresh token 7 din baad expire kar deta hai. Bot ko lagatar chalana ho to OAuth consent screen pe **"Publish app"** karo (personal use ke liye verification ki zaroorat nahi padti, bas "unverified app" ki warning aati hai jo tum khud allow karte ho).

### 3. Facebook Page (optional)
1. developers.facebook.com → wahi app (jo WhatsApp ke liye banayi) ya nayi → **Graph API Explorer**
2. Permissions: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts` → **Generate Access Token**
3. Explorer mein `me/accounts` chalao → apne Page ka `id` aur `access_token` milega → `FB_PAGE_ID`, `FB_PAGE_TOKEN`
4. Token lamba chalane ke liye: Access Token Debugger → "Extend Access Token", phir dobara `me/accounts` se Page token lo (ye expire nahi hota)

> Meta kehta hai ke in permissions ke liye App Review chahiye. Apne hi page pe, app ke admin ke taur pe, development mode mein aksar chal jata hai. Agar error aaye to bot video aur caption folder mein rakh deta hai, aur tum Meta Business Suite se 1 minute mein khud daal sakte ho.

### 4. Chalana (VPS)
```bash
cd videobot
cp .env.example .env && nano .env
docker compose build
docker compose run --rm video python -m videobot ideas 10      # AI 10 topics queue mein daale
docker compose run --rm video python -m videobot list          # dekho kya topics hain
docker compose run --rm video python -m videobot add "Docker kya hai — pehla container"   # apna topic
docker compose run --rm video python -m videobot run           # abhi ek video bana ke upload
docker compose up -d                                           # schedule pe chalta rahe
```
Facebook pe daalna: `docker compose run --rm video python -m videobot approve 1`

Videos `data/videos/` mein save hoti hain: mp4, thumbnail.jpg, aur plan.json (poori script).

## Settings
- `NARRATION_LANG=en` aur `VOICE=en-US-AndrewNeural` → English channel
- `VIDEO_FORMAT=vertical` → Shorts/Reels (1080×1920). Do alag channels/folders chala sakte ho
- `TARGET_MINUTES=4` → video ki lambai
- `SCHEDULE_DAYS=mon,wed,fri`, `SCHEDULE_HOUR_PKT=18`

`edge-tts` Microsoft ki free online voice istemal karta hai. Ye official paid API nahi hai, is liye kabhi band ya slow ho sakti hai. Aisa ho to bata dena, doosra voice option laga dunga.

## Tests
`python -m unittest tests.test_videobot -v` (asli ffmpeg se video banata hai, internet mock)
